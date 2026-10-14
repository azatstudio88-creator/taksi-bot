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
GROUP_ID = -1005465166613                                     
bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def get_restart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔄 Бошқатдан бошлаш")
    return markup

@bot.message_handler(func=lambda message: message.text == "🔄 Бошқатдан бошлаш")
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Қўнғирот", "Нөкис")
    markup.row("Хўжайли", "Бошқа манзил")
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "Ассалому алайкум! Такси буюртма бериш ботига хуш келибсиз.\n\n📍 <b>1. Қайси манзилдан йўлга чиқасиз?</b>", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_qayerdan)

def step_qayerdan(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    user_data[user_id]['qayerdan'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Нөкис", "Қўнғирот")
    markup.row("Тўрткўл", "Тошкент")
    markup.row("Бошқа манзил")
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "🏁 <b>2. Қайси манзилга/шаҳарга борасиз?</b>", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_qayerga)

def step_qayerga(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    user_data[user_id]['qayerga'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Ҳозироқ (тезда)", "Эртага 09:00 га")
    markup.row("Эртага 11:00 га", "Эртага 14:00 га")
    markup.row("Бошқа вақтни ёзиш", "🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "⏰ <b>3. Қачон йўлга чиқасиз?</b>\n(Тайёр вақтлардан танланг ёки ўзингиз хоҳлаган вақтни ёзиб юборинг):", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_vaqt)

def step_vaqt(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    user_data[user_id]['vaqt'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_loc = types.KeyboardButton("📍 Аниқ локацияни юбориш", request_location=True)
    markup.add(btn_loc)
    markup.row("Локация юбормайман")
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "📍 <b>4. Ҳайдовчи сизни тез топиши учун турган жойингиз (локация)ни юборинг:</b>\n(«📍 Аниқ локацияни юбориш» тугмасини босинг ёки мўлжални ёзинг)", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_lokatsiya)

def step_lokatsiya(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    if message.location:
        user_data[user_id]['lat'] = message.location.latitude
        user_data[user_id]['lon'] = message.location.longitude
        user_data[user_id]['lokatsiya_matn'] = "📍 Харита орқали юборилди"
    else:
        user_data[user_id]['lat'] = None
        user_data[user_id]['lon'] = None
        user_data[user_id]['lokatsiya_matn'] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 киши", "2 киши")
    markup.row("3 киши", "4 киши (Салон)")
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "👥 <b>5. Неча киши йўлга чиқасиз?</b>", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_odam)

def step_odam(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    user_data[user_id]['odam'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Йўқ, фақат ўзим(из)")
    markup.row("Ёш бола бор", "Катта сумка/юк бор")
    markup.row("Ҳам бола, ҳам катта юк бор")
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "🧳 <b>6. Ёнингизда ёш бола ёки катта сумка (юк) борми?</b>", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_yuk)

def step_yuk(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    user_data[user_id]['yuk'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_contact = types.KeyboardButton("📱 Телефон рақамни юбориш", request_contact=True)
    markup.add(btn_contact)
    markup.row("🔄 Бошқатдан бошлаш")
    
    bot.send_message(
        user_id, 
        "📞 <b>7. Телефон рақамингизни қолдиринг:</b>\n(Пастдаги «Телефон рақамни юбориш» тугмасини босинг ёки рақамни ёзинг)", 
        parse_mode="HTML", 
        reply_markup=markup
    )
    bot.register_next_step_handler(message, step_telefon)

def step_telefon(message):
    user_id = message.chat.id
    if message.text == "🔄 Бошқатдан бошлаш":
        send_welcome(message)
        return

    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = f"+{phone}"
    else:
        phone = message.text
        
    data = user_data.get(user_id, {})
    username = f"@{message.from_user.username}" if message.from_user.username else "Кўрсатилмаган"
    
    elon_text = (
        "🚖 <b>ЯНГИ БУЮРТМА!</b>\n\n"
        f"📍 <b>Қаердан:</b> {data.get('qayerdan')}\n"
        f"🏁 <b>Қаерга:</b> {data.get('qayerga')}\n"
        f"⏰ <b>Вақти:</b> {data.get('vaqt')}\n"
        f"🗺 <b>Локация/Мўлжал:</b> {data.get('lokatsiya_matn')}\n"
        f"👥 <b>Одам сони:</b> {data.get('odam')}\n"
        f"🧳 <b>Қўшимча:</b> {data.get('yuk')}\n"
        f"📞 <b>Тел:</b> {phone}\n"
        f"👤 <b>Мижоз:</b> {message.from_user.full_name} ({username})"
    )
    
    try:
        bot.send_message(GROUP_ID, elon_text, parse_mode="HTML")
        if data.get('lat') and data.get('lon'):
            bot.send_location(GROUP_ID, latitude=data.get('lat'), longitude=data.get('lon'))
    except Exception as e:
        print(f"Гуруҳга юборишда хатолик: {e}")
        
    bot.send_message(
        user_id, 
        "✅ <b>Буюртмангиз қабул қилинди!</b>\nТез орада ҳайдовчи сиз билан боғланади.\n\nЯнги буюртма бериш учун пастдаги тугмани босинг:", 
        parse_mode="HTML", 
        reply_markup=get_restart_keyboard()
    )

print("Бот муваффақиятли ишга тушди!")
bot.infinity_polling()
