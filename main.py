import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = 321069928

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.reply("Привет! Я бот-публикатор контента для CLANDESTINO.")

@dp.message_handler()
async def echo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Я получил твоё сообщение: " + message.text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)