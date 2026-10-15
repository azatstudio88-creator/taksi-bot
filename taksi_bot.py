import os
import sqlite3
import threading
import uuid
import telebot
from telebot import types
from flask import Flask

# ==============================================================================
# 1. RENDER УЧУН ВЕБ-СЕРВЕР (УХЛАБ ҚОЛМАСЛИГИ УЧУН)
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Taxi & Driver botlari 24/7 faol ishlamoqda!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ==============================================================================
# 2. БОТЛАРНИНГ ТОКЕНЛАРИ ВА СОЗЛАМАЛАРИ
# ==============================================================================
DRIVER_BOT_TOKEN = "8840191609:AAGPVc20CYJF4Nw7gHDzc0lGunrsD9WMeW0"
TAXI_BOT_TOKEN   = "8820304382:AAHL7I8ow2LpNsMmURXoW7ZN6SmpazPYplM"

driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot   = telebot.TeleBot(TAXI_BOT_TOKEN)

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

# Гуруҳлар ID рақамлари (Мижоз боти буюртма юбориши учун)
GROUP_NUKUS     = -1004325420878
GROUP_SHOMANAY  = -1004319753073  # Шоманай — Қоңырат
GROUP_QANLIKOL  = -1004316722887  # Қанлыкөл — Қоңырат
GROUP_AKSHOLAQ  = -1004481922507  # Ақшолақ — Қоңырат
GROUP_SODAZAVOD = -1003771047184  # Сода завод
GROUP_MOYNAQ    = -1003980363859  # Мойнақ

# Ҳайдовчиларни гуруҳга қўшиш ҳаволалари (Driver bot учун)
ROUTE_GROUPS = {
    "Қоңырат — Нөкис": "https://t.me/+jEYRM45p2M82OWQy",
    "Қоңырат — Мойнақ": "https://t.me/+-pDjIZzOC2NkMGMy",
    "Қоңырат — Ақшолақ": "https://t.me/+xKjc0c9HYntkNWMy",
    "Нөкис — Қанлыкөл": "https://t.me/+MXN83qQK3iI5YTcy",
    "Нөкис — Шоманай": "https://t.me/+YT-tKRsz1784MDk6",
    "Қоңырат — Қанлыкөл": "https://t.me/+G5dEw-gVzD8wYzcy",
    "Қоңырат — Шоманай": "https://t.me/+3LsQ5w8Y9WQ2OWZi",
    "Қоңырат — Сода завод": "https://t.me/+BHwD6b2cdsllZTNi"
}

# Комиссия тарифлари (сўмда)
COMMISSION_RATES = {
    "Қоңырат — Нөкис": 4000,
    "Нөкис — Қоңырат": 4000,
    "Қоңырат — Мойнақ": 3000,
    "Мойнақ — Қоңырат": 3000,
    "Қоңырат — Ақшолақ": 3000,
    "Ақшолақ — Қоңырат": 3000,
    "Нөкис — Қанлыкөл": 3000,
    "Қанлыкөл — Нөкис": 3000,
    "Нөкис — Шоманай": 3000,
    "Шоманай — Нөкис": 3000,
    "Қоңырат — Қанлыкөл": 2000,
    "Қанлыкөл — Қоңырат": 2000,
    "Қоңырат — Шоманай": 2000,
    "Шоманай — Қоңырат": 2000,
    "Қоңырат — Сода завод": 2000,
    "Сода завод — Қоңырат": 2000
}

VIDEO_FILE_ID = ""

# Вақтинча маълумотлар хотираси
driver_temp = {}
client_temp = {}
orders_data = {}

# ==============================================================================
# 3. МАЪЛУМОТЛАР БАЗАСИ (SQLITE3)
# ==============================================================================
def init_db():
    conn = sqlite3.connect("drivers.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            car_info TEXT,
            route TEXT,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active'
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_driver(user_id):
    conn = sqlite3.connect("drivers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, phone, car_info, route, balance FROM drivers WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def add_driver(user_id, full_name, phone, car_info, route):
    conn = sqlite3.connect("drivers.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO drivers (user_id, full_name, phone, car_info, route, balance)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, full_name, phone, car_info, route, WELCOME_BONUS))
    conn.commit()
    conn.close()

# ==============================================================================
# 4. ҲАЙДОВЧИЛАР БОТИ (DRIVER BOT)
# ==============================================================================
def get_driver_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Балансым", "📥 Балансты толтырыў")
    markup.row("👤 Профилим", "ℹ️ Қолланба")
    return markup

def get_routes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("Қоңырат — Нөкис", "Қоңырат — Мойнақ")
    markup.row("Қоңырат — Ақшолақ", "Нөкис — Қанлыкөл")
    markup.row("Нөкис — Шоманай", "Қоңырат — Қанлыкөл")
    markup.row("Қоңырат — Шоманай", "Қоңырат — Сода завод")
    return markup

@driver_bot.message_handler(commands=['start'])
def driver_start(message):
    user_id = message.chat.id
    driver = get_driver(user_id)

    if driver:
        driver_bot.send_message(
            user_id,
            f"Ассалаўма алейкум, <b>{driver[1]}</b>! 🚕\nҲайдавшылар кабинетине хош келипсиз.",
            parse_mode="HTML",
            reply_markup=get_driver_menu()
        )
    else:
        driver_bot.send_message(
            user_id,
            "👋 <b>Region 95 Taxi ҳайдавшылар ботына хош келипсиз!</b>\n\n"
            "Жумысты баслаў ушын дизимнен өтиўиңиз керек.\n"
            f"🎁 <b>Сизге басланыўына {WELCOME_BONUS:,} сўм старт бонуси бериледи!</b>\n\n"
            "Аты-фамилияңызды жазып жибериң:",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        driver_bot.register_next_step_handler(message, driver_step_name)

def driver_step_name(message):
    user_id = message.chat.id
    driver_temp[user_id] = {'name': message.text}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)

    driver_bot.send_message(
        user_id,
        "📞 Телефон номериңизди батырма арқалы жибериң яки қолдан жазың:",
        reply_markup=markup
    )
    driver_bot.register_next_step_handler(message, driver_step_phone)

def driver_step_phone(message):
    user_id = message.chat.id
    phone = message.contact.phone_number if message.contact else message.text
    driver_temp[user_id]['phone'] = phone

    driver_bot.send_message(
        user_id,
        "🚘 Автомобилиңиздиң маркасы, түси ҳәм номерин жазың:\n(Мысалы: <i>Ақ Cobalt 95 A 123 AA</i>)",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    driver_bot.register_next_step_handler(message, driver_step_car)

def driver_step_car(message):
    user_id = message.chat.id
    driver_temp[user_id]['car'] = message.text

    driver_bot.send_message(
        user_id,
        "🛣 <b>Тийкарғы қатнайтуғын бағдарыңызды сайлаң:</b>",
        parse_mode="HTML",
        reply_markup=get_routes_keyboard()
    )
    driver_bot.register_next_step_handler(message, driver_step_route)

def driver_step_route(message):
    user_id = message.chat.id
    route = message.text

    name = driver_temp[user_id]['name']
    phone = driver_temp[user_id]['phone']
    car = driver_temp[user_id]['car']

    add_driver(user_id, name, phone, car, route)

    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Буйыртпалар топарына қосылыў", url=group_link)
    inline_markup.add(btn_group)

    driver_bot.send_message(
        user_id,
        "🎉 <b>Сиз табыслы дизимнен өттиңиз!</b>\n\n"
        f"🛣 <b>Бағдарыңыз:</b> {route}\n"
        f"🎁 Балансыңызға <b>{WELCOME_BONUS:,} сўм</b> старт бонуси қосылды!\n\n"
        f"👇 Төмендеги батырма арқалы топарға қосылың:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

    driver_bot.send_message(
        user_id,
        "Жумысты баслаўыңыз мүмкин. Менюден пайдаланың:",
        reply_markup=get_driver_menu()
    )

@driver_bot.message_handler(func=lambda m: m.text == "💰 Балансым")
def driver_balance(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        driver_start(message)
        return
    driver_bot.send_message(user_id, f"💳 <b>Сиздиң балансыңыз:</b> {driver[5]:,} сўм", parse_mode="HTML")

@driver_bot.message_handler(func=lambda m: m.text == "📥 Балансты толтырыў")
def driver_top_up(message):
    user_id = message.chat.id
    driver_bot.send_message(
        user_id,
        f"💳 <b>Балансты толтырыў ушын:</b>\n\n"
        f"1. Төмендеги картаға төлем қылың:\n"
        f"<code>{ADMIN_CARD}</code>\n\n"
        f"2. Төлем чегин усы жерге жибериң.\n\n"
        f"Диспетчер тексерип, балансыңызды көтерип береди!",
        parse_mode="HTML"
    )

@driver_bot.message_handler(func=lambda m: m.text == "👤 Профилим")
def driver_profile(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        driver_start(message)
        return

    route = driver[4]
    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Мениң топарым", url=group_link)
    inline_markup.add(btn_group)

    driver_bot.send_message(
        user_id,
        f"👤 <b>Ҳайдавшы профили:</b>\n\n"
        f"👤 <b>Аты:</b> {driver[1]}\n"
        f"📞 <b>Телефон:</b> {driver[2]}\n"
        f"🚘 <b>Машина:</b> {driver[3]}\n"
        f"🛣 <b>Бағдары:</b> {route}\n"
        f"💰 <b>Баланс:</b> {driver[5]:,} сўм",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

@driver_bot.message_handler(func=lambda m: m.text == "ℹ️ Қолланба")
def driver_rules(message):
    driver_bot.send_message(
        message.chat.id,
        "ℹ️ <b>Қағыйдалар:</b>\n\n"
        "1. Буйыртпа топарға түскенде «Буйыртпаны алыў» батырмасын басың.\n"
        "2. Клиент пенен тез арада байланысып, барыў ўақтын айтың.\n"
        "3. Балансыңызда буйыртпа алыў ушын жетерли қаржы болыўы шәрт.",
        parse_mode="HTML"
    )

# ==============================================================================
# 5. МИЖОЗЛАР БОТИ (TAXI BOT)
# ==============================================================================
def get_restart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔄 Басынан баслаў")
    return markup

def get_locations_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Қоңырат", "Нөкис")
    markup.row("Қанлыкөл", "Шоманай")
    markup.row("Ақшолақ", "Мойнақ")
    markup.row("Сода завод")
    markup.row("📹 Қолланба", "🔄 Басынан баслаў")
    return markup

def get_time_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Ҳәзирге")
    markup.row("09:00", "12:00", "18:00")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_people_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 адам", "2 адам")
    markup.row("3 адам", "4 адам (салон)")
    markup.row("📦 Почта")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_extra_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👶 Жас балам бар", "🧳 Сумка бар")
    markup.row("❌ Ҳеш нәрсе жоқ")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_order_inline_keyboard(order_id):
    markup = types.InlineKeyboardMarkup()
    btn_take = types.InlineKeyboardButton("🚖 Буйрықты алыў", callback_data=f"take_{order_id}")
    markup.add(btn_take)
    return markup

@taxi_bot.message_handler(func=lambda m: m.text in ["🔄 Басынан баслаў", "Басынан баслаў", "🔄 Бошқатдан бошлаш", "/start"])
def client_welcome(message):
    user_id = message.chat.id
    taxi_bot.clear_step_handler_by_chat_id(user_id)
    client_temp[user_id] = {}

    taxi_bot.send_message(
        user_id,
        "📍 <b>1. Қайсы мәнзилден жолға шығасыз?</b>\n(Боттан пайдаланыўды көриў ушын <b>«📹 Қолланба»</b> тугмесин басың)",
        parse_mode="HTML",
        reply_markup=get_locations_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_qayerdan)

@taxi_bot.message_handler(func=lambda m: m.text in ["📹 Қолланба", "Қолланба"])
def client_instruction(message):
    user_id = message.chat.id
    taxi_bot.clear_step_handler_by_chat_id(user_id)

    caption_text = (
        "📹 <b>Боттан пайдаланыў қолланбасы:</b>\n\n"
        "1. Жолға шығатуғын ҳәм баратуғын мәнзилди сайлаң.\n"
        "2. Жолға шығыў ўақтын таңлаң.\n"
        "3. Адам санын яки жүк/почтаны көрсетиң.\n"
        "4. Қосымша бала яки сумка барын сайлаң.\n"
        "5. Телефон номериңизди ҳәм мәнзил локациясын жибериң.\n\n"
        "Буйыртпа бергеннен соң, такси сизге тез арада қоңыраў қылады!"
    )
    taxi_bot.send_message(
        user_id,
        caption_text,
        parse_mode="HTML",
        reply_markup=get_locations_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_qayerdan)

def client_step_qayerdan(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
