from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.utils.i18n import I18n

from isacbot.config import (
    BOT_LANG_LOCAL_DEFUALT,
    BOT_LANG_LOCALES_PATH,
    BOT_TOKEN,
    DB_PATH,
    SMTP_HOSTNAME,
    SMTP_MAIL,
    SMTP_PASSWORD,
)
from isacbot.database.database import Database
from isacbot.service.sendmail import SMTPClient


db = Database(path=DB_PATH)
dp = Dispatcher(storage=MemoryStorage(), fsm_strategy=FSMStrategy.USER_IN_CHAT)  # TODO: Redis
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
mail_client = SMTPClient(
    username=SMTP_MAIL,
    password=SMTP_PASSWORD,
    hostname=SMTP_HOSTNAME,
)
i18n = I18n(path=BOT_LANG_LOCALES_PATH, default_locale=BOT_LANG_LOCAL_DEFUALT, domain='messages')
