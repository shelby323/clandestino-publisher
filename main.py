import os
import openai
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
VK_TOKEN = os.getenv("VK_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")

openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_API_BASE


def rewrite_text(text):
    prompt = f"Перепиши этот текст дерзко, иронично, красиво, лаконично:\n\n{text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def post_to_vk(message):
    url = "https://api.vk.com/method/wall.post"
    params = {
        "access_token": VK_TOKEN,
        "owner_id": f"-{VK_GROUP_ID}",
        "message": message,
        "v": "5.131"
    }
    try:
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        print(f"VK error: {e}")
        return None


if __name__ == "__main__":
    # Временно зашитый тестовый текст, можно заменить на любую RSS-ленту
    original_text = "Бейонсе в прозрачном платье на Met Gala — вот это стиль!"
    rewritten = rewrite_text(original_text)
    if rewritten:
        print("Рерайт готов:", rewritten)
        result = post_to_vk(rewritten)
        print("Результат публикации:", result)
