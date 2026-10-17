import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# ==============================================================================
# 1. RENDER УЧУН ВЕБ-СЕРВЕР (Health Check)
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
# 2. СОЗЛАМАЛАР ВА ЛИНКЛАР
# ==============================================================================
DRIVER_BOT_TOKEN = os.environ.get("DRIVER_BOT_TOKEN")
TAXI_BOT_TOKEN = os.environ.get("TAXI_BOT_TOKEN")

driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot = telebot.TeleBot(TAXI_BOT_TOKEN)

# Анкеталар ва фотолар борадиган ёпиқ админ каналингиз ID рақами
ADMIN_CHANNEL_ID = -1004484123000

# Шу ботнинг юзернейми (бошқа шофёрларга тарқатиш учун)
DRIVER_BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"

# Йўналишлар бўйича гуруҳларингизнинг линклари (ўзингизнинг группа линкларингизни ёзинг):
ROUTE_GROUPS = {
    "qonirat_nukus": {
        "title": "Қоңырат - Нөкис",
        "link": "https://t.me/+QoniratNukusGroupLink"
    },
    "qonirat_shomanay": {
        "title": "Қоңырат - Шоманай",
        "link": "https://t.me/+QoniratShomanayGroupLink"
    }
}

WELCOME_BONUS = 30000

driver_registration_data = {}
orders_data = {}

# ==============================================================================
# 3. МАЪЛУМОТЛАР БАЗАСИ (SQLite)
# ==============================================================================
def init_db():
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            route_key TEXT,
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

def save_pending_driver(user_id, full_name, phone, route_key, car_model, car_number):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO drivers (user_id, full_name, phone, route_key, car_model, car_number, balance, status)
        VALUES (?, ?, ?, ?, ?, ?, 0, 'pending')
    ''', (user_id, full_name, phone, route_key, car_model, car_number))
    conn.commit()
    conn.close()

def approve_driver_in_db(user_id):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE drivers 
        SET status = 'approved', balance = balance + ? 
        WHERE user_id = ?
    ''', (WELCOME_BONUS, user_id))
    conn.commit()
    conn.close()

def reject_driver_in_db(user_id):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE drivers SET status = 'rejected' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ==============================================================================
# 4. ҲАЙДОВЧИНИ РЎЙХАТДАН ЎТКАЗИШ (САВОЛЛАР)
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
    if driver and driver[7] == 'approved':
        driver_bot.send_message(
            message.chat.id,
            f"Ассалаўма әлейкум, <b>{driver[1]}</b>!\nСиз тастыйықланған ҳайдавшысыз.",
            parse_mode="HTML",
            reply_markup=get_driver_main_keyboard()
        )
    elif driver and driver[7] == 'pending':
        driver_bot.send_message(
            message.chat.id,
            "⏳ Сизниң арзаңыз ҳәзирде админлер тәрепинен көрип шығылмақта. Илтимас, күтиң."
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
    driver_bot.send_message(call.message.chat.id, "1. Толық аты-фамилияңызды киргизиң:")
    driver_bot.register_next_step_handler(call.message, process_driver_name)

def process_driver_name(message):
    driver_registration_data[message.chat.id] = {'full_name': message.text}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Телефон номеримди жибериў", request_contact=True))
    driver_bot.send_message(message.chat.id, "2. Телефон номериңизди жибериң:", reply_markup=markup)
    driver_bot.register_next_step_handler(message, process_driver_phone)

def process_driver_phone(message):
    phone = message.contact.phone_number if message.contact else message.text
    driver_registration_data[message.chat.id]['phone'] = phone

    # Шофёр қўлда ёзмаслиги учун йўналиш тугмалари
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, data in ROUTE_GROUPS.items():
        markup.add(types.InlineKeyboardButton(f"📍 {data['title']}", callback_data=f"route_{key}"))

    driver_bot.send_message(
        message.chat.id,
        "3. Қайсы жөнелис бойынша қатнайсыз? Төмендеги туймелерден бирин сайлаң:",
        reply_markup=markup
    )

@driver_bot.callback_query_handler(func=lambda call: call.data.startswith("route_"))
def process_driver_route(call):
    route_key = call.data.replace("route_", "")
    driver_registration_data[call.message.chat.id]['route_key'] = route_key

    route_title = ROUTE_GROUPS.get(route_key, {}).get("title", "")
    driver_bot.send_message(
        call.message.chat.id,
        f"Сайланды: <b>{route_title}</b>\n\n4. Машина маркасы ҳәм моделин киргизиң (мәселен: Cobalt, Nexia 3):",
        parse_mode="HTML",
        reply_markup=types.ReplyKeyboardRemove()
    )
    driver_bot.register_next_step_handler(call.message, process_car_model)

def process_car_model(message):
    driver_registration_data[message.chat.id]['car_model'] = message.text
    driver_bot.send_message(message.chat.id, "5. Машина мәмлекетлик номерин киргизиң (мәселен: 95 A 777 AA):")
    driver_bot.register_next_step_handler(message, process_car_number)

def process_car_number(message):
    driver_registration_data[message.chat.id]['car_number'] = message.text
    driver_bot.send_message(message.chat.id, "6. 📸 Машинаңыздың алды-қапталы көринген сүўретин (фотосын) жибериң:")
    driver_bot.register_next_step_handler(message, process_car_photo)

def process_car_photo(message):
    if not message.photo:
        driver_bot.send_message(message.chat.id, "Илтимас, машина сүўретин фото түринде жибериң:")
        driver_bot.register_next_step_handler(message, process_car_photo)
        return

    driver_registration_data[message.chat.id]['car_photo'] = message.photo[-1].file_id
    driver_bot.send_message(message.chat.id, "7. 📸 Техпаспорт сүўретин (фотосын) жибериң:")
    driver_bot.register_next_step_handler(message, process_tech_passport)

def process_tech_passport(message):
    if not message.photo:
        driver_bot.send_message(message.chat.id, "Илтимас, техпаспорт сүўретин фото түринде жибериң:")
        driver_bot.register_next_step_handler(message, process_tech_passport)
        return

    chat_id = message.chat.id
    driver_registration_data[chat_id]['tech_passport'] = message.photo[-1].file_id
    data = driver_registration_data[chat_id]

    # Вақтинчалик (pending) базага сақлаш
    save_pending_driver(
        chat_id,
        data['full_name'],
        data['phone'],
        data['route_key'],
        data['car_model'],
        data['car_number']
    )

    route_name = ROUTE_GROUPS.get(data['route_key'], {}).get("title", "Белгисиз")

    # Сизнинг каналингиз учун тасдиқлаш тугмалари
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Тастыйықлаў", callback_data=f"approve_{chat_id}"),
        types.InlineKeyboardButton("❌ Бийкар етиў", callback_data=f"reject_{chat_id}")
    )

    admin_caption = (
        f"🚕 <b>ЖАҢА ҲАЙДАВШЫ АРЗАСЫ:</b>\n\n"
        f"👤 <b>Аты:</b> {data['full_name']}\n"
        f"📞 <b>Тел:</b> {data['phone']}\n"
        f"📍 <b>Жөнелис:</b> {route_name}\n"
        f"🚘 <b>Машина:</b> {data['car_model']} ({data['car_number']})\n"
        f"🆔 <b>Telegram ID:</b> <code>{chat_id}</code>"
    )

    try:
        # Каналга техпаспортни юбориш
        driver_bot.send_photo(
            ADMIN_CHANNEL_ID,
            data['tech_passport'],
            caption=f"📄 <b>Техпаспорт:</b> {data['full_name']} (ID: {chat_id})",
            parse_mode="HTML"
        )
        # Каналга машина расми, анкетаси ва Тасдиқлаш/Бекор қилиш тугмаларини юбориш
        driver_bot.send_photo(
            ADMIN_CHANNEL_ID,
            data['car_photo'],
            caption=admin_caption,
            parse_mode="HTML",
            reply_markup=admin_markup
        )
    except Exception as e:
        print(f"Каналга юборишда хатолик: {e}")

    # Ҳайдовчига хабар (унга ҳали ҳеч қандай гуруҳ ссылкаси берилмайди)
    driver_bot.send_message(
        chat_id,
        "✅ <b>Мағлыўматларыңыз админге жиберилди!</b>\n\n"
        "Ҳүжжетлериңиз админ тәрепинен тексерилип тастыйықланғаннан соң, топарға кириў силтемеси жибериледи.",
        parse_mode="HTML"
    )

# ==============================================================================
# 5. КАНАЛДАГИ ТАСТИҚЛАШ / БЕКОР ҚИЛИШ (АДМИН ТУГМАЛАРИ)
# ==============================================================================
@driver_bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    action, target_user_id = call.data.split("_")
    target_user_id = int(target_user_id)

    driver = get_driver(target_user_id)
    if not driver:
        driver_bot.answer_callback_query(call.id, "Ҳайдавшы мағлыўматы табылмады!", show_alert=True)
        return

    if action == "approve":
        approve_driver_in_db(target_user_id)
        
        # Каналдаги пост матнини янгилаш
        driver_bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n<b>✅ ТАСТЫЙЫҚЛАНДЫ (ҚАБЫЛ ЕТИЛДИ)</b>",
            parse_mode="HTML"
        )

        route_key = driver[3]
        route_info = ROUTE_GROUPS.get(route_key, {
            "title": "Такси топары",
            "link": "https://t.me/+YourPrivateGroupLink"
        })

        # Бошқа шофёрларга тарқатиш учун шу ботнинг таклиф линки
        share_bot_link = f"https://t.me/{DRIVER_BOT_USERNAME}?start={target_user_id}"

        driver_markup = types.InlineKeyboardMarkup(row_width=1)
        driver_markup.add(
            types.InlineKeyboardButton(f"🚖 «{route_info['title']}» топарына қосылыў", url=route_info['link']),
            types.InlineKeyboardButton("📲 Ботты басқа ҳайдавшыларға тарқатыў", url=f"https://t.me/share/url?url={share_bot_link}&text=Такси%20хызметине%20ҳайдавшы%20болып%20қосылың!")
        )

        # Фақат сиз тасдиқлаганингиздан кейин шофёрга линк ва бонус боради
        driver_bot.send_message(
            target_user_id,
            f"🎉 <b>Қутлықлаймыз! Сизниң арзаңыз тастыйықланды!</b>\n\n"
            f"🎁 Сизге <b>{WELCOME_BONUS} сўм</b> бонус берилди!\n\n"
            f"📍 Сизниң жөнелисиңиз: <b>{route_info['title']}</b>\n\n"
            f"👇 Төмендеги батырма арқалы өз топарыңызға қосылың ҳәм ботты басқа шофёрларға тарқатың:\n"
            f"Бот силтемеси: {share_bot_link}",
            parse_mode="HTML",
            reply_markup=driver_markup
        )

        driver_bot.send_message(
            target_user_id,
            "Сизниң жумыс кабинетиңиз иске түсти:",
            reply_markup=get_driver_main_keyboard()
        )

    else:
        reject_driver_in_db(target_user_id)
        driver_bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n<b>❌ БИЙКАР ЕТИЛДИ</b>",
            parse_mode="HTML"
        )
        driver_bot.send_message(
            target_user_id,
            "Кешириң, сизниң арзаңыз админ тәрепинен қабыл етилмеди."
        )

# ==============================================================================
# 6. ҲАЙДОВЧИ ПРОФИЛИ ВА ҚЎЛЛАНМА
# ==============================================================================
@driver_bot.message_handler(func=lambda m: m.text == "👤 Профилим")
def driver_profile(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        driver_start(message)
        return

    route_title = ROUTE_GROUPS.get(driver[3], {}).get("title", driver[3])

    text = (
        f"👤 <b>Ҳайдавшы профили</b>\n\n"
        f"👤 <b>Аты:</b> {driver[1]}\n"
        f"📞 <b>Тел:</b> {driver[2]}\n"
        f"📍 <b>Жөнелис:</b> {route_title}\n"
        f"🚘 <b>Машина:</b> {driver[4]} ({driver[5]})\n"
        f"💰 <b>Баланс:</b> {driver[6]} сўм"
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
# 7. МИЖОЗ БОТИДАН БУЮРТМА ОЛИШ (TAXI BOT)
# ==============================================================================
@taxi_bot.callback_query_handler(func=lambda call: call.data.startswith("accept_"))
def handle_accept_order(call):
    try:
        order_id = call.data.split("_")[1]
        driver_user_id = call.from_user.id

        driver = get_driver(driver_user_id)
        if not driver or driver[7] != 'approved':
            driver_bot.answer_callback_query(
                call.id,
                "Буйыртпаны тек тастыйықланған ҳайдавшылар алыўы мүмкин!",
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
# 8. ИШГА ТУШИРИШ
# ==============================================================================
if __name__ == '__main__':
    print("Driver bot ishga tushdi...")
    driver_bot.infinity_polling(skip_pending=True)
