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
# Укажите ваш токен бота и ID группы
BOT_TOKEN = "8820304382:AAH8gAI8BEOWS2D0j80g585XrZJYsBvJpRQ"
GROUP_NUKUS = -1004325420878
GROUP_MOYNAQ = -5450445768
GROUP_SODAZAVOD = -5533102153
GROUP_AKSHOLAQ = -5302796049
GROUP_QANLIKOL = -5424177269
GROUP_SHOMANAY = -5569534477

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

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
    markup.row("📦 Почта / Жүк")
    markup.row("🔄 Басынан баслаў")
    return markup

@bot.message_handler(func=lambda message: message.text in ["🔄 Басынан баслаў", "Басынан баслаў", "🔄 Бошқатдан бошлаш"])
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_data[user_id] = {}

    welcome_text = (
        "Region 95 Taxi (Қонырат — Нукус) ботына хош келипсиз! 🚕\n"
        "Биз бенен машына табыу оте ансат хам тез! 24/7\n\n"
        "📍 <b>1. Қайси манзилдан йўлга чиқасиз?</b>"
    )
    bot.send_message(
        user_id,
        welcome_text,
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
        "🏁 <b>2. Қайси манзилга барасиз?</b>",
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
        "👥 <b>3. Нече адам барасыз яки почтама?</b>",
        parse_mode="HTML",
        reply_markup=get_people_keyboard()
    )
    bot.register_next_step_handler(message, step_odam_soni)

def step_odam_soni(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    user_data[user_id]['odam_soni'] = text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    markup.row(btn_phone)
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📱 <b>4. Телефон номериңизди жибериң яки жазың:</b>",
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
        phone = message.contact.phone_number
    else:
        phone = message.text

    user_data[user_id]['phone'] = phone

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Жок, тек адрес жеткиликли")
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "💬 <b>5. Қосымша мәнзил яки белгили орын бар ма?</b>\n(Мысалы: Базар алды, Вокзал, 14-дом)",
        parse_mode="HTML",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_qoshimcha)

def step_qoshimcha(message):
    user_id = message.chat.id
    text = message.text

    if text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    user_data[user_id]['qoshimcha'] = text

    qayerdan = user_data[user_id].get('qayerdan', '')
    qayerga = user_data[user_id].get('qayerga', '')
    odam = user_data[user_id].get('odam_soni', '')
    phone = user_data[user_id].get('phone', '')
    qoshimcha = user_data[user_id].get('qoshimcha', '')
    user_name = message.from_user.first_name

    order_text = (
        "🚕 <b>ЖАҢА БУЙЫРТПА!</b>\n\n"
        f"📍 <b>Мәнзил:</b> {qayerdan} ➡️ {qayerga}\n"
        f"👤 <b>Клиент:</b> {user_name}\n"
        f"👥 <b>Адам саны:</b> {odam}\n"
        f"📱 <b>Тел:</b> {phone}\n"
        f"💬 <b>Қосымша:</b> {qoshimcha}\n"
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
        bot.send_message(
            user_id,
            "✅ <b>Буйыртпаңыз қабыл етилди!</b>\nТез арада ҳайдаўшы сиз бенен байланысады.",
            parse_mode="HTML",
            reply_markup=get_restart_keyboard()
        )
    except Exception as e:
        bot.send_message(
            user_id,
            "⚠️ Буйыртпаны жибериўде қәтелик жүз берди. Илтимас, қайтадан урынып көриң.",
            reply_markup=get_restart_keyboard()
        )

if __name__ == '__main__':
    bot.infinity_polling()
