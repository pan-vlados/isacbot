import datetime
import logging
from typing import TYPE_CHECKING, Any, Final

from aiogram import BaseMiddleware, html
from aiogram.types import Message, PollAnswer
from aiogram.utils.i18n import gettext as _

from isacbot.commands import ISACBotCommand
from isacbot.config import BOT_TIMEZONE, POLL_DEFAULT_CLOSE_DELAY
from isacbot.database.operations import (
    add_user,
    get_user,
    poll_already_exist,
)
from isacbot.extensions import i18n
from isacbot.filters import CreatePollCommandFilter
from isacbot.states import PollContext, PollState
from isacbot.utils import N_, Weekday


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import User


logger = logging.getLogger(__name__)


class PollCreationMessageInnerMiddleware(BaseMiddleware):
    """Inner middleware for all messages allows to verify it's a poll
    day or not and check if the poll exists in the database.

    Since this middleware is bound to a "Message", it affects all such
    events. This means that all communications will go through this
    middleware when the last one is connected to the router.
    """

    poll_close_delay: int = POLL_DEFAULT_CLOSE_DELAY  # default poll close dealt time in seconds
    _len_command_args: Final = 2

    @property
    def is_pool_day(self) -> bool:
        return Weekday.today() == Weekday.MONDAY

    async def get_poll_close_delay_for_event(self, event: Message) -> int:
        """If the command text specifies two arguments, calculate the open time period in
        seconds to schedule closing of the poll. The open period must be a string
        representing time in ISO 8601 format.

        By default:
            - Return poll close delay in seconds.
            - Answer to message sender with error.
        """
        if len(command_args := ((event.text or '').split(maxsplit=1))) == self._len_command_args:
            command, open_period = command_args
            try:
                close_time = datetime.time.fromisoformat(open_period)
            except ValueError:
                logger.debug(
                    'Incorrect open period argument provided: %s. Expected argument in ISO 8601 format.'
                    % open_period
                )
                await event.answer(
                    text=i18n.gettext(
                        N_(
                            '⚠️ Неправильный формат команды. Пример:\n/{command} <time in ISO 8601 format>\n\nУстановлено стандартное время закрытия опроса через {default_close_time}.'
                        )
                    ).format(
                        command=ISACBotCommand.CREATE_POLL.value,
                        default_close_time=f'{datetime.timedelta(seconds=self.poll_close_delay)!s}',
                    ),
                    parse_mode=None,
                )
            else:
                return int(
                    datetime.timedelta(
                        hours=close_time.hour, minutes=close_time.minute, seconds=close_time.second
                    ).total_seconds()
                )
        return self.poll_close_delay

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[Message, dict[str, Any]], Awaitable[Any]]',
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.bot:
            return None

        # Check for the correct command in message.
        if not (await CreatePollCommandFilter(message=event, bot=event.bot)):
            logger.debug('The message was called with the following text `%s`.' % event.text)
            # All messages will pass through this tiny bottleneck.
            return await handler(event, data)

        poll_date: Final[datetime.date] = event.date.astimezone(tz=BOT_TIMEZONE).date()
        poll_context: PollContext = data['poll_context']
        if (await poll_context.get_state()) or (await poll_already_exist(date=poll_date)):
            logger.debug('Poll already exist.')
            await event.answer(
                text=i18n.gettext(N_('⚠️ Опрос на дату {poll_date} уже сформирован.')).format(
                    poll_date=f'{poll_date:%d.%m.%Y}'
                )
            )
            return None

        if not self.is_pool_day:
            await event.answer(
                i18n.gettext(N_('⚠️ Опрос выполняется только по понедельникам.')), show_alert=True
            )
            return None

        data['poll_close_delay'] = await self.get_poll_close_delay_for_event(event=event)
        data['poll_date'] = poll_date
        return await handler(event, data)


class PollAnswerOuterMiddleware(BaseMiddleware):
    """Outer middleware to process `PollAnswer` event before handlers."""

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[PollAnswer, dict[str, Any]], Awaitable[Any]]',
        event: PollAnswer,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, PollAnswer):  # in case of error
            logger.warning(
                'Incorrect event type called: %s. Expected type %s.' % (type(event), PollAnswer)
            )
            return await handler(event, data)
        # Poll verification has begun. This state is also created in the filter,
        # but I leave it here in case we miss it later or there are some state
        # errors.
        poll_context: PollContext = data['poll_context']
        if (await poll_context.get_state()) not in (
            PollState.STARTED,
            PollState.STARTED_AND_PINNED,
        ):
            logger.debug('Poll context has incorrect state: %s' % poll_context)
            return None

        # Check the poll context data provided.
        if not (poll_context_data := await poll_context.get_data()):
            logger.debug("Poll context doesn't contain data.")
            return None

        # Check the poll message provided.
        poll_message: Message | None = poll_context_data.get('poll_message')
        if not poll_message or not poll_message.poll:
            logger.debug("Poll isn't created or user tried to answer an old poll.")
            return None

        # Check user response to an old poll.
        if event.poll_id != poll_message.poll.id:
            logger.debug('User answered an old poll.')
            return None

        # This path can be reached when a user tries to withdraw their vote from
        # a poll. Also, unanswered options will be skipped, as well as when a
        # user provides a response to an old poll.
        if not event.option_ids:
            logger.debug("User retracted his vote or didn't provide an answer for the poll.")
            return None

        # Check user existence in poll message.
        user: User | None = event.user
        if not user:
            logger.debug('No user found in poll message.')
            return None

        if not event.bot:
            return None

        # Check for user existence in database.
        if not (db_user := await get_user(user_id=user.id)):
            logger.debug('User is not registered in the database.')
            # Register the user even though the user is anonymous.
            await add_user(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
            )
        if not db_user or not db_user.displayname:
            await poll_message.answer(
                text=_(
                    '⚠️ Уважаемый(ая) {full_name}, для регистрации воспользуйтесь командой {command} в приватном чате со мной.'
                ).format(
                    full_name=html.bold(user.full_name),
                    command=html.link(
                        value='/start',
                        link=f'https://t.me/{(await event.bot.get_me()).username}?start=start',
                    ),
                )
            )

        logger.debug('Provided correct poll answer to handler.')

        data['chat_id'] = (
            poll_message.chat.id
        )  # The PollAnswer update does not include a chat variable in the response data by default.
        return await handler(event, data)
