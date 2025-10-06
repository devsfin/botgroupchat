from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

ADMIN_ID = 488787017
CONTACTS = {
    'luda': 1497126590,
    'ketr': 1858219863,
    'daruna': 7179688966,
}
GROUP_ID = -1003172613297
'/'
user_reports = {user_id: None for user_id in CONTACTS.values()}

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
        # Отправляем обычное сообщение всем контактам
        for contact_id in CONTACTS.values():
            await context.bot.send_message(contact_id, text)

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in CONTACTS.values():
        text = update.message.text.strip()
        # Пересылаем любое сообщение в группу
        await context.bot.send_message(GROUP_ID, f"От @{update.effective_user.username}:\n{text}")

        # Если сообщение - трехзначное число, сохраняем для отчета
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

app = ApplicationBuilder().token("8262718662:AAEMKYDvIVQ9zCmcTBM8U8y1F5u_TPcahpM").build()

async def set_bot_commands(application):
    commands = [BotCommand(name, f"Написать {name}") for name in CONTACTS.keys()]
    commands.append(BotCommand("contacts", "Показать список контактов"))
    commands.append(BotCommand("check", "Показать отчет по числам"))
    await application.bot.set_my_commands(commands)

app.post_init = set_bot_commands

app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), forward_to_contacts))
app.add_handler(MessageHandler(filters.TEXT, user_message_handler))

app.add_handler(CommandHandler("check", check_report))

app.run_polling()
