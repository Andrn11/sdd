import logging
from aiogram import Dispatcher, types
import random
import time
import sqlite3
import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data import cats, rarity_weights
from lecsicon import cat_synonyms
from aiogram.types import ParseMode
from Magicsends import register_magic_handlers as register_magic_handlers, jujitsu_command
from shop import register_shop_handlers as register_shop_handlers, shop_command
from ledersboard import register_leaderboard_handlers, leders_command
from ValutionTrade import register_valution_trade_handlers, exchange_command
#from Trade import register_trade_handlers



with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)


async def on_bot_added_to_group(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == 'member' and event.new_chat_member.user.id == event.bot.id:
        await event.bot.send_message(
            event.chat.id,
            "Привет! Я новый карточный бот в вашей группе, напишите 'кот' и получите коллекционную карточку мемного кота! Используйте /bonus для получения бонуса. Напишите Магическая битва и получите магическую карточку."
        )



try:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
except sqlite3.Error as e:
    logging.error(f"Ошибка подключения к базе данных: {e}")
    raise

def check_and_add_magic_scroll_column():
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        if "has_magic_scroll" not in [column[1] for column in columns]:
            cursor.execute("ALTER TABLE users ADD COLUMN has_magic_scroll INTEGER DEFAULT 0")
            conn.commit()
            logging.info("Столбец has_magic_scroll добавлен в таблицу users.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке/добавлении столбца has_magic_scroll: {e}")


check_and_add_magic_scroll_column()

def create_user_cards_table():
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_cards (
                user_id INTEGER,
                card_id TEXT,
                username,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (card_id) REFERENCES cards(cat_id),
                PRIMARY KEY (user_id, card_id)
            );
        ''')
        conn.commit()
        logging.info("Таблица user_cards создана или уже существует.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании таблицы user_cards: {e}")


create_user_cards_table()



try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            rarity TEXT,
            username,
            points INTEGER,
            highest_rarity TEXT,
            cat_coins INTEGER DEFAULT 0,
            last_cat_time INTEGER DEFAULT 0,
            last_bonus_time INTEGER DEFAULT 0,
            last_put_time INTEGER DEFAULT 0,
            has_scratcher INTEGER DEFAULT 0,
            has_companion INTEGER DEFAULT 0,
            booster_end_time INTEGER DEFAULT 0,
            has_time_watch INTEGER DEFAULT 0,
            magic_coins INTEGER DEFAULT 0,
            has_magic_medallion INTEGER DEFAULT 0,
            has_magic_luck_scroll INTEGER DEFAULT 0,
            last_magic_time INTEGER DEFAULT 0
        );
    ''')
    conn.commit()
except sqlite3.Error as e:
    logging.error(f"Ошибка при создании таблицы users: {e}")

def check_and_create_tables():
    try:

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
        if not cursor.fetchone():

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username,
                    user_id INTEGER,
                    cat_id TEXT,
                    cat_image TEXT,
                    rarity TEXT,
                    points INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, cat_id)
                );
            ''')
            conn.commit()
            print("Таблица cards создана.")
        else:
            print("Таблица cards уже существует.")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при проверке/создании таблицы cards: {e}")


check_and_create_tables()


rarities = [
    "обычный",
    "редкий",
    "сверхредкий",
    "эпический",
    "мифический",
    "легендарный",
    "хромотический",
    "особый"
]


cooldown_cat = config['cooldowns']['cat']
cooldown_bonus = config['cooldowns']['bonus']
cooldown_put = config['cooldowns']['put']


cooldowns = {}
bonus_cooldowns = {}


def get_random_cat(cats, has_magic_luck_scroll=False):
    weighted_cats = []
    for cat in cats:
        if has_magic_luck_scroll:

            if cat["rarity"] in ["сверхредкий", "эпический", "мифический", "легендарный", "хромотический", "особый"]:
                weight = rarity_weights.get(cat["rarity"], 1)
                weighted_cats.extend([cat] * weight)
        else:
            weight = rarity_weights.get(cat["rarity"], 1)
            weighted_cats.extend([cat] * weight)
    return random.choice(weighted_cats)


def get_user_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def get_user_cat_coins(user_id):
    cursor.execute("SELECT cat_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def get_user_magic_coins(user_id):
    cursor.execute("SELECT magic_coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username  # Получаем username пользователя

    # Проверяем, есть ли пользователь в базе данных
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        # Если пользователя нет, добавляем его в базу данных
        cursor.execute(
            "INSERT INTO users (user_id, username, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, "обычный", 0, "обычный", 0),
        )
        conn.commit()
    else:
        # Если пользователь уже есть, обновляем его username (на случай, если он изменился)
        cursor.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )
        conn.commit()

    await message.answer("Привет! Напиши 'кот', чтобы получить карточку кота, или используй /bonus для бонусной карточки!")



async def help_command(message: types.Message):
    await message.answer(
        "✨ Список команд: ✨\n\n"
        "———————————————————————————-———————————————————————————-\n"
        "👋 /start - Начать работу с ботом\n"
        "———————————————————————————-———————————————————————————-\n"
        "🐱 кот - Получить случайную карточку кота (кулдаун: 3 часа, писать в чат)\n"
        "———————————————————————————-———————————————————————————-\n"
        "🎁 /bonus - Получить бонусную карточку кота (кулдаун: 6 часов)\n"
        "———————————————————————————-———————————————————————————-\n"
        "🛒 /shop - Магазин (покупка карточек и чашки кофе)\n"
        "———————————————————————————-———————————————————————————-\n"
        "👤 /profil - Ваш профиль\n"
        "———————————————————————————-———————————————————————————-\n"
        "🤗 /put - Погладить котика и получить 1000 очков (требуется Чесалка, кулдаун: 2 часа)\n"
        "———————————————————————————-———————————————————————————-\n"
        "📚 /collection - Просмотреть вашу коллекцию карточек\n"
        "———————————————————————————-———————————————————————————-\n"
        "🐾 /cat - Получить случайную карточку кота (кулдаун: 3 часа)\n"
        "———————————————————————————-———————————————————————————-\n"
        "⚔️ Битва - Получить магическую карту (Писать в чат)\n"
        "———————————————————————————-———————————————————————————-\n"
        "🪄 /jujitsu - Получить магическую карту\n"
        "———————————————————————————-———————————————————————————-\n"
        "🏆 /leders - Просмотреть лидерборд\n"
        "———————————————————————————-———————————————————————————-\n"
        "🔄 /exchange - Обмен валют\n"
        "———————————————————————————-———————————————————————————-\n"
    )



async def cat_command(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    cursor.execute("SELECT has_time_watch, has_magic_luck_scroll FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        cursor.execute(
            "INSERT INTO users (user_id, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?)",
            (user_id, "обычный", 0, "обычный", 0),
        )
        conn.commit()
        has_time_watch = 0
        has_magic_luck_scroll = 0
    else:
        has_time_watch, has_magic_luck_scroll = user_data

    if has_time_watch:
        cooldowns[user_id] = 0
        cursor.execute("UPDATE users SET has_time_watch = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

    if user_id in cooldowns:
        remaining_time = config['cooldowns']['cat'] - (current_time - cooldowns[user_id])
        if remaining_time > 0:
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            await message.answer(
                f"Вы осмотрелись, но не нашли кота на диване. Попробуйте через {hours} часов {minutes} минут."
            )
            return

    cooldowns[user_id] = current_time

    cursor.execute("SELECT booster_end_time FROM users WHERE user_id = ?", (user_id,))
    booster_end_time = cursor.fetchone()[0]
    is_booster_active = booster_end_time and booster_end_time > current_time

    if is_booster_active:
        points_multiplier = 1.5
        coins_multiplier = 1.5
    else:
        points_multiplier = 1.0
        coins_multiplier = 1.0

    cursor.execute("SELECT has_companion FROM users WHERE user_id = ?", (user_id,))
    has_companion = cursor.fetchone()[0]

    if has_companion:
        num_cards = 2
        cursor.execute("UPDATE users SET has_companion = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    else:
        num_cards = 1

    for _ in range(num_cards):
        cat = get_random_cat(cats, has_magic_luck_scroll)

        cat["points"] = int(cat["points"] * points_multiplier)
        cat["cat_coins"] = int(cat["cat_coins"] * coins_multiplier)

        rarities_str = ", ".join(rarities)

        try:
            cursor.execute(
                f"""
                   INSERT INTO users (user_id, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET 
                       rarity = excluded.rarity, 
                       points = points + excluded.points, 
                       highest_rarity = CASE 
                           WHEN INSTR('{rarities_str}', ?) > INSTR('{rarities_str}', highest_rarity) THEN ? 
                           ELSE highest_rarity 
                       END,
                       cat_coins = cat_coins + excluded.cat_coins
               """,
                (
                    user_id,
                    cat["rarity"],
                    cat["points"],
                    cat["rarity"],
                    cat["cat_coins"],
                    cat["rarity"],
                    cat["rarity"],
                ),
            )
            conn.commit()

            cursor.execute(
                "SELECT id FROM cards WHERE user_id = ? AND cat_id = ?",
                (user_id, cat["id"]),
            )
            existing_card = cursor.fetchone()

            if not existing_card:
                cursor.execute(
                    "INSERT INTO cards (user_id, cat_id, cat_image, rarity, points) VALUES (?, ?, ?, ?, ?)",
                    (user_id, cat["id"], cat["photo"], cat["rarity"], cat["points"]),
                )
                conn.commit()

            message_text = (
                f"👤 {message.from_user.first_name}, успех! Вы нашли карточку. \n"
                f"🌟 Карточка «{cat['catname']}» 🐱\n"
                "--------------------------\n"
                f"💎 Редкость: {cat['rarity']}\n"
                f"✨ Очки: +{cat['points']} (Всего: {get_user_points(user_id)})\n"
                f"🐱 Котокоины: +{cat['cat_coins']} (Всего: {get_user_cat_coins(user_id)})\n"
                f"🧧 Описание: {cat['catinfo']}\n"
            )

            if is_booster_active:
                message_text += "🚀 Активен Кот-бустер: +50% очков и котокоинов!\n"

            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("🔄 Получить еще карточку", callback_data="get_another_card"),
                InlineKeyboardButton("📚 Просмотреть коллекцию", callback_data="view_collection")
            )

            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=cat["photo"],
                caption=message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=message.message_id,
                reply_markup=keyboard,
            )
        except sqlite3.Error as e:
            logging.error(f"Ошибка базы данных: {e}")
            await message.answer("Произошла ошибка.")

    if has_magic_luck_scroll:
        cursor.execute("UPDATE users SET has_magic_luck_scroll = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

async def send_cat(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    cursor.execute("SELECT has_time_watch, has_magic_luck_scroll FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        cursor.execute(
            "INSERT INTO users (user_id, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?)",
            (user_id, "обычный", 0, "обычный", 0),
        )
        conn.commit()
        has_time_watch = 0
        has_magic_luck_scroll = 0
    else:
        has_time_watch, has_magic_luck_scroll = user_data

    if has_time_watch:
        cooldowns[user_id] = 0
        cursor.execute("UPDATE users SET has_time_watch = 0 WHERE user_id = ?", (user_id,))
        conn.commit()

    if user_id in cooldowns:
        remaining_time = config['cooldowns']['cat'] - (current_time - cooldowns[user_id])
        if remaining_time > 0:
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            await message.answer(
                f"Вы осмотрелись, но не нашли кота на диване. Попробуйте через {hours} часов {minutes} минут."
            )
            return

    cooldowns[user_id] = current_time

    cursor.execute("SELECT booster_end_time FROM users WHERE user_id = ?", (user_id,))
    booster_end_time = cursor.fetchone()[0]
    is_booster_active = booster_end_time and booster_end_time > current_time

    if is_booster_active:
        points_multiplier = 1.5
        coins_multiplier = 1.5
    else:
        points_multiplier = 1.0
        coins_multiplier = 1.0

    cursor.execute("SELECT has_companion FROM users WHERE user_id = ?", (user_id,))
    has_companion = cursor.fetchone()[0]

    if has_companion:
        num_cards = 2
        cursor.execute("UPDATE users SET has_companion = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    else:
        num_cards = 1

    for _ in range(num_cards):
        cat = get_random_cat(cats, has_magic_luck_scroll)

        cat["points"] = int(cat["points"] * points_multiplier)
        cat["cat_coins"] = int(cat["cat_coins"] * coins_multiplier)

        rarities_str = ", ".join(rarities)

        try:
            cursor.execute(
                f"""
                INSERT INTO users (user_id, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    rarity = excluded.rarity, 
                    points = points + excluded.points, 
                    highest_rarity = CASE 
                        WHEN INSTR('{rarities_str}', ?) > INSTR('{rarities_str}', highest_rarity) THEN ? 
                        ELSE highest_rarity 
                    END,
                    cat_coins = cat_coins + excluded.cat_coins
            """,
                (
                    user_id,
                    cat["rarity"],
                    cat["points"],
                    cat["rarity"],
                    cat["cat_coins"],
                    cat["rarity"],
                    cat["rarity"],
                ),
            )
            conn.commit()

            cursor.execute(
                "SELECT id FROM cards WHERE user_id = ? AND cat_id = ?",
                (user_id, cat["id"]),
            )
            existing_card = cursor.fetchone()

            if not existing_card:
                cursor.execute(
                    "INSERT INTO cards (user_id, cat_id, cat_image, rarity, points) VALUES (?, ?, ?, ?, ?)",
                    (user_id, cat["id"], cat["photo"], cat["rarity"], cat["points"]),
                )
                conn.commit()

            message_text = (
                f"👤 {message.from_user.first_name}, успех! Вы нашли карточку. \n"
                f"🌟 Карточка «{cat['catname']}» 🐱\n"
                "--------------------------\n"
                f"💎 Редкость: {cat['rarity']}\n"
                f"✨ Очки: +{cat['points']} (Всего: {get_user_points(user_id)})\n"
                f"🐱 Котокоины: +{cat['cat_coins']} (Всего: {get_user_cat_coins(user_id)})\n"
                f"🧧 Описание: {cat['catinfo']}\n"
            )

            if is_booster_active:
                message_text += "🚀 Активен Кот-бустер: +50% очков и котокоинов!\n"

            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("🔄 Получить еще карточку", callback_data="get_another_card"),
                InlineKeyboardButton("📚 Просмотреть коллекцию", callback_data="view_collection")
            )

            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=cat["photo"],
                caption=message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=message.message_id,
                reply_markup=keyboard,
            )
        except sqlite3.Error as e:
            logging.error(f"Ошибка базы данных: {e}")
            await message.answer("Произошла ошибка.")


    if has_magic_luck_scroll:
        cursor.execute("UPDATE users SET has_magic_luck_scroll = 0 WHERE user_id = ?", (user_id,))
        conn.commit()


async def bonus_command(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    if user_id in bonus_cooldowns:
        remaining_time = 21600 - (current_time - bonus_cooldowns[user_id])
        if remaining_time > 0:
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            await message.answer(
                f"Вы осмотрелись, но не нашли бонус на полке. Попробуйте через {hours} часов {minutes} минут."
            )
            return

    bonus_cooldowns[user_id] = current_time

    cat = get_random_cat(cats)

    rarities_str = ", ".join(rarities)

    try:
        cursor.execute(
            f"""
            INSERT INTO users (user_id, rarity, points, highest_rarity, cat_coins) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                rarity = excluded.rarity, 
                points = points + excluded.points, 
                highest_rarity = CASE 
                    WHEN INSTR('{rarities_str}', ?) > INSTR('{rarities_str}', highest_rarity) THEN ? 
                    ELSE highest_rarity 
                END,
                cat_coins = cat_coins + excluded.cat_coins
        """,
            (
                user_id,
                cat["rarity"],
                cat["points"],
                cat["rarity"],
                cat["cat_coins"],
                cat["rarity"],
                cat["rarity"],
            ),
        )
        conn.commit()

        cursor.execute(
            "SELECT id FROM cards WHERE user_id = ? AND cat_id = ?",
            (user_id, cat["id"]),
        )
        existing_card = cursor.fetchone()

        if not existing_card:
            cursor.execute(
                "INSERT INTO cards (user_id, cat_id, cat_image, rarity, points) VALUES (?, ?, ?, ?, ?)",
                (user_id, cat["id"], cat["photo"], cat["rarity"], cat["points"]),
            )
            conn.commit()

        message_text = (
            f"👤 {message.from_user.first_name}, успех! Вы нашли бонусную карточку. \n"
            f"🌟 Карточка: «{cat['catname']}» 🐱\n"
            "--------------------------\n"
            f"💎 Редкость: {cat['rarity']}\n"
            f"✨ Очки: +{cat['points']} (Всего: {get_user_points(user_id)})\n"
            f"🐱 Котокоины: +{cat['cat_coins']} (Всего: {get_user_cat_coins(user_id)})\n"
            f"🧧 Описание: {cat['catinfo']}"
        )

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🔄 Получить еще карточку", callback_data="get_bonus_card"),
            InlineKeyboardButton("📚 Просмотреть коллекцию", callback_data="view_collection")
        )

        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=cat["photo"],
            caption=message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=message.message_id,
        )
    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        await message.answer("Произошла ошибка.")


async def profil_command(message: types.Message):
    user_id = message.from_user.id
    cursor.execute(
        "SELECT rarity, points, highest_rarity, cat_coins, magic_coins, has_scratcher, has_companion, booster_end_time, has_time_watch, has_magic_medallion, has_magic_luck_scroll FROM users WHERE user_id = ?",
        (user_id,),
    )
    user_data = cursor.fetchone()
    if user_data:
        rarity, points, highest_rarity, cat_coins, magic_coins, has_scratcher, has_companion, booster_end_time, has_time_watch, has_magic_medallion, has_magic_luck_scroll = user_data
        booster_status = "активен" if booster_end_time and booster_end_time > time.time() else "не активен"
        await message.answer(
            f"Ваш профиль:\n"
            f"💎 Редкость: {rarity}\n"
            f"✨ Очки: {points}\n"
            f"🏆 Самая высокая редкость: {highest_rarity}\n"
            f"🐱 Котокоины: {cat_coins}\n"
            f"🔮 Магические коины: {magic_coins}\n"
            f"🐾 Чесалка: {'есть' if has_scratcher else 'нет'}\n"
            f"🐱 Кот компаньон: {'есть' if has_companion else 'нет'}\n"
            f"🚀 Кот-бустер: {booster_status}\n"
            f"⏳ Часы времени: {'есть' if has_time_watch else 'нет'}\n"
            f"🔮 Магический медальон: {'есть' if has_magic_medallion else 'нет'}\n"
            f"✨ Магический свиток удачи: {'есть' if has_magic_luck_scroll else 'нет'}"
        )
    else:
        await message.answer("У вас еще нет профиля. Получите кота, чтобы создать его!")


async def put_command(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    cursor.execute("SELECT has_scratcher, last_put_time FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        await message.answer("У вас нет Чесалки! Купите её в магазине, чтобы гладить котика.")
        return

    has_scratcher, last_put_time = result

    if last_put_time and (current_time - last_put_time) < 7200:
        remaining_time = 7200 - (current_time - last_put_time)
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        await message.answer(
            f"Вы уже гладили котика недавно. Попробуйте снова через {hours} часов {minutes} минут."
        )
        return

    cursor.execute("UPDATE users SET last_put_time = ? WHERE user_id = ?", (current_time, user_id))
    conn.commit()

    cursor.execute("UPDATE users SET points = points + 1000 WHERE user_id = ?", (user_id,))
    conn.commit()

    await message.answer(
        "Вы погладили котика и получили 1000 очков! 🐾\n"
        "Котик доволен и мурлычет от удовольствия!"
    )


async def collection_command(message: types.Message):
    user_id = message.from_user.id

    cursor.execute("SELECT cat_image, rarity, points, cat_id FROM cards WHERE user_id = ?", (user_id,))
    cards = cursor.fetchall()

    if not cards:
        await message.answer("У вас пока нет карточек в коллекции.")
        return

    await show_card(message, cards, 0)


async def show_card(message: types.Message, cards: list, index: int):
    if index >= len(cards) or index < 0:
        await message.answer("Это все ваши карточки!")
        return

    cat_image, rarity, points, cat_id = cards[index]

    cat = next((cat for cat in cats if cat["id"] == cat_id), None)
    cat_name = cat["catname"] if cat else "Неизвестный кот"

    keyboard = InlineKeyboardMarkup(row_width=2)

    if index > 0:
        keyboard.insert(InlineKeyboardButton("⬅️", callback_data=f"prev_card_{index - 1}"))

    if index < len(cards) - 1:
        keyboard.insert(InlineKeyboardButton("➡️", callback_data=f"next_card_{index + 1}"))

    await message.bot.send_photo(
        chat_id=message.chat.id,
        photo=cat_image,
        caption=f"🐱 Имя: {cat_name}\n💎 Редкость: {rarity}\n✨ Очки: {points}",
        reply_markup=keyboard,
    )


async def next_card_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    index = int(callback.data.split("_")[2])

    cursor.execute("SELECT cat_image, rarity, points, cat_id FROM cards WHERE user_id = ?", (user_id,))
    cards = cursor.fetchall()

    await callback.message.delete()

    await show_card(callback.message, cards, index)


async def prev_card_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    index = int(callback.data.split("_")[2])

    cursor.execute("SELECT cat_image, rarity, points, cat_id FROM cards WHERE user_id = ?", (user_id,))
    cards = cursor.fetchall()

    await callback.message.delete()

    await show_card(callback.message, cards, index)


async def get_another_card_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_time = time.time()

    if user_id in cooldowns:
        remaining_time = 10800 - (current_time - cooldowns[user_id])
        if remaining_time > 0:
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            await callback.answer(
                f"Вы можете получить еще карточку кота через {hours} часов {minutes} минут."
            )
            return

    await callback.answer("Получение карточки...")
    await send_cat(callback.message)


async def get_bonus_card_callback(callback: types.CallbackQuery):
    current_user_id = callback.from_user.id
    current_time = time.time()

    if current_user_id in bonus_cooldowns:
        bonus_remaining_time = 21600 - (current_time - bonus_cooldowns[current_user_id])
        if bonus_remaining_time > 0:
            hours = int(bonus_remaining_time // 3600)
            minutes = int((bonus_remaining_time % 3600) // 60)
            await callback.answer(
                f"Вы можете получить еще бонусную карточку через {hours} часов {minutes} минут."
            )
            return

    await callback.answer("Получение бонусной карточки...")
    bonus_cooldowns[current_user_id] = current_time


async def view_collection_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    cursor.execute("SELECT cat_image, rarity, points, cat_id FROM cards WHERE user_id = ?", (user_id,))
    cards = cursor.fetchall()

    if not cards:
        await callback.answer("У вас пока нет карточек в коллекции.")
        return

    await show_card(callback.message, cards, 0)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_command, commands=["start"])
    dp.register_message_handler(help_command, commands=["help"])
    dp.register_message_handler(cat_command, commands=["cat"])
    dp.register_message_handler(send_cat, lambda message: message.text.lower() == "кот")
    dp.register_message_handler(bonus_command, commands=["bonus"])
    dp.register_message_handler(profil_command, commands=["profil"])
    dp.register_message_handler(put_command, commands=["put"])
    dp.register_message_handler(collection_command, commands=["collection"])
    dp.register_callback_query_handler(next_card_callback, lambda c: c.data.startswith("next_card_"))
    dp.register_callback_query_handler(prev_card_callback, lambda c: c.data.startswith("prev_card_"))
    dp.register_callback_query_handler(get_another_card_callback, lambda c: c.data == "get_another_card")
    dp.register_message_handler(send_cat, lambda message: message.text.lower() in cat_synonyms)
    dp.register_callback_query_handler(get_bonus_card_callback, lambda c: c.data == "get_bonus_card")
    dp.register_callback_query_handler(view_collection_callback, lambda c:c.data == "view_collection")
    dp.register_callback_query_handler(start_command, lambda c: c.data == "start_command")
    dp.register_callback_query_handler(send_cat, lambda c: c.data == "send_cat")
    dp.register_callback_query_handler(bonus_command, lambda c: c.data == "bonus_command")
    dp.register_callback_query_handler(shop_command, lambda c: c.data == "shop_command")
    dp.register_callback_query_handler(profil_command, lambda c: c.data == "profil_command")
    dp.register_callback_query_handler(put_command, lambda c: c.data == "put_command")
    dp.register_callback_query_handler(collection_command, lambda c: c.data == "collection_command")
    dp.register_callback_query_handler(jujitsu_command, lambda c: c.data == "jujitsu_command")
    dp.register_callback_query_handler(leders_command, lambda c: c.data == "leders_command")
    dp.register_callback_query_handler(exchange_command, lambda c: c.data == "exchange_command")
    dp.register_my_chat_member_handler(on_bot_added_to_group)
    register_magic_handlers(dp)
    register_shop_handlers(dp, cooldowns)
    register_leaderboard_handlers(dp)
    register_valution_trade_handlers(dp)
    #register_trade_handlers(dp)
