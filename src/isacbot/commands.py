import enum
from typing import TYPE_CHECKING

from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)

from isacbot.callbacks import StartAction
from isacbot.config import BOT_OWNER_ID
from isacbot.utils import N_


if TYPE_CHECKING:
    from aiogram.utils.i18n import I18n

    _ChatAdministratorsCommands = tuple[list[BotCommand], BotCommandScopeChat]
    _AllPrivateChatsCommands = tuple[list[BotCommand], BotCommandScopeAllPrivateChats]
    _AllChatAdministratorsCommands = tuple[list[BotCommand], BotCommandScopeAllChatAdministrators]
    _AllGroupChatsCommands = tuple[list[BotCommand], BotCommandScopeAllGroupChats]
    _ScopedBotCommands = tuple[
        _ChatAdministratorsCommands,
        _AllPrivateChatsCommands,
        _AllChatAdministratorsCommands,
        _AllGroupChatsCommands,
    ]


class ISACBotCommand(enum.StrEnum):
    START = 'start'
    ADMINS = 'admins'
    CHECKIN = 'checkin'
    CREATE_POLL = 'create_poll'
    FETCH_ADMINS = 'fetch_admins'
    ROAD_MAP = 'road_map'


# About commands scope [see](https://core.telegram.org/bots/api#determining-list-of-commands).
def get_commands(i18n: 'I18n') -> '_ScopedBotCommands':
    START = BotCommand(command=ISACBotCommand.START, description=StartAction.START)
    CREATE_POLL = BotCommand(
        command=ISACBotCommand.CREATE_POLL, description=StartAction.CREATE_POLL
    )
    ROAD_MAP = BotCommand(
        command=ISACBotCommand.ROAD_MAP, description=i18n.gettext(N_('🛣️ [Дорожная карта]'))
    )
    return (
        (
            [
                START,
                CREATE_POLL,
                BotCommand(
                    command=ISACBotCommand.ADMINS,
                    description=i18n.gettext(N_('Показать администраторов')),
                ),
            ],
            BotCommandScopeChat(chat_id=BOT_OWNER_ID),  # owner chat
        ),
        ([START], BotCommandScopeAllPrivateChats()),
        (
            [
                BotCommand(
                    command=ISACBotCommand.FETCH_ADMINS,
                    description=i18n.gettext(N_('Обновить администраторов')),
                ),
                CREATE_POLL,
                ROAD_MAP,
            ],
            BotCommandScopeAllChatAdministrators(),
        ),
        ([ROAD_MAP], BotCommandScopeAllGroupChats()),
    )
