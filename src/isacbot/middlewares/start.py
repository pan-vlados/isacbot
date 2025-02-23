from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import Message


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery


class CallbackMessageProviderMiddleware(BaseMiddleware):
    """Inner middleware to provide callback message argument into handler."""

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]]',
        event: 'CallbackQuery',
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event.message, Message):
            return await handler(event, data)
        data['callback_message'] = event.message
        return await handler(event, data)
