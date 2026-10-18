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
    return "Aydawshylar Bot is running!", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ==============================================================================
# 2. СОЗЛАМАЛАР ВА 8 ТА ЙЎНАЛИШ
# ==============================================================================
# Токенларни пробеллардан тозалаб олиш
DRIVER_BOT_TOKEN = (os.environ.get("DRIVER_BOT_TOKEN") or "").strip()
TAXI_BOT_TOKEN = (os.environ.get("TAXI_BOT_TOKEN") or "").strip()

print(f"--> DRIVER_TOKEN узунлиги: {len(DRIVER_BOT_TOKEN)}")
print(f"--> TAXI_TOKEN узунлиги: {len(TAXI_BOT_TOKEN)}")

driver_bot = telebot.TeleBot(DRIVER_BOT_TOKEN)
taxi_bot = telebot.TeleBot(TAXI_BOT_TOKEN)

# Бот юзернейми ва шапка матни
DRIVER_BOT_USERNAME = "TAXI_REGION95_ADMIN_bot"
HEADER_LINK = f"📲 <b>Басқа айдаўшыларға тарқатыў ушын силтеме:</b> @{DRIVER_BOT_USERNAME}\n" + "—" * 30 + "\n\n"

# БАРЛЫҚ 8 ЖӨНЕЛИС, ГРУППА ИД НОМЕРЛЕРИ ҲӘМ ТАЙЫН СИЛТЕМЕЛЕРИ
# (Егер группада бот админ болмаса, төмендеги invite_link орнына группаңыздың жеке силтемесин қойың)
ROUTE_DATA = {
    "nukus_qonirat": {
        "title": "Нөкис — Қоңырат",
        "group_id": -1004325420878,
        "fee_per_person": 3000,
        "invite_link": "https://t.me/+NukusQoniratGroup"
    },
    "qonirat_shomanay": {
        "title": "Қоңырат — Шоманай",
        "group_id": -1004319753073,
        "fee_per_person": 1500,
        "invite_link": "https://t.me/+QoniratShomanayGroup"
    },
    "qonirat_qanlikol": {
        "title": "Қоңырат — Қанлыкөл",
        "group_id": -1004316722887,
        "fee_per_person": 1000,
        "invite_link": "https://t.me/+QoniratQanlikolGroup"
    },
    "qonirat_aksholaq": {
        "title": "Қоңырат — Ақшолақ",
        "group_id": -1004481922507,
        "fee_per_person": 2000,
        "invite_link": "https://t.me/+QoniratAksholaqGroup"
    },
    "qonirat_sodazavod": {
        "title": "Қоңырат — Сода завод",
        "group_id": -1003771047184,
        "fee_per_person": 1000,
        "invite_link": "https://t.me/+QoniratSodazavodGroup"
    },
    "qonirat_moynaq": {
        "title": "Қоңырат — Мойнақ",
        "group_id": -1003980363859,
        "fee_per_person": 2000,
        "invite_link": "https://t.me/+QoniratMoynaqGroup"
    },
    "nukus_qanlikol": {
        "title": "Нөкис — Қанлыкөл",
        "group_id": -1004223200470,
        "fee_per_person": 2000,
        "invite_link": "https://t.me/+NukusQanlikolGroup"
    },
    "nukus_shomanay": {
        "title": "Нөкис — Шоманай",
        "group_id": -1004450147063,
        "fee_per_person": 2000,
        "invite_link": "https://t.me/+NukusShomanayGroup"
    }
}

WELCOME_BONUS = 30000

driver_registration_data = {}
orders_data = {}

# ==============================================================================
# 3. МАҒЛЫЎМАТЛАР БАЗАСИ (SQLite)
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
            status TEXT DEFAULT 'pending',
            bonus_given INTEGER DEFAULT 0
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
    cursor.execute("SELECT bonus_given FROM drivers WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE drivers 
            SET full_name = ?, phone = ?, route_key = ?, car_model = ?, car_number = ?, status = 'pending'
            WHERE user_id = ?
        ''', (full_name, phone, route_key, car_model, car_number, user_id))
    else:
        cursor.execute('''
            INSERT INTO drivers (user_id, full_name, phone, route_key, car_model, car_number, balance, status, bonus_given)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'pending', 0)
        ''', (user_id, full_name, phone, route_key, car_model, car_number))
    conn.commit()
    conn.close()

def approve_driver_in_db(user_id):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute("SELECT bonus_given FROM drivers WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()

    bonus_to_add = 0
    if res and res[0] == 0:
        bonus_to_add = WELCOME_BONUS
        cursor.execute('''
            UPDATE drivers 
            SET status = 'approved', balance = balance + ?, bonus_given = 1 
            WHERE user_id = ?
        ''', (bonus_to_add, user_id))
    else:
        cursor.execute("UPDATE drivers SET status = 'approved' WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()
    return bonus_to_add

def reject_driver_in_db(user_id):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE drivers SET status = 'rejected' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def deduct_balance(user_id, amount):
    conn = sqlite3.connect('taxi_service.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE drivers SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ==============================================================================
# 4. МЕНЮ ҲӘМ ТАРҚАТЫЎ БАТЫРМАЛАРЫ
# ==============================================================================
def get_driver_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_balance = types.KeyboardButton("💰 Баланс")
    btn_profile = types.KeyboardButton("👤 Профилим")
    btn_rules = types.KeyboardButton("ℹ️ Қолланба")
    markup.row(btn_balance)
    markup.row(btn_profile, btn_rules)
    return markup

def get_share_markup(user_id):
    share_url = f"https://t.me/{DRIVER_BOT_USERNAME}?start={user_id}"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "📲 Ботты басқа айдаўшыларға тарқатыў",
            url=f"https://t.me/share/url?url={share_url}&text=Айдаўшылар%20ботына%20қосылың!"
        )
    )
    return markup

# ==============================================================================
# 5. ДИЗИМНЕН ӨТИЎ ЖОЛЫ
# ==============================================================================
@driver_bot.message_handler(commands=['start'])
def driver_start(message):
    driver = get_driver(message.chat.id)
    if driver and driver[7] == 'approved':
        driver_bot.send_message(
            message.chat.id,
            HEADER_LINK + f"Ассалаўма әлейкум, <b>{driver[1]}</b>!\nСиз тастыйықланған айдаўшысыз.",
            parse_mode="HTML",
            reply_markup=get_driver_main_keyboard()
        )
        driver_bot.send_message(
            message.chat.id,
            "Ботты басқа айдаўшыларға тарқатыў ушын төмендеги батырманы басың:",
            reply_markup=get_share_markup(message.chat.id)
        )
    elif driver and driver[7] == 'pending':
        driver_bot.send_message(
            message.chat.id,
            HEADER_LINK + "⏳ Сизниң арзаңыз ҳәзирде админлер тәрепинен көрип шығылмақта. Илтимас, күтиң.",
            parse_mode="HTML"
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Дизимнен өтиў", callback_data="register_driver"))
        driver_bot.send_message(
            message.chat.id,
            HEADER_LINK + "Ассалаўма әлейкум! Айдаўшы болып ислеў ушын төмендеги батырма арқалы дизимнен өтиң:",
            parse_mode="HTML",
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

    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, data in ROUTE_DATA.items():
        markup.add(types.InlineKeyboardButton(f"📍 {data['title']}", callback_data=f"selroute_{key}"))

    driver_bot.send_message(
        message.chat.id,
        "3. Қайсы жөнелис бойынша қатнайсыз? Төмендеги 8 жөнелистиң бирин сайлаң:",
        reply_markup=markup
    )

@driver_bot.callback_query_handler(func=lambda call: call.data.startswith("selroute_"))
def process_driver_route(call):
    route_key = call.data.replace("selroute_", "")
    driver_registration_data[call.message.chat.id]['route_key'] = route_key

    route_title = ROUTE_DATA.get(route_key, {}).get("title", "")
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

    save_pending_driver(
        chat_id,
        data['full_name'],
        data['phone'],
        data['route_key'],
        data['car_model'],
        data['car_number']
    )

    route_name = ROUTE_DATA.get(data['route_key'], {}).get("title", "Белгисиз")

    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Тастыйықлаў", callback_data=f"approve_{chat_id}"),
        types.InlineKeyboardButton("❌ Бийкар етиў", callback_data=f"reject_{chat_id}")
    )

    admin_caption = (
        f"🚕 <b>ЖАҢА АЙДАЎШЫ АРЗАСЫ:</b>\n\n"
        f"👤 <b>Аты:</b> {data['full_name']}\n"
        f"📞 <b>Тел:</b> {data['phone']}\n"
        f"📍 <b>Жөнелис:</b> {route_name}\n"
        f"🚘 <b>Машина:</b> {data['car_model']} ({data['car_number']})\n"
        f"🆔 <b>Telegram ID:</b> <code>{chat_id}</code>"
    )

    try:
        driver_bot.send_photo(
            ADMIN_CHANNEL_ID,
            data['tech_passport'],
            caption=f"📄 <b>Техпаспорт:</b> {data['full_name']} (ID: {chat_id})",
            parse_mode="HTML"
        )
        driver_bot.send_photo(
            ADMIN_CHANNEL_ID,
            data['car_photo'],
            caption=admin_caption,
            parse_mode="HTML",
            reply_markup=admin_markup
        )
    except Exception as e:
        print(f"Каналга жибериўде қәтелик: {e}")

    driver_bot.send_message(
        chat_id,
        HEADER_LINK + "✅ <b>Мағлыўматларыңыз админге жиберилди!</b>\n\n"
        "Ҳүжжетлериңиз админ тәрепинен тексерилип тастыйықланғаннан соң топарға кириў силтемеси жибериледи.",
        parse_mode="HTML"
    )

# ==============================================================================
# 6. КАНАЛДА ТАСТИЙЫҚЛАЎ (АДМИН)
# ==============================================================================
@driver_bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    action, target_user_id = call.data.split("_")
    target_user_id = int(target_user_id)

    driver = get_driver(target_user_id)
    if not driver:
        driver_bot.answer_callback_query(call.id, "Айдаўшы мағлыўматы табылмады!", show_alert=True)
        return

    if action == "approve":
        bonus_added = approve_driver_in_db(target_user_id)

        driver_bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n<b>✅ ТАСТЫЙЫҚЛАНДЫ</b>",
            parse_mode="HTML"
        )

        route_key = driver[3]
        route_info = ROUTE_DATA.get(route_key, {})
        group_id = route_info.get("group_id")

        # Агар бот гуруҳда админ бўлса янги линк яратади, бўлмаса тайёр invite_link ни олади:
        invite_link = None
        try:
            link_obj = driver_bot.create_chat_invite_link(group_id, member_limit=1)
            invite_link = link_obj.invite_link
        except Exception:
            invite_link = route_info.get("invite_link", f"https://t.me/c/{str(group_id).replace('-100', '')}")

        driver_markup = types.InlineKeyboardMarkup(row_width=1)
        driver_markup.add(
            types.InlineKeyboardButton(f"🚖 «{route_info.get('title')}» топарына кириў", url=invite_link),
            types.InlineKeyboardButton(
                "📲 Ботты басқа айдаўшыларға тарқатыў",
                url=f"https://t.me/share/url?url=https://t.me/{DRIVER_BOT_USERNAME}?start={target_user_id}&text=Айдаўшылар%20ботына%20қосылың!"
            )
        )

        bonus_text = f"🎁 Сизге биринши мәрте дизимнен өткениңиз ушын <b>{WELCOME_BONUS} сўм</b> бонус берилди!\n\n" if bonus_added > 0 else "ℹ️ Сиз алдын дизимнен өткенсиз, сол себепли қосымша бонус берилмеди.\n\n"

        driver_bot.send_message(
            target_user_id,
            HEADER_LINK + f"🎉 <b>Қутлықлаймыз! Сизниң арзаңыз тастыйықланды!</b>\n\n"
            f"{bonus_text}"
            f"📍 Сизниң жөнелисиңиз: <b>{route_info.get('title')}</b>\n\n"
            f"👇 Төмендеги батырма арқалы өз топарыңызға қосылың:",
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
            HEADER_LINK + "Кешириң, сизниң арзаңыз админ тәрепинен қабыл етилмеди.",
            parse_mode="HTML"
        )

# ==============================================================================
# 7. БАЛАНС ТЕКШИРИШ, ПРОФИЛЬ ҲӘМ ҚОЛЛАНБА
# ==============================================================================
@driver_bot.message_handler(func=lambda m: m.text in ["💰 Баланс", "👤 Профилим"])
def driver_profile_and_balance(message):
    user_id = message.chat.id
    driver = get_driver(user_id)
    if not driver:
        driver_start(message)
        return

    route_title = ROUTE_DATA.get(driver[3], {}).get("title", driver[3])

    text = (
        HEADER_LINK +
        f"👤 <b>Айдаўшы кабинети</b>\n\n"
        f"👤 <b>Аты:</b> {driver[1]}\n"
        f"📞 <b>Тел:</b> {driver[2]}\n"
        f"📍 <b>Жөнелис:</b> {route_title}\n"
        f"🚘 <b>Машина:</b> {driver[4]} ({driver[5]})\n"
        f"💰 <b>Балансыңыз:</b> <b>{driver[6]} сўм</b>"
    )
    driver_bot.send_message(user_id, text, parse_mode="HTML", reply_markup=get_share_markup(user_id))

@driver_bot.message_handler(func=lambda m: m.text == "ℹ️ Қолланба")
def driver_rules(message):
    driver_bot.send_message(
        message.chat.id,
        HEADER_LINK +
        "ℹ️ <b>Қағыйдалар ҳәм комиссия:</b>\n\n"
        "1. Буйыртпа топарға түскенде «Буйыртпаны алыў» батырмасын басың.\n"
        "2. Комиссия заказ ушын емес, <b>ҳәр бир адам (жолаўшы) санына</b> قارап есапланады:\n"
        "   • Нөкис — Қоңырат: 3 000 сўм (ҳәр бир адамға)\n"
        "   • Қоңырат — Мойнақ: 2 000 сўм\n"
        "   • Қоңырат — Ақшолақ: 2 000 сўм\n"
        "   • Нөкис — Қанлыкөл: 2 000 сўм\n"
        "   • Нөкис — Шоманай: 2 000 сўм\n"
        "   • Қоңырат — Қанлыкөл: 1 000 сўм\n"
        "   • Қоңырат — Шоманай: 1 500 сўм\n"
        "   • Қоңырат — Сода завод: 1 000 сўм\n"
        "3. Балансыңызда жетерли қаржы болмаса, буйыртпаны алып болмайды.",
        parse_mode="HTML"
    )

# ==============================================================================
# 8. МИЖОЗ БОТИДАН БУЮРТМА ОЛИШ ВА ОДАМ СОНИГА ҚАРАБ КОМИССИЯ ЕЧИШ
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
                "Буйыртпаны тек тастыйықланған айдаўшылар алыўы мүмкин!",
                show_alert=True
            )
            return

        order = orders_data.get(order_id)
        if not order:
            driver_bot.answer_callback_query(call.id, "Бул буйыртпа алдын алынған ямаса бийкар етилген!", show_alert=True)
            return

        route_key = driver[3]
        route_info = ROUTE_DATA.get(route_key, {})
        fee_per_person = route_info.get("fee_per_person", 2000)

        passengers_count = int(order.get('passengers_count', 1))
        total_commission = fee_per_person * passengers_count

        current_balance = driver[6]
        if current_balance < total_commission:
            driver_bot.answer_callback_query(
                call.id,
                f"Балансыңызда қаржы жетпейди!\n"
                f"Буйыртпада: {passengers_count} адам\n"
                f"Керекли комиссия: {total_commission} сўм\n"
                f"Сизниң балансыңыз: {current_balance} сўм",
                show_alert=True
            )
            return

        deduct_balance(driver_user_id, total_commission)

        full_name = driver[1]
        driver_phone = driver[2]

        client_id = order.get('client_id')
        if client_id:
            try:
                taxi_bot.send_message(
                    client_id,
                    f"🎉 <b>Буйыртпаңыз қабылланды!</b>\n\n"
                    f"🚖 <b>Айдаўшы:</b> {full_name}\n"
                    f"📞 <b>Телефон:</b> <code>{driver_phone}</code>\n\n"
                    f"Айдаўшы тез арада сизге қоңыраў қылады. Жолға таярланып турың!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        driver_bot.answer_callback_query(
            call.id,
            f"Буйыртпа қабылланды! {passengers_count} адам ушын {total_commission} сўм комиссия алынды.",
            show_alert=True
        )

        del orders_data[order_id]

    except Exception as e:
        taxi_bot.answer_callback_query(call.id, f"Қәтелик жүз берди: {str(e)}", show_alert=True)

# ==============================================================================
# 9. ИШГА ТУШИРИШ
# ==============================================================================
if __name__ == '__main__':
    import threading
    print("Иккала бот хам муваффакиятли ишга тушди...")
    
    # 1. Шофёрлар ботини алоҳида оқимда юргизиш:
    threading.Thread(target=lambda: driver_bot.infinity_polling(skip_pending=True), daemon=True).start()
    
    # 2. Мижозлар ботини асосий оқимда юргизиш:
    taxi_bot.infinity_polling(skip_pending=True)
