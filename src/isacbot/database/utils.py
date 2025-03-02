import datetime
import enum
from typing import TYPE_CHECKING, Annotated, Any, ParamSpec, TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import mapped_column

from isacbot.config import BOT_TIMEZONE
from isacbot.utils import N_


if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Connection

    _P = ParamSpec('_P')
    _T = TypeVar('_T', bound=Any)


class PollOptions(enum.StrEnum):
    REMOTELY = N_('Удаленно')
    IN_OFFICE = N_('В офисе')
    ON_SICK = N_('На больничном')
    ON_VACATION_RU = N_('В отпуске (РФ)')
    ON_VACATION = N_('В отпуске (не РФ)')
    VALID_REASON = N_('Отсутствую по уважительной причине')
    DEFAULT = N_('Неизвестно')


class PollStatus(enum.Enum):
    NOT_STARTED = enum.auto()
    STARTED = enum.auto()
    COMPLETED = enum.auto()


Timestamp = Annotated[
    datetime.datetime,
    mapped_column(
        sa.DateTime(timezone=False),
        nullable=False,
        default=datetime.datetime.now(tz=BOT_TIMEZONE),
        server_default=sa.func.now(),
    ),
]
Datestamp = Annotated[
    datetime.date,
    mapped_column(sa.Date, nullable=False, server_default=sa.func.current_date()),
]
PollOptionsType = Annotated[
    PollOptions,
    mapped_column(
        sa.Enum(
            PollOptions,
            create_constraint=True,
            values_callable=lambda x: [v.value for v in x],
        ),
        server_default=PollOptions.DEFAULT,
    ),
]
PollStatusType = Annotated[
    PollStatus,
    mapped_column(
        sa.Enum(
            PollStatus,
            create_constraint=True,
        ),
        default=PollStatus.NOT_STARTED.name,
        server_default=PollStatus.NOT_STARTED.name,
    ),
]
SmallIntpk = Annotated[int, mapped_column(sa.SmallInteger, primary_key=True)]
BigIntpk = Annotated[int, mapped_column(sa.BigInteger, primary_key=True)]
str_512 = Annotated[str, mapped_column(sa.String(512))]
str_255 = Annotated[str, mapped_column(sa.String(255))]


def sync_call(
    connection: 'Connection',  # noqa: ARG001
    function: 'Callable[_P, _T]',
    *args: '_P.args',
    **kwargs: '_P.kwargs',
) -> '_T':
    """Wrap `run_sync` call of sqlalchemy connection method.

    Used to remove the `Connection` argument when calling `AsyncConnection.run_sync`.
    and make a synchronous call to the target `function` with the provided arguments.
    """
    return function(*args, **kwargs)
