from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from isacbot._typing import UserContext


class SettingsCallbackQueryMiddleware(BaseMiddleware):
    """Inner middleware to apply additional arguments for settings callback."""

    async def __call__(  # type: ignore[override]
        self,
        handler: 'Callable[[CallbackQuery, dict[str, Any]], Awaitable[Any]]',
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery) or not isinstance(event.message, Message):
            return None

        state: UserContext = data['state']
        if (message_queue := await state.get_value('message_queue')) is None:
            return None

        data['message_queue'] = message_queue
        data['message'] = event.message
        return await handler(event, data)
