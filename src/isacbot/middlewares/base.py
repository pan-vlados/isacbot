"""All base middleware for the entire application."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import CallbackQuery, Message, PollAnswer

from isacbot.filters import ChatTypeIsGroupFilter
from isacbot.states import get_fsm_context


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject

    from isacbot.types_ import UserContext


logger = logging.getLogger(__name__)


class DelayMiddleware(BaseMiddleware):
    """Delay before executing the handler by sleeping specified `sleep` time
    provided in seconds.
    """

    def __init__(self, delay: int) -> None:
        self.delay = delay

    async def __call__(
        self,
        handler: 'Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]',
        event: 'TelegramObject',
        data: dict[str, Any],
    ) -> Any:
        await asyncio.sleep(self.delay)
        result = await handler(event, data)
        logger.debug('Handler was delayed by %d seconds.' % self.delay)
        return result


class EventFromUserMiddleware(BaseMiddleware):
    """Drop an update event not sent from a user.
    If the event was from a user, the middleware provided the handler with a `user_id`
    and `language_code`.
    """

    async def __call__(
        self,
        handler: 'Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]',
        event: 'TelegramObject',
        data: dict[str, Any],
    ) -> Any:
        if not (user := data.get('event_from_user')):
            return None
        data['user_id'] = user.id
        data['language_code'] = user.language_code
        return await handler(event, data)


class BlockCallbackFromOldMessageMiddleware(BaseMiddleware):
    """Oter middleware allows you to block callbacks from old messages to be registered
    when the user tries to interact with the old inline keyboard buttons.

    Also update the `first_message_id` in the `FSMContext` user state when the user
    opens a new dialog by entering any command.
    """

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]]',
        event: 'CallbackQuery',
        data: dict[str, Any],
    ) -> Any:
        if not event.message:
            return None

        state: UserContext = data['state']
        if not (
            first_message_id := await state.get_value('first_message_id')
        ):  # dialogue was called first tome
            return await handler(event, data)

        message_id: int = event.message.message_id
        if first_message_id > message_id:
            logger.debug('Called callback from an old message id: %d.' % message_id)
            return None

        if first_message_id < message_id:
            logger.debug('Called callback from an new message id: %d.' % message_id)
            await state.update_data(first_message_id=message_id)

        return await handler(event, data)


class UnhandledUpdatesLoggerMiddleware(BaseMiddleware):
    """Allow to check all unhandled events."""

    async def __call__(
        self,
        handler: 'Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]',
        event: 'TelegramObject',
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        if result is UNHANDLED:
            logger.warning(msg='Unhandled update `%s`' % type(event))


class SwapUserStateFromPrivateChatOuterMiddleware(BaseMiddleware):
    """Allow to swap state from user private chats into handlers."""

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[Message| PollAnswer, dict[str, Any]], Awaitable[Any]]',
        event: Message | PollAnswer,
        data: dict[str, Any],
    ) -> Any:
        if not event.bot:
            return None

        if not (
            isinstance(event, Message) and (await ChatTypeIsGroupFilter(message=event))
        ) or isinstance(event, PollAnswer):
            return await handler(event, data)

        # The operations below require a valid `state` argument belonging
        # to the event state user. This swap allows to check the authorization
        # status and cancel calls from unauthorized users.
        user_id = data['user_id']
        state: UserContext = data['state']
        data['state'] = get_fsm_context(
            storage=state.storage,
            bot_id=event.bot.id,
            chat_id=user_id,
            user_id=user_id,
            thread_id=None,
        )

        data['raw_state'] = await data['state'].get_state()
        return await handler(event, data)
