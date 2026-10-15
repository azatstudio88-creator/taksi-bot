import telebot
from telebot import types
import os
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot faol ishlab turibdi!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

Thread(target=run).start()


# Укажите ваш токен бота и ID группы
BOT_TOKEN = "8820304382:AAH8gAI8BEOWS2D0j80g585XrZJYsBvJpRQ"

# Гуруҳлар ID рақамлари
GROUP_NUKUS = -1004325420878
GROUP_MOYNAQ = -5450445768
GROUP_SODAZAVOD = -5533102153
GROUP_AKSHOLAQ = -5302796049
GROUP_QANLIKOL = -5424177269
GROUP_SHOMANAY = -5569534477

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# ----------------- ТУГМАЛАР (КЛАВИАТУРА) -----------------
def get_restart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔄 Басынан баслаў")
    return markup

def get_locations_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Қоңырат", "Нөкис")
    markup.row("Қанлыкөл", "Шоманай")
    markup.row("Ақшолақ", "Мойнақ")
    markup.row("Сода завод", "Басқа мәнзил")
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

# ----------------- БОТ ҚАДАМЛАРИ -----------------
@bot.message_handler(func=lambda m: m.text in ["🔄 Басынан баслаў", "Басынан баслаў", "🔄 Бошқатдан бошлаш", "/start"])
def send_welcome(message):
    user_id = message.chat.id
    bot.clear_step_handler_by_chat_id(user_id)
    user_data[user_id] = {}

    bot.send_message(
        user_id,
        "📍 <b>1. Қайсы мәнзилден жолға шығасыз?</b>",
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

    user_data[user_id]['qayerga'] = text

    bot.send_message(
        user_id,
        "👥 <b>3. Неше адам яки почта?</b>",
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
        "ℹ️ <b>4. Қосымша кимлер? (нелер) бар?</b>",
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
        "📞 <b>5. Телефон номериңизди жибериң яки жазың:</b>",
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
        "📍 <b>6. Мәнзил локациясын жибериң:</b>\n(Егер керек болмаса, «Керек емес» тугмесин басың)",
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
    odam = user_data[user_id].get('odam', '-')
    extra = user_data[user_id].get('extra', '-')
    phone = user_data[user_id].get('phone', '-')
    user_name = message.from_user.first_name

    order_text = (
        "🚕 <b>ЖАҢА БУЙЫРТПА!</b>\n\n"
        f"📍 <b>Қайдан:</b> {qayerdan}\n"
        f"🏁 <b>Қайда:</b> {qayerga}\n"
        f"👥 <b>Адам/Почта:</b> {odam}\n"
        f"➕ <b>Қосымша:</b> {extra}\n"
        f"📱 <b>Телефон:</b> {phone}\n"
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
        bot.send_message(chat_id=target_group, text=order_text, parse_mode="HTML")
        if location_obj:
            bot.send_location(chat_id=target_group, latitude=location_obj.latitude, longitude=location_obj.longitude)

        bot.send_message(
            user_id,
            "✅ <b>Сиз бенен тез арада такси байланысады!</b>",
            parse_mode="HTML",
            reply_markup=get_restart_keyboard()
        )
    except Exception as e:
        bot.send_message(
            user_id,
            "⚠️ Буйыртпаны жибериўде қәтелик жүз берди. Илтимас, қайтадан урынып көрсек болады.",
            reply_markup=get_restart_keyboard()
        )

if __name__ == '__main__':
    bot.infinity_polling()
