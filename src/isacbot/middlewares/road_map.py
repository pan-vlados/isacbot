from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import Message


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class RoadMapInputMessageDeleteInnerMiddleware(BaseMiddleware):
    """Inner middleware to keep chat clean by deleting chat messages."""

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[Message, dict[str, Any]], Awaitable[Any]]',
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        await event.delete()
        await handler(event, data)
