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
PLANNER_MODEL = "gemini-fast"
CHARACTER_MODEL = "mistral"
AGENT_MODEL = "gemini-fast"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище
users_data: Dict[int, dict] = {}
active_days: Dict[int, dict] = {}

SPECIAL_USERS = {"@asd123dad"}

@dataclass
class CharacterState:
    name: str
    mood: str
    hunger: str
    health: str
    money: int
    drunk: str
    risk: str
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
    
    if user_id in active_days:
        await message.answer("❌ Сначала заверши текущий день! Нажми ⏹️ Завершить день.")
        return
    
    if user_id not in users_data:
        is_special = f"@{username}" in SPECIAL_USERS if username else False
        days_limit = float('inf') if is_special else 3
        
        users_data[user_id] = {
            "username": username,
            "days_lived": 0,
            "drunk_count": 0,
            "referrals": 0,
            "beer_liters": 1.0,
            "days_limit": days_limit,
            "days_remaining": days_limit if not is_special else float('inf'),
            "history": [],
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
    
    active_days[user_id] = {"stage": "waiting_description", "messages": []}

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    if message.text == "🔙 Назад":
        await message.answer("Главное меню:", reply_markup=get_main_menu())
        return
    
    if user_id in active_days and active_days[user_id].get("stage") == "waiting_description":
        await process_day_description(message)
        return
    
    if user_id in active_days and active_days[user_id].get("stage") == "simulation":
        await message.answer("⏳ День идёт... Жми 🔄 Обновить для продолжения!")
        return

async def process_day_description(message: types.Message):
    user_id = message.from_user.id
    description = message.text
    
    status_msg = await message.answer("🧠 Нейросеть 1 составляет план дня...")
    
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
    
    user = users_data[user_id]
    char_name = user.get("character_name")
    
    if not char_name:
        name_prompt = "Придумай русское имя и фамилию для алк*ша-преступника. Только имя, ничего лишнего."
        char_name = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": name_prompt}])
        char_name = char_name.strip() if char_name else "Алк*ш Петрович"
        user["character_name"] = char_name
    
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
    
    active_days[user_id] = {
        "stage": "simulation",
        "plan": plan,
        "state": state,
        "history": [],
        "message_id": None,
        "chat_id": message.chat.id,
        "tool_failures": 0,
        "waiting_for_user": True,
        "day_ended": False
    }
    
    if user["days_limit"] != float('inf'):
        user["days_remaining"] -= 1
    
    await show_simulation_card(user_id, is_start=True)

async def show_simulation_card(user_id: int, is_start: bool = False):
    """Показывает карточку симуляции (только при старте или по кнопке)"""
    day_data = active_days[user_id]
    state = day_data["state"]
    
    if is_start:
        # Первый запуск — персонаж только проснулся
        display_text = f"Бл*ть, утро... Опять этот д*рьмовый мир. Надо встать и что-то делать, нах*й."
        agent_text = "🌍 Ты дома. Соседи орят за стенкой, погода за окном — х*й пойми какая. Начинается новый день, бл*ть."
        
        day_data["history"].append(f"[{state.time}] {state.name} проснулся дома")
    else:
        # Это не должно вызываться без нажатия кнопки
        return
    
    card_text = format_card(state, day_data, display_text, agent_text, False)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"sim_step_{user_id}")],
        [InlineKeyboardButton(text="⏹️ Завершить день", callback_data=f"end_day_{user_id}")]
    ])
    
    msg = await bot.send_message(
        day_data["chat_id"], 
        card_text, 
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    day_data["message_id"] = msg.message_id

def format_card(state, day_data, char_text, agent_text, has_random_event):
    """Форматирует карточку компактно с HTML"""
    inventory_str = ", ".join(state.inventory) if state.inventory else "Пусто"
    
    # Компактная версия — только важное
    card = f"""🥸 <b>{state.name}</b> — День #{users_data[list(active_days.keys())[list(active_days.values()).index(day_data)]['days_lived'] + 1 if list(active_days.keys())[list(active_days.values()).index(day_data)] in users_data else 1}

⏰ {state.time} | 📍 {state.location}

😡 {state.mood} | 🍗 {state.hunger} | ❤️ {state.health}
💰 {state.money}₽ | 🍺 {state.drunk} | 🎲 {state.risk}
🎒 {inventory_str}

💬 <i>{char_text}</i>

{agent_text}"""
    
    if has_random_event:
        card += "\n\n🔥 <b>СЛУЧАЙНОЕ СОБЫТИЕ!</b>"
    
    return card

@dp.callback_query(F.data.startswith("sim_step_"))
async def simulation_next(callback: types.CallbackQuery):
    """Следующий шаг симуляции — только по кнопке"""
    user_id = int(callback.data.split("_")[2])
    
    if user_id not in active_days:
        await callback.answer("День завершён!", show_alert=True)
        return
    
    day_data = active_days[user_id]
    
    if day_data.get("day_ended"):
        await callback.answer("День уже завершён!", show_alert=True)
        return
    
    await callback.answer("🧠 Думаем...")
    
    # Запускаем шаг симуляции
    await run_simulation_step(user_id, callback)

async def run_simulation_step(user_id: int, callback: types.CallbackQuery):
    """Один шаг симуляции"""
    day_data = active_days[user_id]
    state = day_data["state"]
    
    # Формируем промпт для персонажа
    history_text = "\n".join(day_data["history"][-3:]) if day_data["history"] else "Начало дня."
    
    character_prompt = f"""Ты — {state.name}, персонаж-алк*ш в симуляторе жизни.
    
ТВОЁ СОСТОЯНИЕ:
- Настроение: {state.mood}
- Голод: {state.hunger}
- Здоровье: {state.health}
- Деньги: {state.money}₽
- Пьяность: {state.drunk}
- Азарт: {state.risk}
- Локация: {state.location}
- Время: {state.time}

ПЛАН ДНЯ:
{day_data['plan']}

ЧТО УЖЕ ПРОИЗОШЛО:
{history_text}

Ты должен написать КОРОТКО что ты делаешь/думаешь сейчас (2-3 предложения, матерись, эмодзи).
В конце ОБЯЗАТЕЛЬНО укажи инструмент: [tool:sendagentsimple:твой запрос]

Примеры:
[tool:sendagentsimple:пойти в магазин]
[tool:sendagentsimple:ограбить прохожего]"""

    char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": character_prompt}])
    
    if not char_response:
        day_data["tool_failures"] += 1
        if day_data["tool_failures"] >= 2:
            await callback.message.edit_text("❌ Ошибка персонажа! День прерван, но не потрачен.")
            del active_days[user_id]
            return
        else:
            await asyncio.sleep(1)
            await run_simulation_step(user_id, callback)
            return
    
    day_data["tool_failures"] = 0
    
    # Проверяем инструмент
    tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
    
    if not tool_match:
        day_data["tool_failures"] += 1
        if day_data["tool_failures"] >= 2:
            await callback.message.edit_text("❌ Персонаж не хочет действовать! День прерван.")
            del active_days[user_id]
            return
        
        fix_prompt = character_prompt + "\n\nВАЖНО: Ты забыл добавить [tool:...] в конце! Добавь сейчас!"
        char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": fix_prompt}])
        tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
        
        if not tool_match:
            await callback.message.edit_text("❌ Персонаж в ступоре! День прерван.")
            del active_days[user_id]
            return
    
    tool_text = tool_match.group(1).strip()
    # Убираем tool из текста для показа
    display_text = re.sub(r'\[tool:sendagentsimple:.*?\]', '', char_response, flags=re.IGNORECASE).strip()
    
    # Обновляем историю
    day_data["history"].append(f"[{state.time}] {display_text[:80]}...")
    
    # Запрос к агенту окружения
    # Шанс случайного события — 10%
    random_event = random.random() < 0.10
    
    agent_prompt = f"""Ты — агент окружения в симуляторе жизни.

ПЕРСОНАЖ: {state.name}
ЕГО ДЕЙСТВИЕ: {tool_text}
ТЕКУЩЕЕ ВРЕМЯ: {state.time}
ЛОКАЦИЯ: {state.location}

ПЛАН ДНЯ (для контекста):
{day_data['plan'][:500]}

ЗАДАЧА: Опиши КОРОТКО (1-2 предложения) что происходит вокруг. Используй эмодзи.

{'ВАЖНО: Случилось РАНДОМНОЕ СОБЫТИЕ (10% шанс)! Опиши что-то неожиданное!' if random_event else ''}"""

    agent_response = await call_ai(AGENT_MODEL, [{"role": "user", "content": agent_prompt}])
    
    if not agent_response:
        agent_response = "🌍 Окружение без изменений..."
    
    # Обновляем состояние
    current_hour = int(state.time.split(":")[0])
    new_hour = (current_hour + random.randint(1, 3)) % 24
    state.time = f"{new_hour:02d}:00"
    
    # Случайные изменения параметров
    if random.random() < 0.3:
        state.hunger = random.choice(["😐 Норм", "😠 Хочу жрать", "🤢 Сыт"])
    if random.random() < 0.2:
        state.drunk = random.choice(["😐 Трезв", "😏 Лёгкий б*харик", "🤪 П*ян"])
    
    # Обновляем локацию
    location_keywords = {
        "магазин": "Магазин",
        "банк": "Банк",
        "дом": "Дом",
        "улиц": "Улица",
        "бар": "Бар",
        "тюрьм": "Тюрьма",
        "полиц": "Полиция",
        "работ": "Работа",
        "парк": "Парк"
    }
    for keyword, loc in location_keywords.items():
        if keyword in tool_text.lower():
            state.location = loc
            break
    
    # Формируем карточку
    card_text = format_card(state, day_data, display_text, agent_response, random_event)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"sim_step_{user_id}")],
        [InlineKeyboardButton(text="⏹️ Завершить день", callback_data=f"end_day_{user_id}")]
    ])
    
    try:
        await callback.message.edit_text(card_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception as e:
        # Если не удалось отредактировать — отправляем новое
        msg = await bot.send_message(day_data["chat_id"], card_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        day_data["message_id"] = msg.message_id

@dp.callback_query(F.data.startswith("end_day_"))
async def end_day(callback: types.CallbackQuery):
    """Завершение дня"""
    user_id = int(callback.data.split("_")[2])
    
    if user_id not in active_days:
        await callback.answer("Уже завершено!", show_alert=True)
        return
    
    day_data = active_days[user_id]
    
    if day_data.get("day_ended"):
        await callback.answer("День уже завершается!", show_alert=True)
        return
    
    day_data["day_ended"] = True
    user = users_data[user_id]
    
    await callback.answer("📝 Создаём саммари...")
    
    # Генерируем саммари
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
    for day in user["history"][-5:]:
        history_text += f"""🥸 День #{day['day_number']} — {day['character_name']}
{day['summary']}

"""
    
    await message.answer(history_text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
