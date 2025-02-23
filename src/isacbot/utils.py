import asyncio
import datetime
import enum
import logging
from typing import TYPE_CHECKING

from isacbot.config import BOT_TIMEZONE
from isacbot.errors import TelegramForbiddenError


if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import Message


logger = logging.getLogger(__name__)


def N_(str_: str) -> str:  # noqa: N802  # https://docs.python.org/3/library/gettext.html#deferred-translations
    """Deffer text translation to create .pot content for localization."""
    return str_


async def send_message(bot: 'Bot', chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except TelegramForbiddenError:
        logger.exception(
            "Can't send message to %d. Please check that this user have got opened dialogue with bot."
            % chat_id
        )
    except Exception:
        logger.exception("Can't send message to %d." % chat_id)


async def unpin_poll(pinned_message: 'Message', bot: 'Bot') -> None:
    await bot.unpin_chat_message(
        chat_id=pinned_message.chat.id,
        message_id=pinned_message.message_id,
    )


async def stop_poll(pinned_message: 'Message', bot: 'Bot') -> None:
    await bot.stop_poll(pinned_message.chat.id, pinned_message.message_id)


class AsyncSet:
    __slots__ = ('_lock', '_set')

    def __init__(self) -> None:
        self._set: set[int] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def add(self, item: int) -> None:
        async with self._lock:
            self._set.add(item)

    async def remove(self, item: int) -> None:
        async with self._lock:
            self._set.remove(item)

    async def contains(self, item: int) -> bool:
        async with self._lock:
            return item in self._set

    async def is_empty(self) -> bool:
        async with self._lock:
            return bool(self._set)


class Weekday(enum.IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    @classmethod
    def today(cls) -> 'Weekday':
        return Weekday(datetime.datetime.now(tz=BOT_TIMEZONE).date().isoweekday())
