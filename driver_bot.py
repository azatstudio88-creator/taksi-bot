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
DRIVER_BOT_TOKEN = os.environ.get("DRIVER_BOT_TOKEN")
TAXI_BOT_TOKEN = os.environ.get("TAXI_BOT_TOKEN")


driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot   = telebot.TeleBot(TAXI_BOT_TOKEN)

# Закрытый канал для анкет водителей
ADMIN_CHANNEL_ID = -1004484123000
DRIVER_BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"

ADMIN_CARD = "8600 **** **** **** (Азат)"
WELCOME_BONUS = 30000

# ID групп для отправки клиентских заказов
GROUP_NUKUS     = -1004325420878
GROUP_SHOMANAY  = -1004319753073
GROUP_QANLIKOL  = -1004316722887
GROUP_AKSHOLAQ  = -1004481922507
GROUP_SODAZAVOD = -1003771047184
GROUP_MOYNAQ    = -1003980363859

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
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    if not message.photo:
        driver_bot.send_message(user_id, "⚠️ Илтимас, Автомобильдиң фото сүўретин жибериң:")
        driver_bot.register_next_step_handler(message, driver_step_car_photo)
        return

    driver_temp[user_id]['car_photo'] = message.photo[-1].file_id

    driver_bot.send_message(
        user_id,
        "🛣 <b>Тийкарғы қатнайтуғын бағдарыңызды сайлаң:</b>",
        parse_mode="HTML",
        reply_markup=get_routes_keyboard()
    )
    driver_bot.register_next_step_handler(message, driver_step_route)

def driver_step_route(message):
    user_id = message.chat.id
    if message.text == "🔄 Басынан баслаў":
        driver_start(message)
        return

    route = message.text
    data = driver_temp.get(user_id, {})
    name = data.get('name', '-')
    phone = data.get('phone', '-')
    car_info = "Фото тиркелген"

    # Сохранение в базу
    add_driver(user_id, name, phone, car_info, route)

    # Компактная подпись под фото
    username_text = f"@{message.from_user.username}" if message.from_user.username else "Жоқ"
    admin_caption = (
        "🚖 <b>Жаңа ҳайдавшы</b>\n\n"
        f"👤 <b>Аты:</b> {name}\n"
        f"📞 <b>Тел:</b> <code>{phone}</code>\n"
        f"🛣 <b>Бағдар:</b> {route}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code> | {username_text}"
    )

    # Отправка медиагруппы с точным выводом ошибок при сбое
    try:
        media = [
            types.InputMediaPhoto(data.get('tech_photo'), caption=admin_caption, parse_mode="HTML"),
            types.InputMediaPhoto(data.get('pass_photo')),
            types.InputMediaPhoto(data.get('car_photo'))
        ]
        driver_bot.send_media_group(ADMIN_CHANNEL_ID, media)
    except Exception as e:
        driver_bot.send_message(
            user_id, 
            f"⚠️ <b>Каналға таслаўда қәтелик болды:</b>\n<code>{e}</code>", 
            parse_mode="HTML"
        )

    group_link = ROUTE_GROUPS.get(route, "https://t.me/")

    inline_markup = types.InlineKeyboardMarkup()
    btn_group = types.InlineKeyboardButton("🚕 Буйыртпалар топарына қосылыў", url=group_link)
    inline_markup.add(btn_group)

    driver_bot.send_message(
        user_id,
        "🎉 <b>Сиз табыслы дизимнен өттиңиз!</b>\n\n"
        f"🛣 <b>Бағдарыңыз:</b> {route}\n"
        f"🎁 Балансыңызға <b>{WELCOME_BONUS:,} сўм</b> старт бонуси қосылды!\n\n"
        f"👇 Төмендеги батырма арқалы буйыртпалар топарына қосылың:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

    driver_bot.send_message(
        user_id,
        "Жумысты баслаўыңыз мүмкин. Менюден пайдаланың:",
        reply_markup=get_driver_menu()
    )

@driver_bot.message_handler(func=lambda m: m.text == "📤 Ботты ҳайдавшыларға усыныў")
def driver_share(message):
    share_text = f"🚕 Region 95 Taxi — Ҳайдавшылар ботына қосылың ҳәм 30,000 сўм старт бонусина ийе болың!\n\nБот силтемеси: @{DRIVER_BOT_USERNAME}"
    markup = types.InlineKeyboardMarkup()
    btn_share = types.InlineKeyboardButton(
        "📲 Досларға жибериў", 
        url=f"https://t.me/share/url?url=https://t.me/{DRIVER_BOT_USERNAME}&text={share_text}"
    )
    markup.add(btn_share)

    driver_bot.send_message(
        message.chat.id,
        f"Ҳайдавшы ботын кесиптеслериңизге усыныў ушын төмендеги батырманы басың яки силтемени көширип жибериң:\n\n👉 @{DRIVER_BOT_USERNAME}",
        reply_markup=markup
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

if __name__ == '__main__':
    print("Driver bot ishga tushdi...")
    driver_bot.infinity_polling(skip_pending=True)
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
# 5. БОТ ДЛЯ КЛИЕНТОВ (TAXI BOT)
# ==============================================================================
def get_client_restart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔄 Басынан баслаў")
    return markup

def get_client_locations_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Қоңырат", "Нөкис")
    markup.row("Қанлыкөл", "Шоманай")
    markup.row("Ақшолақ", "Мойнақ")
    markup.row("Сода завод")
    markup.row("📹 Қолланба", "🔄 Басынан баслаў")
    return markup

def get_client_time_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Ҳәзирге")
    markup.row("09:00", "12:00", "18:00")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_client_people_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 адам", "2 адам")
    markup.row("3 адам", "4 адам (салон)")
    markup.row("📦 Почта")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_client_extra_keyboard():
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
        reply_markup=get_client_locations_keyboard()
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
        reply_markup=get_client_locations_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_qayerdan)

def client_step_qayerdan(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return
    elif text in ["📹 Қолланба", "Қолланба"]:
        client_instruction(message)
        return

    client_temp[user_id]['qayerdan'] = text

    taxi_bot.send_message(
        user_id,
        "🏁 <b>2. Қайсы мәнзилге барасыз?</b>",
        parse_mode="HTML",
        reply_markup=get_client_locations_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_qayerga)

def client_step_qayerga(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return
    elif text in ["📹 Қолланба", "Қолланба"]:
        client_instruction(message)
        return

    client_temp[user_id]['qayerga'] = text

    taxi_bot.send_message(
        user_id,
        "⏰ <b>3. Қайсы ўақытта жолға шығасыз?</b>\n(Тугмелерден сайлаң яки басқа ўақыт болса жазып жибериң):",
        parse_mode="HTML",
        reply_markup=get_client_time_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_vaqt)

def client_step_vaqt(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return

    client_temp[user_id]['vaqt'] = text

    taxi_bot.send_message(
        user_id,
        "👥 <b>4. Неше адам яки почта?</b>",
        parse_mode="HTML",
        reply_markup=get_client_people_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_odam)

def client_step_odam(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return

    client_temp[user_id]['odam'] = text

    taxi_bot.send_message(
        user_id,
        "ℹ️ <b>5. Қосымша кимлер? (нелер) бар?</b>",
        parse_mode="HTML",
        reply_markup=get_client_extra_keyboard()
    )
    taxi_bot.register_next_step_handler(message, client_step_extra)

def client_step_extra(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return

    client_temp[user_id]['extra'] = text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)
    markup.row("🔄 Басынан баслаў")

    taxi_bot.send_message(
        user_id,
        "📞 <b>6. Телефон номериңизди жибериң яки жазың:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )
    taxi_bot.register_next_step_handler(message, client_step_phone)

def client_step_phone(message):
    user_id = message.chat.id

    if message.text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return

    if message.contact:
        client_temp[user_id]['phone'] = message.contact.phone_number
    elif message.text:
        client_temp[user_id]['phone'] = message.text
    else:
        client_temp[user_id]['phone'] = "Көрсетилмеген"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_loc = types.KeyboardButton("📍 Локацияны жибериў", request_location=True)
    markup.row(btn_loc)
    markup.row("Керек емес / Тек адрес")
    markup.row("🔄 Басынан баслаў")

    taxi_bot.send_message(
        user_id,
        "📍 <b>7. Мәнзил локациясын жибериң:</b>\n(Егер керек болмаса, «Керек емес» тугмесин басың)",
        parse_mode="HTML",
        reply_markup=markup
    )
    taxi_bot.register_next_step_handler(message, client_step_send_order)

def client_step_send_order(message):
    user_id = message.chat.id

    if message.text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        client_welcome(message)
        return

    location_obj = None
    loc_text = "Жиберилмеди"

    if message.location:
        location_obj = message.location
        loc_text = "📍 Картада жиберилди"
    elif message.text:
        loc_text = message.text

    qayerdan = client_temp[user_id].get('qayerdan', '-')
    qayerga = client_temp[user_id].get('qayerga', '-')
    vaqt = client_temp[user_id].get('vaqt', '-')
    odam = client_temp[user_id].get('odam', '-')
    extra = client_temp[user_id].get('extra', '-')
    phone = client_temp[user_id].get('phone', '-')
    user_name = message.from_user.first_name

    order_id = str(uuid.uuid4())[:8]

    orders_data[order_id] = {
        'client_id': user_id,
        'route': f"{qayerdan} — {qayerga}",
        'client_name': user_name,
        'client_phone': phone,
        'location': loc_text,
        'location_obj': location_obj
    }

    order_text = (
        "🚕 <b>ЖАҢА БУЙЫРТПА!</b>\n\n"
        f"📍 <b>Қайдан:</b> {qayerdan}\n"
        f"🏁 <b>Қайда:</b> {qayerga}\n"
        f"⏰ <b>Ўақты:</b> {vaqt}\n"
        f"👥 <b>Адам/Почта:</b> {odam}\n"
        f"➕ <b>Қосымша:</b> {extra}\n"
        f"📍 <b>Локация:</b> {loc_text}\n"
        f"👤 <b>Клиент:</b> {user_name}\n"
    )

    marshrut = f"{qayerdan} {qayerga}"

    if "Мойнақ" in marshrut:
        target_group = GROUP_MOYNAQ
    elif "Сода завод" in marshrut:
        target_group = GROUP_SODAZAVOD
    elif "Ақшолақ" in marshrut:
        target_group = GROUP_AKSHOLAQ
    elif "Қанлыкөл" in marshrut or "Канлыкол" in marshrut:
        target_group = GROUP_QANLIKOL
    elif "Шоманай" in marshrut:
        target_group = GROUP_SHOMANAY
    else:
        target_group = GROUP_NUKUS

    try:
        taxi_bot.send_message(
            chat_id=target_group,
            text=order_text,
            parse_mode="HTML",
            reply_markup=get_order_inline_keyboard(order_id)
        )

        taxi_bot.send_message(
            user_id,
            "✅ <b>Буйыртпаңыз қабылланды! Сиз бенен тез арада такси байланысады.</b>",
            parse_mode="HTML",
            reply_markup=get_client_restart_keyboard()
        )
    except Exception:
        taxi_bot.send_message(
            user_id,
            "⚠️ Буйыртпаны жибериўде қәтелик жүз берди. Илтимас, қайтадан урынып көрсек болады.",
            reply_markup=get_client_restart_keyboard()
        )

# ----------------- ПРИНЯТИЕ ЗАКАЗА ВОДИТЕЛЕМ -----------------
@taxi_bot.callback_query_handler(func=lambda call: call.data.startswith("take_"))
def process_take_order(call):
    driver_id = call.from_user.id
    order_id = call.data.split("_")[1]

    if order_id not in orders_data:
        taxi_bot.answer_callback_query(call.id, "⚠️ Бул буйыртпа алдын алынған яки актив емес!", show_alert=True)
        return

    order = orders_data[order_id]
    route = order.get('route', '')
    fee = COMMISSION_RATES.get(route, 2000)

    try:
        conn = sqlite3.connect("drivers.db")
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, phone, car_info, balance FROM drivers WHERE user_id = ?", (driver_id,))
        driver = cursor.fetchone()

        if not driver:
            taxi_bot.answer_callback_query(
                call.id, 
                "⚠️ Сиз ҳайдавшылар ботында дизимнен өтпегенсиз! Дәслеп дизимнен өтиң.", 
                show_alert=True
            )
            conn.close()
            return

        full_name, driver_phone, car_info, balance = driver

        if balance < fee:
            taxi_bot.answer_callback_query(
                call.id, 
                f"❌ Балансыңызда қаржы жетпейди!\nБул бағдар ушын: {fee:,} сўм керек.\nБалансыңыз: {balance:,} сўм.", 
                show_alert=True
            )
            conn.close()
            return

        new_balance = balance - fee
        cursor.execute("UPDATE drivers SET balance = ? WHERE user_id = ?", (new_balance, driver_id))
        conn.commit()
        conn.close()

        client_text = (
            f"🚕 <b>Буйыртпа табыслы қабылланды!</b>\n\n"
            f"🛣 <b>Бағдар:</b> {route}\n"
            f"👤 <b>Клиент:</b> {order.get('client_name')}\n"
            f"📞 <b>Телефон:</b> <code>{order.get('client_phone')}</code>\n"
            f"📍 <b>Мәнзил/Локация:</b> {order.get('location')}\n\n"
            f"💵 Балансыңыздан: <b>{fee:,} сўм</b> ешилди.\n"
            f"💰 Қалған балансыңыз: <b>{new_balance:,} сўм</b>"
        )
        
        try:
            taxi_bot.send_message(driver_id, client_text, parse_mode="HTML")
            if order.get('location_obj'):
                loc = order['location_obj']
                taxi_bot.send_location(driver_id, latitude=loc.latitude, longitude=loc.longitude)
        except Exception:
            taxi_bot.answer_callback_query(
                call.id,
                "⚠️ Илтимас, алдын такси ботында /start басың (номерди көриў ушын)!",
                show_alert=True
            )
            return

        taxi_bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{call.message.text}\n\n✅ <b>Буйыртпа алынды!</b>\nҲайдавшы: {full_name}",
            parse_mode="HTML"
        )

        taxi_bot.answer_callback_query(call.id, f"Буйыртпа алынды! Баланстан {fee:,} сўм ешилди.")

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
# 6. ПАРАЛЛЕЛЬНЫЙ ЗАПУСК ОБОИХ БОТОВ
# ==============================================================================
def start_driver_bot():
    print("Driver bot ishga tushdi...")
    driver_bot.infinity_polling(skip_pending=True)

def start_taxi_bot():
    print("Taxi bot ishga tushdi...")
    taxi_bot.infinity_polling(skip_pending=True)

if __name__ == '__main__':
    threading.Thread(target=start_driver_bot, daemon=True).start()
    start_taxi_bot()
