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
    InlineKeyboardButton("💬 История", callback_data="story")
)

post_actions_keyboard = InlineKeyboardMarkup(row_width=2)
post_actions_keyboard.add(
    InlineKeyboardButton("🔁 Редактировать", callback_data="rewrite"),
    InlineKeyboardButton("📤 Опубликовать в ВК", callback_data="post_vk"),
    InlineKeyboardButton("🔄 Хочу ещё", callback_data="next_post")
)

user_cache = {}

BLOCKED_KEYWORDS = ["реклама", "купить", "скидка", "подпишись", "бренд", "инфлюенсер"]
BLOCKED_NAMES = ["local influencer", "рекламодатель", "бренд"]
FOCUS_KEYWORDS = [
    "звезда", "селебрити", "актёр", "певец", "певица", "шоубизнес", "шоу-бизнес",
    "модный показ", "интервью", "красная дорожка", "голливуд", "ведущая", "модель", "блогер"
]

RSS_FEEDS = [
    "https://www.elle.ru/rss/all/",
    "https://www.harpersbazaar.com/rss/",
    "https://www.vogue.com/feed/rss",
    "https://people.com/feed/",
    "https://www.hollywoodreporter.com/t/feed/",
    "https://www.glamourmagazine.co.uk/rss",
    "https://www.etonline.com/news/rss"
]

def is_foreign(text):
    try:
        return detect(text) != "ru"
    except:
        return False

def clean_html(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()

def sanitize_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_advertisement(text):
    text = text.lower()
    return any(keyword in text for keyword in BLOCKED_KEYWORDS) or any(name.lower() in text for name in BLOCKED_NAMES)

def is_on_topic(text):
    text = text.lower()
    return any(keyword in text for keyword in FOCUS_KEYWORDS)

def translate_and_adapt(text, category="news"):
    if is_foreign(text):
        prompt = (
            "Переведи текст на русский язык и адаптируй его под стиль современной VK-группы о звездах и моде. "
            "Только русский язык. Без HTML. Без рекламных фраз. Без упоминания малоизвестных персон. "
            "Напиши лаконично, стильно, 1-4 абзаца. Удали мусор. Фокус — шоу-бизнес, мода, звезды высокого уровня."
            f"\n\n{text}"
        )
    else:
        if category == "quote":
            prompt = (
                "Сделай рерайт цитаты от имени звезды. Сохрани стиль, харизму, краткость. Без HTML, без англоязычных слов."
                f"\n\n{text}"
            )
        elif category == "aesthetics":
            prompt = (
                "Опиши эстетику фото или события в духе модной VK-группы. Сохрани образность и атмосферу. Без HTML."
                f"\n\n{text}"
            )
        elif category == "story":
            prompt = (
                "Перепиши эту историю, сделай её захватывающей и лаконичной. Подходит для поста в VK-группу о шоу-бизнесе."
                f"\n\n{text}"
            )
        else:
            prompt = (
                "Сделай рерайт текста в стиле популярной VK-группы: лаконично, дерзко, эстетично, "
                "от 1 до 4 абзацев. Удали англоязычные фразы, HTML, рекламные элементы, малоизвестные имена. "
                "Фокус = звезды, телеведущие, актеры, певцы, знаменитости мирового уровня."
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

def parse_rss(category):
    all_entries = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            text = clean_html(entry.get("summary", "") or entry.get("description", ""))
            title = entry.get("title", "")
            combined_text = f"{title}\n{text}"
            if not is_advertisement(combined_text) and (is_on_topic(combined_text) or category != "news"):
                all_entries.append(combined_text)
    if not all_entries and category == "news":
        for url in RSS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                text = clean_html(entry.get("summary", "") or entry.get("description", ""))
                title = entry.get("title", "")
                combined_text = f"{title}\n{text}"
                if not is_advertisement(combined_text):
                    all_entries.append(combined_text)
    random.shuffle(all_entries)
    return all_entries

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Выбери тип поста:", reply_markup=menu_keyboard)

@dp.callback_query_handler(lambda c: c.data in ["news", "aesthetics", "quote", "story"])
async def handle_category(callback_query: types.CallbackQuery):
    category = callback_query.data
    await bot.answer_callback_query(callback_query.id)

    all_texts = parse_rss(category)
    if not all_texts:
        await bot.send_message(callback_query.from_user.id, "Нет подходящих новостей")
        return

    adapted = translate_and_adapt(all_texts[0], category)
    user_cache[callback_query.from_user.id] = {"texts": all_texts[1:], "category": category}

    await bot.send_message(callback_query.from_user.id, f"Собран текст:\n\n{adapted}", reply_markup=post_actions_keyboard)

@dp.callback_query_handler(lambda c: c.data == "next_post")
async def handle_next(callback_query: types.CallbackQuery):
    cache = user_cache.get(callback_query.from_user.id, {})
    texts = cache.get("texts", [])
    category = cache.get("category", "news")
    if not texts:
        await bot.send_message(callback_query.from_user.id, "Новостей больше нет. Попробуй снова позже.")
        return
    next_text = texts.pop(0)
    user_cache[callback_query.from_user.id] = {"texts": texts, "category": category}
    adapted = translate_and_adapt(next_text, category)
    await bot.send_message(callback_query.from_user.id, f"Собран текст:\n\n{adapted}", reply_markup=post_actions_keyboard)

@dp.callback_query_handler(lambda c: c.data == "rewrite")
async def handle_rewrite(callback_query: types.CallbackQuery):
    cache = user_cache.get(callback_query.from_user.id, {})
    texts = cache.get("texts", [])
    category = cache.get("category", "news")
    if not texts:
        await bot.send_message(callback_query.from_user.id, "Нечего переписать.")
        return
    original = texts[0]
    rewritten = translate_and_adapt(original, category)
    await bot.send_message(callback_query.from_user.id, f"Вариант переформулировки:\n\n{rewritten}", reply_markup=post_actions_keyboard)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    executor.start_polling(dp, skip_updates=True)



