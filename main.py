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

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

menu_keyboard = InlineKeyboardMarkup(row_width=2)
menu_keyboard.add(
    InlineKeyboardButton("📰 Новости", callback_data="news"),
    InlineKeyboardButton("🎨 Эстетика", callback_data="aesthetics"),
    InlineKeyboardButton("✨ Цитата", callback_data="quote"),
    InlineKeyboardButton("💬 История", callback_data="story"),
)

post_actions_keyboard = InlineKeyboardMarkup(row_width=2)
post_actions_keyboard.add(
    InlineKeyboardButton("🔁 Редактировать", callback_data="rewrite"),
    InlineKeyboardButton("📤 Опубликовать в ВК", callback_data="post_vk"),
    InlineKeyboardButton("🔄 Хочу ещё", callback_data="next_post")
)

user_cache = {}

def log_interaction(data):
    try:
        with open("stats.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        logging.error(f"Ошибка при логировании статистики: {e}")

def is_foreign(text):
    try:
        return detect(text) != "ru"
    except:
        return False

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

def sanitize_text(text):
    text = clean_html(text)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

BLOCKED_KEYWORDS = [
    "subscribe", "buy now", "lookbook", "collection", "sale", "shopping",
    "gender equality", "diversity", "inclusion", "activism",
    "hydrating sticks", "skin care", "косметика", "уход за кожей"
]

BLOCKED_NAMES = [
    "TikTok", "OnlyFans", "local influencer", "рекламодатель", "бренд"
]

def is_advertisement(text):
    text = text.lower()
    return any(keyword in text for keyword in BLOCKED_KEYWORDS) or any(name.lower() in text for name in BLOCKED_NAMES)

def translate_and_adapt(text):
    if is_foreign(text):
        prompt = (
            "Переведи текст на русский язык и адаптируй его под стиль модного Telegram-канала. "
            "Только русский язык. Без HTML. Без английских слов. Без рекламных фраз. Без упоминания малоизвестных персон. "
            "Напиши лаконично, стильно, 1–4 абзаца. Удали мусор. Фокус — шоу-бизнес, мода, звезды высокого уровня."
            f"\n\n{text}"
        )
    else:
        prompt = (
            "Сделай рерайт текста в стиле модного Telegram-канала: лаконично, дерзко, эстетично, "
            "от 1 до 4 абзацев. Удали англоязычные фразы, HTML, рекламные элементы, малоизвестные имена. "
            "Фокус — звезды, телеведущие, актеры, певцы, знаменитости мирового уровня."
            f"\n\n{text}"
        )

    response = requests.post(
        PROXY_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    if response.ok:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
        logging.error(f"Ошибка GPT: {response.text}")
        return "Ошибка при переводе/адаптации текста."
