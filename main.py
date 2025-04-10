
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import Command
import feedparser
import re

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()

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

def clean_html(text):
    return re.sub(r'<[^>]*>', '', text).strip()

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
        for entry in feed.entries:
            if entry.id not in USED_ENTRIES:
                entries.append(entry)

    if not entries:
        await message.answer("Нет новых новостей.")
        return

    entries.sort(key=lambda e: e.get("published_parsed", None), reverse=True)
    latest = entries[0]
    USED_ENTRIES.add(latest.id)

    title = clean_html(latest.get("title", ""))
    summary = clean_html(latest.get("summary", ""))
    link = latest.get("link", "")

    text = f"{title}\n\n{summary}\n\n{link}"

    images = []
    if "media_content" in latest:
        for media in latest.media_content[:6]:
            if "url" in media:
                images.append(media["url"])
    elif "links" in latest:
        for link_info in latest.links:
            if link_info.get("type", "").startswith("image/"):
                images.append(link_info["href"])
        images = images[:6]

    if images:
        media_group = [InputMediaPhoto(media=url) for url in images]
        media_group[0].caption = text
        await message.answer_media_group(media_group)
    else:
        await message.answer(text)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
