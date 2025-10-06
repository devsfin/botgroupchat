from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import os
import logging

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Константы ---
TOKEN = os.getenv("BOT_TOKEN")  # Токен через переменные среды
ADMIN_ID = 488787017
CONTACTS = {
    'luda': 1497126590,
    'ketr': 1858219863,
    'daruna': 7179688966,
}
GROUP_ID = -1003172613297
user_reports = {user_id: None for user_id in CONTACTS.values()}

# --- Flask ---
app = Flask(__name__)

# --- Telegram bot ---
application = Application.builder().token(TOKEN).build()

# --- Хендлеры ---
async def forward_to_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"forward_to_contacts received message from {update.effective_user.id}: {update.message.text}")
    if update.effective_user.id != ADMIN_ID:
        logging.info("User is not admin, ignoring message")
        return

    text = update.message.text.strip()
    if text == '/contacts':
        contacts_list = "\n".join([f"/{name}" for name in CONTACTS.keys()])
        await update.message.reply_text(f"Список контактов:\n{contacts_list}")
        return

    if text == '/check':
        await check_report(update, context)
        return

    if text.startswith('/'):
        cmd, *msg = text[1:].split(' ', 1)
        contact_id = CONTACTS.get(cmd)
        if contact_id:
            if msg:
                await context.bot.send_message(contact_id, msg[0])
                logging.info(f"Sent message to contact {cmd} ({contact_id}): {msg[0]}")
            else:
                await update.message.reply_text(f"Введите сообщение после команды /{cmd}")
        else:
            await update.message.reply_text("Неизвестный контакт.")
    else:
        for contact_id in CONTACTS.values():
            await context.bot.send_message(contact_id, text)
            logging.info(f"Broadcasted message to contact ID {contact_id}: {text}")

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logging.info(f"user_message_handler received message from {user_id}: {text}")
    if user_id in CONTACTS.values():
        await context.bot.send_message(GROUP_ID, f"От @{update.effective_user.username}:\n{text}")
        if text.isdigit() and len(text) == 3:
            user_reports[user_id] = text
            logging.info(f"Updated report for user {user_id} with value {text}")

async def check_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    missing = [name for name, uid in CONTACTS.items() if user_reports.get(uid) is None]
    received = [(name, user_reports.get(uid)) for name, uid in CONTACTS.items() if user_reports.get(uid) is not None]

    msg = "Отчет по присланным числам:\n"
    if received:
        msg += "\nПолучено от:\n" + "\n".join([f"{name}: {num}" for name, num in received])
    else:
        msg += "\nДанных о полученных числах нет."

    if missing:
        msg += "\n\nНе получили от:\n" + "\n".join(missing)
    else:
        msg += "\n\nВсе прислали числа."

    await update.message.reply_text(msg)
    logging.info("Sent report summary")

# --- Регистрация хендлеров ---
application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), forward_to_contacts))
application.add_handler(MessageHandler(filters.TEXT, user_message_handler))
application.add_handler(CommandHandler("check", check_report))

# --- Flask route для Telegram webhook ---
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    logging.info("Received webhook update")
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        logging.info("Update processed successfully")
    except Exception as e:
        logging.error(f"Error processing update: {e}")
    return "ok"

@app.route('/', methods=['GET'])
def index():
    return "Bot is running!", 200

# --- Запуск ---
if __name__ == '__main__':
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    logging.info(f"Setting webhook to {webhook_url}")
    asyncio.run(application.bot.set_webhook(webhook_url))
    app.run(host='0.0.0.0', port=10000)
