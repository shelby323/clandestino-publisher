import os
import logging
import requests
import datetime
import json
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

def translate_and_adapt(text):
    prompt = (
        "Переведи этот текст на русский язык и адаптируй его под стиль модного Telegram-канала: "
        "лаконично, дерзко, эстетично, с фокусом на стиль, моду, визуальность. "
        "Оставь только самое главное, сделай из него короткий пост.\n\n"
        f"{text}"
    )

    response = requests.post(
        PROXY_URL,
        headers={"Content-Type": "application/json"},
        json={"messages": [{"role": "user", "content": prompt}]}
    )

    if response.ok:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
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
        "news": "Сделай короткий пост в стиле модного Telegram-канала: лаконично, дерзко, цепляюще. Тема — мода, знаменитости, весна 2025.",
        "aesthetics": "Создай визуально вдохновляющий текст, как пост в эстетичном Instagram-аккаунте. Тема — стиль и атмосфера весны 2025.",
        "quote": "Придумай короткую цитату от имени вымышленной знаменитости о стиле, весне и самоощущении. Без лишнего пафоса.",
        "story": "Напиши короткую художественную историю на 3-5 предложений о девушке, которая влюбилась этой весной, в стиле дневника."
    }

    prompt = prompt_map[callback_query.data]

    response = requests.post(
        PROXY_URL,
        headers={"Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
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

@dp.callback_query_handler(lambda c: c.data == "collect")
async def handle_collect(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    sample_text = "Paris Fashion Week kicks off with bold designs and celebrity appearances."

    if is_foreign(sample_text):
        adapted_text = translate_and_adapt(sample_text)
    else:
        adapted_text = sample_text

    await bot.send_message(callback_query.from_user.id, f"Собран текст:\n\n{adapted_text}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
