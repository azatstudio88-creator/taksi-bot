import os
import sqlite3
import uuid
from threading import Thread
import telebot
from telebot import types
from flask import Flask

# ----------------- RENDER УЧУН ВЕБ-СЕРВЕР -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Taksi bot faol ishlab turibdi!", 200

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Серверни фонда юргизамиз
Thread(target=run, daemon=True).start()

# ----------------- БОТ СОЗЛАМАЛАРИ -----------------
BOT_TOKEN =

GROUP_NUKUS = -1004325420878
GROUP_SHOMANAY = -1004319753073
GROUP_QANLIKOL = -1004316722887
GROUP_AKSHOLAQ = -1004481922507
GROUP_SODAZAVOD = -1003771047184
GROUP_MOYNAQ = -1003980363859

VIDEO_FILE_ID = "" 

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
orders_data = {}

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

# ----------------- ТУГМАЛАР -----------------
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

# ----------------- МИЖОЗ БОСҚИЧЛАРИ -----------------
@bot.message_handler(func=lambda m: m.text in ["🔄 Басынан баслаў", "Басынан баслаў", "🔄 Бошқатдан бошлаш", "/start"])
def send_welcome(message):
    user_id = message.chat.id
    bot.clear_step_handler_by_chat_id(user_id)
    user_data[user_id] = {}

    bot.send_message(
        user_id,
        "📍 <b>1. Қайсы мәнзилден жолға шығасыз?</b>\n(Боттан пайдаланыўды көриў ушын <b>«📹 Қолланба»</b> тугмесин басың)",
        parse_mode="HTML",
        reply_markup=get_locations_keyboard()
    )
    bot.register_next_step_handler(message, step_qayerdan)

@bot.message_handler(func=lambda m: m.text in ["📹 Қолланба", "Қолланба"])
def show_instruction(message):
    user_id = message.chat.id
    bot.clear_step_handler_by_chat_id(user_id)

    caption_text = (
        "📹 <b>Боттан пайдаланыў қолланбасы:</b>\n\n"
        "1. Жолға шығатуғын ҳәм баратуғын мәнзилди сайлаң.\n"
        "2. Жолға шығыў ўақтын таңлаң.\n"
        "3. Адам санын яки жүк/почтаны көрсетиң.\n"
        "4. Қосымша бала яки сумка барын сайлаң.\n"
        "5. Телефон номериңизди ҳәм мәнзил локациясын жибериң.\n\n"
        "Буйыртпа бергеннен соң, такси сизге тез арада қоңыраў қылады!"
    )
    bot.send_message(
        user_id,
        caption_text,
        parse_mode="HTML",
        reply_markup=get_locations_keyboard()
    )
    bot.register_next_step_handler(message, step_qayerdan)

def step_qayerdan(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return
    elif text in ["📹 Қолланба", "Қолланба"]:
        show_instruction(message)
        return

    user_data[user_id]['qayerdan'] = text

    bot.send_message(
        user_id,
        "🏁 <b>2. Қайсы мәнзилге барасыз?</b>",
        parse_mode="HTML",
        reply_markup=get_locations_keyboard()
    )
    bot.register_next_step_handler(message, step_qayerga)

def step_qayerga(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return
    elif text in ["📹 Қолланба", "Қолланба"]:
        show_instruction(message)
        return

    user_data[user_id]['qayerga'] = text

    bot.send_message(
        user_id,
        "⏰ <b>3. Қайсы ўақытта жолға шығасыз?</b>\n(Тугмелерден сайлаң яки басқа ўақыт болса жазып жибериң):",
        parse_mode="HTML",
        reply_markup=get_time_keyboard()
    )
    bot.register_next_step_handler(message, step_vaqt)

def step_vaqt(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    user_data[user_id]['vaqt'] = text

    bot.send_message(
        user_id,
        "👥 <b>4. Неше адам яки почта?</b>",
        parse_mode="HTML",
        reply_markup=get_people_keyboard()
    )
    bot.register_next_step_handler(message, step_odam)

def step_odam(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    user_data[user_id]['odam'] = text

    bot.send_message(
        user_id,
        "ℹ️ <b>5. Қосымша кимлер? (нелер) бар?</b>",
        parse_mode="HTML",
        reply_markup=get_extra_keyboard()
    )
    bot.register_next_step_handler(message, step_extra)

def step_extra(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    user_data[user_id]['extra'] = text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📞 <b>6. Телефон номериңизди жибериң яки жазың:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_phone)

def step_phone(message):
    user_id = message.chat.id

    if message.text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    if message.contact:
        user_data[user_id]['phone'] = message.contact.phone_number
    elif message.text:
        user_data[user_id]['phone'] = message.text
    else:
        user_data[user_id]['phone'] = "Көрсетилмеген"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_loc = types.KeyboardButton("📍 Локацияны жибериў", request_location=True)
    markup.row(btn_loc)
    markup.row("Керек емес / Тек адрес")
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📍 <b>7. Мәнзил локациясын жибериң:</b>\n(Егер керек болмаса, «Керек емес» тугмесин басың)",
        parse_mode="HTML",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_location_and_send)

# ----------------- БУЮРТМАНИ ЮБОРИШ -----------------
def step_location_and_send(message):
    user_id = message.chat.id

    if message.text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    location_obj = None
    loc_text = "Жиберилмеди"

    if message.location:
        location_obj = message.location
        loc_text = "📍 Картада жиберилди"
    elif message.text:
        loc_text = message.text

    qayerdan = user_data[user_id].get('qayerdan', '-')
    qayerga = user_data[user_id].get('qayerga', '-')
    vaqt = user_data[user_id].get('vaqt', '-')
    odam = user_data[user_id].get('odam', '-')
    extra = user_data[user_id].get('extra', '-')
    phone = user_data[user_id].get('phone', '-')
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
        bot.send_message(
            chat_id=target_group, 
            text=order_text, 
            parse_mode="HTML", 
            reply_markup=get_order_inline_keyboard(order_id)
        )

        bot.send_message(
            user_id,
            "✅ <b>Сиз бенен тез арада такси байланысады!</b>",
            parse_mode="HTML",
            reply_markup=get_restart_keyboard()
        )
    except Exception:
        bot.send_message(
            user_id,
            "⚠️ Буйыртпаны жибериўде қәтелик жүз берди. Илтимас, қайтадан урынып көрсек болады.",
            reply_markup=get_restart_keyboard()
        )

# ----------------- БУЮРТМАНИ ҲАЙДОВЧИ ҚАБУЛ ҚИЛИШИ -----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("take_"))
def process_take_order(call):
    driver_id = call.from_user.id
    order_id = call.data.split("_")[1]

    if order_id not in orders_data:
        bot.answer_callback_query(call.id, "⚠️ Бул буйыртпа алдын алынған яки актив емес!", show_alert=True)
        return

    order = orders_data[order_id]
    route = order.get('route', '')
    fee = COMMISSION_RATES.get(route, 2000)

    conn = sqlite3.connect("drivers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, phone, car_info, balance FROM drivers WHERE user_id = ?", (driver_id,))
    driver = cursor.fetchone()

    if not driver:
        bot.answer_callback_query(
            call.id, 
            "⚠️ Сиз ҳайдавшылар ботында дизимнен өтпегенсиз! Дәслеп дизимнен өтиң.", 
            show_alert=True
        )
        conn.close()
        return

    full_name, driver_phone, car_info, balance = driver

    if balance < fee:
        bot.answer_callback_query(
            call.id, 
            f"❌ Балансыңызда қаржы жетпейди!\nБул бағдар ушын кем дегенде {fee:,} сўм керек.\nСиздиң балансыңыз: {balance:,} сўм.", 
            show_alert=True
        )
        conn.close()
        return

    new_balance = balance - fee
    cursor.execute("UPDATE drivers SET balance = ? WHERE user_id = ?", (new_balance, driver_id))
    conn.commit()
    conn.close()

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{call.message.text}\n\n✅ <b>Буйыртпа алынды!</b>\nҲайдавшы: {full_name} ({car_info})",
        parse_mode="HTML"
    )

    client_text = (
        f"🚕 <b>Буйыртпа табыслы қабылланды!</b>\n\n"
        f"🛣 <b>Бағдар:</b> {route}\n"
        f"👤 <b>Клиент:</b> {order.get('client_name')}\n"
        f"📞 <b>Телефон:</b> <code>{order.get('client_phone')}</code>\n"
        f"📍 <b>Мәнзил/Локация:</b> {order.get('location')}\n\n"
        f"💵 Балансыңыздан: <b>{fee:,} сўм</b> ешилди.\n"
        f"💰 Қалған балансыңыз: <b>{new_balance:,} сўм</b>"
    )
    bot.send_message(driver_id, client_text, parse_mode="HTML")

    if order.get('location_obj'):
        loc = order['location_obj']
        bot.send_location(driver_id, latitude=loc.latitude, longitude=loc.longitude)

    bot.answer_callback_query(call.id, f"Буйыртпа алынды! Баланстан {fee:,} сўм ешилди.")

    client_id = order.get('client_id')
    if client_id:
        try:
            bot.send_message(
                client_id,
                f"🎉 <b>Буйыртпаңыз қабылланды!</b>\n\n"
                f"🚖 <b>Ҳайдавшы:</b> {full_name}\n"
                f"🚘 <b>Автомобиль:</b> {car_info}\n"
                f"📞 <b>Телефон:</b> <code>{driver_phone}</code>\n\n"
                f"Ҳайдавшы тез арада сизге қоңыраў қылады. Жолға таярланып турың!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    del orders_data[order_id]

# ----------------- БОТНИНГ АСОСИЙ ИШГА ТУШИШ ҚИСМИ -----------------
if __name__ == '__main__':
    print("Taksi bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
