
import asyncio
import logging
import os
import feedparser
import random

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.filters import Command
from aiogram import Router

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}

RSS_FEEDS = [
    "https://www.vogue.com/rss",
    "https://hypebeast.com/feed",
    "https://www.highsnobiety.com/rss",
    "https://www.dazeddigital.com/rss",
    "https://theartwolf.com/rss",
    "https://www.justluxe.com/rss/",
    "https://www.luxuo.com/feed",
    "https://www.eonline.com/syndication/feeds/rssfeeds/topstories.xml",
    "https://pagesix.com/feed/"
]

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Привет! Я бот-публикатор контента для CLANDESTINO. Напиши /news или /новость.")

@router.message(Command("ping"))
async def ping_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Я в сети и готов к работе.")

@router.message(Command("news", "новость"))
async def news_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return

    all_entries = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            all_entries.extend(feed.entries[:2])  # максимум по 2 из каждой
        except Exception as e:
            continue

    if not all_entries:
        await message.answer("Не удалось получить новости.")
        return

    entry = random.choice(all_entries)
    title = entry.get("title", "Без заголовка")
    link = entry.get("link", "")
    summary = entry.get("summary", "")

    image = ""
    if "media_content" in entry and entry.media_content:
        image = entry.media_content[0].get("url", "")
    elif "media_thumbnail" in entry and entry.media_thumbnail:
        image = entry.media_thumbnail[0].get("url", "")

    text = f"<b>{title}</b>\n{link}"

    try:
        if image:
            await message.answer_photo(photo=image, caption=text, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)
    except:
        await message.answer(text)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
