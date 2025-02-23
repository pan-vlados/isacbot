import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter

from isacbot.commands import ISACBotCommand
from isacbot.filters import IsAdminFilter


if TYPE_CHECKING:
    from aiogram.types import ChatMemberUpdated, Message

    from isacbot.handlers.admin import AdminsSetType


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.my_chat_member.filter(F.chat.type == ChatType.PRIVATE)
router.message.filter(F.chat.type == ChatType.PRIVATE)


PRIVATE_USERS: set[int] = set()
_LOCK = asyncio.Lock()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER))
async def user_blocked_bot_handler(event: 'ChatMemberUpdated') -> None:
    """Handle events when user block or remove/delete private chat with bot."""
    async with _LOCK:
        PRIVATE_USERS.discard(event.from_user.id)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_MEMBER))
async def user_unblocked_bot_handler(event: 'ChatMemberUpdated') -> None:
    """Handle events when user unblock or add/open private chat with bot."""
    async with _LOCK:
        PRIVATE_USERS.add(event.from_user.id)


@router.message(Command(ISACBotCommand.ADMINS), IsAdminFilter.user_is_administrator)
async def admins_handler(message: 'Message', admins: 'AdminsSetType') -> None:
    await message.answer(
        text='\n'.join(
            f'chat ID: {chat_id}\n\tadmin ID: {"\n\tadmin ID: ".join(map(str, (admins_id if isinstance(admins_id, set) else {admins_id})))}'
            for chat_id, admins_id in admins.items()
        ),
    )
