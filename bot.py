# bot.py
import os
import json
import re
import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

# Конфиг
BOT_TOKEN = "8523466237:AAFywm1AUCDcecTWD_jlq2HNjaPNFTrgauE"
API_KEY = "sk_49Qj5lxK5hI7HRWQ9sCuIFzIfHkqTHTG"
POLLINATIONS_URL = "https://gen.pollinations.ai/v1/chat/completions"

# Модели
PLANNER_MODEL = "gemini-fast"  # Нейросеть 1 - планировщик
CHARACTER_MODEL = "mistral"     # Нейросеть 2 - персонаж
AGENT_MODEL = "gemini-fast"     # Нейросеть 3 - агент окружения

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище (в проде заменить на Redis/БД)
users_data: Dict[int, dict] = {}
active_days: Dict[int, dict] = {}  # user_id -> данные текущего дня

SPECIAL_USERS = {"@asd123dad"}  # Бесконечные дни

@dataclass
class CharacterState:
    name: str
    mood: str  # 😡/😐/😊
    hunger: str  # 🍗
    health: str  # ❤️
    money: int  # 💰
    drunk: str  # 🍺
    risk: str  # 🎲
    inventory: List[str]
    location: str
    time: str
    
    def to_dict(self):
        return asdict(self)

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🥸 Б*хать!"), KeyboardButton(text="⏳ Профиль")],
            [KeyboardButton(text="🔗 Рефералка"), KeyboardButton(text="🎁 Бонус")],
            [KeyboardButton(text="📲 Скачать ОЛО")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_back_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True
    )

async def call_ai(model: str, messages: list, temperature: float = 0.7) -> Optional[str]:
    """Универсальный вызов AI через Pollinations"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(POLLINATIONS_URL, headers=headers, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return None
    except Exception as e:
        print(f"AI Error: {e}")
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверка активного дня
    if user_id in active_days:
        await message.answer("❌ Сначала заверши текущий день! Нажми ⏹️ Завершить день в карточке персонажа.")
        return
    
    if user_id not in users_data:
        # Новый пользователь
        is_special = f"@{username}" in SPECIAL_USERS if username else False
        days_limit = float('inf') if is_special else 3
        
        users_data[user_id] = {
            "username": username,
            "days_lived": 0,
            "drunk_count": 0,
            "referrals": 0,
            "beer_liters": 1.0,  # Стартовый литр
            "days_limit": days_limit,
            "days_remaining": days_limit if not is_special else float('inf'),
            "history": [],  # История дней для саммари
            "character_name": None
        }
        
        welcome_text = f"""🥸 Ну что ж, приветик!
Тут ты можешь смотреть на своего алк*ша!

{'✨ У тебя БЕСКОНЕЧНЫЕ дни, босс!' if is_special else 'У тебя 3 дня пробного периода. Пригласи друга — получи +2 дня!'}"""
    else:
        welcome_text = "🥸 С возвращением, алк*ш!"
    
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.message(F.text == "🥸 Б*хать!")
async def drink_beer(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in active_days:
        await message.answer("❌ Сначала заверши текущий день!")
        return
    
    user = users_data[user_id]
    
    if user["beer_liters"] <= 0:
        await message.answer("🍺 У тебя кончилось п*вко! Иди в бонус или рефералку.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍻 Ещё кружечку", callback_data="drink_more")]
    ])
    
    await message.answer(
        f"""🥸 Б*хни! Сколько раз ты б*хнул можно будет посмотреть в профиле!
🫗 Литров п*вка: {user['beer_liters']}

[Б*хнуть!] — тратит 0.5 литра""",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "drink_more")
async def process_drinking(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = users_data[user_id]
    
    if user["beer_liters"] >= 0.5:
        user["beer_liters"] -= 0.5
        user["drunk_count"] += 1
        
        await callback.message.edit_text(
            f"""🔥 Ох, ты жестко б*хнул!
Осталось п*вка: {user['beer_liters']} литров

🥴 Теперь ты в лёгком угаре..."""
        )
    else:
        await callback.answer("Недостаточно п*вка!", show_alert=True)
    
    await callback.answer()

@dp.message(F.text == "⏳ Профиль")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    user = users_data.get(user_id)
    
    if not user:
        await message.answer("Сначала нажми /start")
        return
    
    days_text = "∞" if user["days_limit"] == float('inf') else int(user["days_remaining"])
    
    profile_text = f"""🥸 Ты жил: {user['days_lived']} дней!
🥸 Б*хнул: {user['drunk_count']} раз!
🥸 Пригласил: {user['referrals']} алк*шей!
🥸 Ты: алк*ш ✅
🫗 П*вка осталось: {user['beer_liters']}л

⏳ Дней доступно: {days_text}"""
    
    await message.answer(profile_text, reply_markup=get_back_button())

@dp.message(F.text == "🔗 Рефералка")
async def show_referral(message: types.Message):
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    await message.answer(
        f"""🔗 Рефералка

Пригласи друга и получи них*я!
Ссылка: {ref_link}

🫠 И всё-таки тебе дадут 2 дня за это 🫠""",
        reply_markup=get_back_button()
    )

@dp.message(F.text == "🎁 Бонус")
async def show_bonus(message: types.Message):
    user_id = message.from_user.id
    user = users_data[user_id]
    user["beer_liters"] += 1.0
    
    await message.answer(
        f"""🎁 Ты получил **1 литр п*вка!**
ПОРА Б*ХАТЬ!

🫗 Теперь у тебя: {user['beer_liters']} литров""",
        reply_markup=get_back_button()
    )

@dp.message(F.text == "📲 Скачать ОЛО")
async def download_olo(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in active_days:
        await message.answer("❌ Сначала заверши текущий день!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕓 Начать Новый День", callback_data="start_day")],
        [InlineKeyboardButton(text="🍺 БУХНУТЬ НА ***", callback_data="goto_drink")]
    ])
    
    await message.answer(
        """🎮 ГЛАВНАЯ ФИЧА БОТА — СМОТРИ ЗА ПЕРСОНАЖЕМ И ЗА ЕГО ПРОХОДЯЩИМ ДНЁМ!""",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "goto_drink")
async def goto_drink(callback: types.CallbackQuery):
    await callback.message.delete()
    await drink_beer(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "start_day")
async def start_new_day(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = users_data[user_id]
    
    # Проверка лимита дней
    if user["days_limit"] != float('inf') and user["days_remaining"] <= 0:
        await callback.answer("У тебя закончились дни! Пригласи друзей!", show_alert=True)
        return
    
    await callback.message.edit_text(
        """✏️ Опиши, как должен пройти день твоего персонажа:

Примеры:
• "Ну персонаж должен ограбить банк"
• "Познакомиться с девушкой"  
• "Утром встать, поср*ть, днём тоже и вечером тоже"
• "Украсть машину и съ*б*ться от полиции"

Пиши что угодно, нейросеть составит план!"""
    )
    
    # Устанавливаем состояние ожидания описания дня
    active_days[user_id] = {"stage": "waiting_description", "messages": []}

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Назад":
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        return
    
    # Если активен день и ждём описание
    if user_id in active_days and active_days[user_id].get("stage") == "waiting_description":
        await process_day_description(message)
        return
    
    # Если активен день и идёт симуляция
    if user_id in active_days and active_days[user_id].get("stage") == "simulation":
        # Юзер может писать комменты, но они игнорируются или влияют?
        await message.answer("⏳ День идёт... Смотри за персонажем выше!")
        return

async def process_day_description(message: types.Message):
    user_id = message.from_user.id
    description = message.text
    
    status_msg = await message.answer("🧠 Нейросеть 1 составляет план дня...")
    
    # Запрос к планировщику (Нейросеть 1)
    planner_prompt = f"""Ты — планировщик дней для персонажа-алк*ша в игре-симуляторе.
    
Задача пользователя: "{description}"

Составь ДЕТАЛЬНЫЙ план дня с временными метками (утро/день/вечер/ночь).
Персонаж может материться, совершать преступления, знакомиться, есть, ср*ть — всё что угодно.
План должен быть конкретным, с примерным временем каждого действия.

Формат:
Утро (6:00-12:00):
- [время]: действие
- [время]: действие

День (12:00-18:00):
- [время]: действие

Вечер (18:00-22:00):
- [время]: действие

Ночь (22:00-6:00):
- [время]: действие

Пиши серьёзно, без эмодзи, чётко по пунктам."""
    
    plan = await call_ai(PLANNER_MODEL, [{"role": "user", "content": planner_prompt}])
    
    if not plan:
        await status_msg.edit_text("❌ Ошибка планировщика! День не потрачен, попробуй снова.")
        return
    
    await status_msg.edit_text("✅ План составлен! Запускаем персонажа...")
    
    # Инициализация персонажа
    user = users_data[user_id]
    char_name = user.get("character_name")
    
    if not char_name:
        # Генерируем имя если первый раз
        name_prompt = "Придумай русское имя и фамилию для алк*ша-преступника. Только имя, ничего лишнего."
        char_name = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": name_prompt}])
        char_name = char_name.strip() if char_name else "Алк*ш Петрович"
        user["character_name"] = char_name
    
    # Начальное состояние
    state = CharacterState(
        name=char_name,
        mood="😐 Норм",
        hunger="🍗 Не голоден",
        health="❤️ Здоров",
        money=random.randint(100, 1000),
        drunk="🍺 Трезв",
        risk="🎲 Средний",
        inventory=[],
        location="Дом",
        time="07:00"
    )
    
    # Сохраняем данные дня
    active_days[user_id] = {
        "stage": "simulation",
        "plan": plan,
        "state": state,
        "history": [],
        "message_id": None,
        "chat_id": message.chat.id,
        "tool_failures": 0
    }
    
    # Уменьшаем счётчик дней
    if user["days_limit"] != float('inf'):
        user["days_remaining"] -= 1
    
    # Запускаем цикл симуляции
    await run_simulation(user_id)

async def run_simulation(user_id: int):
    """Основной цикл дня"""
    day_data = active_days[user_id]
    state = day_data["state"]
    
    # Первый запуск — персонаж просыпается
    await simulation_step(user_id, "start")

async def simulation_step(user_id: int, context: str):
    """Один шаг симуляции"""
    day_data = active_days[user_id]
    state = day_data["state"]
    
    # Формируем промпт для персонажа (Нейросеть 2)
    history_text = "\n".join(day_data["history"][-5:]) if day_data["history"] else "День только начался."
    
    character_prompt = f"""Ты — {state.name}, персонаж-алк*ш в симуляторе жизни.
    
ТВОЁ СОСТОЯНИЕ:
😡 Настроение: {state.mood}
🍗 Голод: {state.hunger}
❤️ Здоровье: {state.health}
💰 Деньги: {state.money}₽
🍺 Пьяность: {state.drunk}
🎲 Азарт: {state.risk}
📍 Локация: {state.location}
⏰ Время: {state.time}

ПЛАН ДНЯ:
{day_data['plan']}

ЧТО УЖЕ ПРОИЗОШЛО:
{history_text}

ТЕКУЩАЯ СИТУАЦИЯ: {context}

Ты должен:
1. Написать что ты делаешь/думаешь СЕЙЧАС (матерись как с*ка, используй эмодзи)
2. В конце ОБЯЗАТЕЛЬНО указать инструмент для агента в формате [tool:sendagentsimple:твой запрос]

Примеры инструментов:
[tool:sendagentsimple:пойти в магазин]
[tool:sendagentsimple:ограбить прохожего]
[tool:sendagentsimple:познакомиться с девушкой]
[tool:sendagentsimple:выпить пива]
[tool:sendagentsimple:съ*б*ться от полиции]

Пиши от первого лица, живо, с матами, эмодзи. Используй инструмент в конце!"""

    char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": character_prompt}])
    
    if not char_response:
        day_data["tool_failures"] += 1
        if day_data["tool_failures"] >= 2:
            await bot.send_message(day_data["chat_id"], "❌ Ошибка персонажа! День прерван, но не потрачен.")
            del active_days[user_id]
            return
        else:
            # Повторная попытка
            await asyncio.sleep(1)
            await simulation_step(user_id, context)
            return
    
    day_data["tool_failures"] = 0  # Сброс счётчика ошибок
    
    # Проверяем наличие инструмента
    tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
    
    if not tool_match:
        # Пытаемся извлечь намерение или повторяем
        day_data["tool_failures"] += 1
        if day_data["tool_failures"] >= 2:
            await bot.send_message(day_data["chat_id"], "❌ Персонаж не хочет действовать! День прерван.")
            del active_days[user_id]
            return
        
        # Просим ещё раз с напоминанием
        fix_prompt = character_prompt + "\n\nВАЖНО: Ты забыл добавить [tool:...] в конце! Добавь сейчас!"
        char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": fix_prompt}])
        tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
        
        if not tool_match:
            await bot.send_message(day_data["chat_id"], "❌ Персонаж в ступоре! День прерван.")
            del active_days[user_id]
            return
    
    tool_text = tool_match.group(1).strip()
    # Убираем tool из текста для показа юзеру
    display_text = re.sub(r'\[tool:sendagentsimple:.*?\]', '', char_response, flags=re.IGNORECASE).strip()
    
    # Обновляем историю
    day_data["history"].append(f"[{state.time}] {state.name}: {display_text[:100]}...")
    
    # Теперь запрос к агенту окружения (Нейросеть 3)
    # Случайное событие с 30% шансом
    random_event = random.random() < 0.3
    
    agent_prompt = f"""Ты — агент окружения и событий в симуляторе жизни.

ПЕРСОНАЖ: {state.name}
ЕГО ДЕЙСТВИЕ (через инструмент): {tool_text}
ТЕКУЩЕЕ ВРЕМЯ: {state.time}
ЛОКАЦИЯ: {state.location}

ПЛАН ДНЯ (чтобы знать контекст):
{day_data['plan']}

ЗАДАЧА:
Опиши, что происходит В ОКРУЖЕНИИ. Что видит персонаж? Кто рядом? Что изменилось?
Используй эмодзи, будь живым, можешь добавить драмы.

{'ВАЖНО: Случилось РАНДОМНОЕ СОБЫТИЕ! Опиши что-то неожиданное: погода испортилась, появился полицейский, нашёлся кошелёк, etc.' if random_event else ''}

Формат ответа:
🌍 [Описание окружения с эмодзи]

Если есть событие — опиши его ярко!"""

    agent_response = await call_ai(AGENT_MODEL, [{"role": "user", "content": agent_prompt}])
    
    if not agent_response:
        agent_response = "🌍 Окружение без изменений..."
    
    # Обновляем состояние (имитация)
    # Меняем время
    current_hour = int(state.time.split(":")[0])
    new_hour = (current_hour + random.randint(1, 3)) % 24
    state.time = f"{new_hour:02d}:00"
    
    # Случайные изменения параметров
    if random.random() < 0.3:
        state.hunger = random.choice(["🍗 Голоден", "🍗 Хочу жрать п*здец", "🍗 Не голоден"])
    if random.random() < 0.2:
        state.drunk = random.choice(["🍺 Трезв", "🍺 Лёгкий б*харик", "🍺 П*ян в ж*пу"])
    
    # Обновляем локацию на основе инструмента (простая эвристика)
    location_keywords = {
        "магазин": "Магазин",
        "банк": "Банк",
        "дом": "Дом",
        "улиц": "Улица",
        "бар": "Бар",
        "тюрьм": "Тюрьма",
        "полиц": "Участок"
    }
    for keyword, loc in location_keywords.items():
        if keyword in tool_text.lower():
            state.location = loc
            break
    
    # Формируем карточку
    card_text = f"""🥸 {state.name} — День #{users_data[user_id]['days_lived'] + 1}

⏰ {state.time} | 📍 {state.location}

😡 Настроение: {state.mood}
🍗 Голод: {state.hunger}
❤️ Здоровье: {state.health}
💰 Деньги: {state.money}₽
🍺 Пьяность: {state.drunk}
🎲 Азарт: {state.risk}
🎒 Инвентарь: {', '.join(state.inventory) if state.inventory else 'Пусто'}

💬 {state.name} говорит:
{display_text}

{agent_response}

{'🔥 СЛУЧАЙНОЕ СОБЫТИЕ!' if random_event else ''}"""

    # Кнопки управления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"sim_step_{user_id}")],
        [InlineKeyboardButton(text="⏹️ Завершить день", callback_data=f"end_day_{user_id}")]
    ])
    
    # Редактируем или отправляем новое сообщение
    if day_data.get("message_id"):
        try:
            await bot.edit_message_text(
                card_text,
                chat_id=day_data["chat_id"],
                message_id=day_data["message_id"],
                reply_markup=keyboard
            )
        except:
            # Если не удалось отредактировать, отправляем новое
            msg = await bot.send_message(day_data["chat_id"], card_text, reply_markup=keyboard)
            day_data["message_id"] = msg.message_id
    else:
        msg = await bot.send_message(day_data["chat_id"], card_text, reply_markup=keyboard)
        day_data["message_id"] = msg.message_id

@dp.callback_query(F.data.startswith("sim_step_"))
async def simulation_next(callback: types.CallbackQuery):
    """Следующий шаг симуляции"""
    user_id = int(callback.data.split("_")[2])
    
    if user_id not in active_days:
        await callback.answer("День уже завершён!")
        return
    
    await callback.answer("⏳ Думаем...")
    await simulation_step(user_id, "продолжение")

@dp.callback_query(F.data.startswith("end_day_"))
async def end_day(callback: types.CallbackQuery):
    """Завершение дня"""
    user_id = int(callback.data.split("_")[2])
    
    if user_id not in active_days:
        await callback.answer("Уже завершено!")
        return
    
    day_data = active_days[user_id]
    user = users_data[user_id]
    
    await callback.answer("📝 Создаём саммари дня...")
    
    # Генерируем саммари через Нейросеть 1
    history_text = "\n".join(day_data["history"])
    
    summary_prompt = f"""Составь краткое саммари дня для персонажа {day_data['state'].name}:

ИСТОРИЯ ДНЯ:
{history_text}

Напиши серьёзное саммари в 3-5 предложений, что произошло за день. Без матов, для истории."""

    summary = await call_ai(PLANNER_MODEL, [{"role": "user", "content": summary_prompt}])
    
    if not summary:
        summary = "День прошёл событийно, но детали утеряны в алкогольном тумане..."
    
    # Сохраняем в историю
    user["days_lived"] += 1
    user["history"].append({
        "day_number": user["days_lived"],
        "summary": summary,
        "character_name": day_data["state"].name
    })
    
    # Очищаем активный день
    del active_days[user_id]
    
    await callback.message.edit_text(
        f"""✅ День #{user['days_lived']} завершён!

📖 Саммари:
{summary}

Можешь начать новый день в меню "Скачать ОЛО"!"""
    )

@dp.message(Command("history"))
async def show_history(message: types.Message):
    """Показать историю дней"""
    user_id = message.from_user.id
    user = users_data.get(user_id)
    
    if not user or not user["history"]:
        await message.answer("📭 История пуста!")
        return
    
    history_text = "📜 История твоих алк*шей:\n\n"
    for day in user["history"][-5:]:  # Последние 5 дней
        history_text += f"""🥸 День #{day['day_number']} — {day['character_name']}
{day['summary']}

"""
    
    await message.answer(history_text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
