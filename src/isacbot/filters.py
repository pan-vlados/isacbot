import logging
from typing import TYPE_CHECKING, Literal

from aiogram.enums import ChatType
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.filters.chat_member_updated import (
    IS_ADMIN,
    KICKED,
    LEFT,
    MEMBER,
    RESTRICTED,
    ChatMemberUpdatedFilter,
)
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from aiogram.utils.chat_member import ADMINS, MEMBERS
from email_validator import EmailNotValidError, validate_email

from isacbot.commands import ISACBotCommand
from isacbot.states import UserState


if TYPE_CHECKING:
    from collections.abc import Collection

    from aiogram import Bot
    from aiogram.types import Chat

    from isacbot._typing import AdminsSetType


logger = logging.getLogger(__name__)


# Chat admin transitions. For additional info [see](https://docs.aiogram.dev/en/stable/dispatcher/filters/chat_member_updated.html#chatmemberupdated)
IS_NOT_ADMIN = KICKED | LEFT | RESTRICTED | MEMBER  # there is no this type in aiogram types
PROMOTED_TRANSITION = IS_NOT_ADMIN >> IS_ADMIN
DEMOTED_TRANSITION = IS_NOT_ADMIN << IS_ADMIN


class ChatTypeFilter(BaseFilter):
    """Filter for specific chat type."""

    chat_type: 'Collection[ChatType]'

    def __init__(self, chat_type: 'Collection[ChatType]') -> None:
        self.chat_type = chat_type

    async def __call__(self, message: 'Message') -> bool:
        return message.chat.type in self.chat_type


class IsAdminFilter(BaseFilter):
    """Filter for admins only.
    Assume the user is admin for his PRIVATE chat with bot.

    There are two ways of use:
        1. `IsAdminFilter.user_is_administrator` - return `bool`,
        static check in set of admins
        2. `IsAdminFilter.__call__(...)` - statick check in set of
        admins and dynamic check for member rights in chat.
    """

    @staticmethod
    async def user_is_administrator(
        bot: 'Bot', chat_id: int, user_id: int, admins: 'AdminsSetType'
    ) -> bool:
        return user_id in admins[chat_id] or isinstance(
            (await bot.get_chat_member(chat_id=chat_id, user_id=user_id)), ADMINS
        )

    async def __call__(  # type: ignore[override]
        self,
        event: Message | CallbackQuery | ChatMemberUpdated,
        bot: 'Bot',
        user_id: int,
        admins: 'AdminsSetType',
    ) -> bool:
        chat: Chat
        if isinstance(event, Message | ChatMemberUpdated):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat
        else:
            return False

        return await self.user_is_administrator(
            bot=bot, chat_id=chat.id, user_id=user_id, admins=admins
        )


class ChatMemberFilter(BaseFilter):
    """Filter for members only."""

    async def __call__(self, message: 'Message', bot: 'Bot', user_id: int) -> bool:
        return isinstance((await bot.get_chat_member(message.chat.id, user_id)), MEMBERS)


def validate_email_filter(message: 'Message') -> dict[Literal['email'], str] | None:
    if not message.text:
        return None
    try:
        return {'email': validate_email(message.text, timeout=2).normalized.lower()}
    except EmailNotValidError:
        return None


class IsMemberFilter(BaseFilter):
    async def __call__(
        self, event: Message | CallbackQuery | ChatMemberUpdated, bot: 'Bot', user_id: int
    ) -> bool:
        chat: Chat
        if isinstance(event, Message | ChatMemberUpdated):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat
        else:
            return False
        return isinstance((await bot.get_chat_member(chat.id, user_id)), MEMBERS)


ChatTypeIsGroupFilter = ChatTypeFilter(chat_type=(ChatType.GROUP, ChatType.SUPERGROUP))
ChatMemberPromotedFilter = ChatMemberUpdatedFilter(member_status_changed=PROMOTED_TRANSITION)
ChatMemberDemotedFilter = ChatMemberUpdatedFilter(member_status_changed=DEMOTED_TRANSITION)
CreatePollCommandFilter = Command(ISACBotCommand.CREATE_POLL)
UserIsAuthorizedFilter = StateFilter(UserState.AUTHORIZED, UserState.SETTINGS_CHANGE_REQUESTED)
