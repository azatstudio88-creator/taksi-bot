import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# ==============================================================================
# 1. WEB SERVER ДЛЯ RENDER (Health Check)
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Driver Bot is running!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ==============================================================================
# 2. НАСТРОЙКИ И ТОКЕНЫ БОТОВ
# ==============================================================================
DRIVER_BOT_TOKEN = os.environ.get("DRIVER_BOT_TOKEN")
TAXI_BOT_TOKEN = os.environ.get("TAXI_BOT_TOKEN")

driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot = telebot.TeleBot(TAXI_BOT_TOKEN)

# Закрытый канал для анкет водителей
ADMIN_CHANNEL_ID = -1004484123000
DRIVER_BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

# Временные хранилища состояний
driver_registration_data = {}
orders_data = {}

# ==============================================================================
# 3. БАЗА ДАННЫХ
# ==============================================================================
def init_db():
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            car_model TEXT,
            car_number TEXT,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_driver(user_id):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drivers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def register_driver_in_db(user_id, full_name, phone, car_model, car_number):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO drivers (user_id, full_name, phone, car_model, car_number, balance, status)
        VALUES (?, ?, ?, ?, ?, ?, 'approved')
    ''', (user_id, full_name, phone, car_model, car_number, WELCOME_BONUS))
    conn.commit()
    conn.close()

# ==============================================================================
# 4. ЛОГИКА DRIVER BOT (БОТ ДЛЯ ВОДИТЕЛЕЙ)
# ==============================================================================
def get_driver_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_profile = types.KeyboardButton("👤 Профилим")
    btn_rules = types.KeyboardButton("ℹ️ Қолланба")
    markup.add(btn_profile, btn_rules)
    return markup

@driver_bot.message_handler(commands=['start'])
def driver_start(message):
    driver = get_driver(message.chat.id)
    if driver and driver[6] == 'approved':
        driver_bot.send_message(
            message.chat.id,
            f"Ассалаўма әлейкум, <b>{driver[1]}</b>!\nСиз дизимнен өткенсиз.",
            parse_mode="HTML",
            reply_markup=get_driver_main_keyboard()
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Дизимнен өтиў", callback_data="register_driver"))
        driver_bot.send_message(
            message.chat.id,
            "Ассалаўма әлейкум! Ҳайдавшы болып ислеў ушын дизимнен өтиң:",
            reply_markup=markup
        )

@driver_bot.callback_query_handler(func=lambda call: call.data == "register_driver")
def start_driver_reg(call):
    driver_bot.send_message(call.message.chat.id, "Толық аты-фамилияңызды киргизиң:")
    driver_bot.register_next_step_handler(call.message, process_driver_name)

def process_driver_name(message):
    driver_registration_data[message.chat.id] = {'full_name': message.text}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Телефон номеримди жибериў", request_contact=True))
    driver_bot.send_message(message.chat.id, "Телефон номериңизди жибериң:", reply_markup=markup)
    driver_bot.register_next_step_handler(message, process_driver_phone)

def process_driver_phone(message):
    phone = message.contact.phone_number if message.contact else message.text
    driver_registration_data[message.chat.id]['phone'] = phone
    driver_bot.send_message(message.chat.id, "Машина маркасы ҳәм моделин киргизиң (мәселен: Cobalt, Nexia 3):", reply_markup=types.ReplyKeyboardRemove())
    driver_bot.register_next_step_handler(message, process_car_model)

def process_car_model(message):
    driver_registration_data[message.chat.id]['car_model'] = message.text
    driver_bot.send_message(message.chat.id, "Машина мәмлекетлик номерин киргизиң (мәселен: 95 A 777 AA):")
    driver_bot.register_next_step_handler(message, process_car_number)

def process_car_number(message):
    chat_id = message.chat.id
    driver_registration_data[chat_id]['car_number'] = message.text
    data = driver_registration_data[chat_id]

    register_driver_in_db(
        chat_id,
        data['full_name'],
        data['phone'],
        data['car_model'],
        data['car_number']
    )

    driver_bot.send_message(
        chat_id,
        f"🎉 <b>Қутлықлаймыз! Сиз дизимнен табыслы өттиңиз!</b>\n\n"
        f"🎁 Сизге <b>{WELCOME_BONUS} сўм</b> бонус берилди!\n"
        f"Енди буйыртпаларды қабыл қылыўыңыз мүмкин.",
        parse_mode="HTML",
        reply_markup=get_driver_main_keyboard()
    )

@driver_bot.message_handler(func=lambda m: m.text == "👤 Профилим")
def driver_profile(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        driver_start(message)
        return

    text = (
        f"👤 <b>Ҳайдавшы профили</b>\n\n"
        f"👤 <b>Аты:</b> {driver[1]}\n"
        f"📞 <b>Тел:</b> {driver[2]}\n"
        f"🚘 <b>Машина:</b> {driver[3]} ({driver[4]})\n"
        f"💰 <b>Баланс:</b> {driver[5]} сўм"
    )
    driver_bot.send_message(user_id, text, parse_mode="HTML")

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
# 5. ОБРАБОТКА ДЕЙСТВИЙ И ЗАКАЗОВ (TAXI BOT)
# ==============================================================================
def get_client_restart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚕 Такси шақырыў"))
    return markup

@taxi_bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def handle_accept_order(call):
    try:
        order_id = call.data.split("_")[1]
        driver_user_id = call.from_user.id

        driver = get_driver(driver_user_id)
        if not driver:
            driver_bot.answer_callback_query(
                call.id,
                "Буйыртпаны тек дизимнен өткен ҳайдавшылар алыўы мүмкин!",
                show_alert=True
            )
            return

        order = orders_data.get(order_id)
        if not order:
            driver_bot.answer_callback_query(call.id, "Бул буйыртпа алдын алынған ямаса бийкар етилген!", show_alert=True)
            return

        full_name = driver[1]
        driver_phone = driver[2]

        client_id = order.get('client_id')
        if client_id:
            try:
                taxi_bot.send_message(
                    client_id,
                    f"🎉 <b>Буйыртпаңыз қабылланды!</b>\n\n"
                    f"🚖 <b>Ҳайдавшы:</b> {full_name}\n"
                    f"📞 <b>Телефон:</b> <code>{driver_phone}</code>\n\n"
                    f"Ҳайдавшы тез арада сизге қоңыраў қылады. Жолға таярланып турың!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        del orders_data[order_id]

    except Exception as e:
        taxi_bot.answer_callback_query(call.id, f"Қәтелик жүз берди: {str(e)}", show_alert=True)

# ==============================================================================
# 6. ТОЧКА ВХОДА (ТОЛЬКО ДЛЯ DRIVER BOT)
# ==============================================================================
if __name__ == '__main__':
    print("Driver bot ishga tushdi...")
    driver_bot.infinity_polling(skip_pending=True)
