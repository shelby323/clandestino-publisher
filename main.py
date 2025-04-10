
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram.filters import Command
from aiogram import Router

import feedparser

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Привет! Я бот-публикатор контента для CLANDESTINO.")

@router.message(Command("ping"))
async def ping_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Я получил твоё сообщение: /ping")

@router.message(Command("news"))
async def news_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return

    urls = [
        "https://www.gq.ru/rss/all",
        "https://www.elle.ru/rss/",
        "https://www.interviewrussia.ru/rss",
        "https://vogue.ru/feed",
        "https://www.the-village.ru/rss",
        "https://daily.afisha.ru/rss/",
        "https://style.rbc.ru/rss/",
        "https://snob.ru/feed/"
    ]

    entries = []
    for url in urls:
        feed = feedparser.parse(url)
        if feed.entries:
            entries.extend(feed.entries)

    if not entries:
        await message.answer("Нет новых новостей.")
        return

    entries.sort(key=lambda e: e.get("published_parsed", None), reverse=True)
    latest = entries[0]

    text = f"<b>{latest.title}</b>
{latest.link}"
    if hasattr(latest, 'media_content'):
        image_url = latest.media_content[0]['url']
        await message.answer_photo(photo=image_url, caption=text, parse_mode=ParseMode.HTML)
    else:
        await message.answer(text, parse_mode=ParseMode.HTML)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
