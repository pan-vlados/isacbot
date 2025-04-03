import asyncio

from aiogram.utils.i18n.middleware import (
    FSMI18nMiddleware,
)

from isacbot.background.tasks import create_poll_in_chat
from isacbot.commands import get_commands
from isacbot.config import (
    BOT_ADMINS,
    BOT_MAIN_CHAT_ID,
    BOT_OWNER_ID,
    BOT_TIMEZONE,
)
from isacbot.database.models import Base
from isacbot.extensions import (
    CronTrigger,
    bot,
    db,
    dp,
    i18n,
    mail_client,  # noqa: F401
    scheduler,
)
from isacbot.handlers import admin, group, poll, private, road_map, settings, start
from isacbot.middlewares import (
    BlockCallbackFromOldMessageMiddleware,
    DelayMiddleware,
    EventFromUserMiddleware,
    UnhandledUpdatesLoggerMiddleware,
)
from isacbot.states import PollContext
from isacbot.utils import N_, send_message


async def set_commands() -> None:
    """Commands for all users. All commands described in `routers.py`."""
    for commands, scope in get_commands(i18n=i18n):
        await bot.set_my_commands(commands=commands, scope=scope)


async def add_admins_from_main_chat() -> None:
    """Let's assume the bot works only with one main chat. This allows us to
    add admins from main chat to bot admins dictionary for correspondent chat.
    """
    if BOT_MAIN_CHAT_ID and BOT_MAIN_CHAT_ID != BOT_OWNER_ID:
        BOT_ADMINS[BOT_MAIN_CHAT_ID] = {
            admin.user.id for admin in (await bot.get_chat_administrators(chat_id=BOT_MAIN_CHAT_ID))
        }


async def start_scheduler() -> None:
    scheduler.start()
    scheduler.add_job(  # Add poll creation on every Monday an 8:00
        id='main_chat_poll_every_monday_id',
        name='main_chat_poll_every_monday',
        replace_existing=True,
        misfire_grace_time=None,
        func=create_poll_in_chat,
        kwargs={'chat_id': BOT_MAIN_CHAT_ID},
        trigger=CronTrigger(day_of_week='mon', hour='8', minute='00', timezone=BOT_TIMEZONE),
    )


async def start_bot() -> None:
    await set_commands()
    await add_admins_from_main_chat()
    await start_scheduler()
    await send_message(
        bot=bot,
        chat_id=BOT_OWNER_ID,
        text=i18n.gettext(N_('{name} запущен🥳')).format(name=f'{(await bot.get_my_name()).name}'),
    )


async def stop_bot() -> None:
    await send_message(
        bot=bot,
        chat_id=BOT_OWNER_ID,
        text=i18n.gettext(N_('{name} остановлен😔')).format(
            name=f'{(await bot.get_my_name()).name}'
        ),
    )


async def main() -> None:
    async with db.connect():
        # Perform database preparation.
        await db.create_database()
        await db.create_tables(base=Base)
        # Register middleware.
        group.router.message.middleware(DelayMiddleware(delay=1))
        poll.router.message.middleware(DelayMiddleware(delay=1))
        private.router.message.middleware(DelayMiddleware(delay=1))
        # message.router.chat_member.filter(F.chat.id == config.main_chat_id)  # set default router to main chat only
        dp.update.outer_middleware(
            FSMI18nMiddleware(i18n=i18n)
        )  # include internationalization middleware
        dp.update.outer_middleware(
            EventFromUserMiddleware()
        )  # provide user_id and language_code into handlers
        dp.update.outer_middleware(UnhandledUpdatesLoggerMiddleware())  # log all unhandled events
        dp.callback_query.outer_middleware(BlockCallbackFromOldMessageMiddleware())
        # Register routers and their handlers. Order matters.
        dp.include_routers(
            start.router,
            admin.router,
            private.router,
            group.router,
            poll.router,
            road_map.router,
            settings.router,
        )

        # Register bot functions.
        # NOTE: If we wait in a registered callback on startup/shutdown, we won't
        # be able to apply the i18n translation because it's not in the bot context
        # at the time of registration.
        dp.startup.register(callback=start_bot)
        dp.shutdown.register(callback=stop_bot)

        async with bot.session:  # clear all updates that were made during the moments of inactivity
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                close_bot_session=True,
                admins=BOT_ADMINS,
                poll_context=PollContext,
            )


if __name__ == '__main__':
    asyncio.run(main())
