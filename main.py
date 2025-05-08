import os
import logging
import requests
import datetime
import json
import feedparser
import random
import re
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from langdetect import detect

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_IDS = {int(i) for i in os.getenv("OWNER_IDS", "").split(",") if i.strip().isdigit()}
PROXY_URL = os.getenv("PROXY_URL", "https://clandestino-proxy.onrender.com/v1/chat/completions")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

menu_keyboard = InlineKeyboardMarkup(row_width=2)
menu_keyboard.add(
    InlineKeyboardButton("📰 Новость", callback_data="news"),
    InlineKeyboardButton("🧠 Цитата", callback_data="quote"),
    InlineKeyboardButton("💫 Эстетика", callback_data="aesthetic"),
    InlineKeyboardButton("🎬 История", callback_data="story"),
    InlineKeyboardButton("📊 Статистика", callback_data="stats")
)

RSS_FEEDS = [
    "https://www.harpersbazaar.com/rss/celebrity-news.xml",
    "https://www.vogue.com/feed/rss",
    "https://people.com/feed/",
    "https://www.elle.com/rss/all.xml"
]

BLOCKED_KEYWORDS = ["unsubscribe", "newsletter", "cookie", "advertising", "privacy"]

user_cache = {}

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    if message.from_user.id in OWNER_IDS:
        await message.answer("Выбери тип поста:", reply_markup=menu_keyboard)

@dp.callback_query_handler(lambda c: c.data in ["news", "quote", "aesthetic", "story", "stats"])
async def process_callback(callback_query: types.CallbackQuery):
    action = callback_query.data
    if action == "stats":
        await callback_query.message.edit_text("📊 В разработке: статистика будет здесь.", reply_markup=menu_keyboard)
        return

    raw = fetch_random_entry()
    if not raw:
        await callback_query.message.edit_text("😢 Не удалось найти подходящий материал. Попробуй еще.", reply_markup=menu_keyboard)
        return

    rewritten = generate_post(raw, category=action)
    if not rewritten:
        await callback_query.message.edit_text("⚠️ Ошибка генерации поста. Попробуй еще раз.", reply_markup=menu_keyboard)
        return

    user_cache[callback_query.from_user.id] = rewritten
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✏️ Редактировать", callback_data="edit"),
        InlineKeyboardButton("📤 Опубликовать в VK", callback_data="publish"),
        InlineKeyboardButton("🔄 Хочу ещё", callback_data=action)
    )
    await callback_query.message.edit_text(f"Собран текст:\n\n{rewritten}", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["edit", "publish"])
async def handle_post_actions(callback_query: types.CallbackQuery):
    uid = callback_query.from_user.id
    cached = user_cache.get(uid)
    if not cached:
        await callback_query.message.edit_text("⚠️ Нет текста для обработки.")
        return

    if callback_query.data == "edit":
        await callback_query.message.edit_text(f"Редактируй текст и пришли обратно:\n\n{cached}")
    elif callback_query.data == "publish":
        response = publish_to_vk(cached)
        if "response" in response:
            await callback_query.message.edit_text("✅ Пост успешно опубликован во ВКонтакте!")
        else:
            await callback_query.message.edit_text(f"❌ Ошибка публикации: {response}")

def fetch_random_entry():
    max_attempts = 10
    attempts = 0
    while attempts < max_attempts:
        feed_url = random.choice(RSS_FEEDS)
        feed = feedparser.parse(feed_url)
        entries = feed.entries
        if not entries:
            attempts += 1
            continue
        entry = random.choice(entries)
        content = entry.get("summary") or entry.get("description") or entry.get("title")
        content = BeautifulSoup(content, "html.parser").get_text()
        content = content.strip()

        if len(content) < 200 or any(bad in content.lower() for bad in BLOCKED_KEYWORDS):
            attempts += 1
            continue
        if content.count("?") > 2 or content.endswith("?"):
            attempts += 1
            continue
        if re.search(r'\b(how|why|what|where|when|who)\b.*\?', content.lower()):
            attempts += 1
            continue
        try:
            lang = detect(content)
            if lang not in ['ru', 'en']:
                attempts += 1
                continue
        except:
            attempts += 1
            continue
        return content
    return ""

def generate_post(prompt_text, category="news"):
    system_prompt = "Ты создаешь модные, лаконичные, визуально привлекательные посты во ВКонтакте для паблика про стиль, искусство и знаменитостей."
    user_prompt_map = {
        "news": f"Сделай из этой новости законченный пост с дерзким стилем, хэштегами, с 2–4 абзацами:\n{prompt_text}",
        "quote": f"Оформи это как пост с цитатой звезды, добавь эмоциональное вступление и дерзкий тон:\n{prompt_text}",
        "aesthetic": f"Сделай стильный пост в эстетике глянца и моды, вдохновляющий и визуальный:\n{prompt_text}",
        "story": f"Сделай интересную историю о знаменитости, поданную живо и красиво, как для глянцевого журнала:\n{prompt_text}"
    }
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_map.get(category, prompt_text)}
        ]
    }
    response = requests.post(PROXY_URL, headers=headers, data=json.dumps(payload))
    if response.ok:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content")
    return None

def publish_to_vk(text):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "access_token": VK_TOKEN,
        "owner_id": f"-{VK_GROUP_ID}",
        "message": text,
        "v": "5.199"
    }
    response = requests.post(url, params=params)
    return response.json()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)




