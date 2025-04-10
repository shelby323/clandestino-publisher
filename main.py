import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import Command
from aiogram import Router
import feedparser

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}

router = Router()
SEEN_FILE = "seen.json"

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

    seen_links = set()
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen_links = set(json.load(f))

    entries = []
    for url in urls:
        feed = feedparser.parse(url)
        if feed.entries:
            entries.extend(feed.entries)

    entries.sort(key=lambda e: e.get("published_parsed", None), reverse=True)

    for entry in entries:
        if entry.link in seen_links:
            continue

        seen_links.add(entry.link)
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_links), f)

        text = f"{entry.title}\n\n{entry.get('summary', '')[:300]}...\n{entry.link}"
        image_urls = []

        if hasattr(entry, 'media_content'):
            image_urls = [m['url'] for m in entry.media_content if 'url' in m][:6]
        elif 'image' in entry:
            image_urls = [entry.image.get('href')]

        # Отправим изображения галереей, если больше одного
        if len(image_urls) > 1:
            media = [InputMediaPhoto(media=url) for url in image_urls]
            await message.answer_media_group(media)
        elif image_urls:
            await message.answer_photo(photo=image_urls[0])

        # Отправим текст (plain text, без HTML)
        await message.answer(text)
        return

    await message.answer("Нет новых новостей.")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())