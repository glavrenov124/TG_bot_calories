import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.dispatcher.router import Router
from middleware import LoggingMiddleware
from storage import (
    get_user,
    set_user,
    add_water,
    add_food_calories,
    add_burned_calories,
    delete_user
)
import utils
from keyboards import get_main_menu

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    greeting = (
        "Привет! Я бот для отслеживания вашего прогресса по воде, калориям и тренировкам.\n\n"
        "Доступные команды:\n"
        "• /set_profile - Настроить профиль\n"
        "• /log_water <кол-во> - Залогировать выпитую воду\n"
        "• /log_food <название продукта> - Залогировать прием пищи\n"
        "• /log_workout <тип> <время (мин)> - Залогировать тренировку\n"
        "• /check_progress - Проверить прогресс\n"
        "• /delete_profile - Удалить профиль\n\n"
        "Также воспользуйтесь удобным меню ниже."
    )
    await message.answer(greeting, reply_markup=get_main_menu())

class SetProfile(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    calorie_goal = State()

@router.message(Command("set_profile"))
async def cmd_set_profile(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(SetProfile.weight)

@router.message(SetProfile.weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число для веса.")
        return
    await state.update_data(weight=weight)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(SetProfile.height)

@router.message(SetProfile.height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число для роста.")
        return
    await state.update_data(height=height)
    await message.answer("Введите ваш возраст:")
    await state.set_state(SetProfile.age)

@router.message(SetProfile.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите целое число для возраста.")
        return
    await state.update_data(age=age)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(SetProfile.activity)

@router.message(SetProfile.activity)
async def process_activity(message: types.Message, state: FSMContext):
    try:
        activity = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число для минут активности.")
        return
    await state.update_data(activity=activity)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(SetProfile.city)

@router.message(SetProfile.city)
async def process_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    await state.update_data(city=city)
    await message.answer("Введите цель калорий или напишите 'авто' для автоматического расчёта:")
    await state.set_state(SetProfile.calorie_goal)

@router.message(SetProfile.calorie_goal)
async def process_calorie_goal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        if message.text.lower() == "авто":
            manual_goal = None
        else:
            manual_goal = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число или 'авто'.")
        return

    weight = data.get("weight")
    height = data.get("height")
    age = data.get("age")
    activity = data.get("activity")
    city = data.get("city")

    temperature = await utils.get_city_temperature(city)
    if temperature is None:
        await message.answer("Не удалось получить данные о погоде для вашего города. Используем стандартную норму.")
        temperature = 20

    water_goal = utils.calculate_water_goal(weight, activity, temperature)
    calorie_goal = utils.calculate_calorie_goal(weight, height, age, activity, manual_goal)

    user_data = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity": activity,
        "city": city,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0
    }
    set_user(message.from_user.id, user_data)

    await message.answer(
        f"Профиль настроен!\n"
        f"Вес: {weight} кг, Рост: {height} см, Возраст: {age}\n"
        f"Активность: {activity} мин/день, Город: {city}\n"
        f"Цель воды: {water_goal} мл, Цель калорий: {calorie_goal} ккал.",
        reply_markup=get_main_menu()
    )
    await state.clear()

class LogFood(StatesGroup):
    waiting_for_product = State()
    waiting_for_grams = State()

@router.message(Command("log_food"))
async def cmd_log_food(message: types.Message, command: CommandObject, state: FSMContext):
    if command.args:
        product_name = command.args.strip()
        product_info = await utils.get_food_info(product_name)
        if product_info is None:
            await message.answer("Не удалось найти информацию о продукте.")
            return
        await state.update_data(
            product_name=product_info.get("product_name", product_name),
            calories_per_100g=product_info["calories_per_100g"]
        )
        await message.answer(
            f"🍽 {product_info.get('product_name', product_name)} — {product_info['calories_per_100g']} ккал на 100 г.\n"
            "Сколько грамм вы съели?"
        )
        await state.set_state(LogFood.waiting_for_grams)
    else:
        await message.answer("Введите название продукта (например, банан):")
        await state.set_state(LogFood.waiting_for_product)

@router.message(LogFood.waiting_for_product)
async def process_food_product(message: types.Message, state: FSMContext):
    product_name = message.text.strip()
    product_info = await utils.get_food_info(product_name)
    if product_info is None:
        await message.answer("Не удалось найти информацию о продукте. Попробуйте еще раз.")
        return
    await state.update_data(
        product_name=product_info.get("product_name", product_name),
        calories_per_100g=product_info["calories_per_100g"]
    )
    await message.answer(
        f"🍽 {product_info.get('product_name', product_name)} — {product_info['calories_per_100g']} ккал на 100 г.\n"
        "Сколько грамм вы съели?"
    )
    await state.set_state(LogFood.waiting_for_grams)

@router.message(LogFood.waiting_for_grams)
async def process_food_grams(message: types.Message, state: FSMContext):
    try:
        grams = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число для граммов.")
        return
    data = await state.get_data()
    calories_per_100g = data.get("calories_per_100g")
    product_name = data.get("product_name")
    total_calories = utils.calculate_food_calories(calories_per_100g, grams)
    add_food_calories(message.from_user.id, total_calories)
    await message.answer(f"Записано: {total_calories:.1f} ккал для продукта {product_name}.")
    await state.clear()

class LogWater(StatesGroup):
    waiting_for_amount = State()

@router.message(Command("log_water"))
async def cmd_log_water(message: types.Message, command: CommandObject, state: FSMContext):
    if command.args:
        try:
            amount = int(command.args.strip())
        except ValueError:
            await message.answer("Пожалуйста, укажите корректное число.")
            return
        user = get_user(message.from_user.id)
        if not user:
            await message.answer("Сначала настройте профиль с помощью /set_profile.")
            return
        add_water(message.from_user.id, amount)
        user = get_user(message.from_user.id)
        water_goal = user.get("water_goal", 0)
        logged = user.get("logged_water", 0)
        remaining = water_goal - logged if water_goal > logged else 0
        await message.answer(
            f"Записано: {amount} мл воды.\n"
            f"Выпито: {logged} мл из {water_goal} мл.\n"
            f"Осталось: {remaining} мл."
        )
    else:
        await message.answer("Введите количество воды в мл. (например, 250):")
        await state.set_state(LogWater.waiting_for_amount)

@router.message(LogWater.waiting_for_amount)
async def process_log_water_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        return
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        await state.clear()
        return
    add_water(message.from_user.id, amount)
    user = get_user(message.from_user.id)
    water_goal = user.get("water_goal", 0)
    logged = user.get("logged_water", 0)
    remaining = water_goal - logged if water_goal > logged else 0
    await message.answer(
        f"Записано: {amount} мл воды.\n"
        f"Выпито: {logged} мл из {water_goal} мл.\n"
        f"Осталось: {remaining} мл."
    )
    await state.clear()

class LogWorkout(StatesGroup):
    waiting_for_input = State()

@router.message(Command("log_workout"))
async def cmd_log_workout(message: types.Message, command: CommandObject, state: FSMContext):
    if command.args:
        parts = command.args.split()
        if len(parts) < 2:
            await message.answer("Использование: /log_workout <тип тренировки> <время (мин)>\nПример: /log_workout бег 30")
            return
        workout_type = parts[0]
        try:
            minutes = int(parts[1])
        except ValueError:
            await message.answer("Пожалуйста, укажите корректное число для времени тренировки.")
            return
        stats = utils.calculate_workout_stats(workout_type, minutes)
        add_burned_calories(message.from_user.id, stats["burned_calories"])
        await message.answer(
            f"🏃‍♂️ {workout_type.capitalize()} {minutes} минут — {stats['burned_calories']} ккал сожжено.\n"
            f"Дополнительно: выпейте {stats['water_recommendation']} мл воды."
        )
    else:
        await message.answer("Введите тип тренировки и время (в минутах) через пробел (например, бег 30):")
        await state.set_state(LogWorkout.waiting_for_input)

@router.message(LogWorkout.waiting_for_input)
async def process_log_workout_input(message: types.Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Пожалуйста, введите тип тренировки и время (в минутах) через пробел (например, бег 30).")
        return
    workout_type = parts[0]
    try:
        minutes = int(parts[1])
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число для времени тренировки.")
        return
    stats = utils.calculate_workout_stats(workout_type, minutes)
    add_burned_calories(message.from_user.id, stats["burned_calories"])
    await message.answer(
        f"🏃‍♂️ {workout_type.capitalize()} {minutes} минут — {stats['burned_calories']} ккал сожжено.\n"
        f"Дополнительно: выпейте {stats['water_recommendation']} мл воды."
    )
    await state.clear()

@router.message(Command("check_progress"))
async def cmd_check_progress(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала настройте профиль с помощью /set_profile.")
        return
    water_goal = user.get("water_goal", 0)
    logged_water = user.get("logged_water", 0)
    remaining_water = water_goal - logged_water if water_goal > logged_water else 0
    calorie_goal = user.get("calorie_goal", 0)
    logged_calories = user.get("logged_calories", 0)
    burned_calories = user.get("burned_calories", 0)
    balance = calorie_goal - (logged_calories - burned_calories)
    await message.answer(
        f"📊 Прогресс:\n\n"
        f"Вода:\n- Выпито: {logged_water} мл из {water_goal} мл.\n- Осталось: {remaining_water} мл.\n\n"
        f"Калории:\n- Потреблено: {logged_calories} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {burned_calories} ккал.\n- Баланс: {balance} ккал."
    )

@router.message(Command("delete_profile"))
async def cmd_delete_profile(message: types.Message, command: CommandObject = None):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Данные пользователя не найдены.")
        return
    delete_user(message.from_user.id)
    await message.answer("Данные пользователя удалены.")

@router.callback_query(lambda c: c.data == "set_profile")
async def cb_set_profile(callback: types.CallbackQuery, state: FSMContext):
    await cmd_set_profile(callback.message, state)
    await callback.answer()

@router.callback_query(lambda c: c.data == "check_progress")
async def cb_check_progress(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала настройте профиль с помощью /set_profile.")
    else:
        water_goal = user.get("water_goal", 0)
        logged_water = user.get("logged_water", 0)
        remaining_water = water_goal - logged_water if water_goal > logged_water else 0
        calorie_goal = user.get("calorie_goal", 0)
        logged_calories = user.get("logged_calories", 0)
        burned_calories = user.get("burned_calories", 0)
        balance = calorie_goal - (logged_calories - burned_calories)
        progress_text = (
            f"📊 Прогресс:\n\n"
            f"Вода:\n- Выпито: {logged_water} мл из {water_goal} мл.\n- Осталось: {remaining_water} мл.\n\n"
            f"Калории:\n- Потреблено: {logged_calories} ккал из {calorie_goal} ккал.\n"
            f"- Сожжено: {burned_calories} ккал.\n- Баланс: {balance} ккал."
        )
        await callback.message.answer(progress_text)
    await callback.answer()

@router.callback_query(lambda c: c.data == "delete_profile")
async def cb_delete_profile(callback: types.CallbackQuery):
    await cmd_delete_profile(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "log_water")
async def cb_log_water(callback: types.CallbackQuery, state: FSMContext):
    await cmd_log_water(callback.message, CommandObject(args=""), state)
    await callback.answer()

@router.callback_query(lambda c: c.data == "log_food")
async def cb_log_food(callback: types.CallbackQuery, state: FSMContext):
    await cmd_log_food(callback.message, CommandObject(args=""), state)
    await callback.answer()

@router.callback_query(lambda c: c.data == "log_workout")
async def cb_log_workout(callback: types.CallbackQuery, state: FSMContext):
    await cmd_log_workout(callback.message, CommandObject(args=""), state)
    await callback.answer()

async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="set_profile", description="Настроить профиль"),
        types.BotCommand(command="log_water", description="Логировать воду"),
        types.BotCommand(command="log_food", description="Логировать прием пищи"),
        types.BotCommand(command="log_workout", description="Логировать тренировку"),
        types.BotCommand(command="check_progress", description="Проверить прогресс"),
        types.BotCommand(command="delete_profile", description="Удалить профиль"),
    ]
    await bot.set_my_commands(commands)


async def main():
    API_TOKEN = "YOUR_API_TOKEN"  
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    dp.message.middleware.register(LoggingMiddleware())
    dp.include_router(router)
    
    await set_commands(bot)
    print("Бот запущен, начинаю polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
