import os
import logging
import feedparser
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Разрешённые пользователи
ALLOWED_USERS = [321069928, 5677874594]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    await message.reply("Привет! Я бот-публикатор контента для CLANDESTINO. Используй команду /новость для получения свежей новости.")

@dp.message_handler(commands=['новость'])
async def send_news(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return

    # RSS источник
    feed_url = "https://www.vogue.ru/rss/all"
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        await message.answer("Не удалось загрузить новости 😔")
        return

    entry = feed.entries[0]
    title = entry.get("title", "Без заголовка")
    link = entry.get("link", "")
    summary = entry.get("summary", "")
    
    # Попробуем достать изображение из описания
    img_url = ""
    if "media_content" in entry:
        img_url = entry.media_content[0]["url"]
    elif "media_thumbnail" in entry:
        img_url = entry.media_thumbnail[0]["url"]

    text = f"<b>{title}</b>\n\n{summary}\n\n<a href='{link}'>Читать далее</a>"

    try:
        if img_url:
            await bot.send_photo(message.chat.id, photo=img_url, caption=title, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"{title}\n{link}")

@dp.message_handler()
async def echo(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    await message.answer("Команда не распознана. Используй /новость или /help.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)