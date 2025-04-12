import logging
import os
import random
import re
import feedparser
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InputMediaPhoto, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from bs4 import BeautifulSoup
import openai

BOT_TOKEN = os.getenv("API_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

OWNER_IDS = {321069928, 5677874594}
USED_ENTRIES = set()
router = Router()

menu_keyboard = InlineKeyboardBuilder()
menu_keyboard.button(text="🎯 Эстетика", callback_data="type:aesthetic")
menu_keyboard.button(text="📰 Новости", callback_data="type:news")
menu_keyboard.button(text="✨ Факт о знаменитости", callback_data="type:celebrity_fact")
menu_keyboard.button(text="📖 История о звезде", callback_data="type:celebrity_story")
menu_keyboard.adjust(2)

news_source_keyboard = InlineKeyboardBuilder()
news_source_keyboard.button(text="🛰 Новости из соцсетей", callback_data="news_vk")
news_source_keyboard.button(text="🗞 Новости с RSS", callback_data="news_rss")
news_source_keyboard.adjust(1)

persistent_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📜 Меню")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

def clean_html(text):
    return re.sub(r'<[^>]*>', '', text).strip()

async def send_menu(message: Message):
    await message.answer("Выбери, какой пост хочешь опубликовать:", reply_markup=menu_keyboard.as_markup())

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    await send_menu(message)
    await message.answer("Меню доступно ниже", reply_markup=persistent_keyboard)

@router.message()
async def menu_handler(message: Message):
    if message.from_user.id not in OWNER_IDS:
        return
    user_input = message.text.strip().lower()
    if "меню" in user_input:
        await send_menu(message)

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    try:
        data = callback.data
        if data.startswith("type:"):
            post_type = data.split(":")[1]
            if post_type == "news":
                await callback.message.answer("Выбери источник новостей:", reply_markup=news_source_keyboard.as_markup())
            elif post_type == "aesthetic":
                await callback.message.answer("Посты с эстетикой будут реализованы позже.")
            elif post_type == "celebrity_fact":
                await send_celebrity_fact(callback.message)
            elif post_type == "celebrity_story":
                await send_celebrity_story(callback.message)
        elif data == "news_vk":
            await send_vk_news(callback.message)
        elif data == "news_rss":
            await send_rss_news(callback.message)
        elif data in ["post:confirm", "post:cancel"]:
            if data == "post:confirm":
                await post_to_vk(callback.message)
                await callback.message.answer("✅ Пост опубликован в группу ВКонтакте")
            else:
                await callback.message.answer("❌ Публикация отменена")
        await callback.answer()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка в обработке: {str(e)}")

async def fetch_vk_group_posts(group_ids=None, count=5):
    if group_ids is None:
        group_ids = [
            "ray.blog", "instalove", "gorod_grexxxov", "urban.bliss", "cherrybombcult",
            "soft.rage", "beautycore.club", "kinky.journal", "glittermag", "glamcrushmag"
        ]
    posts = []
    async with aiohttp.ClientSession() as session:
        for group_id in group_ids:
            print(f"📡 Обрабатываем группу: {group_id}")
            url = f"https://api.vk.com/method/wall.get?domain={group_id}&count={count}&access_token={VK_TOKEN}&v=5.199"
            async with session.get(url) as response:
                result = await response.json()
                print(f"📥 Получен ответ от VK для {group_id}: {result.get('response') and len(result['response'].get('items', []))} постов")
                if "response" in result:
                    posts.extend(result["response"].get("items", []))
    return posts

async def send_vk_news(message: Message):
    try:
        news_items = await fetch_vk_group_posts()
        print(f"🔍 Ищем пост с фото среди {len(news_items)} постов")
        top_post = next(
            (p for p in news_items if 'attachments' in p and any(a['type'] == 'photo' for a in p['attachments'])),
            None
        )
        if not top_post:
            print("❌ Не найдено постов с фото")
            await message.answer("Новости не найдены.")
            return
        text = top_post.get("text", "")
        photos = [a['photo']['sizes'][-1]['url'] for a in top_post['attachments'] if a['type'] == 'photo']
        if not text:
            text = "Пост из VK без текста."
        print(f"✅ Отправляем пост: {text[:60]}...")
        await message.answer_photo(photo=photos[0], caption=text)
    except Exception as e:
        print(f"🛑 Ошибка в send_vk_news: {e}")
        await message.answer(f"⚠️ Ошибка при получении новостей: {str(e)}")

async def send_rss_news(message: Message):
    rss_feeds = [
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
    for url in rss_feeds:
        print(f"🌐 Парсим RSS: {url}")
        feed = feedparser.parse(url)
        entries.extend(feed.entries)
    entries.sort(key=lambda e: e.get("published_parsed", None), reverse=True)
    latest = next((e for e in entries if e.get("title") and e.get("link") and e.get("link") not in USED_ENTRIES), None)
    if not latest:
        print("❌ Нет новостей в RSS")
        await message.answer("Новости не найдены в RSS.")
        return
    USED_ENTRIES.add(latest.get("link"))
    title = clean_html(latest.get("title", ""))
    summary = clean_html(latest.get("summary", ""))
    link = latest.get("link", "")
    print(f"🧠 GPT рерайт: {title}")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты кратко и дерзко переписываешь новостные тексты в стиле глянца. Не упоминай источник."},
                {"role": "user", "content": f"{title}\n\n{summary}"}
            ]
        )
        rewritten = response.choices[0].message.content.strip()
        if not rewritten:
            raise ValueError("GPT ответ пустой")
        print(f"✅ GPT вернул: {rewritten[:60]}...")
    except Exception as e:
        print(f"⚠️ Ошибка OpenAI: {e}")
        rewritten = f"<b>{title}</b>\n\n{summary}"
    text = f"{rewritten}\n\n#новости"
    await message.answer(text, parse_mode=ParseMode.HTML)

async def send_celebrity_fact(message: Message):
    await message.answer("Факты о знаменитостях будут добавлены позже.")

async def send_celebrity_story(message: Message):
    await message.answer("Истории о звездах будут добавлены позже.")

async def post_to_vk(message: Message):
    await message.answer("Функция публикации в VK будет реализована позже.")
