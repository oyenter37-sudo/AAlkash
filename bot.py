# bot.py
import os
import json
import re
import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict, field

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
    current_step: int = 0
    total_steps: int = 0
    
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
    
    active_days[user_id] = {"stage": "waiting_description"}

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
        await message.answer("⏳ День идёт... Жди завершения действия!")
        return

async def process_day_description(message: types.Message):
    user_id = message.from_user.id
    description = message.text
    
    status_msg = await message.answer("🧠 Нейросеть 1 составляет детальный план дня...")
    
    planner_prompt = f"""Ты — планировщик дней для персонажа-алк*ша в игре-симуляторе.
    
Задача пользователя: "{description}"

Составь ДЕТАЛЬНЫЙ план дня из МИНИМУМ 10 конкретных действий. Не просто "утро/день/вечер", а конкретные шаги:
1. Проснуться и осмотреться
2. Выпить кофе/пива
3. Пойти туда-то
4. Сделать то-то
5. И так далее...

Каждое действие должно быть конкретным с примерным временем.
Персонаж может материться, совершать преступления, знакомиться, есть, ср*ть — всё что угодно.

Формат (строго):
1. [время]: конкретное действие
2. [время]: конкретное действие
3. [время]: конкретное действие
...
(минимум 10 пунктов)

Пиши серьёзно, без эмодзи, чётко по пунктам. Персонаж ОБЯЗАН следовать этому плану строго, не отклоняясь."""
    
    # Максимум 3 попытки сгенерировать план
    max_attempts = 3
    plan_steps = []
    
    for attempt in range(max_attempts):
        plan = await call_ai(PLANNER_MODEL, [{"role": "user", "content": planner_prompt}])
        
        if not plan:
            if attempt < max_attempts - 1:
                await status_msg.edit_text(f"🔄 Попытка {attempt + 1}/{max_attempts}... Ошибка, пробуем снова...")
                await asyncio.sleep(1)
                continue
            else:
                await status_msg.edit_text("❌ Ошибка планировщика после 3 попыток! День не потрачен.")
                return
        
        # Парсим план на шаги
        plan_steps = []
        for line in plan.strip().split('\n'):
            # Ищем строки типа "1. [10:00]: действие" или "1. 10:00: действие" или "1. действие"
            match = re.match(r'^\d+[\.\)]\s*\[?(\d{1,2}:?\d{0,2})\]?\s*[:.\-]?\s*(.+)$', line.strip())
            if match:
                time_str = match.group(1) if match.group(1) else "???"
                action = match.group(2).strip()
                if len(action) > 5:  # Фильтруем короткий мусор
                    plan_steps.append({"time": time_str, "action": action})
        
        # Если нашли достаточно шагов — ок
        if len(plan_steps) >= 6:
            break
        else:
            if attempt < max_attempts - 1:
                await status_msg.edit_text(f"🔄 План слишком короткий ({len(plan_steps)} шагов), пробуем снова... ({attempt + 1}/{max_attempts})")
                await asyncio.sleep(1)
            else:
                # Последняя попытка — берём что есть или дефолтный план
                if len(plan_steps) < 3:
                    await status_msg.edit_text("❌ Не удалось составить план! День не потрачен.")
                    return
    
    if len(plan_steps) < 3:
        await status_msg.edit_text("❌ План слишком короткий! День не потрачен.")
        return
    
    await status_msg.edit_text(f"✅ План составлен! {len(plan_steps)} действий. Запускаем персонажа...")
    
    user = users_data[user_id]
    char_name = user.get("character_name")
    
    if not char_name:
        name_prompt = "Придумай русское имя и фамилию для алк*ша-преступника. Только имя, ничего лишнего."
        char_name = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": name_prompt}])
        char_name = char_name.strip() if char_name else "Алк*ш Петрович"
        user["character_name"] = char_name
    
    state = CharacterState(
        name=char_name,
        mood="Норм",
        hunger="Не голоден",
        health="Здоров",
        money=random.randint(100, 1000),
        drunk="Трезв",
        risk="Средний",
        inventory=[],
        location="Неизвестно",
        time=plan_steps[0]["time"] if plan_steps else "07:00",
        current_step=0,
        total_steps=len(plan_steps)
    )
    
    active_days[user_id] = {
        "stage": "simulation",
        "plan": plan,
        "plan_steps": plan_steps,
        "state": state,
        "agent_context": "Персонаж только проснулся. Находится дома. Обычное утро, соседи шумят за стенкой.",
        "history": [],
        "message_id": None,
        "chat_id": message.chat.id,
        "processing": False,
        "day_ended": False
    }
    
    if user["days_limit"] != float('inf'):
        user["days_remaining"] -= 1
    
    # Показываем стартовую карточку
    await show_initial_card(user_id)

async def show_initial_card(user_id: int):
    """Показывает начальную карточку без действий персонажа"""
    day_data = active_days[user_id]
    state = day_data["state"]
    user = users_data[user_id]
    
    current_action = day_data["plan_steps"][0]["action"] if day_data["plan_steps"] else "Начать день"
    
    card_text = f"""🥸 <b>{state.name}</b> — День #{user['days_lived'] + 1}

⏰ {state.time} | 📍 {state.location}
📋 Шаг {state.current_step + 1}/{state.total_steps}

😡 Настроение: {state.mood}
🍗 Голод: {state.hunger} | ❤️ Здоровье: {state.health}
💰 {state.money}₽ | 🍺 {state.drunk} | 🎲 {state.risk}
🎒 {', '.join(state.inventory) if state.inventory else 'Пусто'}

📋 <b>План дня:</b>
{day_data['plan'][:800]}...

⏳ <i>Персонаж готовится начать день...</i>
⏳ <i>Нажми Обновить, чтобы увидеть первое действие</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"sim_step_{user_id}_0")],
        [InlineKeyboardButton(text="⏹️ Завершить день", callback_data=f"end_day_{user_id}")]
    ])
    
    msg = await bot.send_message(day_data["chat_id"], card_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    day_data["message_id"] = msg.message_id

@dp.callback_query(F.data.startswith("sim_step_"))
async def simulation_next(callback: types.CallbackQuery):
    """Следующий шаг симуляции"""
    parts = callback.data.split("_")
    user_id = int(parts[2])
    requested_step = int(parts[3]) if len(parts) > 3 else -1
    
    if user_id not in active_days:
        await callback.answer("День завершён!", show_alert=True)
        return
    
    day_data = active_days[user_id]
    
    if day_data.get("day_ended"):
        await callback.answer("День уже завершён!", show_alert=True)
        return
    
    if day_data.get("processing"):
        await callback.answer("⏳ Персонаж ещё думает... Жди!", show_alert=True)
        return
    
    # Проверяем что шаг правильный
    if requested_step != day_data["state"].current_step:
        await callback.answer("❌ Этот шаг уже прошёл!", show_alert=True)
        return
    
    # Блокируем кнопку
    day_data["processing"] = True
    await callback.answer("🧠 Персонаж думает...")
    
    # Показываем "Жди..." на кнопке
    await update_button_to_waiting(callback, day_data)
    
    # Запускаем шаг
    await run_simulation_step(user_id, callback)
    
    day_data["processing"] = False

async def update_button_to_waiting(callback: types.CallbackQuery, day_data: dict):
    """Меняет кнопку на 'Жди...'"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏳ Жди...", callback_data="waiting")],
            [InlineKeyboardButton(text="⏹️ Завершить день", callback_data=f"end_day_{callback.from_user.id}")]
        ])
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except:
        pass

async def run_simulation_step(user_id: int, callback: types.CallbackQuery):
    """Один шаг симуляции"""
    day_data = active_days[user_id]
    state = day_data["state"]
    
    if state.current_step >= len(day_data["plan_steps"]):
        # День закончился по плану
        await end_day_by_plan(user_id, callback)
        return
    
    current_step_data = day_data["plan_steps"][state.current_step]
    plan_action = current_step_data["action"]
    state.time = current_step_data["time"]
    
    # 1. Персонаж думает и решает как выполнить план (НЕ видит ответ агента)
    character_prompt = f"""Ты — {state.name}, персонаж-алк*ш в симуляторе жизни.
    
ТВОЁ ТЕКУЩЕЕ СОСТОЯНИЕ:
- Настроение: {state.mood}
- Голод: {state.hunger}
- Здоровье: {state.health}
- Деньги: {state.money}₽
- Пьяность: {state.drunk}
- Азарт: {state.risk}
- Локация: {state.location}
- Время: {state.time}
- Инвентарь: {state.inventory}

ТВОЯ ЗАДАЧА СЕЙЧАС (строго по плану):
"{plan_action}"

КОНТЕКСТ ОТ ПРОШЛЫХ СОБЫТИЙ:
{day_data['agent_context'][:500]}

Ты должен выполнить эту задачу из плана. Напиши КОРОТКО (2-3 предложения) что ты делаешь, как ты это делаешь. Матерись, используй эмодзи. Это твои мысли и действия — их увидит пользователь.

В конце укажи инструмент для агента (только он его увидит): [tool:sendagentsimple:твой запрос к агенту]"""

    char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": character_prompt}])
    
    if not char_response:
        await handle_ai_error(user_id, callback, "персонаж не отвечает")
        return
    
    # Извлекаем инструмент
    tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
    
    if not tool_match:
        # Пробуем ещё раз с напоминанием
        fix_prompt = character_prompt + "\n\nВАЖНО: Ты забыл добавить [tool:sendagentsimple:...] в конце! Это обязательно!"
        char_response = await call_ai(CHARACTER_MODEL, [{"role": "user", "content": fix_prompt}])
        tool_match = re.search(r'\[tool:sendagentsimple:(.*?)\]', char_response, re.IGNORECASE)
        
        if not tool_match:
            await handle_ai_error(user_id, callback, "персонаж не хочет использовать инструменты")
            return
    
    tool_text = tool_match.group(1).strip()
    display_text = re.sub(r'\[tool:sendagentsimple:.*?\]', '', char_response, flags=re.IGNORECASE).strip()
    
    # 2. Агент обрабатывает (пользователь этого НЕ видит!)
    # Шанс случайного события — 10%
    random_event = random.random() < 0.10
    
    agent_prompt = f"""Ты — агент окружения в симуляторе жизни. Пользователь НЕ видит твой ответ — только персонаж.

ПЕРСОНАЖ: {state.name}
ЕГО ЗАПРОС (через инструмент): {tool_text}
ТЕКУЩЕЕ ВРЕМЯ: {state.time}
ТЕКУЩАЯ ЛОКАЦИЯ: {state.location}

ЗАДАЧА ИЗ ПЛАНА: {plan_action}

ПРЕДЫДУЩИЙ КОНТЕКСТ:
{day_data['agent_context'][:300]}

{'ВАЖНО: Случилось РАНДОМНОЕ СОБЫТИЕ (10% шанс)! Опиши что-то неожиданное, что меняет ситуацию!' if random_event else ''}

Твоя задача:
1. Опиши что происходит вокруг (локация, люди, обстановка)
2. Опиши результат действия персонажа (успех/неудача)
3. Обнови локацию если нужно (любая, не шаблонная)
4. Обнови состояние персонажа если логично (ранение, находка денег, etc.)

Пиши подробно, это внутренняя логика игры. Персонаж потом увидит результат и отреагирует."""

    agent_response = await call_ai(AGENT_MODEL, [{"role": "user", "content": agent_prompt}])
    
    if not agent_response:
        agent_response = "Окружение без изменений. Действие выполнено."
    
    # Обновляем контекст для следующих шагов (персонаж будет знать, но юзер нет)
    day_data["agent_context"] = agent_response
    
    # Обновляем состояние персонажа на основе ответа агента
    update_state_from_agent(state, agent_response, tool_text)
    
    # Сохраняем в историю
    day_data["history"].append({
        "step": state.current_step,
        "time": state.time,
        "action": plan_action,
        "char_thoughts": display_text,
        "agent_result": agent_response  # Юзер этого не видит!
    })
    
    # 3. Показываем пользователю только мысли персонажа и его состояние
    await show_step_result(user_id, callback, display_text, random_event)
    
    # Переходим к следующему шагу
    state.current_step += 1

def update_state_from_agent(state: CharacterState, agent_text: str, tool_text: str):
    """Обновляет состояние на основе ответа агента"""
    # Обновляем локацию если агент упомянул
    location_indicators = ["ты в", "ты находишься в", "локация:", "место:"]
    for indicator in location_indicators:
        if indicator in agent_text.lower():
            # Пытаемся извлечь локацию
            parts = agent_text.lower().split(indicator)
            if len(parts) > 1:
                possible_loc = parts[1].split('.')[0].split(',')[0].strip()
                if len(possible_loc) > 2:
                    state.location = possible_loc[:50]
                    break
    
    # Если локация не определена, берём из инструмента
    if state.location == "Неизвестно" or not state.location:
        if "дом" in tool_text.lower():
            state.location = "Дом"
        elif "улиц" in tool_text.lower():
            state.location = "Улица"
        elif "магазин" in tool_text.lower():
            state.location = "Магазин"
        elif "банк" in tool_text.lower():
            state.location = "Банк"
        elif "бар" in tool_text.lower():
            state.location = "Бар"
        elif "тюрьм" in tool_text.lower():
            state.location = "Тюрьма"
        else:
            state.location = "Неизвестная локация"
    
    # Случайные изменения параметров
    if "ранен" in agent_text.lower() or "поранил" in agent_text.lower():
        state.health = "Ранен"
    if "деньги" in agent_text.lower() or "нашёл" in agent_text.lower() or "украл" in agent_text.lower():
        # Парсим сумму если есть
        import re
        money_match = re.search(r'(\d+)\s*(руб|₽)', agent_text.lower())
        if money_match:
            state.money += int(money_match.group(1))
    
    # Обновляем голод и пьянство случайно
    if random.random() < 0.3:
        state.hunger = random.choice(["Сыт", "Норм", "Хочу жрать"])
    if random.random() < 0.2:
        state.drunk = random.choice(["Трезв", "Лёгкий б*харик", "П*ян"])

async def show_step_result(user_id: int, callback: types.CallbackQuery, char_text: str, has_random_event: bool):
    """Показывает результат шага пользователю (только персонаж, без агента)"""
    day_data = active_days[user_id]
    state = day_data["state"]
    user = users_data[user_id]
    
    # Следующий шаг для кнопки
    next_step = state.current_step + 1
    
    # Проверяем конец дня
    if state.current_step >= len(day_data["plan_steps"]) - 1:
        is_last = True
        next_button_text = "🏁 Завершить день"
    else:
        is_last = False
        next_button_text = "🔄 Следующий шаг"
    
    event_text = "\n\n🔥 <b>СЛУЧАЙНОЕ СОБЫТИЕ!</b>" if has_random_event else ""
    
    card_text = f"""🥸 <b>{state.name}</b> — День #{user['days_lived'] + 1}

⏰ {state.time} | 📍 {state.location}
📋 Шаг {state.current_step + 1}/{state.total_steps}

😡 {state.mood} | 🍗 {state.hunger} | ❤️ {state.health}
💰 {state.money}₽ | 🍺 {state.drunk} | 🎲 {state.risk}
🎒 {', '.join(state.inventory) if state.inventory else 'Пусто'}

💬 <i>{char_text}</i>{event_text}

{'<i>День завершён по плану!</i>' if is_last else '<i>Нажми для продолжения...</i>'}"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=next_button_text, callback_data=f"sim_step_{user_id}_{next_step}")],
        [InlineKeyboardButton(text="⏹️ Завершить день досрочно", callback_data=f"end_day_{user_id}")]
    ])
    
    try:
        await callback.message.edit_text(card_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    except Exception as e:
        msg = await bot.send_message(day_data["chat_id"], card_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        day_data["message_id"] = msg.message_id

async def handle_ai_error(user_id: int, callback: types.CallbackQuery, error_text: str):
    """Обработка ошибки AI"""
    day_data = active_days[user_id]
    day_data["processing"] = False
    
    await callback.message.edit_text(
        f"""❌ Ошибка: {error_text}

День прерван, но не потрачен. Начни заново!"""
    )
    del active_days[user_id]

async def end_day_by_plan(user_id: int, callback: types.CallbackQuery):
    """Завершение дня по плану (все шаги выполнены)"""
    day_data = active_days[user_id]
    user = users_data[user_id]
    
    await callback.answer("📝 День завершён по плану! Создаём саммари...")
    
    # Генерируем саммари
    history_text = "\n".join([f"Шаг {h['step']}: {h['char_thoughts'][:100]}" for h in day_data["history"]])
    
    summary_prompt = f"""Составь краткое саммари дня для персонажа {day_data['state'].name}:

ИСТОРИЯ ДНЯ:
{history_text}

Напиши серьёзное саммари в 3-5 предложений, что произошло за день. Без матов."""

    summary = await call_ai(PLANNER_MODEL, [{"role": "user", "content": summary_prompt}])
    
    if not summary:
        summary = "День прошёл событийно, но детали утеряны..."
    
    user["days_lived"] += 1
    user["history"].append({
        "day_number": user["days_lived"],
        "summary": summary,
        "character_name": day_data['state'].name
    })
    
    del active_days[user_id]
    
    await callback.message.edit_text(
        f"""✅ День #{user['days_lived']} завершён по плану!

📖 Саммари:
{summary}

Можешь начать новый день!"""
    )

@dp.callback_query(F.data.startswith("end_day_"))
async def end_day(callback: types.CallbackQuery):
    """Досрочное завершение дня"""
    user_id = int(callback.data.split("_")[2])
    
    if user_id not in active_days:
        await callback.answer("Уже завершено!", show_alert=True)
        return
    
    day_data = active_days[user_id]
    
    if day_data.get("processing"):
        await callback.answer("⏳ Дождись окончания текущего действия!", show_alert=True)
        return
    
    if day_data.get("day_ended"):
        await callback.answer("День уже завершается!", show_alert=True)
        return
    
    day_data["day_ended"] = True
    user = users_data[user_id]
    
    await callback.answer("📝 Создаём саммари...")
    
    history_text = "\n".join([f"Шаг {h['step']}: {h['char_thoughts'][:100]}" for h in day_data["history"]])
    
    summary_prompt = f"""Составь краткое саммари дня для персонажа {day_data['state'].name} (завершён досрочно):

ИСТОРИЯ ДНЯ:
{history_text}

Напиши серьёзное саммари в 3-5 предложений, что произошло. Без матов."""

    summary = await call_ai(PLANNER_MODEL, [{"role": "user", "content": summary_prompt}])
    
    if not summary:
        summary = "День закончился раньше времени..."
    
    user["days_lived"] += 1
    user["history"].append({
        "day_number": user["days_lived'],
        "summary": summary,
        "character_name": day_data['state'].name
    })
    
    del active_days[user_id]
    
    await callback.message.edit_text(
        f"""✅ День #{user['days_lived']} завершён досрочно!

📖 Саммари:
{summary}

Можешь начать новый день!"""
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
