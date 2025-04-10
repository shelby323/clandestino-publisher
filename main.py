
import os
import logging
import feedparser
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.reply("Привет! Я бот-публикатор контента для CLANDESTINO.")

@dp.message_handler(commands=['ping'])
async def echo(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Я получил твоё сообщение: " + message.text)

@dp.message_handler(commands=['news', 'новость', 'новости'])
async def send_news(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    feed = feedparser.parse("https://www.vogue.ru/rss.xml")
    if not feed.entries:
        await message.reply("Новостей не найдено.")
        return
    entry = feed.entries[0]
    text = f"<b>{entry.title}</b>\n{entry.link}"
    await message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
