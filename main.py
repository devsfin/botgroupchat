from flask import Flask, request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio
import os

# --- Константы ---
TOKEN = os.getenv("BOT_TOKEN")  # токен через переменные среды (безопаснее)
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
    if update.effective_user.id != ADMIN_ID:
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
            else:
                await update.message.reply_text(f"Введите сообщение после команды /{cmd}")
        else:
            await update.message.reply_text("Неизвестный контакт.")
    else:
        for contact_id in CONTACTS.values():
            await context.bot.send_message(contact_id, text)

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in CONTACTS.values():
        text = update.message.text.strip()
        await context.bot.send_message(GROUP_ID, f"От @{update.effective_user.username}:\n{text}")
        if text.isdigit() and len(text) == 3:
            user_reports[user_id] = text

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

# --- Регистрация хендлеров ---
application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), forward_to_contacts))
application.add_handler(MessageHandler(filters.TEXT, user_message_handler))
application.add_handler(CommandHandler("check", check_report))

# --- Flask route для Telegram webhook ---
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

@app.route('/')
def index():
    return "Bot is running!", 200

# --- Запуск ---
if __name__ == '__main__':
    # Установим webhook на Render-домен
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    asyncio.run(application.bot.set_webhook(webhook_url))
    app.run(host='0.0.0.0', port=10000)
