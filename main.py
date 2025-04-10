import asyncio
import logging
import os
import random
import re
import feedparser
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

BOT_TOKEN = os.getenv("API_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()
router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Эстетика", callback_data="type:aesthetic")
    kb.button(text="📰 Новости", callback_data="type:news")
    kb.button(text="✨ Факт о знаменитости", callback_data="type:celebrity_fact")
    kb.adjust(2)
    await message.answer("Выбери, какой пост хочешь опубликовать:", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data and c.data.startswith("type:"))
async def generate_posts(callback: CallbackQuery):
    post_type = callback.data.split(":")[1]
    if post_type == "news":
        await send_news(callback.message)
    elif post_type == "aesthetic":
        await callback.message.answer("Посты с эстетикой будут реализованы позже.")
    elif post_type == "celebrity_fact":
        await callback.message.answer("Посты с фактами о знаменитостях будут реализованы позже.")
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
    random.shuffle(entries)
    latest = entries[0]
    USED_ENTRIES.add(latest.id)

    title = clean_html(latest.get("title", ""))
    summary = clean_html(latest.get("summary", ""))
    text = f"<b>{title}</b>\n\n{summary}\n\n#новости #лакшери"

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

    await message.answer("Пост готов к публикации:")
    if images:
        media_group = [InputMediaPhoto(media=url) for url in images]
        media_group[0].caption = text
        media_group[0].parse_mode = ParseMode.HTML
        await message.answer_media_group(media_group)
    else:
        await message.answer(text, parse_mode=ParseMode.HTML)

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Опубликовать", callback_data="post:confirm")
    kb.button(text="❌ Отменить", callback_data="post:cancel")
    await message.answer("Опубликовать этот пост в группу?", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data in ["post:confirm", "post:cancel"])
async def handle_post_confirmation(callback: CallbackQuery):
    if callback.data == "post:confirm":
        await post_to_vk(callback.message)
        await callback.message.answer("✅ Пост опубликован в группу ВКонтакте")
    else:
        await callback.message.answer("❌ Публикация отменена")
    await callback.answer()

async def post_to_vk(message: Message):
    async with aiohttp.ClientSession() as session:
        async for msg in message.chat.history(limit=10):
            if msg.text and msg.text.startswith("<b>"):
                payload = {
                    "access_token": VK_TOKEN,
                    "v": "5.199",
                    "owner_id": f"-{VK_GROUP_ID}",
                    "message": re.sub(r'<[^>]*>', '', msg.text),
                }
                await session.post("https://api.vk.com/method/wall.post", data=payload)
                break

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
