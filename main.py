import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import openai
import requests

# Загрузка переменных окружения
TELEGRAM_TOKEN = os.getenv("API_TOKEN")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Пример команды
@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот CLANDESTINO. Готов к публикации модных постов во ВКонтакте 😉")

# Пример генерации текста с OpenAI
def generate_text(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Или другой, если доступен
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Ошибка генерации: {str(e)}"

# Публикация в ВКонтакте
def post_to_vk(text: str):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "owner_id": f"-{VK_GROUP_ID}",
        "message": text,
        "access_token": VK_TOKEN,
        "v": "5.199"
    }
    response = requests.post(url, params=params)
    return response.json()

# Команда для генерации и публикации поста
@dp.message_handler(commands=["post"])
async def handle_post(message: types.Message):
    await message.reply("Генерирую пост...")
    prompt = "Напиши стильный и дерзкий пост для группы про моду, искусство и лакшери. Коротко, цепляюще."
    text = generate_text(prompt)
    vk_response = post_to_vk(text)
    if "error" in vk_response:
        await message.reply(f"Ошибка публикации: {vk_response['error']['error_msg']}")
    else:
        await message.reply("Пост успешно опубликован во ВКонтакте!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
