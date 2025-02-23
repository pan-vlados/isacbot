import enum
import logging
from collections import defaultdict
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypeVar
from zoneinfo import ZoneInfo

from dotenv import find_dotenv, load_dotenv


if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping

    _ChatID = int
    _AdminsID = TypeVar('_AdminsID', bound=set[int] | int)
    AdminsContainerType = MutableMapping[_ChatID, _AdminsID]
    AdminsSetType = AdminsContainerType[set[int]]


class _LogColour(enum.StrEnum):
    WHITE = '\033[37m'
    WHITE_ON_RED_BG = '\033[41m'
    WHITE_ON_BLUE_BG = '\033[44m'
    GRAY_ON_GREEN_BG = '\033[42m'
    GRAY_ON_YELLOW_BG = '\033[43m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    RESET = '\033[0m'


_LOG_FORMAT: Final = '%(asctime)s %(levelname)s %(name)s.%(funcName)s: %(message)s'
_LOG_FORMATS: 'Mapping[int, str]' = {
    logging.DEBUG: f'{_LogColour.WHITE_ON_BLUE_BG}{_LOG_FORMAT}{_LogColour.RESET}',
    logging.INFO: f'{_LogColour.WHITE}{_LOG_FORMAT}{_LogColour.RESET}',
    logging.WARNING: f'{_LogColour.YELLOW}{_LOG_FORMAT}{_LogColour.RESET}',
    logging.ERROR: f'{_LogColour.WHITE_ON_RED_BG}{_LOG_FORMAT}{_LogColour.RESET}',
    logging.CRITICAL: f'{_LogColour.WHITE}{_LOG_FORMAT}{_LogColour.RESET}',
}


class _LevelDependentFormatter(logging.Formatter):
    """Colourfull and level dependent formatter for logger.
    Thanks to: https://stackoverflow.com/a/56944275.
    """

    _formats: 'Mapping[int, str]' = _LOG_FORMATS
    _datefmt: Final = '%Y-%m-%d %H:%M:%S'  # logs without milliseconds

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self._formats.get(record.levelno)
        return logging.Formatter(log_fmt, datefmt=self._datefmt).format(record)


def _level_dependent_formated_stream_handler() -> logging.StreamHandler:
    """FOR DEBUG ONLY. Provide level dependent stream handler with
    colourfull formatter.
    """
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(_LevelDependentFormatter())
    return stream_handler


logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FORMAT,
    datefmt='%Y-%m-%d %H:%M:%S',  # logs without milliseconds
    handlers=[_level_dependent_formated_stream_handler()],
)


load_dotenv(dotenv_path=find_dotenv(filename='.env.prd', raise_error_if_not_found=True))


BOT_TOKEN: Final[str] = getenv('BOT_TOKEN', '')
BOT_USERNAME: Final[str] = getenv('BOT_USERNAME', '')
DB_PATH: Final[Path] = (
    Path(__file__).absolute().parent.parent / 'instance' / getenv('DB_NAME', 'main.db')
)
BOT_ID: Final[int] = int(getenv('BOT_ID') or 0)
BOT_OWNER_ID: Final[int] = int(getenv('BOT_OWNER_ID') or 0)
BOT_MAIN_CHAT_ID: Final[int | None] = (
    int(owner_id) if (owner_id := getenv('BOT_MAIN_CHAT_ID')) else None
)  # can be 0 when no main chat provided
BOT_ADMINS: 'AdminsContainerType[set[int] | int]' = defaultdict(
    set, {BOT_OWNER_ID: BOT_OWNER_ID}
)  # owner personal chat is always added as admin
BOT_TIMEZONE: Final[ZoneInfo] = ZoneInfo('Europe/Moscow')
POLL_DEFAULT_CLOSE_DELAY: Final[int] = int(getenv('POLL_DEFAULT_CLOSE_DELAY') or 3600)
SMTP_MAIL: Final[str] = getenv('SMTP_MAIL', '')
SMTP_PASSWORD: Final[str] = getenv('SMTP_PASSWORD', '')
SMTP_HOSTNAME: Final[str] = getenv('SMTP_HOSTNAME', '')
BOT_LANG_LOCALES_PATH: Final[Path] = Path(__file__).absolute().parent.parent / 'locales'
BOT_LANG_LOCAL_DEFUALT: Final = getenv('BOT_LANG_LOCAL_DEFUALT', 'en')
