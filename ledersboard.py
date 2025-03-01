from aiogram import Dispatcher, types
import sqlite3
from aiogram.types import ParseMode


try:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
except sqlite3.Error as e:
    print(f"Ошибка подключения к базе данных: {e}")
    raise

async def show_leaderboard(message: types.Message, leaderboard_type: str):


    if leaderboard_type == "points":
        column = "points"
        title = "🏆 Лидерборд по очкам 🏆"
    elif leaderboard_type == "cat_coins":
        column = "cat_coins"
        title = "🐱 Лидерборд по котокоинам 🐱"
    elif leaderboard_type == "magic_coins":
        column = "magic_coins"
        title = "🔮 Лидерборд по магическим коинам 🔮"
    else:
        await message.answer("Неверный тип лидерборда.")
        return


    cursor.execute(f"""
        SELECT user_id, {column} 
        FROM users 
        ORDER BY {column} DESC
    """)
    leaderboard = cursor.fetchall()

    if not leaderboard:
        await message.answer("Лидерборд пуст.")
        return


    leaderboard_text = f"{title}\n\n"
    for index, (user_id, value) in enumerate(leaderboard, start=1):

        try:
            user = await message.bot.get_chat(user_id)
            user_name = user.first_name
        except Exception as e:
            user_name = f"Пользователь {user_id}"

        leaderboard_text += f"{index}. {user_name}: {value}\n"


    await message.answer(leaderboard_text, parse_mode=ParseMode.MARKDOWN)

async def leders_command(message: types.Message):

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🏆 По очкам", callback_data="leaderboard_points"),
        types.InlineKeyboardButton("🐱 По котокоинам", callback_data="leaderboard_cat_coins"),
        types.InlineKeyboardButton("🔮 По магическим коинам", callback_data="leaderboard_magic_coins"),
    )

    await message.answer(
        "Выберите тип лидерборда:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )

async def leaderboard_callback(callback: types.CallbackQuery):


    leaderboard_type = callback.data.replace("leaderboard_", "")
    await callback.answer()
    await show_leaderboard(callback.message, leaderboard_type)

def register_leaderboard_handlers(dp: Dispatcher):

    dp.register_message_handler(leders_command, commands=["leders"])
    dp.register_callback_query_handler(leaderboard_callback, lambda c: c.data.startswith("leaderboard_"))