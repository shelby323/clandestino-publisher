import os
import logging
import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
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

@dp.message_handler(commands=["start", "menu"])
async def cmd_start(message: types.Message):
    if message.from_user.id == OWNER_ID:
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
    else:
        await bot.send_message(callback_query.from_user.id, "Ошибка при получении ответа от GPT.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
