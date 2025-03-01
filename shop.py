from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
import random
import sqlite3
import logging
from data import cats, rarity_weights
import time
import json


with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)


def get_random_cat(cats):
    weighted_cats = []
    for cat in cats:
        weight = rarity_weights.get(cat["rarity"], 1)
        weighted_cats.extend([cat] * weight)
    return random.choice(weighted_cats)


try:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
except sqlite3.Error as e:
    logging.error(f"Ошибка подключения к базе данных: {e}")
    raise


CARD_PRICE = config['prices']['card']
COFFEE_PRICE = config['prices']['coffee']
SCRATCHER_PRICE = config['prices']['scratcher']
COMPANION_PRICE = config['prices']['companion']
BOOSTER_PRICE = config['prices']['booster']
TIME_WATCH_PRICE = config['prices']['time_watch']
MAGIC_MEDALLION_PRICE = config['prices']['magic_medallion']
MAGIC_LUCK_SCROLL_PRICE = config['prices']['magic_luck_scroll']
MAGIC_SCROLL_PRICE = config['prices']['magic_scroll']


async def shop_command(message: types.Message):
    if message.chat.type != "private":
        await message.answer("Эта команда работает только в личных сообщениях (ЛС).")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎴 Купить карточку кота", callback_data="buy_card"),
        InlineKeyboardButton("☕ Купить кофе", callback_data="buy_coffee"),
        InlineKeyboardButton("🐾 Купить Чесалку", callback_data="buy_scratcher"),
        InlineKeyboardButton("🐱 Кот компаньон", callback_data="buy_companion"),
        InlineKeyboardButton("🚀 Кот-бустер", callback_data="buy_booster"),
        InlineKeyboardButton("⏳ Часы времени", callback_data="buy_time_watch"),
        InlineKeyboardButton("🔮 Магический медальон", callback_data="buy_magic_medallion"),
        InlineKeyboardButton("✨ Магический свиток удачи", callback_data="buy_magic_luck_scroll"),
        InlineKeyboardButton("🧪 Магический свиток", callback_data="buy_magic_scroll")
    )


    await message.answer(
            "✨ **Добро пожаловать в наш уютный магазин!** 🛒✨\n"
            f"🎴 **Случайная карточка кота** — `{config['prices']['card']}` котокоинов\n"
            f"☕ **Чашка кофе** — `{config['prices']['coffee']}` котокоинов\n"
            f"🐾 **Чесалка** — `{config['prices']['scratcher']}` котокоинов\n"
            f"🐱 **Кот-компаньон** — `{config['prices']['companion']}` котокоинов\n"
            f"🚀 **Кот-бустер** — `{config['prices']['booster']}` котокоинов\n"
            f"⏳ **Часы времени** — `{config['prices']['time_watch']}` котокоинов\n"
            f"🔮 **Магический медальон** — `{config['prices']['magic_medallion']}` магических коинов\n"
            f"✨ **Магический свиток удачи** — `{config['prices']['magic_luck_scroll']}` магических коинов\n"
            f"🧪 **Магический свиток** — `{config['prices']['magic_scroll']}` магических коинов\n",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
     )

async def buy_card_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins = result[0]

    if cat_coins < CARD_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {CARD_PRICE}, а у вас {cat_coins}.")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ? WHERE user_id = ?", (CARD_PRICE, user_id))
    conn.commit()

    cat = get_random_cat(cats)

    rarities_str = ", ".join([
        "обычный",
        "редкий",
        "сверхредкий",
        "эпический",
        "мифический",
        "легендарный",
        "хромотический",
        "особый"
    ])

    try:
        cursor.execute(
            f"""
            UPDATE users SET 
                rarity = ?, 
                points = points + ?, 
                highest_rarity = CASE 
                    WHEN INSTR('{rarities_str}', ?) > INSTR('{rarities_str}', highest_rarity) THEN ? 
                    ELSE highest_rarity 
                END
            WHERE user_id = ?
            """,
            (
                cat["rarity"],
                cat["points"],
                cat["rarity"],
                cat["rarity"],
                user_id,
            ),
        )
        conn.commit()
        message_text = (
            f"🎴 Вы купили карточку «{cat['catname']}» за {CARD_PRICE} котокоинов!\n\n"
            f"💎 Редкость: {cat['rarity']}\n"
            f"✨ Очки: +{cat['points']}\n"
            f"🐱 Остаток котокоинов: {cat_coins - CARD_PRICE}"
        )
        await callback.message.answer_photo(
            photo=cat["photo"],
            caption=message_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        await callback.answer("Произошла ошибка.")


async def buy_coffee_callback(callback: types.CallbackQuery, cooldowns: dict):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins, last_cat_time FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins, last_cat_time = result

    if cat_coins < COFFEE_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {COFFEE_PRICE}, а у вас {cat_coins}.")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ? WHERE user_id = ?", (COFFEE_PRICE, user_id))
    conn.commit()

    if user_id in cooldowns:
        cooldowns[user_id] -= 3600
    else:
        cooldowns[user_id] = last_cat_time - 3600

    cursor.execute("UPDATE users SET last_cat_time = ? WHERE user_id = ?", (cooldowns[user_id], user_id))
    conn.commit()

    await callback.message.answer(
        f"☕ Вы купили чашку кофе за {COFFEE_PRICE} котокоинов!\n"
        f"Теперь кулдаун для команды 'кот' сокращён на 1 час.\n"
        f"🐱 Остаток котокоинов: {cat_coins - COFFEE_PRICE}"
    )


async def buy_scratcher_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins, has_scratcher FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins, has_scratcher = result

    if has_scratcher:
        await callback.answer("У вас уже есть Чесалка!")
        return

    if cat_coins < SCRATCHER_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {SCRATCHER_PRICE}, а у вас {cat_coins}.")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ?, has_scratcher = 1 WHERE user_id = ?", (SCRATCHER_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"🐾 Вы купили Чесалку за {SCRATCHER_PRICE} котокоинов!\n"
        f"Теперь вы можете использовать команду /put, чтобы погладить котика и получить 1000 очков!\n"
        f"🐱 Остаток котокоинов: {cat_coins - SCRATCHER_PRICE}"
    )


async def buy_companion_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins = result[0]

    if cat_coins < COMPANION_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {COMPANION_PRICE}, а у вас {cat_coins}.")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ?, has_companion = 1 WHERE user_id = ?", (COMPANION_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"🐱 Вы купили Кота компаньона за {COMPANION_PRICE} котокоинов!\n"
        f"Теперь при команде 'кот' вы получите несколько карточек!\n"
        f"🐱 Остаток котокоинов: {cat_coins - COMPANION_PRICE}"
    )


async def buy_booster_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins, booster_end_time FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins, booster_end_time = result

    if cat_coins < BOOSTER_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {BOOSTER_PRICE}, а у вас {cat_coins}.")
        return

    if booster_end_time and booster_end_time > time.time():
        await callback.answer("У вас уже активен Кот-бустер!")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ? WHERE user_id = ?", (BOOSTER_PRICE, user_id))
    conn.commit()

    booster_end_time = int(time.time()) + 86400
    cursor.execute("UPDATE users SET booster_end_time = ? WHERE user_id = ?", (booster_end_time, user_id))
    conn.commit()

    await callback.message.answer(
        f"🚀 Вы купили Кот-бустер за {BOOSTER_PRICE} котокоинов!\n"
        f"Теперь в течение 24 часов вы будете получать на 50% больше очков и котокоинов за карточки!\n"
        f"🐱 Остаток котокоинов: {cat_coins - BOOSTER_PRICE}"
    )


async def buy_time_watch_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT cat_coins, has_time_watch FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    cat_coins, has_time_watch = result

    if has_time_watch:
        await callback.answer("У вас уже есть Часы времени!")
        return

    if cat_coins < TIME_WATCH_PRICE:
        await callback.answer(f"У вас недостаточно котокоинов. Нужно {TIME_WATCH_PRICE}, а у вас {cat_coins}.")
        return

    cursor.execute("UPDATE users SET cat_coins = cat_coins - ?, has_time_watch = 1 WHERE user_id = ?", (TIME_WATCH_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"⏳ Вы купили Часы времени за {TIME_WATCH_PRICE} котокоинов!\n"
        f"Теперь при следующем использовании команды 'кот' кулдаун будет сброшен.\n"
        f"🐱 Остаток котокоинов: {cat_coins - TIME_WATCH_PRICE}"
    )


async def buy_magic_medallion_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT magic_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    magic_coins = result[0]

    if magic_coins < MAGIC_MEDALLION_PRICE:
        await callback.answer(f"У вас недостаточно Магических коинов. Нужно {MAGIC_MEDALLION_PRICE}, а у вас {magic_coins}.")
        return

    cursor.execute("UPDATE users SET magic_coins = magic_coins - ?, has_magic_medallion = 1 WHERE user_id = ?", (MAGIC_MEDALLION_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"🔮 Вы купили Магический медальон за {MAGIC_MEDALLION_PRICE} Магических коинов!\n"
        f"Теперь в течение 24 часов вы будете получать на 25% больше Магических коинов за магические карты.\n"
        f"🔮 Остаток Магических коинов: {magic_coins - MAGIC_MEDALLION_PRICE}"
    )


async def buy_magic_luck_scroll_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT magic_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    magic_coins = result[0]

    if magic_coins < MAGIC_LUCK_SCROLL_PRICE:
        await callback.answer(f"У вас недостаточно Магических коинов. Нужно {MAGIC_LUCK_SCROLL_PRICE}, а у вас {magic_coins}.")
        return

    cursor.execute("UPDATE users SET magic_coins = magic_coins - ?, has_magic_luck_scroll = 1 WHERE user_id = ?", (MAGIC_LUCK_SCROLL_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"✨ Вы купили Магический свиток удачи за {MAGIC_LUCK_SCROLL_PRICE} Магических коинов!\n"
        f"Теперь в течение 24 часов у вас увеличен шанс на получение редких карт на 20%.\n"
        f"🔮 Остаток Магических коинов: {magic_coins - MAGIC_LUCK_SCROLL_PRICE}"
    )


async def buy_magic_scroll_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT magic_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")
        return

    magic_coins = result[0]

    if magic_coins < MAGIC_SCROLL_PRICE:
        await callback.answer(f"У вас недостаточно Магических коинов. Нужно {MAGIC_SCROLL_PRICE}, а у вас {magic_coins}.")
        return


    cursor.execute("UPDATE users SET magic_coins = magic_coins - ?, last_magic_time = 0 WHERE user_id = ?", (MAGIC_SCROLL_PRICE, user_id))
    conn.commit()

    await callback.message.answer(
        f"🧪 Вы купили Магический свиток за {MAGIC_SCROLL_PRICE} Магических коинов!\n"
        f"Теперь вы можете использовать команду 'магическая битва' без ожидания кулдауна.\n"
        f"🔮 Остаток Магических коинов: {magic_coins - MAGIC_SCROLL_PRICE}"
    )


def register_shop_handlers(dp: Dispatcher, cooldowns: dict):
    dp.register_message_handler(shop_command, commands=["shop"])
    dp.register_callback_query_handler(buy_card_callback, lambda c: c.data == "buy_card")
    dp.register_callback_query_handler(lambda c: buy_coffee_callback(c, cooldowns), lambda c: c.data == "buy_coffee")
    dp.register_callback_query_handler(buy_scratcher_callback, lambda c: c.data == "buy_scratcher")
    dp.register_callback_query_handler(buy_companion_callback, lambda c: c.data == "buy_companion")
    dp.register_callback_query_handler(buy_booster_callback, lambda c: c.data == "buy_booster")
    dp.register_callback_query_handler(buy_time_watch_callback, lambda c: c.data == "buy_time_watch")
    dp.register_callback_query_handler(buy_magic_medallion_callback, lambda c: c.data == "buy_magic_medallion")
    dp.register_callback_query_handler(buy_magic_luck_scroll_callback, lambda c: c.data == "buy_magic_luck_scroll")
    dp.register_callback_query_handler(buy_magic_scroll_callback, lambda c: c.data == "buy_magic_scroll")