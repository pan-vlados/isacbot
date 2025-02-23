import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from isacbot.database.utils import (
    BigIntpk,
    Datestamp,
    PollOptionsType,
    PollStatusType,
    Timestamp,
    str_255,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BaseMixin:
    created_at: Mapped[Timestamp]
    updated_at: Mapped[Timestamp] = mapped_column(onupdate=sa.func.now())


class User(BaseMixin, Base):
    __tablename__ = 'users'
    id: Mapped[BigIntpk]
    username: Mapped[str_255 | None]
    full_name: Mapped[str_255 | None]
    displayname: Mapped[str_255 | None]  # usually different from full_name
    email: Mapped[str_255 | None]


class Poll(BaseMixin, Base):
    __tablename__ = 'polls'
    id: Mapped[BigIntpk]
    question: Mapped[str_255]
    status: Mapped[PollStatusType]
    date: Mapped[Datestamp] = mapped_column(unique=True)


class PollAnswers(BaseMixin, Base):
    __tablename__ = 'poll_answers'
    user_id: Mapped[BigIntpk] = mapped_column(
        sa.ForeignKey(User.id, ondelete='CASCADE', onupdate='CASCADE')
    )
    poll_id: Mapped[BigIntpk] = mapped_column(
        sa.ForeignKey(Poll.id, ondelete='CASCADE', onupdate='CASCADE')
    )
    answer: Mapped[PollOptionsType]

    @classmethod
    def upsert(cls, user_id: BigIntpk, poll_id: BigIntpk, answer: PollOptionsType) -> sa.Insert:
        """Upsert answer if user already answer for this poll."""
        ins_stmt = sqlite.insert(table=cls).values(
            user_id=user_id,
            poll_id=poll_id,
            answer=answer,
        )
        return ins_stmt.on_conflict_do_update(
            index_elements=[cls.user_id.key, cls.poll_id.key],
            set_={
                cls.answer.key: ins_stmt.excluded.answer,
                cls.updated_at.key: datetime.datetime.now(tz=datetime.UTC),
            },  # if we don't define this key it will not trigger onupdate function for `updated_at` column
        )
