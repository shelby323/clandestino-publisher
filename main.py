
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
    url = "https://www.gq.ru/rss/all"  # Пример RSS-ленты
    feed = feedparser.parse(url)
    if feed.entries:
        entry = feed.entries[0]
        text = f"<b>{entry.title}</b>\n{entry.link}"
        if "media_content" in entry and entry.media_content:
            await message.answer_photo(entry.media_content[0]['url'], caption=text, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await message.answer("Нет новых новостей.")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
