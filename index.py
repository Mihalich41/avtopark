import logging
import ssl
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
from openai import OpenAI

OPENAI_API_KEY = "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"

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for detailed logs

# Переменные окружения
TELEGRAM_TOKEN = "801854876:AAGIq_Zd_bKObkezZt9bxq9JBLId0bSYmDY"
DATABASE_PATH = "/ru-central1/b1gm7qip4sdep322r0b3/etn55fsfav32krmaaqk4"
ENDPOINT = "grpcs://ydb.serverless.yandexcloud.net:2135/"
OPENAI_API_KEY = "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"

# Установка API-ключа OpenAI
# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()  # Updated for non-deprecated initialization

# Ключевые слова и разделы с ID
sections = {
    "ДТП": {"id": 1, "keywords": ["виноват", "авария", "столкновение"]},
    "Долг": {"id": 2, "keywords": ["долг", "баланс", "списание", "лишняя сумма"]},
    "Неисправность": {"id": 3, "keywords": ["масло", "колодки", "резина", "сломалось"]},
    "Техосмотр": {"id": 4, "keywords": ["день", "техосмотр", "пройти", "назначенный день"]},
    "Другая проблема": {"id": 5, "keywords": ["проблема", "вопрос"]},
    "Оператор": {"id": 6, "keywords": ["оператор", "помощь", "связаться"]}
}

# Генерация клавиатуры для выбора города
cities = [
    "Санкт-Петербург", "Реутов", "Воронеж", "Волгоград", "Краснодар", "Ростов-на-Дону", "Нижний Новгород"
]
city_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in cities]
)

# Генерация клавиатуры для выбора проблемы
problem_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[:2]],
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[2:4]],
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[4:]]
    ]
)

@dp.message(lambda message: message.text == '/start')
async def send_welcome(message: types.Message):
    logging.debug("Handling /start command")
    await message.answer(
        "Пожалуйста, укажите ваш город из списка:",
        reply_markup=city_keyboard
    )

@dp.callback_query(lambda callback: callback.data.startswith("city_"))
async def handle_city_selection(callback_query: types.CallbackQuery):
    city = callback_query.data[len("city_"):]  # Extract city name from callback data
    logging.debug(f"City selected: {city}")
    await callback_query.message.answer(f"Ваш город: {city}.\n\nОпишите проблему:", reply_markup=problem_keyboard)
    await callback_query.answer()

@dp.callback_query(lambda callback: callback.data.startswith("problem_"))
async def handle_problem_selection(callback_query: types.CallbackQuery):
    problem_id = int(callback_query.data[len("problem_"):])
    logging.debug(f"Problem ID selected: {problem_id}")
    for section, details in sections.items():
        if details['id'] == problem_id:
            if problem_id in [5, 6]:  # "Другая проблема" or "Оператор"
                await callback_query.message.answer("Сообщите вашу проблему.")
            elif problem_id == 1:  # "ДТП"
                await callback_query.message.answer("Кто виноват в ДТП?")
            else:
                await callback_query.message.answer(f"Вы выбрали раздел: {section}")
            break
    await callback_query.answer()

@dp.message()
async def handle_user_message(message: types.Message):
    user_message = message.text.lower()
    logging.debug(f"Received user message: {user_message}")

    # Формируем контекст для OpenAI с разделами
    sections_context = "\n".join([f"{name}: {', '.join(details['keywords'])}" for name, details in sections.items()])

    # Формируем системное сообщение для OpenAI
    system_message = (
        "Вы бот, который помогает определить, к какому разделу относится сообщение пользователя. "
        "Возможные разделы и их ключевые слова:\n"
        f"{sections_context}\n"
        "На основании сообщения пользователя определите, какой раздел подходит лучше всего. "
        "Верните только название раздела."
    )

    try:
        # Создаем запрос к OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_message},  # Инструкция для модели
                {"role": "user", "content": user_message},  # Сообщение пользователя
            ],
            model="gpt-4o-mini",
        )

        # Извлекаем текст ответа
        response_text = response.choices[0].message.content.strip()  # Ответ модели

        # Отправляем ответ пользователю
        await message.answer(f"Ваше сообщение относится к разделу: {response_text}")

    except Exception as e:
        logging.error(f"Error analyzing message: {e}")
        await message.answer("Произошла ошибка при анализе сообщения. Попробуйте снова позже.")

async def main():
    logging.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except RuntimeError as e:
        logging.error("Error in the main loop: %s", e)
    except Exception as e:
        logging.error("Unexpected error: %s", e)

if __name__ == '__main__':
    try:
        if not asyncio.get_event_loop().is_running():
            asyncio.run(main())
        else:
            # If an event loop is already running, use it to run the bot
            loop = asyncio.get_event_loop()
            loop.create_task(main())
    except Exception as e:
        logging.error("Error running the bot: %s", e)
