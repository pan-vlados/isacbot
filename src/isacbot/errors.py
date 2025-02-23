from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError  # noqa: F401
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError  # noqa: F401


class BotSendMessageError(Exception): ...


class ForeignKeyConstraintError(SQLAlchemyError): ...


class PollContextAlreadyExistError(Exception): ...
