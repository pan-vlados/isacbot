import asyncio
import logging
from typing import TYPE_CHECKING, Final

from aiogram import F, Router, html
from aiogram.enums import ChatType
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from isacbot.callbacks import (
    SettingsAction,
    SettingsCallback,
    StartAction,
    StartCallback,
)
from isacbot.database.operations import (
    get_user,
    update_user,
)
from isacbot.errors import TelegramBadRequest
from isacbot.filters import (
    UserIsAuthorizedFilter,
    validate_email_filter,
)
from isacbot.handlers import start
from isacbot.keyboards import back_kb, settings_kb
from isacbot.middlewares import SettingsCallbackQueryMiddleware
from isacbot.states import UserState


if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import CallbackQuery

    from isacbot._typing import AdminsSetType, UserContext, UserStateDataMapping
    from isacbot.database.operations import UserUpdateMapping

    # ruff: noqa: ARG001


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.message.filter(F.chat.type == ChatType.PRIVATE, UserIsAuthorizedFilter)
router.callback_query.middleware(SettingsCallbackQueryMiddleware())


_MAX_DISPLAYNAME_LEN: Final = 255


@router.callback_query(StartCallback.filter(F.action == StartAction.SETTINGS))
async def settings_callback_handler(
    callback: 'CallbackQuery',
    message: 'Message',
    message_queue: asyncio.LifoQueue['Message'],
    language_code: str,
) -> None:
    message_queue.put_nowait(message)
    await message.edit_text(
        text=_('⚙️ <b>Выберите доступные настройки:</b>'),
        reply_markup=settings_kb(language_code=language_code),
        cache_time=300,
    )


@router.callback_query(
    SettingsCallback.filter(
        F.action.in_((SettingsAction.CHANGE_DISPLAYNAME, SettingsAction.CHANGE_EMAIL))
    ),
)
async def change_settings_handler(
    callback: 'CallbackQuery',
    message: 'Message',
    state: 'UserContext',
    callback_data: SettingsCallback,
    user_id: int,
    message_queue: asyncio.LifoQueue['Message'],
    language_code: str,
) -> None:
    user = await get_user(user_id=user_id)
    if not user:
        return

    match callback_data.action:
        case SettingsAction.CHANGE_DISPLAYNAME:
            text = (
                _(
                    'Ваше имя {displayname}. Для изменения напишите новое имя в сообщении ниже 📝👇'
                ).format(displayname=html.bold(user.displayname))
                if user.displayname
                else _('Имя не установлено. Напишите новое имя в сообщении ниже 👇')
            )
        case SettingsAction.CHANGE_EMAIL:
            text = (
                _(
                    'Ваш email {email}. Для изменения напишите новый email в сообщении ниже 📝👇'
                ).format(email=html.bold(user.email))
                if user.email
                else _('Email не установлен. Напишите новый email в сообщении ниже 📝👇')
            )

    message_queue.put_nowait(message)
    await state.set_state(UserState.SETTINGS_CHANGE_REQUESTED)
    await state.update_data(
        action=callback_data.action,
        callback=callback,
    )

    await message.edit_text(
        text=text,
        reply_markup=back_kb(language_code=language_code),
    )


@router.message(UserState.SETTINGS_CHANGE_REQUESTED, F.text)
async def change_settings_response_handler(
    message: 'Message',
    bot: 'Bot',
    state: 'UserContext',
    user_id: int,
    language_code: str,
    admins: 'AdminsSetType',
) -> None:
    if not (text := message.text):
        return

    user_state_data: UserStateDataMapping = await state.get_data()  # type: ignore  # see: https://discuss.python.org/t/should-typeddict-be-compatible-with-dict-any-any/40935
    update_kwargs: UserUpdateMapping = {}
    match user_state_data.get('action'):
        case SettingsAction.CHANGE_EMAIL if validate_email_filter(message=message):
            asnwer_text = _('✨ Ваш новый email {text} успешно зарегистрирован.').format(text=text)
            update_kwargs.update({'email': text})
        case SettingsAction.CHANGE_EMAIL:
            asnwer_text = _(
                '❌ Ошибка при попытке зарегистрировать email: {text}. Укажите корректный адрес электронной почты.'
            ).format(text=text)
        case SettingsAction.CHANGE_DISPLAYNAME if len(text) < _MAX_DISPLAYNAME_LEN:
            asnwer_text = _('✨ Ваше новое имя {text} успешно зарегистрировано.').format(text=text)
            update_kwargs.update({'displayname': text})
        case SettingsAction.CHANGE_DISPLAYNAME:
            asnwer_text = _(
                '❌ Ошибка при попытке зарегистрировать имя: {text}. Превышено допустимое количество символов, введите другое значение.'
            ).format(text=text)

    if not (callback_query := user_state_data.get('callback')):
        return

    if not update_kwargs:
        # Show error popup for callback message once. If the error occurs two times in a row,
        # respond to the error message and collect the message ID ranges from start to end,
        # otherwise the following error will occur:
        # aiogram.exceptions.TelegramBadRequest: Telegram server says - Bad Request: query is too old and response timeout expired or query ID is invalid
        callback_called_once = user_state_data.get('callback_called_once')
        if not callback_called_once:
            return
        if callback_called_once.is_set():
            await message.answer(text=asnwer_text)
            return

        try:
            await callback_query.answer(
                text=asnwer_text,
                show_alert=True,
            )
        except TelegramBadRequest:
            # Telegram server says - Bad Request: query is too old and response timeout expired
            # or query ID is invalid.
            await bot.send_message(
                chat_id=user_id,
                text=asnwer_text,
            )

        await message.delete()  # do not show an invalid attempt if a warning was shown
        callback_called_once.set()
        return

    if not await update_user(
        user_id=user_id,
        **update_kwargs,  # type: ignore
    ):
        return

    if not isinstance(callback_query.message, Message):
        return

    try:
        await callback_query.answer(
            text=asnwer_text,
            show_alert=True,
        )
    except TelegramBadRequest:
        # Telegram server says - Bad Request: query is too old and response timeout expired
        # or query ID is invalid.
        await bot.send_message(
            chat_id=user_id,
            text=asnwer_text,
        )

    await callback_query.message.delete()
    await start.start_handler(
        message=message,
        bot=bot,
        state=state,
        user_id=user_id,
        language_code=language_code,
        admins=admins,
    )
