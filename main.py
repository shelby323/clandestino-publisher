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
    kb.button(text="📖 История о звезде", callback_data="type:celebrity_story")
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
        await send_celebrity_fact(callback.message)
    elif post_type == "celebrity_story":
        await send_celebrity_story(callback.message)
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
            if entry.id not in USED_ENTRIES and any(kw in entry.title.lower() for kw in ["звезда", "мода", "стиль", "красота", "лук", "celebrity", "луки"]):
                entries.append(entry)
    if not entries:
        await message.answer("Нет новых подходящих новостей.")
        return
    random.shuffle(entries)
    latest = entries[0]
    USED_ENTRIES.add(latest.id)

    title = clean_html(latest.get("title", ""))
    summary = clean_html(latest.get("summary", ""))
    text = f"<b>{title}</b>\n\n{summary}\n\n#новости #лакшери"

    images = []
    media_fields = ["media_content", "media_thumbnail"]
    for field in media_fields:
        if field in latest:
            for media in latest[field][:6]:
                if "url" in media:
                    images.append(media["url"])
    if not images and "links" in latest:
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

async def send_celebrity_fact(message: Message):
    facts = [
        {
            "text": "🧠 В юности Киану Ривз мечтал стать хоккеистом, а не актёром.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/7/79/Keanu_Reeves_2013.jpg"
        },
        {
            "text": "💄 Одри Хепбёрн носила одежду только от Givenchy — так родилась мода на коллаборации со звёздами.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Audrey_Hepburn_1956.jpg"
        },
        {
            "text": "👑 Рианна стала первой женщиной-исполнительницей, открывшей модный дом Fenty под крылом LVMH.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Rihanna_2018.png"
        }
    ]
    fact = random.choice(facts)
    await message.answer_photo(photo=fact["image"], caption=fact["text"])

async def send_celebrity_story(message: Message):
    stories = [
        {
            "text": "💋 Марлен Дитрих отказалась от голливудских стереотипов и ввела в моду мужские костюмы на женщинах.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/4/41/Marlene_Dietrich_%281930%29.jpg"
        },
        {
            "text": "📸 Вивьен Вествуд — королева панк-эстетики, доказала, что стиль — это вызов, а не компромисс.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/9/93/Vivienne_Westwood_2008.jpg"
        },
        {
            "text": "🔥 Бейонсе когда-то проиграла кастинг на роль в Disney, а теперь диктует стандарты моды и поп-культуры.",
            "image": "https://upload.wikimedia.org/wikipedia/commons/1/10/Beyonce_2011.jpg"
        }
    ]
    story = random.choice(stories)
    await message.answer_photo(photo=story["image"], caption=story["text"])

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
