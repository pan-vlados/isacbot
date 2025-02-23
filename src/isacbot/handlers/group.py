import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.utils.i18n import gettext as _

from isacbot.filters import ChatTypeIsGroupFilter


if TYPE_CHECKING:
    from aiogram.types import ChatMemberUpdated


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.message.filter(ChatTypeIsGroupFilter)  # Only these groups can use handlers below.


@router.chat_member()
async def somebody_added(event: 'ChatMemberUpdated') -> None:
    if not event.new_chat_member:
        return
    await event.answer(
        text=_('Добро пожаловать, {full_name}! 🫡').format(
            full_name=event.new_chat_member.user.full_name
        )
    )
