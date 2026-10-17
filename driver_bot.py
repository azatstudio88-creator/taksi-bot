import os
import sqlite3
import threading
import uuid
import telebot
from telebot import types
from flask import Flask

# ==============================================================================
# 1. ВЕБ-СЕРВЕР ДЛЯ РАБОТЫ НА RENDER
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Taksi va Driver botlari muvaffaqiyatli ishlamoqda!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ==============================================================================
# 2. НАСТРОЙКИ И ТОКЕНЫ БОТОВ
# ==============================================================================
DRIVER_BOT_TOKEN = os.environ.get("DRIVER_BOT_TOKEN", "8840191609:AAGPVc20CYJF4Nw7gHDzc0lGunrsD9WMeW0")
TAXI_BOT_TOKEN   = os.environ.get("TAXI_BOT_TOKEN", "8820304382:AAHL7I8ow2LpNsMmURXoW7ZN6SmpazPYplM")

driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot   = telebot.TeleBot(TAXI_BOT_TOKEN)

# Закрытый канал для анкет водителей
ADMIN_CHANNEL_ID = -1004484123000
DRIVER_BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

# ID групп для отправки клиентских заказов
GROUP_NUKUS     = -1004325420878
GROUP_SHOMANAY  = -1004319753073  # Шоманай — Қоңырат
GROUP_QANLIKOL  = -1004316722887  # Қанлыкөл — Қоңырат
GROUP_AKSHOLAQ  = -1004481922507  # Ақшолақ — Қоңырат
GROUP_SODAZAVOD = -1003771047184  # Сода завод
GROUP_MOYNAQ    = -1003980363859  # Мойнақ

# Ссылки на группы по направлениям
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

# Тарифы комиссии
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

# Временное хранилище состояний в памяти
driver_temp = {}
client_temp = {}
orders_data = {}

# ==============================================================================
# 3. БАЗА ДАННЫХ SQLITE3
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
# 4. БОТ ДЛЯ ВОДИТЕЛЕЙ (DRIVER BOT)
# ==============================================================================
def get_driver_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Балансым", "📥 Балансты толтырыў")
    markup.row("👤 Профилим", "ℹ️ Қолланба")
    markup.row("📤 Ботты ҳайдавшыларға усыныў")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_routes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("Қоңырат — Нөкис", "Қоңырат — Мойнақ")
    markup.row("Қоңырат — Ақшолақ", "Нөкис — Қанлыкөл")
    markup.row("Нөкис — Шоманай", "Қоңырат — Қанлыкөл")
    markup.row("Қоңырат — Шоманай", "Қоңырат — Сода завод")
    markup.row("🔄 Басынан баслаў")
    return markup

@driver_bot.message_handler(commands=['start'])
@driver_bot.message_handler(func=lambda m: m.text == "🔄 Басынан баслаў")
def driver_start(message):
    user_id = message.chat.id
    driver_bot.clear_step_handler_by_chat_id(user_id)
    driver_temp[user_id] = {}

    driver = get_driver(user_id)
    if driver and message.text != "🔄 Басынан баслаў":
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
            "👤 <b>Аты-фамилияңызды жазып жибериң:</b>",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        driver_bot.register_next_step_handler(message, driver_step_name)

def driver_step_name(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    driver_temp[user_id]['name'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)
    markup.row("🔄 Басынан баслаў")

    driver_bot.send_message(
        user_id,
        "📞 Телефон номериңизди батырма арқалы жибериң яки қолдан жазың:",
        reply_markup=markup
    )
    driver_bot.register_next_step_handler(message, driver_step_phone)

def driver_step_phone(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    phone = message.contact.phone_number if message.contact else message.text
    driver_temp[user_id]['phone'] = phone

    restart_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    restart_markup.row("🔄 Басынан баслаў")

    driver_bot.send_message(
        user_id,
        "📄 <b>ТехПаспорт фотосын жибериң:</b>",
        parse_mode="HTML",
        reply_markup=restart_markup
    )
    driver_bot.register_next_step_handler(message, driver_step_techpasport)

def driver_step_techpasport(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    if not message.photo:
        driver_bot.send_message(user_id, "⚠️ Илтимас, ТехПаспорттың фото сүўретин жибериң:")
        driver_bot.register_next_step_handler(message, driver_step_techpasport)
        return

    driver_temp[user_id]['tech_photo'] = message.photo[-1].file_id

    driver_bot.send_message(
        user_id,
        "🪪 <b>Паспорт (яки ID карта) фотосын жибериң:</b>",
        parse_mode="HTML"
    )
    driver_bot.register_next_step_handler(message, driver_step_passport)

def driver_step_passport(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    if not message.photo:
        driver_bot.send_message(user_id, "⚠️ Илтимас, Паспорттың фото сүўретин жибериң:")
        driver_bot.register_next_step_handler(message, driver_step_passport)
        return

    driver_temp[user_id]['pass_photo'] = message.photo[-1].file_id

    driver_bot.send_message(
        user_id,
        "🚘 <b>Автомобилиңиздиң (алдынан яки капталынан) фотосын жибериң:</b>",
        parse_mode="HTML"
    )
    driver_bot.register_next_step_handler(message, driver_step_car_photo)

def driver_step_car_photo(message):
    user_id = message.chat.id
    
