import os
import threading
import sqlite3
import telebot
from telebot import types
from flask import Flask

# --- Render учун веб-сервер ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Driver bot faol ishlab turibdi!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()
# ------------------------------

# Токенни хавфсиз олиш (ёки тўғридан-тўғри янги токенни қўйишингиз мумкин)
DRIVER_BOT_TOKEN = os.environ.get("DRIVER_BOT_TOKEN", "8820304382:AAFEgn7Lm3DqnlTpdWiIF1qKQexHiaCNu7c")
bot = telebot.TeleBot(DRIVER_BOT_TOKEN)

# ⚠️ Шахсий каналингизнинг рақамли ID'сини шу ерга қўйинг (Бот каналда админ бўлиши шарт!)
ADMIN_CHANNEL_ID = -1002345678901  # Ўзингизнинг каналингиз ID'сини қўйинг
BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

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

driver_temp = {}

# ----------------- БОТНИ БОШЛАШ -----------------
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda m: m.text == "🔄 Басынан баслаў")
def start_cmd(message):
    user_id = message.chat.id
    bot.clear_step_handler_by_chat_id(user_id)
    driver_temp[user_id] = {}

    driver = get_driver(user_id)
    if driver and message.text != "🔄 Басынан баслаў":
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
            "👤 <b>Аты-фамилияңызды жазып жибериң:</b>",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, step_name)

# 1-қадам: Исм-фамилия
def step_name(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    driver_temp[user_id]['name'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📞 Телефон номериңизди батырма арқалы жибериң яки қолдан жазың:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_phone)

# 2-қадам: Телефон рақам
def step_phone(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    phone = message.contact.phone_number if message.contact else message.text
    driver_temp[user_id]['phone'] = phone

    restart_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    restart_markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📄 <b>ТехПаспорт фотосын жибериң:</b>",
        parse_mode="HTML",
        reply_markup=restart_markup
    )
    bot.register_next_step_handler(message, step_techpasport)

# 3-қадам: ТехПаспорт фотоси
def step_techpasport(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    if not message.photo:
        bot.send_message(user_id, "⚠️ Илтимас, ТехПаспорттың фото сүўретин жибериң:")
        bot.register_next_step_handler(message, step_techpasport)
        return

    driver_temp[user_id]['tech_photo'] = message.photo[-1].file_id

    bot.send_message(
        user_id,
        "🪪 <b>Паспорт (яки ID карта) фотосын жибериң:</b>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, step_passport)

# 4-қадам: Паспорт фотоси
def step_passport(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    if not message.photo:
        bot.send_message(user_id, "⚠️ Илтимас, Паспорттың фото сүўретин жибериң:")
        bot.register_next_step_handler(message, step_passport)
        return

    driver_temp[user_id]['pass_photo'] = message.photo[-1].file_id

    bot.send_message(
        user_id,
        "🚘 <b>Автомобилиңиздиң (алдынан яки капталынан) фотосын жибериң:</b>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(message, step_car_photo)

# 5-қадам: Автомобил фотоси
def step_car_photo(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    if not message.photo:
        bot.send_message(user_id, "⚠️ Илтимас, Автомобильдиң фото сүўретин жибериң:")
        bot.register_next_step_handler(message, step_car_photo)
        return

    driver_temp[user_id]['car_photo'] = message.photo[-1].file_id

    bot.send_message(
        user_id,
        "🛣 <b>Тийкарғы қатнайтуғын бағдарыңызды сайлаң:</b>",
        parse_mode="HTML",
        reply_markup=get_routes_keyboard()
    )
    bot.register_next_step_handler(message, step_route)

# 6-қадам: Йўналишни танлаш ва каналга юбориш
def step_route(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        start_cmd(message)
        return

    route = message.text
    data = driver_temp.get(user_id, {})
    name = data.get('name', '-')
    phone = data.get('phone', '-')
    car_info = "Фото тиркелген"

    # Базага сақлаш
    add_driver(user_id, name, phone, car_info, route)

    # Каналга админлар учун юбориладиган маълумот
    admin_caption = (
        "🆕 <b>ЖАҢА ҲАЙДАВШЫ ДИЗИМНЕН ӨТТИ!</b>\n\n"
        f"👤 <b>Аты-фамилиясы:</b> {name}\n"
        f"📞 <b>Телефоны:</b> <code>{phone}</code>\n"
        f"🛣 <b>Бағдары:</b> {route}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"🔗 <b>Профиль:</b> @{message.from_user.username if message.from_user.username else 'Жоқ'}"
    )

    # Ҳужжатларни каналга фото-альбом шаклида юбориш
    try:
        media = [
            types.InputMediaPhoto(data['tech_photo'], caption=admin_caption, parse_mode="HTML"),
            types.InputMediaPhoto(data['pass_photo']),
            types.InputMediaPhoto(data['car_photo'])
        ]
        bot.send_media_group(ADMIN_CHANNEL_ID, media)
    except Exception as e:
        print(f"Каналга юборишда хатолик: {e}")

    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Буйыртпалар топарына қосылыў", url=group_link)
    inline_markup.add(btn_group)

    bot.send_message(
        user_id,
        "🎉 <b>Сиз табыслы дизимнен өттиңиз!</b>\n\n"
        f"🛣 <b>Бағдарыңыз:</b> {route}\n"
        f"🎁 Балансыңызға <b>{WELCOME_BONUS:,} сўм</b> старт бонуси қосылды!\n\n"
        f"👇 Төмендеги батырма арқалы буйыртпалар топарына қосылың:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

    bot.send_message(
        user_id,
        "Жумысты баслаўыңыз мүмкин. Менюден пайдаланың:",
        reply_markup=get_main_menu()
    )

# ----------------- БОТНИ БОШҚАЛАРГА УЛАШИШ -----------------
@bot.message_handler(func=lambda m: m.text == "📤 Ботты ҳайдавшыларға усыныў")
def share_bot(message):
    share_text = f"🚕 Region 95 Taxi — Ҳайдавшылар ботына қосылың ҳәм 30,000 сўм старт бонусына ийе болың!\n\nБот силтемеси: @{BOT_USERNAME}"
    
    markup = types.InlineKeyboardMarkup()
    btn_share = types.InlineKeyboardButton(
        "📲 Досларға жибериў", 
        url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text={share_text}"
    )
    markup.add(btn_share)

    bot.send_message(
        message.chat.id,
        f"Ҳайдавшы ботын кесиптеслериңизге усыныў ушын төмендеги батырманы басың яки силтемени көширип жибериң:\n\n👉 @{BOT_USERNAME}",
        reply_markup=markup
    )

# ----------------- ҚЎШИМЧА МЕНЮ БЎЛИМЛАРИ -----------------
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
    user_id = message.chat.id
    bot.send_message(
        user_id,
        f"💳 <b>Балансты толтырыў ушын:</b>\n\n"
        f"1. Төмендеги картаға төлем қылың:\n"
        f"<code>{ADMIN_CARD}</code>\n\n"
        f"2. Төлем чегин усы жерге жибериң.\n\n"
        f"Диспетчер тексерип, балансыңызды көтерип береди!",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "👤 Профилим")
def show_profile(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        start_cmd(message)
        return

    route = driver[4]
    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Мениң топарым", url=group_link)
    inline_markup.add(btn_group)

    bot.send_message(
        user_id,
        f"👤 <b>Ҳайдавшы профили:</b>\n\n"
        f"👤 <b>Аты:</b> {driver[1]}\n"
        f"📞 <b>Телефон:</b> {driver[2]}\n"
        f"🛣 <b>Бағдары:</b> {route}\n"
        f"💰 <b>Баланс:</b> {driver[5]:,} сўм",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

@bot.message_handler(func=lambda m: m.text == "ℹ️ Қолланба")
def show_rules(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ <b>Қағыйдалар:</b>\n\n"
        "1. Буйыртпа топарға түскенде «Буйыртпаны алыў» батырмасын басың.\n"
        "2. Клиент пенен тез арада байланысып, барыў ўақтын айтың.\n"
        "3. Балансыңызда буйыртпа алыў ушын жетерли қаржы болыўы шәрт.",
        parse_mode="HTML"
    )

if __name__ == '__main__':
    print("Driver bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
