import asyncio
import logging
import os
import random
import re
import feedparser
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.filters.text import Text
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("API_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()
router = Router()

menu_keyboard = InlineKeyboardBuilder()
menu_keyboard.button(text="🎯 Эстетика", callback_data="type:aesthetic")
menu_keyboard.button(text="📰 Новости", callback_data="type:news")
menu_keyboard.button(text="✨ Факт о знаменитости", callback_data="type:celebrity_fact")
menu_keyboard.button(text="📖 История о звезде", callback_data="type:celebrity_story")
menu_keyboard.adjust(2)

persistent_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📋 Меню")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Выбери, какой пост хочешь опубликовать:", reply_markup=menu_keyboard.as_markup())

@router.message(Text(text="меню"))
@router.message(Text(text="📋 Меню"))
async def menu_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await message.answer("Выбери, какой пост хочешь опубликовать:", reply_markup=menu_keyboard.as_markup())

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    data = callback.data
    if data.startswith("type:"):
        post_type = data.split(":")[1]
        if post_type == "news":
            await send_news(callback.message)
        elif post_type == "aesthetic":
            await callback.message.answer("Посты с эстетикой будут реализованы позже.")
        elif post_type == "celebrity_fact":
            await send_celebrity_fact(callback.message)
        elif post_type == "celebrity_story":
            await send_celebrity_story(callback.message)
        await callback.answer()
    elif data in ["post:confirm", "post:cancel"]:
        if data == "post:confirm":
            await post_to_vk(callback.message)
            await callback.message.answer("✅ Пост опубликован в группу ВКонтакте")
        else:
            await callback.message.answer("❌ Публикация отменена")
        await callback.answer()

def clean_html(text):
    return re.sub(r'<[^>]*>', '', text).strip()

async def fetch_pinterest_images(query, limit=3):
    search_url = f"https://www.pinterest.com/search/pins/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            imgs = soup.find_all('img')
            image_urls = [img.get('src') for img in imgs if img.get('src') and '236x' in img.get('src')]
            return image_urls[:limit]

async def fetch_celebrity_facts():
    url = "https://www.factinate.com/people/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            facts = soup.find_all('li')
            return [clean_html(fact.get_text()) for fact in facts if len(fact.get_text()) > 40]

async def fetch_wiki_quote():
    url = "https://en.wikiquote.org/wiki/Special:Random"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            quotes = soup.select('ul li')
            return [q.get_text() for q in quotes if len(q.get_text()) > 40][:5]

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

    query = title.split()[0] + " fashion"
    images = await fetch_pinterest_images(query)

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
    facts = await fetch_celebrity_facts()
    if not facts:
        await message.answer("Фактов не найдено.")
        return
    fact = random.choice(facts)
    query = fact.split()[0] + " celebrity"
    images = await fetch_pinterest_images(query)
    if images:
        await message.answer_photo(photo=images[0], caption=fact)
    else:
        await message.answer(fact)

async def send_celebrity_story(message: Message):
    quotes = await fetch_wiki_quote()
    if not quotes:
        await message.answer("Истории не найдены.")
        return
    story = random.choice(quotes)
    query = story.split()[0] + " portrait"
    images = await fetch_pinterest_images(query)
    if images:
        await message.answer_photo(photo=images[0], caption=story)
    else:
        await message.answer(story)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.set_my_commands([types.BotCommand(command="start", description="Перезапустить бота")])
    await bot.set_chat_menu_button(menu_button=types.MenuButtonCommands())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
