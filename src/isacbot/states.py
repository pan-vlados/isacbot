import asyncio
import enum
from functools import cache
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import (
    State,
    StatesGroup,
    any_state,  # noqa: F401
    default_state,  # noqa: F401
)
from aiogram.fsm.storage.base import StorageKey

from isacbot.errors import PollContextAlreadyExistError


if TYPE_CHECKING:
    from asyncio import Lock

    from aiogram.fsm.storage.base import BaseStorage


class PollState(StatesGroup):
    NOT_STARTED = State()
    STARTED = State()
    STARTED_AND_PINNED = State()
    COMPLETED = State()


class UserState(StatesGroup):
    UNAUTHORIZED = State()
    AUTHORIZED = State()
    SETTINGS_CHANGE_REQUESTED = State()


class UserThreadID(enum.IntEnum):
    SETTINGS = enum.auto()
    ROAD_MAP = enum.auto()


class PollContext:
    """Poll context conatin states where `user_id == bot_id` for
    provided `chat_id`. Context of such poll unique for every bot
    in chat.

    Storage is getting from actual storage of any event.
    All implementation is like `FSMContext`.
    This class work only for single poll.
    """

    key: ClassVar[StorageKey | None] = None
    storage: ClassVar['BaseStorage | None'] = None
    _value: ClassVar['FSMContext | None'] = None
    _lock: ClassVar['Lock'] = asyncio.Lock()

    @classmethod
    async def get_state(cls) -> str | None:
        async with cls._lock:
            if cls._value:
                return await cls._value.get_state()
            return None

    @classmethod
    async def get_data(cls) -> dict[str, Any] | None:
        async with cls._lock:
            if cls._value:
                return await cls._value.get_data()
            return None

    @classmethod
    async def set_state(cls, state: str | State | None = None) -> None:
        async with cls._lock:
            if cls._value:
                await cls._value.set_state(state)

    @classmethod
    async def set_data(cls, data: dict[str, Any]) -> None:
        async with cls._lock:
            if cls._value:
                await cls._value.set_data(data)

    @classmethod
    async def set(cls, storage: 'BaseStorage', bot_id: int, chat_id: int) -> None:
        if cls._value:
            raise PollContextAlreadyExistError
        async with cls._lock:
            cls.key = StorageKey(
                bot_id=bot_id,
                chat_id=chat_id,
                user_id=bot_id,
            )
            cls.storage = storage
            cls._value = FSMContext(storage=storage, key=cls.key)

    @classmethod
    async def update_data(
        cls, data: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any] | None:
        if data:
            kwargs.update(data)
        async with cls._lock:
            if cls.storage and cls.key:
                return await cls.storage.update_data(key=cls.key, data=kwargs)
            return None

    @classmethod
    async def get(cls) -> 'FSMContext | None':
        return cls._value

    @classmethod
    async def clear(cls) -> None:
        async with cls._lock:
            if cls._value:
                await cls._value.clear()
                cls._value = None
                cls.key = None
                cls.storage = None


@cache
def get_fsm_context(
    storage: 'BaseStorage',
    bot_id: int,
    chat_id: int,
    user_id: int,
    thread_id: int | UserThreadID | None = None,
) -> FSMContext:
    """Get thread independent FSM context from storage by generated key."""
    return FSMContext(
        storage=storage,
        key=StorageKey(
            bot_id=bot_id,
            chat_id=chat_id,
            user_id=user_id,
            thread_id=thread_id,
        ),
    )
