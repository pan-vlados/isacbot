import logging
from typing import TYPE_CHECKING

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.i18n import gettext as _

from isacbot.callbacks import (
    BackButtonCallback,
    RoadMapAction,
    SendPollCallback,
    SettingsAction,
    SettingsCallback,
    StartAction,
    StartCallback,
)


if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Row

    from isacbot._typing import cache
    from isacbot.database.utils import BigIntpk, Datestamp

    # ruff: noqa: ARG001
else:
    from functools import cache


logger = logging.getLogger(__name__)


@cache
def start_kb(*, is_admin: bool = False, language_code: str) -> InlineKeyboardMarkup:
    settings_callback_data = StartCallback(action=StartAction.SETTINGS)
    help_callback_data = StartCallback(action=StartAction.HELP)
    create_poll_callback_data = StartCallback(action=StartAction.CREATE_POLL)
    send_poll_result_callback_data = StartCallback(action=StartAction.SEND_POLL_RESULT)
    kb: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_(settings_callback_data.action), callback_data=settings_callback_data.pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=_(help_callback_data.action), callback_data=help_callback_data.pack()
            )
        ],
    ]
    if is_admin:
        kb = [
            [
                InlineKeyboardButton(
                    text=_(create_poll_callback_data.action),
                    callback_data=create_poll_callback_data.pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_(send_poll_result_callback_data.action),
                    callback_data=send_poll_result_callback_data.pack(),
                )
            ],
            *kb,
        ]
    return InlineKeyboardMarkup(
        inline_keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=_('Воспользуйся меню👇'),
    )


@cache
def back_kb(language_code: str) -> InlineKeyboardMarkup:
    back_callback_data = BackButtonCallback()
    kb: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_(back_callback_data.action), callback_data=back_callback_data.pack()
            ),
        ],
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@cache
def settings_kb(language_code: str) -> InlineKeyboardMarkup:
    change_displayname_callback_data = SettingsCallback(action=SettingsAction.CHANGE_DISPLAYNAME)
    change_email_callback_data = SettingsCallback(action=SettingsAction.CHANGE_EMAIL)
    back_callback_data = BackButtonCallback()
    kb: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_(change_displayname_callback_data.action),
                callback_data=change_displayname_callback_data.pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=_(change_email_callback_data.action),
                callback_data=change_email_callback_data.pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=_(back_callback_data.action), callback_data=back_callback_data.pack()
            )
        ],
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=_('Выберите статус☝️'),
    )


@cache
def road_map_kb(*, is_acquired: bool = True, language_code: str) -> ReplyKeyboardMarkup:
    """Acquire/release keyboard for road map.

    `acquire` - flag for corresponding action keyboard.
    """
    kb: list[list[KeyboardButton]] = [
        [
            KeyboardButton(text=_(RoadMapAction.ACQUIRE))
            if is_acquired
            else KeyboardButton(text=_(RoadMapAction.RELEASE)),
        ],
        [KeyboardButton(text=_(RoadMapAction.WAIT_RELEASED))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=_('Выберите действие 👇'),
    )


def send_poll_kb(polls: 'Sequence[Row[tuple[Datestamp, BigIntpk]]]') -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f'{date:%d.%m.%Y}',
                callback_data=SendPollCallback(poll_id=poll_id, date=f'{date:%d.%m.%Y}').pack(),
            )
        ]
        for date, poll_id in polls
    ]
    back_callback_data = BackButtonCallback()
    kb.append(
        [
            InlineKeyboardButton(
                text=_(back_callback_data.action), callback_data=back_callback_data.pack()
            )
        ]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=kb,
        resize_keyboard=True,
    )
