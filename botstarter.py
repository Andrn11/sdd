import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from commands import register_handlers
from dotenv import load_dotenv
import json


load_dotenv()

with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

API_TOKEN = os.getenv("API_TOKEN")

if API_TOKEN is None:
    raise ValueError("Токен API не установлен. Проверьте файл .env.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

register_handlers(dp)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)