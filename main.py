
import os
import logging
import feedparser
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = [321069928, 5677874594]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.reply("Привет! Я бот-публикатор контента для CLANDESTINO.")

@dp.message_handler(commands=['ping'])
async def ping(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("✅ Я получил твоё сообщение: /ping")

@dp.message_handler(commands=['news', 'новость'])
async def news(message: types.Message):
    if message.from_user.id not in OWNER_IDS:
        return
    url = "https://lenta.ru/rss/news"
    feed = feedparser.parse(url)
    if not feed.entries:
        await message.reply("Не удалось получить новости.")
        return
    entry = feed.entries[0]
    text = f"<b>{entry.title}</b>
{entry.link}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(entry.link) as resp:
                html = await resp.text()
        # Ищем изображение
        import re
        img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if img_match:
            await message.bot.send_photo(chat_id=message.chat.id, photo=img_match.group(1), caption=text, parse_mode='HTML')
        else:
            await message.reply(text, parse_mode='HTML')
    except Exception as e:
        await message.reply(f"Ошибка при получении изображения: {e}")

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)
