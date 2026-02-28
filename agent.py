import os
import time
import threading
import schedule
import requests
from datetime import datetime, timedelta
import telebot
import anthropic

# ============================================================
# CONFIGURATION
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
MY_CHAT_ID = int(os.environ.get("MY_CHAT_ID", "0"))
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")

ISRAEL_UTC_OFFSET = 2

bot = telebot.TeleBot(TELEGRAM_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ============================================================
# HELPERS
# ============================================================
def get_israel_now():
    from datetime import timezone
    return datetime.now(timezone.utc) + timedelta(hours=ISRAEL_UTC_OFFSET)

def today_display():
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    days_ru = {
        0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг",
        4: "Пятница", 5: "Суббота", 6: "Воскресенье"
    }
    now = get_israel_now()
    return f"{days_ru[now.weekday()]}, {now.day} {months_ru[now.month]} {now.year}"

# ============================================================
# WEB SEARCH FOR HISTORICAL FACTS
# ============================================================
def fetch_this_day_facts():
    """Fetch real historical facts for today from Wikipedia API."""
    now = get_israel_now()
    day, month = now.day, now.month
    facts = ""

    # Wikipedia On This Day — events
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month:02d}/{day:02d}"
        resp = requests.get(url, headers={"User-Agent": "MotivatorBot/1.0"}, timeout=15)
        if resp.status_code == 200:
            events = resp.json().get("events", [])
            keywords = ["compan", "invent", "found", "launch", "patent", "discover",
                        "first", "record", "billion", "million", "startup", "technolog",
                        "israel", "revolution", "independ", "nobel", "space", "comput",
                        "internet", "phone", "electric", "medicine", "women", "rights",
                        "freedom", "surviv", "overcame", "bankrupt", "fail", "success",
                        "entrepren", "business", "market", "apple", "google", "amazon",
                        "tesla", "microsoft", "war", "peace", "treaty"]
            selected = []
            other = []
            for e in events:
                text = e.get("text", "")
                year = e.get("year", "")
                entry = f"[{year}] {text}"
                if any(kw in text.lower() for kw in keywords):
                    selected.append(entry)
                else:
                    other.append(entry)
            import random
            random.shuffle(other)
            all_events = selected[:10] + other[:5]
            if all_events:
                facts += "СОБЫТИЯ ЭТОГО ДНЯ В ИСТОРИИ:\n"
                for s in all_events:
                    facts += f"- {s}\n"
    except Exception as e:
        print(f"Wikipedia events error: {e}")

    # Wikipedia On This Day — births
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/births/{month:02d}/{day:02d}"
        resp = requests.get(url, headers={"User-Agent": "MotivatorBot/1.0"}, timeout=15)
        if resp.status_code == 200:
            births = resp.json().get("births", [])
            biz_keywords = ["entrepren", "business", "invent", "found", "ceo",
                            "billion", "scientist", "pioneer", "leader", "nobel",
                            "author", "philosoph", "israel", "engineer", "vision"]
            notable = []
            for b in births:
                text = b.get("text", "")
                year = b.get("year", "")
                if any(kw in text.lower() for kw in biz_keywords):
                    notable.append(f"[{year}] {text}")
            if notable:
                facts += "\nРОДИЛИСЬ В ЭТОТ ДЕНЬ:\n"
                for n in notable[:8]:
                    facts += f"- {n}\n"
    except Exception as e:
        print(f"Wikipedia births error: {e}")

    return facts if facts else "Факты не загрузились. Используй свои знания о событиях этого дня."

# ============================================================
# CLAUDE API
# ============================================================
def call_claude(system_prompt, user_content, max_tokens=2500, retries=3):
    for attempt in range(retries):
        try:
            response = claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < retries - 1:
                time.sleep((attempt + 1) * 10)
                continue
            print(f"Claude error: {e.status_code}")
            return None
        except Exception as e:
            print(f"Claude exception: {e}")
            return None

# ============================================================
# BOT PERSONALITY
# ============================================================
BASE_PROMPT = """Ты — личный мотивационный коуч в Telegram. Пишешь ОДНОМУ человеку — Мише, предпринимателю из Израиля. Салон красоты iStudio в Ришон ле-Ционе, семья, второй бизнес, здоровье и саморазвитие.

ГЛАВНОЕ — ФАКТЫ:
- Тебе даются РЕАЛЬНЫЕ исторические события этого дня из Wikipedia
- Выбирай МАЛОИЗВЕСТНЫЕ но поразительные — не банальщину
- Рассказывай как историю: завязка → поворот → урок
- Связывай с бизнесом и жизнью предпринимателя
- НИКОГДА не выдумывай. Если не уверен — не упоминай

СТИЛЬ:
- Как начитанный остроумный друг, а не робот
- Короткие фразы, живой язык, разговорный тон
- Эмодзи: 3-6 к месту
- НЕ используй звёздочки, подчёркивания, Markdown
- Русский, сочный, с энергией
- 1500-2000 символов максимум
- Каждое сообщение = мини-история которую хочется дочитать до конца"""

MORNING_PROMPT = BASE_PROMPT + """

УТРО (07:00) — ЗАРЯД
Тон: крепкий эспрессо. Бодрый, дерзкий.

Структура:
1. Дата + день недели
2. Главный факт дня — разверни в историю (5-7 предложений) с неожиданным поворотом
3. Ещё 2-3 коротких факта (по 1 предложению) — удивляющие
4. Цитата (НЕ банальная — не "верь в себя", а что-то острое и неожиданное)
5. Пинок на день — одно предложение"""

DAY_PROMPT = BASE_PROMPT + """

ДЕНЬ (13:00) — ПЕРЕЗАГРУЗКА
Тон: умный друг за обедом. С перчинкой.

Структура:
1. Неформальное начало
2. Один факт дня который НЕ был утром
3. Бизнес-совет — конкретный, применимый сегодня (маркетинг, продажи, переговоры)
4. Израильский стартап или tech-факт — малоизвестный, удивительный
5. Бизнес-юмор или ирония (1-2 предложения)"""

EVENING_PROMPT = BASE_PROMPT + """

ВЕЧЕР (21:00) — РЕФЛЕКСИЯ
Тон: мудрый наставник. Спокойный, глубокий, не занудный.

Структура:
1. Спокойное начало
2. История преодоления — кто провалился и преуспел. С деталями и цифрами. Малоизвестная.
3. Вопрос для рефлексии — КОНКРЕТНЫЙ. Не "что ты ценишь" а "какой клиент мог бы вернуться если бы ты позвонил ему сегодня?"
4. Тёплый финал — по-мужски"""

# ============================================================
# SAFE SEND
# ============================================================
def safe_send(chat_id, text, max_len=4000):
    if not text:
        text = "Мотиватор задумался..."
    if len(text) <= max_len:
        try:
            bot.send_message(chat_id, text)
        except Exception as e:
            print(f"Send error: {e}")
        return
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        split_at = text.rfind("\n\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    for part in parts:
        try:
            bot.send_message(chat_id, part)
            time.sleep(0.3)
        except Exception as e:
            print(f"Send error: {e}")

# ============================================================
# SCHEDULED MESSAGES
# ============================================================
def send_morning():
    date_str = today_display()
    facts = fetch_this_day_facts()
    prompt = f"Сегодня: {date_str}.\n\n{facts}\n\nСгенерируй УТРЕННЕЕ сообщение. Выбери самые удивительные факты."
    response = call_claude(MORNING_PROMPT, prompt)
    if response:
        safe_send(MY_CHAT_ID, response)
    else:
        safe_send(MY_CHAT_ID, f"☀️ {date_str}\n\nClaude думает... Но ты не думай — действуй!")

def send_afternoon():
    date_str = today_display()
    facts = fetch_this_day_facts()
    prompt = f"Сегодня: {date_str}.\n\n{facts}\n\nСгенерируй ДНЕВНОЕ сообщение. Выбери ДРУГИЕ факты, не те что могли быть утром."
    response = call_claude(DAY_PROMPT, prompt)
    if response:
        safe_send(MY_CHAT_ID, response)
    else:
        safe_send(MY_CHAT_ID, "🍽 Сделай одну вещь которую откладывал. Прямо сейчас.")

def send_evening():
    date_str = today_display()
    facts = fetch_this_day_facts()
    prompt = f"Сегодня: {date_str}.\n\n{facts}\n\nСгенерируй ВЕЧЕРНЕЕ сообщение. Фокус на преодоление и рефлексию."
    response = call_claude(EVENING_PROMPT, prompt)
    if response:
        safe_send(MY_CHAT_ID, response)
    else:
        safe_send(MY_CHAT_ID, "🌙 Чем сегодня будешь гордиться через год? Отдыхай.")

# ============================================================
# COMMANDS
# ============================================================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    if message.chat.id != MY_CHAT_ID:
        return
    safe_send(MY_CHAT_ID,
        "🔥 Мотиватор на связи!\n\n"
        "Три сообщения в день с реальными фактами из истории:\n\n"
        "☀️ 07:00 — Заряд (факты дня + цитата + пинок)\n"
        "🍽 13:00 — Перезарядка (бизнес-совет + стартап + юмор)\n"
        "🌙 21:00 — Рефлексия (история преодоления + вопрос)\n\n"
        "/morning /afternoon /evening — вызвать вручную\n"
        "/motivate — мотивация сейчас\n"
        "/fact — 5 фактов про сегодняшний день\n\n"
        "Или просто напиши — отвечу как коуч."
    )

@bot.message_handler(commands=["morning"])
def cmd_morning(message):
    if message.chat.id != MY_CHAT_ID: return
    safe_send(MY_CHAT_ID, "☀️ Секунду...")
    send_morning()

@bot.message_handler(commands=["afternoon"])
def cmd_afternoon(message):
    if message.chat.id != MY_CHAT_ID: return
    safe_send(MY_CHAT_ID, "🍽 Секунду...")
    send_afternoon()

@bot.message_handler(commands=["evening"])
def cmd_evening(message):
    if message.chat.id != MY_CHAT_ID: return
    safe_send(MY_CHAT_ID, "🌙 Секунду...")
    send_evening()

@bot.message_handler(commands=["motivate"])
def cmd_motivate(message):
    if message.chat.id != MY_CHAT_ID: return
    facts = fetch_this_day_facts()
    prompt = f"Сегодня: {today_display()}.\n\n{facts}\n\nОдин удивительный факт из списка + связь с жизнью предпринимателя. 5-7 предложений. Мощно и коротко."
    response = call_claude(BASE_PROMPT, prompt)
    if response:
        safe_send(MY_CHAT_ID, response)

@bot.message_handler(commands=["fact"])
def cmd_fact(message):
    if message.chat.id != MY_CHAT_ID: return
    safe_send(MY_CHAT_ID, "🔍 Ищу факты...")
    facts = fetch_this_day_facts()
    prompt = (
        f"Сегодня: {today_display()}.\n\n{facts}\n\n"
        "Выбери 5 самых УДИВИТЕЛЬНЫХ и малоизвестных фактов. "
        "Каждый в 2-3 предложениях с деталями. Пронумеруй."
    )
    response = call_claude(BASE_PROMPT, prompt)
    if response:
        safe_send(MY_CHAT_ID, response)

# ============================================================
# FREE TEXT — Coach
# ============================================================
COACH_PROMPT = """Ты — мотивационный коуч Миши (предприниматель, Израиль, салон красоты iStudio).
Коротко (3-7 предложений). Конкретно. Без Markdown. Тон зависит от времени суток."""

@bot.message_handler(func=lambda m: m.chat.id == MY_CHAT_ID)
def handle_text(message):
    user_text = message.text.strip()
    hour = get_israel_now().hour
    time_ctx = "утро" if hour < 12 else "день" if hour < 18 else "вечер"
    prompt = f"Сейчас {time_ctx} ({get_israel_now().strftime('%H:%M')}). Миша: «{user_text}»"
    response = call_claude(COACH_PROMPT, prompt, max_tokens=1000)
    if response:
        safe_send(MY_CHAT_ID, response)

# ============================================================
# SCHEDULER
# ============================================================
def run_scheduler():
    schedule.every().day.at(f"{7 - ISRAEL_UTC_OFFSET:02d}:00").do(send_morning)
    schedule.every().day.at(f"{13 - ISRAEL_UTC_OFFSET:02d}:00").do(send_afternoon)
    schedule.every().day.at(f"{21 - ISRAEL_UTC_OFFSET:02d}:00").do(send_evening)
    print("📋 07:00 | 13:00 | 21:00 (Israel)")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    print("🔥 МОТИВАТОР НА ПОСТУ!")
    print(f"📅 {get_israel_now().strftime('%Y-%m-%d %H:%M')}")
    bot.delete_webhook(drop_pending_updates=True)
    time.sleep(1)
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("📱 Polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
