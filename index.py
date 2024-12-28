import logging
import ssl
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_PATH = os.getenv("DATABASE_PATH")
ENDPOINT = os.getenv("ENDPOINT")

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for detailed logs

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()  # Updated for non-deprecated initialization

try:
    # Открываем файл
    with open('c:/work/arendator/data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Проверяем ключ
    if 'sections' not in data:
        raise KeyError("Ключ 'sections' отсутствует в данных.")

    # Используем sections
    sections = data['sections']
    print(sections)

except FileNotFoundError:
    print("Файл не найден. Проверьте путь.")
except json.JSONDecodeError:
    print("Ошибка при разборе JSON. Проверьте содержимое файла.")
except KeyError as e:
    print(f"Ошибка: {e}")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")


sections = data['sections']
subsections = data['subsections']
prompt_template = data['prompt_template']

cities = [
    "Санкт-Петербург", "Реутов", "Воронеж", "Волгоград", "Краснодар", "Ростов-на-Дону", "Нижний Новгород"
]
city_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in cities]
)

problem_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[:2]],
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[2:4]],
        [InlineKeyboardButton(text=name, callback_data=f"problem_{details['id']}") for name, details in list(sections.items())[4:]]
    ]
)

user_data = {}

@dp.message(lambda message: message.text == '/start')
async def send_welcome(message: types.Message):
    logging.debug("Handling /start command")
    await message.answer(
        "Выберите ваш город:",
        reply_markup=city_keyboard
    )

@dp.callback_query(lambda callback: callback.data.startswith("city_"))
async def handle_city_selection(callback_query: types.CallbackQuery):
    city = callback_query.data[len("city_"):]  # Extract city name
    user_data[callback_query.from_user.id] = {"city": city}
    logging.debug(f"City selected: {city}")
    await callback_query.message.answer(
        f"Вы выбрали город: {city}. Теперь выберите раздел, который соответствует вашей проблеме:",
        reply_markup=problem_keyboard
    )
    await callback_query.answer()

@dp.callback_query(lambda callback: callback.data.startswith("problem_"))
async def handle_problem_selection(callback_query: types.CallbackQuery):
    problem_id = int(callback_query.data[len("problem_"):])
    logging.debug(f"Problem ID selected: {problem_id}")
    selected_section = None

    for section, details in sections.items():
        if details['id'] == problem_id:
            selected_section = section
            user_data[callback_query.from_user.id]["section"] = section
            await callback_query.message.answer(details["content"])

            # Display relevant subsections as buttons if available
            relevant_subsections = [name for name, sub in subsections.items() if sub["parent_id"] == problem_id]
            if relevant_subsections:
                subsection_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=sub, callback_data=f"subsection_{sub}")]
                                     for sub in relevant_subsections]
                )
                await callback_query.message.answer("Выберите нужный подраздел:", reply_markup=subsection_keyboard)
            break

    if not selected_section:
        await callback_query.message.answer("Произошла ошибка при выборе раздела. Попробуйте снова.")
    
    await callback_query.answer()

@dp.callback_query(lambda callback: callback.data.startswith("subsection_"))
async def handle_subsection_selection(callback_query: types.CallbackQuery):
    subsection_name = callback_query.data[len("subsection_"):]  # Extract subsection name
    logging.debug(f"Subsection selected: {subsection_name}")

    if subsection_name in subsections:
        city = user_data.get(callback_query.from_user.id, {}).get("city", "указанном городе")
        content = subsections[subsection_name]["content"].format(city=city)
        await callback_query.message.answer(content)
    else:
        await callback_query.message.answer("Произошла ошибка при выборе подраздела. Попробуйте снова.")

    await callback_query.answer()

@dp.message()
async def handle_user_message(message: types.Message):
    user_message = message.text.lower()
    logging.debug(f"Received user message: {user_message}")

    # Попытка определения раздела локально
    determined_section = None
    for section, details in sections.items():
        if any(keyword in user_message for keyword in details["keywords"]):
            determined_section = section
            break

    if determined_section:
        logging.debug(f"Local section determination: {determined_section}")
        await message.answer(f"Определён раздел по ключевым словам: {determined_section}")
        await message.answer(sections[determined_section]["content"])

        # Display relevant subsections as buttons if available
        problem_id = sections[determined_section]["id"]
        relevant_subsections = [name for name, sub in subsections.items() if sub["parent_id"] == problem_id]
        if relevant_subsections:
            subsection_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=sub, callback_data=f"subsection_{sub}")]
                                 for sub in relevant_subsections]
            )
            await message.answer("Выберите нужный подраздел:", reply_markup=subsection_keyboard)
    else:
        # Если раздел не определён, запрос к OpenAI
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            prompt = prompt_template.format(
                sections="\n".join([f"{section}: {', '.join(details['keywords'])}" for section, details in sections.items()]),
                user_message=user_message
            )
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
            )

            response_text = response.choices[0].message.content.strip()
            await message.answer(f"ChatGPT определил раздел: {response_text}")

            if response_text in sections:
                await message.answer(sections[response_text]["content"])

                # Display relevant subsections as buttons if available
                problem_id = sections[response_text]["id"]
                relevant_subsections = [name for name, sub in subsections.items() if sub["parent_id"] == problem_id]
                if relevant_subsections:
                    subsection_keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text=sub, callback_data=f"subsection_{sub}")]
                                         for sub in relevant_subsections]
                    )
                    await message.answer("Выберите нужный подраздел:", reply_markup=subsection_keyboard)
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
            loop = asyncio.get_event_loop()
            loop.create_task(main())
    except Exception as e:
        logging.error("Error running the bot: %s", e)
