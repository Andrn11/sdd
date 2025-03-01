import random
import time
import sqlite3
from MagicData import magic, technique_weights
from lecsicon import magic_synonyms
from aiogram import Dispatcher, types
import logging
import json

logging.basicConfig(level=logging.INFO)

with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

try:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
except sqlite3.Error as e:
    logging.error(f"Ошибка подключения к базе данных: {e}")
    raise

def get_random_magic(magic, has_magic_luck_scroll=False):
    weighted_magic = []
    for m in magic:
        if has_magic_luck_scroll:

            if m["technique"] in ["Сложная", "Великая"]:
                weight = technique_weights.get(m["technique"], 1) * 2
            else:
                weight = technique_weights.get(m["technique"], 1)
        else:
            weight = technique_weights.get(m["technique"], 1)
        weighted_magic.extend([m] * weight)
    return random.choice(weighted_magic)


async def jujitsu_command(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    cursor.execute(
        "SELECT last_magic_time, has_magic_medallion, has_magic_luck_scroll, has_magic_scroll FROM users WHERE user_id = ?",
        (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        cursor.execute(
            "INSERT INTO users (user_id, rarity, points, highest_rarity, magic_coins, has_magic_scroll) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "обычный", 0, "обычный", 0, 0),
        )
        conn.commit()
        last_magic_time = 0
        has_magic_medallion = 0
        has_magic_luck_scroll = 0
        has_magic_scroll = 0
    else:
        last_magic_time, has_magic_medallion, has_magic_luck_scroll, has_magic_scroll = user_data

    if last_magic_time and (current_time - last_magic_time) < 21600 and not has_magic_scroll:
        remaining_time = 21600 - (current_time - last_magic_time)
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        await message.answer(
            f"Вы осмотрелись, но не нашли магической карты. Попробуйте через {hours} часов {minutes} минут."
        )
        return

    if has_magic_scroll:
        cursor.execute("UPDATE users SET has_magic_scroll = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

    cursor.execute("UPDATE users SET last_magic_time = ? WHERE user_id = ?", (current_time, user_id))
    conn.commit()

    magic_card = get_random_magic(magic, has_magic_luck_scroll)

    if has_magic_medallion:
        magic_card["magic_coins"] = int(magic_card["magic_coins"] * 1.25)

    if has_magic_luck_scroll:
        magic_card["points"] = int(magic_card["points"] * 1.2)

    try:
        cursor.execute(
            """
            UPDATE users SET 
                rarity = ?, 
                points = points + ?, 
                highest_rarity = CASE 
                    WHEN ? > highest_rarity THEN ? 
                    ELSE highest_rarity 
                END,
                magic_coins = magic_coins + ?
            WHERE user_id = ?
            """,
            (
                magic_card["technique"],
                magic_card["points"],
                magic_card["technique"],
                magic_card["technique"],
                magic_card["magic_coins"],
                user_id,
            ),
        )
        conn.commit()

        message_text = (
            f"👤 {message.from_user.first_name}, успех! Вы нашли магическую карту!\n"
            f"✨ Карта: «{magic_card['magicname']}»\n"
            "--------------------------\n"
            f"🔮 Техника: {magic_card['technique']}\n"
            f"💎 Очки: +{magic_card['points']}\n"
            f"🔮 Магические коины: +{magic_card['magic_coins']}\n"
            f"🧧 Описание: {magic_card['magicinfo']}"
        )

        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=magic_card["photo"],
            caption=message_text,
            reply_to_message_id=message.message_id,
            parse_mode=types.ParseMode.MARKDOWN,
        )
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        await message.answer("Произошла ошибка.")


async def send_magic(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    cursor.execute("SELECT last_magic_time, has_magic_medallion, has_magic_luck_scroll, has_magic_scroll FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        cursor.execute(
            "INSERT INTO users (user_id, rarity, points, highest_rarity, magic_coins, has_magic_scroll) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "обычный", 0, "обычный", 0, 0),
        )
        conn.commit()
        last_magic_time = 0
        has_magic_medallion = 0
        has_magic_luck_scroll = 0
        has_magic_scroll = 0
    else:
        last_magic_time, has_magic_medallion, has_magic_luck_scroll, has_magic_scroll = user_data


    if last_magic_time and (current_time - last_magic_time) < 21600 and not has_magic_scroll:
        remaining_time = 21600 - (current_time - last_magic_time)
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        await message.answer(
            f"Вы осмотрелись, но не нашли магической карты. Попробуйте через {hours} часов {minutes} минут."
        )
        return


    if has_magic_scroll:
        cursor.execute("UPDATE users SET has_magic_scroll = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

    cursor.execute("UPDATE users SET last_magic_time = ? WHERE user_id = ?", (current_time, user_id))
    conn.commit()

    magic_card = get_random_magic(magic, has_magic_luck_scroll)


    if has_magic_medallion:
        magic_card["magic_coins"] = int(magic_card["magic_coins"] * 1.25)


    if has_magic_luck_scroll:
        magic_card["points"] = int(magic_card["points"] * 1.2)

    try:
        cursor.execute(
            """
            UPDATE users SET 
                rarity = ?, 
                points = points + ?, 
                highest_rarity = CASE 
                    WHEN ? > highest_rarity THEN ? 
                    ELSE highest_rarity 
                END,
                magic_coins = magic_coins + ?
            WHERE user_id = ?
            """,
            (
                magic_card["technique"],
                magic_card["points"],
                magic_card["technique"],
                magic_card["technique"],
                magic_card["magic_coins"],
                user_id,
            ),
        )
        conn.commit()

        message_text = (
            f"👤 {message.from_user.first_name}, успех! Вы нашли магическую карту!\n"
            f"✨ Карта: «{magic_card['magicname']}»\n"
            "--------------------------\n"
            f"🔮 Техника: {magic_card['technique']}\n"  
            f"💎 Очки: +{magic_card['points']}\n"
            f"🔮 Магические коины: +{magic_card['magic_coins']}\n"
            f"🧧 Описание: {magic_card['magicinfo']}"
        )

        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=magic_card["photo"],
            caption=message_text,
            reply_to_message_id=message.message_id,
            parse_mode=types.ParseMode.MARKDOWN,
        )

    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        await message.answer("Произошла ошибка.")

def register_magic_handlers(dp: Dispatcher):
    dp.register_message_handler(send_magic, lambda message: message.text.lower() in magic_synonyms)
    dp.register_message_handler(jujitsu_command, commands=["jujitsu"])