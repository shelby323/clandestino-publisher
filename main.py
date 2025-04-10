import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import feedparser
import re
import random

BOT_TOKEN = os.getenv("API_TOKEN")
OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()
router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="💫 Эстетика", callback_data="type:aesthetic")
    kb.button(text="📰 Новость", callback_data="type:news")
    kb.button(text="⭐ Факт о знаменитости", callback_data="type:celebrity_fact")
    kb.adjust(2)
    await message.answer("Выбери, какой пост хочешь опубликовать:", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data and c.data.startswith("type:"))
async def generate_post(callback: CallbackQuery):
    post_type = callback.data.split(":")[1]
    if post_type == "news":
        await send_news(callback.message)
    elif post_type == "aesthetic":
        await callback.message.answer("Посты с эстетикой будут реализованы позже.")
    elif post_type == "celebrity_fact":
        await callback.message.answer("Факты о знаменитостях будут добавлены позже.")
    await callback.answer()

def clean_html(text):
    return re.sub(r'<[^>]*>', '', text).strip()

async def send_news(message: Message):
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
    text = f"<b>{title}</b>

{summary[:500]}..."

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
        media_group[0].parse_mode = "HTML"
        await message.answer_media_group(media_group)
    else:
        await message.answer(text, parse_mode="HTML")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
