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

# Йўналишлар бўйича гуруҳларнинг ID рақамлари
GROUP_NUKUS = -1004325420878
GROUP_MOYNAQ = -5450445768
GROUP_SODAZAVOD = -5533102153
GROUP_AKSHOLAQ = -5302796049
GROUP_QANLIKOL = -5424177269
GROUP_SHOMANAY = -5569534477

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

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
    markup.row("Сода завод", "Басқа мәнзил")
    markup.row("🔄 Басынан баслаў")
    return markup

def get_people_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 адам", "2 адам")
    markup.row("3 адам", "4 адам (салон)")
    markup.row("📦 Почта / Жүк", "👶 Жас бала бар")
    markup.row("🧳 Багаж / Жүк бар")
    markup.row("🔄 Басынан баслаў")
    return markup

# ----------------- БОТ БОШЛАНИШИ -----------------
@bot.message_handler(func=lambda m: m.text in ["🔄 Басынан баслаў", "Басынан баслаў", "🔄 Бошқатдан бошлаш", "/start"])
def send_welcome(message):
    user_id = message.chat.id
    bot.clear_step_handler_by_chat_id(user_id)
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
        "👥 <b>3. Нече адам барасыз яки почта/бала/багаж бар ма?</b>",
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

    # Телефон рақам ва локация сўраш тугмалари
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Телефон номерди жибериў", request_contact=True)
    btn_location = types.KeyboardButton("📍 Локацияны жибериў", request_location=True)
    markup.row(btn_phone)
    markup.row(btn_location)
    markup.row("🔄 Басынан баслаў")

    bot.send_message(
        user_id,
        "📱 <b>4. Телефон номериңизди яки локацияңызды жибериң:</b>\n(Сондай-ақ номерди қолдан жазсаңыз да болады)",
        parse_mode="HTML",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_order_final)

# ----------------- БУЮРТМАНИ ГУРУҲГА ЮБОРИШ -----------------
def process_order_final(message):
    user_id = message.chat.id

    if message.text in ["🔄 Басынан баслаў", "Басынан баслаў"]:
        send_welcome(message)
        return

    phone_or_contact = "Көрсетилмеген"
    location_obj = None

    if message.contact:
        phone_or_contact = message.contact.phone_number
    elif message.location:
        location_obj = message.location
        phone_or_contact = "📍 Локация жиберилди (картада)"
    elif message.text:
        phone_or_contact = message.text

    qayerdan = user_data[user_id].get('qayerdan', '-')
    qayerga = user_data[user_id].get('qayerga', '-')
    odam = user_data[user_id].get('odam_soni', '-')
    user_name = message.from_user.first_name

    order_text = (
        "🚕 <b>ЖАҢА БУЙЫРТПА!</b>\n\n"
        f"📍 <b>Мәнзил:</b> {qayerdan} ➡️ {qayerga}\n"
        f"👤 <b>Клиент:</b> {user_name}\n"
        f"👥 <b>Мағлыўмат:</b> {odam}\n"
        f"📱 <b>Байланыс:</b> {phone_or_contact}\n"
    )

    # Йўналиш бўйича гуруҳни танлаш
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
        # Гуруҳга буюртма матнини юбориш
        bot.send_message(chat_id=target_group, text=order_text, parse_mode="HTML")
        
        # Агар мижоз локация юборган бўлса, гуруҳга картадаги нуқтасини ҳам ташлаб беради
        if location_obj:
            bot.send_location(chat_id=target_group, latitude=location_obj.latitude, longitude=location_obj.longitude)

        bot.send_message(
            user_id,
            "✅ <b>Буйыртпаңыз қабыл етилди!</b>\nТез арада ҳайдаўшы сиз бенен байланысады.",
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
