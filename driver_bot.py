import sqlite3
from telebot import types

# Ҳар бир йўналишнинг комиссия нархлари
COMMISSION_RATES = {
    "Қоңырат — Нөкис": 4000,
    "Қоңырат — Мойнақ": 3000,
    "Қоңырат — Ақшолақ": 3000,
    "Нөкис — Қанлыкөл": 3000,
    "Нөкис — Шоманай": 3000,
    "Қоңырат — Қанлыкөл": 2000,
    "Қоңырат — Шоманай": 2000,
    "Қоңырат — Сода завод": 2000
}

# 1. Буюртма гуруҳга юборилганда чиқадиган тугма:
def get_order_inline_keyboard(order_id):
    markup = types.InlineKeyboardMarkup()
    btn_take = types.InlineKeyboardButton("🚖 Буюртмани олиш", callback_data=f"take_{order_id}")
    markup.add(btn_take)
    return markup


# 2. Ҳайдовчи тугмани босганда ишлайдиган қисм:
@bot.callback_query_handler(func=lambda call: call.data.startswith("take_"))
def process_take_order(call):
    driver_id = call.from_user.id
    order_id = call.data.split("_")[1]

    # Буюртма мавжудлигини текшириш
    if order_id not in orders_data:
        bot.answer_callback_query(call.id, "⚠️ Бу буюртма олдин олинган ёки муддати ўтган!", show_alert=True)
        return

    order = orders_data[order_id]
    route = order.get('route', '')
    fee = COMMISSION_RATES.get(route, 2000)

    # Ҳайдовчи базада бор-йўқлигини текшириш
    conn = sqlite3.connect("drivers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, phone, car_info, balance FROM drivers WHERE user_id = ?", (driver_id,))
    driver = cursor.fetchone()

    if not driver:
        bot.answer_callback_query(
            call.id, 
            "⚠️ Сиз ҳайдовчилар ботидан рўйхатдан ўтмагансиз! Аввал ҳайдовчилар ботидан рўйхатдан ўтинг.", 
            show_alert=True
        )
        conn.close()
        return

    full_name, phone, car_info, balance = driver

    # Балансда етарли маблағ борлигини текшириш
    if balance < fee:
        bot.answer_callback_query(
            call.id, 
            f"❌ Балансингизда маблағ етмайди!\nБу йўналиш учун камида {fee:,} сўм керак.\nСизнинг балансингиз: {balance:,} сўм.", 
            show_alert=True
        )
        conn.close()
        return

    # Балансдан пулни ечиш
    new_balance = balance - fee
    cursor.execute("UPDATE drivers SET balance = ? WHERE user_id = ?", (new_balance, driver_id))
    conn.commit()
    conn.close()

    # Гуруҳдаги хабарни янгилаш (бошқалар ололмаслиги учун)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{call.message.text}\n\n✅ <b>Буюртма олинди!</b>\nҲайдовчи: {full_name} ({car_info})",
        parse_mode="HTML"
    )

    # Ҳайдовчининг личкасига мижоз маълумотларини юбориш
    client_text = (
        f"🚕 <b>Буюртма муваффақиятли олинди!</b>\n\n"
        f"🛣 <b>Йўналиш:</b> {route}\n"
        f"👤 <b>Мижоз:</b> {order.get('client_name')}\n"
        f"📞 <b>Телефон:</b> {order.get('client_phone')}\n"
        f"📍 <b>Манзил:</b> {order.get('location')}\n\n"
        f"💵 Балансдан {fee:,} сўм ечилди.\n"
        f"💰 Қолган баланс: {new_balance:,} сўм"
    )
    bot.send_message(driver_id, client_text, parse_mode="HTML")
    bot.answer_callback_query(call.id, f"Буюртма қабул қилинди! Балансдан {fee:,} сўм ечилди.")

    # Буюртмани фаол рўйхатдан ўчириш
    del orders_data[order_id]
