from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypedDict,
    Unpack,
    overload,
)


if TYPE_CHECKING:
    import asyncio

    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from isacbot.callbacks import SettingsAction

    class UserStateDataMapping(TypedDict, total=False):
        first_message_id: int  # points on the first dialogue message id
        message_queue: asyncio.LifoQueue[
            Message
        ]  # Allow to get last callback to make popup response.
        callback_called_once: asyncio.Event  # Allow to check if we already answer on the message.
        action: SettingsAction
        callback: CallbackQuery  # Allow to get last message to recreate start dialogue from the beggining.
        rml_owner: bool  # Allow to identify if the user is owner of the Road Map Lock

    class UserContext(FSMContext):
        async def set_data(self, data: UserStateDataMapping) -> None: ...  # type: ignore[override]

        async def get_data(self) -> UserStateDataMapping: ...  # type: ignore[override]

        @overload  # type: ignore[override]
        async def get_value(
            self, key: Literal['message_queue'], default: Any | None = None
        ) -> asyncio.LifoQueue[Message | None] | None: ...

        @overload
        async def get_value(
            self, key: Literal['rml_owner'], default: Any | None = None
        ) -> bool | None: ...

        @overload
        async def get_value(
            self, key: Literal['first_message_id'], default: Any | None = None
        ) -> int | None: ...

        async def get_value(self, key: str, default: Any | None = None) -> Any | None: ...

        async def update_data(  # type: ignore[override]
            self, data: UserStateDataMapping | None = None, **kwargs: Unpack[UserStateDataMapping]
        ) -> UserStateDataMapping: ...
