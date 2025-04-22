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
    InlineKeyboardButton("📡 Собрать свежие материалы", callback_data="collect")
)

post_actions_keyboard = InlineKeyboardMarkup(row_width=2)
post_actions_keyboard.add(
    InlineKeyboardButton("🔁 Редактировать", callback_data="rewrite"),
    InlineKeyboardButton("📤 Опубликовать в ВК", callback_data="post_vk")
)

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

BLOCKED_KEYWORDS = ["subscribe", "buy now", "lookbook", "collection", "sale", "shopping"]


def is_advertisement(text):
    text = text.lower()
    return any(keyword in text for keyword in BLOCKED_KEYWORDS)

def translate_and_adapt(text):
    if is_foreign(text):
        prompt = (
            "Переведи текст на русский язык и адаптируй его под стиль модного Telegram-канала. "
            "Только русский язык. Без HTML. Без английских слов. Без рекламных фраз. Напиши лаконично, стильно, 1–4 абзаца. "
            "Фокус на визуальность, известных людей, образы, звёзд шоу-бизнеса. Удали мусор."
            f"\n\n{text}"
        )
    else:
        prompt = (
            "Сделай рерайт текста в стиле модного Telegram-канала: лаконично, дерзко, эстетично, "
            "от 1 до 4 абзацев, с фокусом на стиль, моду, визуальность, известных людей, знаменитостей и их образы. "
            "Удали англоязычные фразы и элементы кода, оставь чистый русский текст."
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

@dp.message_handler(commands=["start", "menu"])
async def cmd_start(message: types.Message):
    if message.from_user.id in OWNER_IDS:
        await message.answer("Выбери тип поста:", reply_markup=menu_keyboard)
    else:
        await message.reply("Недостаточно прав.")

@dp.callback_query_handler(lambda c: c.data in ["news", "aesthetics", "quote", "story"])
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    prompt_map = {
        "news": "Сделай короткий пост в стиле модного Telegram-канала: лаконично, дерзко, цепляюще. Тема — мода, знаменитости, стиль, шоу-бизнес, весна 2025.",
        "aesthetics": "Создай визуально вдохновляющий текст, как пост в эстетичном Instagram-аккаунте. Тема — стиль, мода, знаменитости, атмосфера весны 2025.",
        "quote": "Придумай короткую цитату от имени вымышленной знаменитости о стиле, весне и самоощущении. Без лишнего пафоса.",
        "story": "Напиши короткую художественную историю на 3-5 предложений о девушке или звезде шоу-бизнеса, которая влюбилась этой весной, в стиле дневника."
    }
    prompt = prompt_map[callback_query.data]
    response = requests.post(
        PROXY_URL,
        headers={"Content-Type": "application/json"},
        json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}
    )
    if response.ok:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        await bot.send_message(callback_query.from_user.id, text.strip())
        log_interaction({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "action": callback_query.data,
            "timestamp": datetime.datetime.now().isoformat(),
            "response": text.strip()
        })
    else:
        await bot.send_message(callback_query.from_user.id, "Ошибка при получении ответа от GPT.")

last_collected_text = None
recent_titles = set()
used_entries = set()
RSS_FEEDS = [
    "https://www.glamour.ru/rss/news",
    "https://www.vogue.ru/rss.xml",
    "https://www.elle.ru/rss.xml",
    "https://www.kinopoisk.ru/media/news/rss.xml",
    "https://www.woman.ru/rss/",
    "https://7days.ru/rss/",
    "https://www.starhit.ru/rss/",
    "https://www.cosmo.ru/rss.xml",
    "https://life.ru/rss.xml",
    "https://www.vogue.com/feed",
    "https://www.harpersbazaar.com/rss/all.xml",
    "https://www.lofficielusa.com/rss",
    "https://www.wmagazine.com/rss",
    "https://people.com/feed",
    "https://www.etonline.com/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/style/rss.xml",
    "https://www.gq.com/feed/rss",
    "https://www.instyle.com/news/rss"
]

@dp.callback_query_handler(lambda c: c.data == "collect")
async def handle_collect(callback_query: types.CallbackQuery):
    global last_collected_text, recent_titles, used_entries
    await bot.answer_callback_query(callback_query.id)

    all_entries = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        all_entries.extend(feed.entries)

    all_entries = [e for e in all_entries if getattr(e, "title", "").strip() or getattr(e, "summary", "").strip()]
    all_entries = [e for e in all_entries if not is_advertisement(e.title + " " + getattr(e, "summary", ""))]
    all_entries = sorted(all_entries, key=lambda e: getattr(e, "published_parsed", datetime.datetime.min), reverse=True)
    logging.info(f"Собрано {len(all_entries)} записей из RSS-источников.")

    fresh_news = [entry for entry in all_entries if entry.title not in recent_titles and entry.title not in used_entries]

    if not fresh_news:
        logging.info("Нет новых новостей — покажем самые свежие доступные.")
        fresh_news = all_entries[:20]

    if not fresh_news:
        logging.warning("Не удалось найти даже старые новости.")
        await bot.send_message(callback_query.from_user.id, "Нет новостей для отображения.")
        return

    entry = random.choice(fresh_news)
    title = sanitize_text(entry.title)
    summary = sanitize_text(getattr(entry, "summary", ""))
    combined = f"{title}\n{summary}".strip()

    adapted_text = translate_and_adapt(combined)
    last_collected_text = combined
    recent_titles.add(title)
    used_entries.add(title)
    if len(recent_titles) > 200:
        recent_titles = set(list(recent_titles)[-100:])

    await bot.send_message(callback_query.from_user.id, f"Собран текст:\n\n{adapted_text}", reply_markup=post_actions_keyboard)

@dp.callback_query_handler(lambda c: c.data == "rewrite")
async def handle_rewrite(callback_query: types.CallbackQuery):
    global last_collected_text
    await bot.answer_callback_query(callback_query.id)
    if last_collected_text:
        alt_version = translate_and_adapt(last_collected_text)
        await bot.send_message(callback_query.from_user.id, f"Вариант переформулировки:\n\n{alt_version}", reply_markup=post_actions_keyboard)
    else:
        await bot.send_message(callback_query.from_user.id, "Нет текста для редактирования.")

@dp.callback_query_handler(lambda c: c.data == "post_vk")
async def handle_post_vk(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "🛠 Функция публикации в ВК находится в разработке.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)


