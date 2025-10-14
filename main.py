import os
from telegram import Update, BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

TOKEN = os.getenv('BOTTOKEN')
if not TOKEN:
    raise ValueError("BOTTOKEN environment variable is not set.")

ADMIN_ID = 488787017
CONTACTS = {
    'ketr': 7415558897,
    'daruna': 7179688966,
}
GROUP_ID = -1003172613297
user_reports = {user_id: None for user_id in CONTACTS.values()}


# === Только для админа ===
async def forward_to_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Эта команда только для администратора.")
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


# === Команда /balu для всех пользователей ===
async def balu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("Пожалуйста, отправьте одно число из 2 или 3 цифр, например: /balu 45 или /balu 123")
        return

    value = context.args[0]

    if not value.isdigit() or not (2 <= len(value) <= 3):
        await update.message.reply_text("❌ Неверный формат. Введите одно число из 2 или 3 цифр, например: /balu 45 или /balu 123")
        return

    number = int(value)
    user_reports[user_id] = number

    await update.message.reply_text(f"✅ Принято число: {number}")

    report_msg = f"От @{update.effective_user.username or update.effective_user.full_name} получено число: {number}"
    await context.bot.send_message(GROUP_ID, report_msg)


from datetime import datetime, time

# === Проверка отчетов (только для админа) ===
async def check_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Эта команда только для администратора.")
        return

    now = datetime.now().time()
    start_time = time(9, 15)   # 09:15 утра
    end_time = time(3, 0)      # 03:00 ночи

    def is_in_time_window(report_time):
        """Проверка: report_time учитываем только в заданное время"""
        if start_time <= report_time or report_time <= end_time:
            return True
        return False

    # Фильтруем отчёты по времени
    missing = []
    received = []

    for name, uid in CONTACTS.items():
        report = user_reports.get(uid)
        if report is not None:
            report_time = report['time']  # предполагаем, что в user_reports хранится {'nums': [...], 'time': datetime}
            if is_in_time_window(report_time.time()):
                received.append((name, report['nums']))
            else:
                missing.append(name)  # если прислано вне времени — считаем как не получено
        else:
            missing.append(name)

    msg = "Отчет по присланным числам:\n"
    if received:
        msg += "\nПолучено от:\n" + "\n".join([f"{name}: {nums}" for name, nums in received])
    else:
        msg += "\nДанных о полученных числах нет."

    if missing:
        msg += "\n\nНе получили от:\n" + "\n".join(missing)
    else:
        msg += "\n\nВсе прислали числа."

    await update.message.reply_text(msg)



# === Любое сообщение от пользователя → в группу ===
async def forward_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return

    caption = update.message.caption or update.message.text or ""
    header = f"💬 Сообщение от @{user.username or user.full_name}:\n"

    try:
        if update.message.photo:
            await context.bot.send_photo(GROUP_ID, photo=update.message.photo[-1].file_id, caption=header + caption)
        elif update.message.document:
            await context.bot.send_document(GROUP_ID, document=update.message.document.file_id, caption=header + caption)
        elif update.message.video:
            await context.bot.send_video(GROUP_ID, video=update.message.video.file_id, caption=header + caption)
        elif update.message.voice:
            await context.bot.send_voice(GROUP_ID, voice=update.message.voice.file_id, caption=header + caption)
        elif update.message.audio:
            await context.bot.send_audio(GROUP_ID, audio=update.message.audio.file_id, caption=header + caption)
        elif update.message.sticker:
            await context.bot.send_sticker(GROUP_ID, sticker=update.message.sticker.file_id)
            await context.bot.send_message(GROUP_ID, header + "(стикер)")
        elif caption:
            await context.bot.send_message(GROUP_ID, header + caption)
        else:
            await context.bot.send_message(GROUP_ID, header + "(сообщение без текста)")

        await update.message.reply_text("✅ Сообщение отправлено в группу.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при пересылке: {e}")


# === Разные команды для админа и пользователей ===
async def set_bot_commands(application):
    # Команды для обычных пользователей
    user_commands = [
        BotCommand("balu", "Отправить одно число (2–3 цифры)")
    ]

    # Команды для админа
    admin_commands = [
        BotCommand("balu", "Отправить одно число (2–3 цифры)"),
        BotCommand("contacts", "Показать список контактов"),
        BotCommand("check", "Показать отчет по числам")
    ]

    # Устанавливаем пользователям
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())

    # А админу — его команды
    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))


# === Запуск приложения ===
app = ApplicationBuilder().token(TOKEN).build()
app.post_init = set_bot_commands

# Хендлеры
app.add_handler(CommandHandler("balu", balu_command))
app.add_handler(CommandHandler("check", check_report))
app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), forward_to_contacts))
app.add_handler(MessageHandler(~filters.User(ADMIN_ID), forward_user_message))

if __name__ == "__main__":
    app.run_polling()
