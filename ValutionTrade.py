import random
import time
import sqlite3
import logging
import asyncio
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

def create_exchange_rates_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            previous_rate REAL,
            current_rate REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

create_exchange_rates_table()

exchange_rate = 0.5
previous_exchange_rate = exchange_rate
last_rate_update = time.time()

def update_exchange_rate():
    global exchange_rate, last_rate_update, previous_exchange_rate
    current_time = time.time()
    if current_time - last_rate_update >= config['exchange_rate_update_interval']:
        previous_exchange_rate = exchange_rate
        exchange_rate = round(random.uniform(0.1, 1.0), 2)
        last_rate_update = current_time

        cursor.execute('''
            INSERT INTO exchange_rates (previous_rate, current_rate)
            VALUES (?, ?)
        ''', (previous_exchange_rate, exchange_rate))
        conn.commit()

        logging.info(f"Курс обновлен: 1000 котокоинов = {int(1000 * exchange_rate)} магических коинов")

async def on_startup(dp: Dispatcher):
    exchange_rate_update_interval = config['exchange_rate_update_interval']

    async def update_rate_periodically():
        while True:
            update_exchange_rate()
            await asyncio.sleep(exchange_rate_update_interval)

    asyncio.create_task(update_rate_periodically())

async def exchange_command(message: types.Message):
    update_exchange_rate()
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🐱 Котокоины → 🔮 Магические коины", callback_data="exchange_cat_to_magic"),
        InlineKeyboardButton("🔮 Магические коины → 🐱 Котокоины", callback_data="exchange_magic_to_cat"),
        InlineKeyboardButton("📈 Проверить курс", callback_data="check_rate"),
    )
    await message.answer(
        f"Текущий курс обмена:\n"
        f"\n"
        f"1000 котокоинов = {int(1000 * exchange_rate)} магических коинов\n\n"
        f"Курс меняется каждую минуту, не забывайте его проверять.\n"
        "Выберите направление обмена:",
        reply_markup=keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )

async def exchange_callback(callback: types.CallbackQuery):
    data = callback.data
    if data == "check_rate":
        if exchange_rate > previous_exchange_rate:
            await callback.message.answer(
                f"Курс поднялся! Текущий курс: 1000 котокоинов = {int(1000 * exchange_rate)} магических коинов. 📈")
        elif exchange_rate < previous_exchange_rate:
            await callback.message.answer(
                f"Курс упал! Текущий курс: 1000 котокоинов = {int(1000 * exchange_rate)} магических коинов. 📉")
        else:
            await callback.message.answer(
                f"Курс остался прежним: 1000 котокоинов = {int(1000 * exchange_rate)} магических коинов. ⚖️")

async def exchange_callback_(callback: types.CallbackQuery):
    data = callback.data
    if data == "exchange_cat_to_magic":
        await choose_amount(callback.message, "cat_to_magic")
    elif data == "exchange_magic_to_cat":
        await choose_amount(callback.message, "magic_to_cat")
    await callback.answer()



async def choose_amount(message: types.Message, exchange_type: str):
    keyboard = InlineKeyboardMarkup(row_width=3)
    amounts = [100, 500, 1000, 2000, 5000, 10000]
    for amount in amounts:
        keyboard.insert(InlineKeyboardButton(str(amount), callback_data=f"amount_{exchange_type}_{amount}"))

    await message.answer(
        "Выберите сумму для обмена:",
        reply_markup=keyboard,
        parse_mode=types.ParseMode.MARKDOWN,
    )

async def amount_callback(callback: types.CallbackQuery):
    try:
        data = callback.data.split("_")
        logging.info(f"Полученные данные: {data}")


        if len(data) < 4 or data[0] != "amount":
            logging.error(f"Неверный формат данных: {callback.data}")
            await callback.answer("Неверный формат данных. Попробуйте снова.")
            return


        exchange_type = f"{data[1]}_to_{data[3]}"
        amount = int(data[-1])

        logging.info(f"Тип обмена: {exchange_type}, сумма: {amount}")

        if amount not in [100, 500, 1000, 2000, 5000, 10000]:
            logging.error(f"Неверная сумма: {amount}")
            await callback.answer("Неверная сумма. Попробуйте снова.")
            return

        user_id = callback.from_user.id
        cursor.execute("SELECT cat_coins, magic_coins FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
            return

        cat_coins, magic_coins = user_data

        if exchange_type == "magic_to_cat":
            if magic_coins < amount:
                await callback.answer(f"У вас недостаточно магических коинов. У вас {magic_coins}, а нужно {amount}.")
                return

            exchanged_cat_coins = int(amount / exchange_rate)
            cursor.execute("UPDATE users SET magic_coins = magic_coins - ?, cat_coins = cat_coins + ? WHERE user_id = ?", (amount, exchanged_cat_coins, user_id))
            conn.commit()
            await callback.message.answer(f"Вы обменяли {amount} магических коинов на {exchanged_cat_coins} котокоинов.")

        elif exchange_type == "cat_to_magic":
            if cat_coins < amount:
                await callback.answer(f"У вас недостаточно котокоинов. У вас {cat_coins}, а нужно {amount}.")
                return

            exchanged_magic_coins = int(amount * exchange_rate)
            cursor.execute("UPDATE users SET cat_coins = cat_coins - ?, magic_coins = magic_coins + ? WHERE user_id = ?", (amount, exchanged_magic_coins, user_id))
            conn.commit()
            await callback.message.answer(f"Вы обменяли {amount} котокоинов на {exchanged_magic_coins} магических коинов.")

        await callback.answer()

    except ValueError as e:
        logging.error(f"Ошибка при обработке суммы: {e}")
        await callback.answer("Произошла ошибка при обработке суммы. Убедитесь, что вы выбрали правильную сумму.")
    except Exception as e:
        logging.error(f"Ошибка в amount_callback: {e}")
        await callback.answer("Произошла ошибка. Попробуйте снова.")



def register_valution_trade_handlers(dp: Dispatcher):
    dp.register_message_handler(exchange_command, commands=["exchange"])
    dp.register_callback_query_handler(exchange_callback_, lambda c: c.data.startswith("exchange_"))
    dp.register_callback_query_handler(amount_callback, lambda c: c.data.startswith("amount_"))
    dp.register_callback_query_handler(exchange_callback)