import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy_utils as su
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from isacbot.database.utils import sync_call


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.orm import DeclarativeBase


logger = logging.getLogger(__name__)


class Database:
    url: sa.URL
    engine: 'AsyncEngine'
    session: async_sessionmaker['AsyncSession']

    def __init__(self, path: 'Path | str') -> None:
        self.url = sa.engine.make_url(f'sqlite+aiosqlite:///{path}')

    @asynccontextmanager
    async def connect(self) -> 'AsyncGenerator[Database]':
        self.engine = create_async_engine(
            url=self.url,
            echo=False,
            echo_pool=False,
            poolclass=sa.NullPool,
            isolation_level='SERIALIZABLE',
        )
        try:
            self.session = async_sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
            )
            yield self
        except Exception:
            logger.exception('Error while trying to create async session.')
            raise
        finally:
            # For AsyncEngine created in function scope, it's advisable to close
            # and clean-up pooled connections.
            await self.engine.dispose()
            logger.info('Database cleanup success.')

    # Default database methods in async style.
    async def create_database(self) -> None:
        async with self.engine.begin() as connection:
            if not su.database_exists(self.engine.url):
                await connection.run_sync(sync_call, su.create_database, self.engine.url)
                logger.info('Database created.')

    async def drop_database(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(sync_call, su.drop_database, url=self.engine.url)
            logger.info('Database dropped.')

    async def create_tables(self, base: type['DeclarativeBase']) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(base.metadata.create_all)

    async def drop_tables(self, base: type['DeclarativeBase']) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(base.metadata.drop_all)
