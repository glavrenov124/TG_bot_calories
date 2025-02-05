from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Настроить профиль", callback_data="set_profile"),
            InlineKeyboardButton(text="Прогресс", callback_data="check_progress")
        ],
        [
            InlineKeyboardButton(text="Логирование воды", callback_data="log_water"),
            InlineKeyboardButton(text="Логирование еды", callback_data="log_food"),
            InlineKeyboardButton(text="Логирование тренировки", callback_data="log_workout")
        ],
        [
            InlineKeyboardButton(text="Удалить профиль", callback_data="delete_profile")
        ]
    ])
    return keyboard
