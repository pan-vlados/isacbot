import asyncio
import logging
from typing import TYPE_CHECKING, Final

from aiogram import F, Router
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.types import Message

from isacbot.background.utils import create_delayed_background_task
from isacbot.database.operations import (
    add_answer,
    create_poll,
    update_poll_status,
)
from isacbot.database.utils import PollOptions, PollStatus
from isacbot.extensions import i18n
from isacbot.filters import CreatePollCommandFilter, IsAdminFilter
from isacbot.middlewares import (
    PollAnswerOuterMiddleware,
    PollCreationMessageInnerMiddleware,
    SwapUserStateFromPrivateChatOuterMiddleware,
)
from isacbot.states import PollState
from isacbot.utils import N_, stop_poll, unpin_poll


if TYPE_CHECKING:
    import datetime
    from collections.abc import Mapping

    from aiogram import Bot
    from aiogram.types import PollAnswer

    from isacbot._typing import UserContext
    from isacbot.states import PollContext


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.poll_answer.outer_middleware(PollAnswerOuterMiddleware())
router.poll_answer.outer_middleware(
    SwapUserStateFromPrivateChatOuterMiddleware()
)  # Allow to use information about authorization for specific user from private chat
router.message.middleware(PollCreationMessageInnerMiddleware())


_POLL_OPTIONS: 'Mapping[int, PollOptions]' = dict(enumerate(PollOptions))


# The following events represent the poll end and poll unpinned status when set:
_POLL_END = asyncio.Event()
_POLL_UNPINNED = asyncio.Event()


async def _SET_POLL_END() -> None:  # noqa: N802
    """Async function to provide `_POLL_END.set` as the callabale coroutine."""
    _POLL_END.set()


@router.message(
    CreatePollCommandFilter,
    IsAdminFilter(),
)
async def crete_poll_handler(
    message: Message,
    bot: 'Bot',
    state: 'UserContext',
    poll_context: 'PollContext',
    poll_date: 'datetime.date',
    poll_close_delay: int,
) -> None:
    """Unregistered users can create a poll by calling this handler, but these
    users are always verified using `IsAdminFilter`, so it doesn't matter.
    """
    await poll_context.clear()
    question: Final[str] = i18n.gettext(N_('💻 Где Вы сегодня {poll_date}?')).format(
        poll_date=f'{poll_date:%d.%m.%Y}'
    )
    message = await bot.send_poll(
        chat_id=message.chat.id,
        question=question,
        options=[i18n.gettext(option.value) for option in _POLL_OPTIONS.values()],
        type='regular',
        is_anonymous=False,
        allows_multiple_answers=False,
        disable_notification=False,
        protect_content=True,
        reply_markup=None,
    )
    if not message.poll:
        return

    await poll_context.set(
        storage=state.storage,
        bot_id=bot.id,
        chat_id=message.chat.id,
    )
    poll_id = int(message.poll.id)
    await create_poll(
        poll_id=poll_id, question=question, date=poll_date, status=PollStatus.STARTED
    )  # create poll in database
    await poll_context.set_state(PollState.STARTED)
    # Pin message and context for the poll.
    if await message.pin(disable_notification=False):
        # There is an issue: the pinned message after the `message.pin()` method
        # does not receive any FSM states from the poll message because the user
        # ID of the poll creator is not equal to the user ID of the pinned message.
        # In the first case it is a user, in the second it is a bot. That's why we
        # need to manually create a `StorageKey` and provide some filters to intercept
        # the pinned message with the corresponding FSM state. This manually created
        # `StorageKey` placed inside `poll_context` variable and initialized before handler.
        await poll_context.set_state(PollState.STARTED_AND_PINNED)
    await poll_context.update_data(poll_message=message)

    await create_delayed_background_task(task=_SET_POLL_END, delay=poll_close_delay)
    logger.info('Poll started.')

    # Wait until the end of the poll.
    await _POLL_END.wait()
    await stop_poll(pinned_message=message, bot=bot)
    logger.info('Poll finished.')
    await update_poll_status(poll_id=poll_id, status=PollStatus.COMPLETED)
    # Wait until the poll is unpinned, then clear both events.
    await _POLL_UNPINNED.wait()
    _POLL_END.clear()
    _POLL_UNPINNED.clear()

    await poll_context.clear()


@router.message(
    F.content_type == ContentType.PINNED_MESSAGE,
    StateFilter(PollState.STARTED, PollState.STARTED_AND_PINNED),
)
async def pin_handler(message: Message, bot: 'Bot') -> None:
    """Pin handler user state from poll_message_context evaluated above in
    crete_poll_handler. The initialization of this handler is the point where
    `message.pin()` called. This handler use bot context, cause the message
    provided by function call is a service message.
    Only here we can get pinned message and perform operations on it.
    """
    if not isinstance(message.pinned_message, Message):
        return
    await _POLL_END.wait()  # wait until end of the poll
    await unpin_poll(pinned_message=message.pinned_message, bot=bot)
    logger.info('Poll unpinned.')
    _POLL_UNPINNED.set()


@router.poll_answer()
async def poll_answer_handler(poll_answer: 'PollAnswer', user_id: int) -> None:
    """Gandler start after user choosed any answer."""
    if _POLL_END.is_set():
        return
    option = _POLL_OPTIONS[poll_answer.option_ids[0]]  # no multiple answers, return first
    await add_answer(user_id=user_id, poll_id=int(poll_answer.poll_id), answer=option)
