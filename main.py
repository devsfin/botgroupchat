import os
from datetime import datetime, time
from telegram import Update, BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

# ===== Настройки =====
TOKEN = os.getenv('BOTTOKEN')
if not TOKEN:
    raise ValueError("BOTTOKEN environment variable is not set.")

ADMIN_ID = 488787017
CONTACTS = {
    'Luda': 1497126590,
    'Mama': 5110918542,
    'Slava': 394747876,
    'Anna': 405409720,
    'KetD': 616933881,
    'KetR': 1858219863,
    'Andre': 1614813445,
    'Vera': 5205993905,
    'Anton': 107042242,
    'Jeca': 91380845,
}
GROUP_ID = -1003172613297

# user_reports тепер зберіга словники: {"nums": число, "time": datetime}
user_reports = {user_id: None for user_id in CONTACTS.values()}


# === Функція пересилання повідомлень адміном контактамам ===
async def forward_to_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Ця команда тільки для адміна.")
        return

    text = update.message.text.strip()

    if text == '/contacts':
        contacts_list = "\n".join([f"/{name}" for name in CONTACTS.keys()])
        await update.message.reply_text(f"Список контактів:\n{contacts_list}")
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
                await update.message.reply_text(f"Введіть повідомлення після команди /{cmd}")
        else:
            await update.message.reply_text("Невідомий контакт.")
    else:
        for contact_id in CONTACTS.values():
            await context.bot.send_message(contact_id, text)


# === Команда /balu для користувачів ===
async def balu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("Будьласка, відправте одне число з 2 чи 3 цифр, наприклад: /balu 45 чи /balu 123")
        return

    value = context.args[0]

    if not value.isdigit() or not (2 <= len(value) <= 3):
        await update.message.reply_text("❌ Невірний формат. відправте одне число з 2 чи 3 цифр, наприклад: /balu 45 чи /balu 123")
        return

    number = int(value)
    # Зберігаем число і час відправки
    user_reports[user_id] = {"nums": number, "time": datetime.now()}

    await update.message.reply_text(f"✅ Прийнято число: {number}")

    report_msg = f"Від @{update.effective_user.username or update.effective_user.full_name} отримано число: {number}"
    await context.bot.send_message(GROUP_ID, report_msg)


# === Перевірка звіту (тільки для адміна) ===
async def check_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Ця команда тільки для адміна.")
        return

    start_time = time(9, 15)
    end_time = time(3, 0)  # 03:00 следующего дня

    def is_in_time_window(report_time):
        return start_time <= report_time or report_time <= end_time

    missing = []
    received = []

    for name, uid in CONTACTS.items():
        report = user_reports.get(uid)
        if report is not None and isinstance(report, dict) and 'time' in report:
            report_time = report['time']
            if is_in_time_window(report_time.time()):
                received.append((name, report['nums']))
            else:
                missing.append(name)
        else:
            missing.append(name)

    msg = "Звіт по отриманих числах:\n"
    if received:
        msg += "\nОтримано від:\n" + "\n".join([f"{name}: {nums}" for name, nums in received])
    else:
        msg += "\nДанних о отриманих числах нема."

    if missing:
        msg += "\n\nНе отримали від:\n" + "\n".join(missing)
    else:
        msg += "\n\nВсі прислали числа."

    await update.message.reply_text(msg)


# === Любе повідомлення від користувача → в группу ===
async def forward_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        return

    caption = update.message.caption or update.message.text or ""
    header = f"💬 Повідомлення від @{user.username or user.full_name}:\n"

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
            await context.bot.send_message(GROUP_ID, header + "(Повідомлення без тексту)")

        await update.message.reply_text("✅ Повідомлення відправлено в группу.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Помилка при пересиланні: {e}")


# === Установка команд бота ===
async def set_bot_commands(application):
    user_commands = [BotCommand("balu", "Відправте одне число (2–3 цифри)")]
    admin_commands = [
        BotCommand("balu", "Відправте одне число (2–3 цифри)"),
        BotCommand("contacts", "Показати список контактів"),
        BotCommand("check", "Показати звіт по числам")
    ]

    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())
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
    print("Bot is running...")
    app.run_polling()
