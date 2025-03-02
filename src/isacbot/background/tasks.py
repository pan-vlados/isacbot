from typing import TYPE_CHECKING, Any

from isacbot.commands import ISACBotCommand
from isacbot.extensions import bot, dp
from isacbot.handlers import poll
from isacbot.middlewares.poll import PollCreationMessageOuterMiddleware
from isacbot.states import PollContext, get_fsm_context


if TYPE_CHECKING:
    from aiogram.types import Message


async def create_poll_in_chat(chat_id: int) -> None:
    """Create a poll in the chat using bot.

    Fully emulate the creation of a poll by a user using bot.
    """

    async def _crete_poll_handler_coro(message: 'Message', data: dict[str, Any]) -> None:
        """Async function to provide `crete_poll_handler` as the callabale coroutine."""
        await poll.crete_poll_handler(message, **data)

    message: Message = await bot.send_message(
        chat_id=chat_id,
        text=f'/{ISACBotCommand.CREATE_POLL}',
    )
    await PollCreationMessageOuterMiddleware().__call__(
        handler=_crete_poll_handler_coro,
        event=message,
        data={
            'bot': bot,
            'poll_context': PollContext,
            'state': get_fsm_context(
                storage=dp.storage,
                bot_id=bot.id,
                chat_id=message.chat.id,
                user_id=bot.id,
            ),
        },
    )
