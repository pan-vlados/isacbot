import asyncio
import enum
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, ClassVar

from aiogram import F, Router, html
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import lazy_gettext as __

from isacbot.callbacks import RoadMapAction
from isacbot.commands import ISACBotCommand
from isacbot.filters import ChatTypeIsGroupFilter, IsAdminFilter
from isacbot.keyboards import road_map_kb
from isacbot.middlewares import (
    RoadMapInputMessageDeleteInnerMiddleware,
    SwapUserStateFromPrivateChatOuterMiddleware,
)
from isacbot.utils import AsyncSet


if TYPE_CHECKING:
    from aiogram.types import Message, User

    from isacbot.types_ import UserContext


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.message.filter(
    ChatTypeIsGroupFilter,  # UserIsAuthorizedFilter
)  # Only these groups can use handlers below.
router.message.outer_middleware(SwapUserStateFromPrivateChatOuterMiddleware())
router.message.middleware(
    RoadMapInputMessageDeleteInnerMiddleware()
)  # all messages afte rfilter will be delted in chat


class _RMLState(enum.Enum):
    LOCKED = enum.auto()
    RELEASED = enum.auto()
    ALREADY_LOCKED = enum.auto()
    ALREADY_RELEASED = enum.auto()
    ALREADY_IN_WAITERS = enum.auto()
    ACQUIRED = enum.auto()


class _RML:
    """Road Map Lock (_RML). Acquire/release road map lock."""

    owner: ClassVar['User | None'] = None
    waiters: ClassVar[AsyncSet] = AsyncSet()
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _condition: ClassVar[asyncio.Condition] = asyncio.Condition()

    @classmethod
    async def acquire(cls, owner: 'User') -> _RMLState:
        if cls.is_locked():
            if not cls.owner:
                raise ValueError  # no owner
            if cls.owner == owner:
                return _RMLState.ALREADY_LOCKED
            return _RMLState.LOCKED
        await cls._lock.acquire()
        cls.owner = owner
        return _RMLState.ACQUIRED

    @classmethod
    def is_locked(cls) -> bool:
        return cls._lock.locked()

    @classmethod
    async def wait_until_notified(cls, owner: 'User') -> AsyncGenerator[_RMLState | None]:
        """Block coroutine inside method until condition is achived and coroutine
        is notified.

        The asynchronous generator is only used to react to various _RML states and
        perform operations at the end of a certain state. This generator can only
        be called twice (allows any operation to be performed between calls).
        """
        if not cls.is_locked():
            yield _RMLState.ALREADY_RELEASED
        elif await cls.waiters.contains(item=owner.id):
            yield _RMLState.ALREADY_IN_WAITERS
        elif cls.owner == owner:
            yield _RMLState.ALREADY_LOCKED
        else:
            async with cls._condition:
                await cls.waiters.add(owner.id)
                logger.debug('User %d added as road map waiter.' % owner.id)
                yield _RMLState.RELEASED
                await cls._condition.wait_for(
                    lambda: not cls.is_locked()
                )  # this is the point where await is blocking coroutine
                await cls.waiters.remove(owner.id)
                logger.debug('Waiter %d recieved road map flow.' % owner.id)
        yield None

    @classmethod
    async def release(cls) -> _RMLState:
        """Release and notify next _RML waiter."""
        if not cls.is_locked():
            return _RMLState.ALREADY_RELEASED
        cls._lock.release()
        cls.owner = None
        async with cls._condition:
            cls._condition.notify()
        return _RMLState.RELEASED


@router.message(Command(ISACBotCommand.ROAD_MAP))
async def road_map_handler(message: 'Message', language_code: str) -> None:
    await message.answer(
        text=_('Состояние дорожной карты: {rml_status}').format(
            rml_status=html.bold(
                _('🔒 Заблокирована') if _RML.is_locked() else _('🔓 Разблокирована')
            )
        ),
        reply_markup=road_map_kb(is_acquired=True, language_code=language_code),
    )


@router.message(F.text.in_((__(RoadMapAction.ACQUIRE), RoadMapAction.ACQUIRE)))
async def acquire_road_map_message_handler(
    message: 'Message', state: 'UserContext', language_code: str
) -> None:
    if not (user := message.from_user):
        return

    match await _RML.acquire(owner=user):
        case _RMLState.ALREADY_LOCKED:
            _text = _('⚠️ ДК уже предоставлена Вам {full_name}.').format(
                full_name=html.bold(user.full_name)
            )
        case _RMLState.LOCKED if _RML.owner:
            _text = _('⛔ ДК заблокирована пользователем {full_name}.').format(
                full_name=html.bold(_RML.owner.full_name)
            )
        case _RMLState.ACQUIRED:
            _text = _('✅ ДК предоставлена пользователю, {full_name}.').format(
                full_name=html.bold(user.full_name)
            )
            await state.update_data(rml_owner=True)
    await message.answer(
        text=_text,
        reply_markup=road_map_kb(is_acquired=False, language_code=language_code),
    )


@router.message(F.text.in_((__(RoadMapAction.WAIT_RELEASED), RoadMapAction.WAIT_RELEASED)))
async def wait_road_map_released_message_handler(
    message: 'Message', state: 'UserContext', language_code: str
) -> None:
    if not (user := message.from_user):
        return

    wait_generator = _RML.wait_until_notified(owner=user)
    match await anext(wait_generator):
        case _RMLState.ALREADY_RELEASED:  # go to acquire road map
            await acquire_road_map_message_handler(
                message=message, state=state, language_code=language_code
            )
        case _RMLState.ALREADY_IN_WAITERS:
            await message.answer(text=_('⚠️ Вы уже находитесь в очереди ожидания.'))
        case _RMLState.ALREADY_LOCKED:
            await message.answer(
                text=_('⚠️ ДК уже заблокирована Вами {full_name}.').format(
                    full_name=html.bold(user.full_name)
                ),
                reply_markup=road_map_kb(is_acquired=False, language_code=language_code),
            )
        case _RMLState.RELEASED:
            await message.answer(
                text=_('⏰ Пользователь {full_name} встал в очередь ДК.').format(
                    full_name=html.bold(user.full_name)
                )
            )
            # Here is the implicit wait operation in the second `__anext__`. The
            # generator will not exit until the coroutine is notified if and only
            # if _RML is in the `_RMLState.RELEASED` state.
            await anext(wait_generator)
            await acquire_road_map_message_handler(
                message=message, state=state, language_code=language_code
            )


@router.message(F.text.in_((__(RoadMapAction.RELEASE), RoadMapAction.RELEASE)), IsAdminFilter())
async def release_road_map_message_handler(
    message: 'Message', state: 'UserContext', *, is_admin: bool, language_code: str
) -> None:
    if not _RML.is_locked():
        return

    if not (await state.get_value('rml_owner') or is_admin):
        await message.answer(
            text=_('⛔ Вы не можете разблокировать ДК заблокированную другим пользователем.'),
            reply_markup=road_map_kb(is_acquired=True, language_code=language_code),
        )
        return

    match await _RML.release():
        case _RMLState.ALREADY_RELEASED:
            return
        case _RMLState.RELEASED:
            await state.update_data(rml_owner=False)

    if await _RML.waiters.is_empty():
        return
    await message.answer(
        text=_('🆓 ДК разблокирована.'),
        reply_markup=road_map_kb(is_acquired=True, language_code=language_code),
    )


# TODO: _RML waiters list status ordered
