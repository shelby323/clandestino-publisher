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

        # Фильтрация по языку и длине
        if len(content) < 200:
            attempts += 1
            continue
        try:
            lang = detect(content)
            if lang != 'ru' and lang != 'en':
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
        "model": "gpt-3.5-turbo",
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




