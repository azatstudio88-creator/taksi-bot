import telebot
from telebot import types
import sqlite3

# Ҳайдовчилар боти токени
DRIVER_BOT_TOKEN = "8840191609:AAGPVc20CYJF4Nw7gHDzc0lGunrsD9WMeW0"
bot = telebot.TeleBot(DRIVER_BOT_TOKEN)

# Сизнинг тўлов картангиз ва бонус миқдори
ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000  # Янги ҳайдовчига бериладиган старт бонуси (30 000 сўм)

# Ҳар бир йўналишнинг ҳайдовчилар гуруҳига кириш линклари (Invite Links)
ROUTE_GROUPS = {
    "Қоңырат — Нөкис": "https://t.me/+qo'ng'irot_nukus_link",
    "Қоңырат — Ақшолақ": "https://t.me/+aksholaq_link",
    "Қоңырат — Сода завод": "https://t.me/+sodazavod_link",
    "Қоңырат — Мойнақ": "https://t.me/+moynaq_link",
    "Қоңырат — Шоманай": "https://t.me/+shomanay_link",
    "Қоңырат — Қанлыкөл": "https://t.me/+qanlikol_link",
    "Нөкис — Шоманай": "https://t.me/+nukus_shomanay_link",
    "Нөкис — Қанлыкөл": "https://t.me/+nukus_qanlikol_link"
}

# ----------------- БАЗАНИ СОЗЛАШ (SQLite) -----------------
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

# ----------------- ТУГМАЛАР (МЕНЮ) -----------------
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Балансым", "📥 Балансты толтырыў")
    markup.row("👤 Профилим", "ℹ️ Қолланба")
    return markup

def get_routes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("Қоңырат — Нөкис", "Қоңырат — Ақшолақ")
    markup.row("Қоңырат — Сода завод", "Қоңырат — Мойнақ")
    markup.row("Қоңырат — Шоманай", "Қоңырат — Қанлыкөл")
    markup.row("Нөкис — Шоманай", "Нөкис — Қанлыкөл")
    return markup

# ----------------- РЎЙХАТДАН ЎТИШ ЖАРАЁНИ -----------------
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
            f"🎁 <b>Сизге басланыўына {WELCOME_BONUS:,} сўм старт бонуси бериледи! (15 буйыртпа бийпул)</b>\n\n"
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
        "📞 Телефон номериңизди төмендеги батырма арқалы жибериң яки қолдан жазың:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    user_id = message.chat.id
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text

    driver_temp[user_id]['phone'] = phone

    bot.send_message(
        user_id,
        "🚘 Автомобилиңиздиң маркасы, түси ҳәм мәмлекетлик номерин жазың:\n(Мысалы: <i>Ақ Cobalt 95 A 123 AA</i>)",
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

    # Базага ҳайдовчини ёзиш ва 30 000 сўм бонус бериш
    add_driver(user_id, name, phone, car, route)

    # Йўналиш гуруҳи линки
    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Буйыртпалар топарына қосылыў", url=group_link)
    inline_markup.add(btn_group)

    bot.send_message(
        user_id,
        "🎉 <b>Сиз табыслы дизимнен өттиңиз!</b>\n\n"
        f"🛣 <b>Бағдарыңыз:</b> {route}\n"
        f"🎁 Балансыңызға <b>{WELCOME_BONUS:,} сўм</b> старт бонуси қосылды!\n\n"
        f"👇 Төмендеги батырманы басып, <b>«{route}»</b> бағдарының буйыртпалар топарына қосылың:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

    bot.send_message(
        user_id,
        "Жумысты баслаўыңыз мүмкин. Балансыңызды қадағалаў ушын менюден пайдаланың:",
        reply_markup=get_main_menu()
    )

# ----------------- БАЛАНС ҲӘМ МЕНЮ -----------------
@bot.message_handler(func=lambda m: m.text == "💰 Балансым")
def show_balance(message):
    user_id = message.chat.id
    driver = get_driver(user_id)

    if not driver:
        start_cmd(message)
        return

    balance = driver[5]
    bot.send_message(
        user_id,
        f"💳 <b>Сиздиң балансыңыз:</b> {balance:,} сўм\n\n"
        f"ℹ️ Ҳәр бир қабыл етилген буйыртпа ушын баланстан 2 000 сўм алынады.",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "📥 Балансты толтырыў")
def top_up_balance(message):
    user_id = message.chat.id
    bot.send_message(
        user_id,
        f"💳 <b>Балансты толтырыў ушын:</b>\n\n"
        f"1. Төмендеги картаға Click яки Payme арқалы төлем қылың:\n"
        f"<code>{ADMIN_CARD}</code>\n\n"
        f"2. Төлем еткен соң, чектиң расмин (скриншотын) усы жерге жибериң.\n\n"
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
        f"🚘 <b>Машина:</b> {driver[3]}\n"
        f"🛣 <b>Бағдары:</b> {route}\n"
        f"💰 <b>Баланс:</b> {driver[5]:,} сўм",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

@bot.message_handler(func=lambda m: m.text == "ℹ️ Қолланба")
def show_rules(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ <b>Ҳайдавшылар ушын қағыйдалар:</b>\n\n"
        "1. Буйыртпа топарға түскенде «Буйыртпаны алыў» батырмасын басың.\n"
        "2. Клиент пенен тез арада байланысып, баратуғын ўақтыңызды айтың.\n"
        "3. Балансыңызда кем дегенде 2 000 сўм болыўы шәрт.",
        parse_mode="HTML"
    )

if __name__ == '__main__':
    print("Ҳайдавшылар боты 30 000 сўм бонус пенен иске түсти...")
    bot.infinity_polling()
