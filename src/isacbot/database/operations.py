import datetime
import logging
from typing import TYPE_CHECKING, NotRequired, TypedDict, Unpack

import sqlalchemy as sa

from isacbot.config import BOT_TIMEZONE
from isacbot.database.models import Poll, PollAnswers, User
from isacbot.database.utils import (
    BigIntpk,
    Datestamp,
    PollOptionsType,
    PollStatus,
    get_timezone_aware_date,
    str_255,
)
from isacbot.errors import IntegrityError, NoResultFound, SQLAlchemyError
from isacbot.extensions import db


if TYPE_CHECKING:
    from collections.abc import Sequence

    class UserUpdateMapping(TypedDict):
        displayname: NotRequired[str | None]
        email: NotRequired[str | None]

    type PollAnswerType = tuple[
        Datestamp,
        str_255,
        str_255 | None,
        str_255 | None,
        str_255 | None,
        PollOptionsType,
        Datestamp,
    ]


logger = logging.getLogger(__name__)


async def add_user(user_id: int, username: str | None, full_name: str | None) -> None:
    async with db.session.begin() as session:
        try:
            session.add(User(id=user_id, username=username, full_name=full_name))
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            logger.exception('Error while trying to add user_id=%d' % user_id)
        else:
            logger.info('user_id=%d created.' % user_id)


async def get_user(user_id: int) -> User | None:
    async with db.session.begin() as session:
        try:
            return await session.get_one(User, user_id)
        except NoResultFound:
            await session.rollback()
            logger.debug('User not found in database. user_id=%d' % user_id)
        return None


async def update_user(user_id: int, **kawrgs: Unpack['UserUpdateMapping']) -> bool:
    """Async update event in database return `True` if update was succsessfull."""
    async with db.session.begin() as session:
        try:
            await session.execute(sa.update(User).where(User.id == user_id).values(**kawrgs))
        except SQLAlchemyError:
            await session.rollback()
            logger.exception('Error while trying to update user_id=%d, data=%s' % (user_id, kawrgs))
            return False
    logger.info('user_id=%d updated.' % user_id)
    return True


async def user_already_exist(user_id: int) -> bool:
    async with db.session.begin() as session:
        if await session.scalar(sa.select(User).where(User.id == user_id)):
            logger.debug('user_id=%d already exist.' % user_id)
            return True
        return False


async def poll_already_exist(date: datetime.date) -> bool:
    async with db.session.begin() as session:
        if await session.scalar(sa.select(Poll).where(Poll.date == date)):
            logger.debug('Poll already exist on the %s' % date.strftime('%d.%m.%Y.'))
            return True
        return False


async def add_answer(user_id: BigIntpk, poll_id: BigIntpk, answer: PollOptionsType) -> None:
    async with db.session.begin() as session:
        try:
            await session.execute(
                sa.text('PRAGMA foreign_keys = ON;')
            )  # by default sqlite foreign keys dosen't work
            await session.execute(
                statement=PollAnswers.upsert(user_id=user_id, poll_id=poll_id, answer=answer)
            )
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            if isinstance(e, IntegrityError) and str(e.orig) == 'FOREIGN KEY constraint failed':
                msg = "user_id=%d or poll_id=%d isn't registred in database." % (user_id, poll_id)
            else:
                msg = 'Error while trying to save answer. user_id=%d, poll_id=%d' % (
                    user_id,
                    poll_id,
                )
            logger.exception(msg)
        else:
            logger.info('Answer saved. user_id=%d' % user_id)


async def create_poll(
    poll_id: BigIntpk, question: str_255, date: Datestamp, status: PollStatus
) -> None:
    poll = Poll(id=poll_id, question=question, date=date, status=status.name)
    async with db.session.begin() as session:
        try:
            session.add(poll)
            await session.commit()
            logger.info('poll_id=%d created on the %s.' % (poll_id, date.strftime('%d.%m.%Y')))
        except SQLAlchemyError:
            await session.rollback()
            logger.exception(
                'Error while trying to create pool_id=%d fon the %s.'
                % (poll_id, date.strftime('%d.%m.%Y'))
            )


async def update_poll_status(poll_id: BigIntpk, status: PollStatus) -> None:
    async with db.session.begin() as session:
        await session.execute(sa.update(Poll).where(Poll.id == poll_id).values(status=status.name))


_PollAnswersLabel_created_at = sa.Label(
    name='aswered_at',
    element=get_timezone_aware_date(attribute=PollAnswers.created_at, tz=BOT_TIMEZONE),
)  # there is no cast() funcion for sqlite [see](https://github.com/sqlalchemy/sqlalchemy/issues/5104).


async def get_poll_answers(poll_id: int, date: datetime.date) -> sa.Result['PollAnswerType']:
    async with db.session.begin() as session:
        return await session.execute(
            sa.select(
                Poll.date,
                Poll.question,
                User.username,
                User.full_name,
                User.displayname,
                PollAnswers.answer,
                _PollAnswersLabel_created_at,
            )
            .distinct()
            .select_from(PollAnswers)
            .where(
                sa.and_(
                    PollAnswers.poll_id == poll_id,
                    _PollAnswersLabel_created_at == date,
                )
            )
            .join(User, User.id == PollAnswers.user_id)
            .join(Poll, Poll.id == PollAnswers.poll_id)
            .order_by(User.username, User.full_name)
        )


async def get_poll_data(limit: int = 4) -> 'Sequence[sa.Row[tuple[Datestamp, BigIntpk]]]':
    """Get poll's data. Default `limit = 4`."""
    async with db.session.begin() as session:
        return (
            await session.execute(
                sa.select(
                    Poll.date,
                    Poll.id,
                )
                .select_from(Poll)
                .order_by(Poll.date)
                .limit(limit)
            )
        ).all()
