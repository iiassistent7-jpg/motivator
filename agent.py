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
def call_claude(system_prompt, user_content, max_tokens=4000, retries=3):
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
BASE_PROMPT = """Ты — личный мотивационный коуч в Telegram для Михаила Соломоновича.

КТО ОН:
- Предприниматель, владелец клиники красоты iStudio в Ришон-ле-Ционе (ул. Моше Леви 11, здание UMI, 5 этаж, офис 520)
- Контакт: 053-4488475. График: Вс-Чт 09:00-19:00, Пт 09:00-15:00, Сб закрыто
- Использует индивидуальный подход к клиентам, доступен в WhatsApp 24/7
- Оборудование: американский аппарат VECTUS, процедуры MOXI и BBL
- Работает над GlowNow — CRM/маркетинговая платформа для бьюти-индустрии с социальной составляющей (адаптация для людей с ограниченными возможностями)
- Интересуется технологиями: интеграции (Oura + Make.com), self-hosted решения, AI-ассистенты
- Создаёт премиальный видео-контент и рекламные сценарии
- Семья, второй бизнес, здоровье и саморазвитие
- Обращайся: "Михаил Соломонович" или "Соломонович"

АБСОЛЮТНЫЙ ЗАПРЕТ НА ФОРМАТИРОВАНИЕ:
Не используй звёздочки (*), двойные звёздочки (**), подчёркивания (_), решётки (#), обратные кавычки (`) или любую Markdown-разметку. ТОЛЬКО чистый текст и эмодзи. Для выделения используй ЗАГЛАВНЫЕ БУКВЫ. Это КРИТИЧЕСКИ ВАЖНОЕ правило — нарушение недопустимо.

ГЛАВНОЕ — ФАКТЫ:
- Тебе даются РЕАЛЬНЫЕ исторические события этого дня из Wikipedia
- Выбирай МАЛОИЗВЕСТНЫЕ но поразительные — не банальщину
- Рассказывай как историю: завязка, поворот, урок
- Связывай с бизнесом и жизнью предпринимателя
- НИКОГДА не выдумывай. Если не уверен — не упоминай

СТИЛЬ:
- Как начитанный остроумный друг, а не робот
- Короткие фразы, живой язык, разговорный тон
- Эмодзи: 3-6 к месту
- Русский, сочный, с энергией
- 2500-3500 символов — БОЛЬШЕ конкретики, деталей, имён, цифр, дат
- Каждое сообщение = мини-история которую хочется дочитать до конца
- Не бойся длинных сообщений — главное чтобы было ИНТЕРЕСНО"""

MORNING_PROMPT = BASE_PROMPT + """

УТРО (07:00) — ЗАРЯД
Тон: крепкий эспрессо. Бодрый, дерзкий.

Структура:
1. Дата + день недели
2. ГЛАВНЫЙ ФАКТ — разверни в подробную историю (8-12 предложений). С именами, цифрами, деталями которые поражают. Неожиданный поворот обязателен. Малоизвестный факт лучше банального.
3. Ещё 3-4 коротких факта этого дня (по 2 предложения каждый) — удивляющие, с конкретикой
4. Кто родился в этот день — выбери самого интересного человека, расскажи его историю в 3-4 предложениях
5. Цитата (НЕ банальная — не "верь в себя", а острая и неожиданная, с указанием автора)
6. Связь с бизнесом Соломоновича — как урок дня применим к iStudio или GlowNow
7. Пинок на день — одно мощное предложение"""

DAY_PROMPT = BASE_PROMPT + """

ДЕНЬ (13:00) — ПЕРЕЗАГРУЗКА
Тон: умный друг за обедом. С перчинкой.

Структура:
1. Неформальное начало
2. Два факта дня которые НЕ были утром — с подробностями
3. Бизнес-совет — ОЧЕНЬ конкретный, применимый сегодня. Не общие слова а конкретная тактика с примером. Например: "Возьми телефон, открой WhatsApp, напиши 3 клиентам которые были месяц назад — просто спроси как результат процедуры"
4. Израильский стартап — КОНКРЕТНАЯ история: название, основатель, что сделали, сколько подняли, что необычного. Малоизвестный лучше.
5. Бизнес-юмор или ирония (2-3 предложения)
6. Мини-поддержка — одно тёплое предложение"""

EVENING_PROMPT = BASE_PROMPT + """

ВЕЧЕР (21:00) — РЕФЛЕКСИЯ
Тон: мудрый наставник. Спокойный, глубокий, не занудный.

Структура:
1. Спокойное начало
2. ИСТОРИЯ ПРЕОДОЛЕНИЯ — подробная (10-15 предложений). Кто, когда, что случилось, как упал, что сделал, чем закончилось. С конкретными цифрами, датами, именами. Малоизвестная история лучше чем Стив Джобс или Илон Маск.
3. Урок из этой истории — как это применимо к предпринимателю
4. Факт дня — один удивительный, которого не было утром и днём
5. Вопрос для рефлексии — КОНКРЕТНЫЙ. "Какой один звонок завтра может изменить следующий месяц в iStudio?" или "Если бы у тебя остался только один рекламный канал — какой бы выбрал и почему?"
6. Тёплый финал — по-мужски, с уважением"""

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
COACH_PROMPT = """Ты — мотивационный коуч Михаила Соломоновича (предприниматель, Израиль, клиника красоты iStudio, проект GlowNow).
Коротко (3-7 предложений). Конкретно. НЕ используй звёздочки, подчёркивания или Markdown — ТОЛЬКО чистый текст и эмодзи. Тон зависит от времени суток.
Обращайся: Соломонович или Михаил Соломонович."""

@bot.message_handler(func=lambda m: m.chat.id == MY_CHAT_ID)
def handle_text(message):
    user_text = message.text.strip()
    hour = get_israel_now().hour
    time_ctx = "утро" if hour < 12 else "день" if hour < 18 else "вечер"
    prompt = f"Сейчас {time_ctx} ({get_israel_now().strftime('%H:%M')}). Соломонович: «{user_text}»"
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
