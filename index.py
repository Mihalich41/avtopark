import logging
import ssl
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for detailed logs

# Переменные окружения
TELEGRAM_TOKEN = "801854876:AAGIq_Zd_bKObkezZt9bxq9JBLId0bSYmDY"
DATABASE_PATH = "/ru-central1/b1gm7qip4sdep322r0b3/etn55fsfav32krmaaqk4"
ENDPOINT = "grpcs://ydb.serverless.yandexcloud.net:2135/"

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()  # Updated for non-deprecated initialization

# Города для выбора
cities = [
    "Санкт-Петербург", "Реутов", "Воронеж", "Волгоград", "Краснодар", "Ростов-на-Дону", "Нижний Новгород"
]

# Генерация клавиатуры для выбора города
city_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in cities]
)

# Генерация клавиатуры для выбора проблемы
problem_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="ДТП", callback_data="problem_ДТП"),
         InlineKeyboardButton(text="Долг", callback_data="problem_Долг")],
        [InlineKeyboardButton(text="Неисправность", callback_data="problem_Неисправность"),
         InlineKeyboardButton(text="Техосмотр", callback_data="problem_Техосмотр")],
        [InlineKeyboardButton(text="Другая проблема", callback_data="problem_Другая"),
         InlineKeyboardButton(text="Оператор", callback_data="problem_Оператор")]
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
    city = callback_query.data[len("city_"):]
    logging.debug(f"City selected: {city}")
    await callback_query.message.answer(f"Ваш город: {city}.\n\nОпишите проблему:", reply_markup=problem_keyboard)
    await callback_query.answer()

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
