import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Final

import pandas as pd
from aiogram import F, Router, html
from aiogram.enums import ChatType
from aiogram.filters import CommandStart
from aiogram.utils.i18n import gettext as _

from isacbot.callbacks import (
    BackButtonCallback,
    DefaultAction,
    SendPollCallback,
    SettingsAction,
    StartAction,
    StartCallback,
)
from isacbot.commands import ISACBotCommand
from isacbot.database.operations import (
    add_user,
    get_poll_answers,
    get_poll_data,
    get_user,
    user_already_exist,
)
from isacbot.extensions import mail_client
from isacbot.filters import (
    ChatMemberFilter,
    IsAdminFilter,
)
from isacbot.keyboards import send_poll_kb, start_kb
from isacbot.middlewares import CallbackMessageProviderMiddleware
from isacbot.states import UserState


if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import CallbackQuery, Message

    from isacbot.types_ import AdminsSetType, UserContext

    # ruff: noqa: ARG001


logger = logging.getLogger(name=__name__)
router = Router(name=__name__)
router.message.filter(F.chat.type == ChatType.PRIVATE, ChatMemberFilter())
router.callback_query.middleware(CallbackMessageProviderMiddleware())


MAX_DIALOUGE_DEEP: Final = 2  # the value corresponds to the maximum dialogue deep with user


@router.message(CommandStart())
async def start_handler(
    message: 'Message',
    bot: 'Bot',
    state: 'UserContext',
    user_id: int,
    language_code: str,
    admins: 'AdminsSetType',
) -> None:
    await state.clear()  # clear settings state as well cause it's stored inside data of this state
    if not (message_user := message.from_user):  # in case there is no from_user
        return

    logger.info('Command /%s from user_id=%s.' % (ISACBotCommand.START, user_id))
    if not (await user_already_exist(user_id=user_id)):
        await add_user(
            user_id=user_id,
            username=message_user.username,
            full_name=message_user.full_name,
        )
        text = _('Добрый день, пользователь! Выберите необходимое действие:')
    else:
        text = _('Добрый день, {full_name}! Выберите необходимое действие:').format(
            full_name=html.bold(message_user.full_name)
        )

    await state.update_data(
        first_message_id=message.message_id,
        message_queue=asyncio.LifoQueue(maxsize=MAX_DIALOUGE_DEEP),  # deep of the dialogue
        callback_called_once=asyncio.Event(),  # this flag is used later
    )
    await state.set_state(UserState.AUTHORIZED)

    await message.answer(
        text=text,
        reply_markup=start_kb(
            is_admin=await IsAdminFilter.user_is_administrator(
                bot=bot, chat_id=message.chat.id, user_id=user_id, admins=admins
            ),
            language_code=language_code,
        ),
    )


@router.callback_query(
    StartCallback.filter(F.action == StartAction.CREATE_POLL),
    IsAdminFilter(),
)
async def create_poll_callback_handler(callback: 'CallbackQuery') -> None:
    await callback.answer(
        text=_('Что то пошло не так... ☹️'),
        show_alert=True,
    )


@router.callback_query(
    StartCallback.filter(F.action == StartAction.SEND_POLL_RESULT),
    IsAdminFilter(),
)
async def send_poll_result_callback_handler(
    callback: 'CallbackQuery', state: 'UserContext', callback_message: 'Message'
) -> None:
    polls = await get_poll_data()  # TODO: can be cached by day
    if not polls:
        await callback.answer(
            text=_('Опросы не найдены.'),
            show_alert=True,
        )
        return

    if not (message_queue := await state.get_value('message_queue')):
        return
    message_queue.put_nowait(callback_message)

    await callback_message.edit_text(
        text=_('📆 Выберите дату опроса:'),
        reply_markup=send_poll_kb(polls=polls),
    )


@router.callback_query(
    SendPollCallback.filter(F.date.regexp(pattern=r'^\d{1,2}\.\d{1,2}\.\d{2,4}$')),
    IsAdminFilter(),
)
async def send_poll_date_chosen_callback_handler(
    callback: 'CallbackQuery',
    bot: 'Bot',
    user_id: int,
    callback_data: SendPollCallback,
    state: 'UserContext',
    callback_message: 'Message',
    language_code: str,
    admins: 'AdminsSetType',
) -> None:
    if not (user := await get_user(user_id=user_id)):
        await callback.answer(
            text=_(
                '⚠️ Уважаемый(ая) {full_name}, для регистрации воспользуйтесь командой {action}.'
            ).format(full_name=callback.from_user.full_name, action=_(StartAction.START)),
            show_alert=True,
        )
        return

    if not user.email:
        await callback.answer(
            text=_('⚠️ Необходимо указать почтовый адрес в команде {sequence_of_actions}').format(
                sequence_of_actions=f'{_(StartAction.SETTINGS)} -> {_(SettingsAction.CHANGE_EMAIL)}.'
            ),
            show_alert=True,
        )
        return

    answers = await get_poll_answers(
        poll_id=callback_data.poll_id,
        date=datetime.datetime.strptime(callback_data.date, '%d.%m.%Y').date(),  # noqa: DTZ007
    )
    attachment = pd.DataFrame(answers.all(), columns=[*answers.keys()])
    if attachment.empty:
        await callback.answer(
            text=_('⚠️ Ответы на опрос отсутствуют в базе данных.'),
            show_alert=True,
        )
        return

    message = await mail_client.create_message(
        to_=user.email,
        subject_=_('Результат опроса на дату {date}').format(date=callback_data.date),
        attachments_=(attachment,),
    )
    if not message:
        await callback.answer(
            text=_('❌ Ошибка при создании сообщения.'),
            show_alert=True,
        )
        return

    errors, response = await mail_client.send_message(message=message)
    if errors:
        logger.error(
            'Error while sending message to recipients:\n%s.'
            % '\n'.join('%s: %s' % (recipient, status) for recipient, status in errors.items())
        )
        await callback.answer(
            text=_('❌ Ошибка при отправке сообщения.'),
            show_alert=True,
        )
        return

    await callback.answer(
        text=_('✅ Результат опроса успешно отправлен на почтовый адрес {email}.').format(
            email=user.email
        ),
        show_alert=True,
    )
    logger.info('The message was sent to recipient: %s. user_id=%d' % (user.email, user_id))

    await callback_message.delete()
    await start_handler(
        message=callback_message,
        bot=bot,
        state=state,
        user_id=user_id,
        language_code=language_code,
        admins=admins,
    )


@router.callback_query(BackButtonCallback.filter(F.action == DefaultAction.BACK))
async def back_callback_handler(
    callback: 'CallbackQuery', state: 'UserContext', callback_message: 'Message'
) -> None:
    """Handle all back button callbacks."""
    message_queue: asyncio.LifoQueue | None = await state.get_value('message_queue')
    if not message_queue:
        return

    last_message: Message = message_queue.get_nowait()
    if not (text := last_message.text):
        return

    await callback_message.edit_text(
        text=text,
        reply_markup=last_message.reply_markup,
    )


@router.callback_query(StartCallback.filter(F.action == StartAction.HELP))
async def help_callback_handler(
    callback: 'CallbackQuery',
    callback_message: 'Message',
) -> None:
    await callback_message.answer(
        text=_(
            '🤖 Этот бот позволяет:\n\n'
            '- 📆 создавать и получать опрос о посещаемости сотрудников по понедельникам;\n'
            '- 📧 отправлять результаты опроса на почтовый ящик;\n'
            '- 📝 \u200b\u200bрегистрировать имя и email пользователя;\n'
            '- 🔒 участвовать в блокировке/разблокировке дорожной карты (рабочего файла, заполненного по направлениям деятельности отдела).'
        ),
    )
