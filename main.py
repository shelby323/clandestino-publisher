
import asyncio
import logging
import os
import random
import re
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import Command
import feedparser

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()

router = Router()

def clean_html(text):
    return re.sub(r'<[^>]*>', '', text).strip()

def stylize_post(entry):
    title = clean_html(entry.get("title", ""))
    summary = clean_html(entry.get("summary", ""))[:300]
    link = entry.get("link", "")

    intros = [
        "Забудь, как было вчера.",
        "Мода? Нет. Это провокация.",
        "Где стиль — там CLANDESTINO.",
        "Ты к этому не готов. Но мы покажем.",
        "Всё, что ты знал — устарело.",
        "Эстетика ударом по лицу.",
        "Смотри. Читай. Молчи."
    ]
    ending_tags = ["#clandestino", "#мода", "#искусство", "#luxury", "#стиль", "#тебенемодно", "#андеграунд"]

    intro = random.choice(intros)
    tags = " ".join(random.sample(ending_tags, 2))

    text = f"{intro}\n\n{title}\n\n{summary}\n\n{link}\n\n{tags}"
    return text

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id in OWNER_IDS:
        await message.answer("CLANDESTINO здесь. Готов к эстетике и дерзости.")

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
        await message.answer("Нет новых дерзких новостей. Придётся делать самому.")
        return

    entries.sort(key=lambda e: e.get("published_parsed", None), reverse=True)
    latest = entries[0]
    USED_ENTRIES.add(latest.id)

    text = stylize_post(latest)

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
        media_group[0].caption = text[:1024]
        await message.answer_media_group(media_group)
        if len(text) > 1024:
            await message.answer(text[1024:])
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
