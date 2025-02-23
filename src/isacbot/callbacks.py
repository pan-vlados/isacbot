import enum

from aiogram.filters.callback_data import CallbackData

from isacbot.utils import N_


class StartAction(enum.StrEnum):
    START = N_('Старт 🚀')
    CREATE_POLL = N_('📊 [Создать опрос]')
    SEND_POLL_RESULT = N_('📨 [Отправить результат опроса]')
    SETTINGS = N_('⚙️ Настройки')
    HELP = N_('❓ Помощь')


class RoadMapAction(enum.StrEnum):
    ACQUIRE = N_('🔒 Взять ДК')
    RELEASE = N_('🔓 Отпустить ДК')
    WAIT_RELEASED = N_('↩️ Встать в очередь ДК')


class DefaultAction(enum.StrEnum):
    BACK = N_('🔙 Назад')


class SettingsAction(enum.StrEnum):
    CHANGE_DISPLAYNAME = N_('👤 [Изменить имя]')
    CHANGE_EMAIL = N_('📧 [Изменить email]')


class SendPollCallback(CallbackData, prefix='send-poll'):
    poll_id: int
    date: str


class StartCallback(CallbackData, prefix='start'):
    action: StartAction


class SettingsCallback(CallbackData, prefix='settings'):
    action: SettingsAction


class BackButtonCallback(CallbackData, prefix='back'):
    action: DefaultAction = DefaultAction.BACK


class RoadMapCallback(CallbackData, prefix='road-map'):
    action: RoadMapAction
