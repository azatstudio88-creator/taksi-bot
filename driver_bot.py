import telebot
from telebot import types
import sqlite3
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Render'да ботни фаол (Live) сақлаб туриш учун веб-сервер ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Driver bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# -------------------------------------------------------------

DRIVER_BOT_TOKEN = "8840191609:AAGPVc20CYJF4Nw7gHDzc0lGunrsD9WMeW0"
bot = telebot.TeleBot(DRIVER_BOT_TOKEN)

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

# Гуруҳларингиз линклари
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

def get_main_menu():
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

driver_temp = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    driver = get_driver(user_id)

    if driver:
        bot.send_message(
            user_id,
            f"Ассалаўма алейкум, <b>{driver[1]}</b>! 🚕\nҲайдавшылар кабинетине хош келипсиз.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    else:
        bot.send_message(
            user_id,
            "👋 <b>Region 95 Taxi ҳайдавшылар ботына хош келипсиз!</b>\n\n"
            "Жумысты баслаў ушын дизимнен өтиўиңиз керек.\n"
            f"🎁 <b>Сизге басланыўына {WELCOME_BONUS:,} сўм старт бонуси бериледи!</b>\n\n"
            "Аты-фамилияңызды жазып жибериң:",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, step_name)

def step_name(message):
    user_id = message.chat.id
    driver_temp[user_id] = {'name': message.text}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)

    bot.send_message(
        user_id,
        "📞 Телефон номериңизди батырма арқалы жибериң яки қолдан жазың:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    user_id = message.chat.id
    phone = message.contact.phone_number if message.contact else message.text
    driver_temp[user_id]['phone'] = phone

    bot.send_message(
        user_id,
        "🚘 Автомобилиңиздиң маркасы, түси ҳәм номерин жазың:\n(Мысалы: <i>Ақ Cobalt 95 A 123 AA</i>)",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message, step_car)

def step_car(message):
    user_id = message.chat.id
    driver_temp[user_id]['car'] = message.text

    bot.send_message(
        user_id,
        "🛣 <b>Тийкарғы қатнайтуғын бағдарыңызды сайлаң:</b>",
        parse_mode="HTML",
        reply_markup=get_routes_keyboard()
    )
    bot.register_next_step_handler(message, step_route)

def step_route(message):
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

    bot.send_message(
        user_id,
        "🎉 <b>Сиз табыслы дизимнен өттиңиз!</b>\n\n"
        f"🛣 <b>Бағдарыңыз:</b> {route}\n"
        f"🎁 Балансыңызға <b>{WELCOME_BONUS:,} сўм</b> старт бонуси қосылды!\n\n"
        f"👇 Төмендеги батырма арқалы топарға қосылың:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

    bot.send_message(
        user_id,
        "Жумысты баслаўыңыз мүмкин. Менюден пайдаланың:",
        reply_markup=get_main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "💰 Балансым")
def show_balance(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        start_cmd(message)
        return
    bot.send_message(user_id, f"💳 <b>Сиздиң балансыңыз:</b> {driver[5]:,} сўм", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📥 Балансты толтырыў")
def top_up_balance(message):
    user_id
