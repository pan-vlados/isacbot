"""These handlers allow to track some usefull information about changes in
administration privileges, such as:
    - bot added/removed as admin;
    - chat member added/removed as admin.
"""

import asyncio
import enum
import logging
from typing import TYPE_CHECKING

from aiogram import F, Router, html
from aiogram.filters import Command
from aiogram.utils.i18n import gettext as _

from isacbot.commands import ISACBotCommand
from isacbot.config import BOT_ID, BOT_OWNER_ID
from isacbot.filters import (
    ChatMemberDemotedFilter,
    ChatMemberPromotedFilter,
    ChatTypeIsGroupFilter,
)
from isacbot.utils import send_message


if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import (
        Chat,
        ChatMemberAdministrator,
        ChatMemberBanned,
        ChatMemberLeft,
        ChatMemberMember,
        ChatMemberOwner,
        ChatMemberRestricted,
        ChatMemberUpdated,
        Message,
    )

    from isacbot.types_ import AdminsSetType

    type _NewChatMemberType = (
        ChatMemberOwner
        | ChatMemberAdministrator
        | ChatMemberMember
        | ChatMemberRestricted
        | ChatMemberLeft
        | ChatMemberBanned
    )


class _EventType(enum.StrEnum):
    PROMOTION = enum.auto()
    DEMOTION = enum.auto()


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.my_chat_member.filter(ChatTypeIsGroupFilter)
router.chat_member.filter(ChatTypeIsGroupFilter)
router.message.filter(ChatTypeIsGroupFilter)


_LOCK = asyncio.Lock()


def _get_message_text_by_event(
    chat: 'Chat', member: '_NewChatMemberType', event_type: _EventType
) -> str:
    """Additional method allow to get prepared text depends on event attributes."""
    match event_type:
        case _EventType.PROMOTION if member.user.id == BOT_ID:
            logger.info('Bot was added as administrator in chat ID: %d.' % chat.id)
            return _(
                'Бот {full_name} был повышен до Администратора в чате {chat_full_name}!'
            ).format(full_name=html.bold(member.user.full_name), chat_full_name=chat.full_name)
        case _EventType.DEMOTION if member.user.id == BOT_ID:
            logger.info('Bot was removed as administrator in chat ID: %d.' % chat.id)
            return _(
                'Бот {full_name} был понижен до обычного юзера в чате {chat_full_name}!'
            ).format(full_name=html.bold(member.user.full_name), chat_full_name=chat.full_name)
        case _EventType.PROMOTION:
            return _(
                'Пользователь {full_name} был(а) повышен(а) до Администратора в чате {chat_full_name}!'
            ).format(full_name=html.bold(member.user.full_name), chat_full_name=chat.full_name)
        case _EventType.DEMOTION:
            return _(
                'Пользователь {full_name} был(а) понижен(а) до обычного юзера в чате {chat_full_name}!'
            ).format(full_name=html.bold(member.user.full_name), chat_full_name=chat.full_name)


@router.my_chat_member(ChatMemberPromotedFilter)
@router.chat_member(ChatMemberPromotedFilter)
async def admin_promoted_handler(
    event: 'ChatMemberUpdated', bot: 'Bot', admins: 'AdminsSetType'
) -> None:
    member: _NewChatMemberType = event.new_chat_member
    chat: Chat = event.chat
    async with _LOCK:
        admins[chat.id].add(member.user.id)
    await send_message(
        bot=bot,
        chat_id=BOT_OWNER_ID,
        text=_get_message_text_by_event(chat=chat, member=member, event_type=_EventType.PROMOTION),
    )


@router.my_chat_member(ChatMemberDemotedFilter)
@router.chat_member(ChatMemberDemotedFilter)
async def admin_demoted_handler(
    event: 'ChatMemberUpdated', bot: 'Bot', admins: 'AdminsSetType'
) -> None:
    member: _NewChatMemberType = event.new_chat_member
    chat: Chat = event.chat
    async with _LOCK:
        admins[chat.id].discard(member.user.id)
    await send_message(
        bot=bot,
        chat_id=BOT_OWNER_ID,
        text=_get_message_text_by_event(chat=chat, member=member, event_type=_EventType.DEMOTION),
    )


@router.message(Command(ISACBotCommand.FETCH_ADMINS), F.from_user.id == BOT_OWNER_ID)
async def fetch_admins_handler(message: 'Message', bot: 'Bot', admins: 'AdminsSetType') -> None:
    """Get administrators in the open chat where the command was posted."""
    fetched_admins = await bot.get_chat_administrators(chat_id=message.chat.id)
    async with _LOCK:
        admins[message.chat.id].update({admin.user.id for admin in fetched_admins})
    await send_message(
        bot=bot,
        chat_id=BOT_OWNER_ID,
        text=_(
            'Пользователи:\n\t{users_info}\nзагружены как Администраторы в чате {chat_full_name}.'
        ).format(
            users_info=html.bold(
                '</b>\n\t<b>'.join(
                    f'{i}. {admin.user.full_name}' for i, admin in enumerate(fetched_admins, 1)
                )
            ),
            chat_full_name=html.bold(message.chat.full_name),
        ),
    )
