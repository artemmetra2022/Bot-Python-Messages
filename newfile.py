import logging
from uuid import uuid4
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import threading
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_messages = {}
temp_messages = {}
message_reactions = {}
user_notifications = {}

def print_status():
    while True:
        print("Бот работает")
        time.sleep(300)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    unique_link = f"https://t.me/{context.bot.username}?start={uuid4()}"
    user_messages[user_id] = {"link": unique_link, "messages": []}
    user_notifications[user_id] = True
    await update.message.reply_text(
        f"👋 Привет! Вот твоя уникальная ссылка:\n\n{unique_link}\n\n"
        "Поделись ей, чтобы получать анонимные сообщения. 😊\n\n"
        "Используй команду /help, чтобы узнать больше."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📜 Список команд:\n\n"
        "/start - Получить уникальную ссылку.\n"
        "/help - Показать это сообщение.\n"
        "/my_messages - Просмотреть все анонимные сообщения.\n"
        "/clear - Удалить все сообщения.\n"
        "/stats - Показать статистику по сообщениям.\n"
        "/notify on - Включить уведомления.\n"
        "/notify off - Выключить уведомления."
    )
    await update.message.reply_text(help_text)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = int(context.args[0]) if context.args else None
    if user_id and user_id in user_messages:
        temp_messages[update.message.from_user.id] = {"target_user_id": user_id}
        keyboard = [
            [InlineKeyboardButton("1 час", callback_data="1h")],
            [InlineKeyboardButton("2 часа", callback_data="2h")],
            [InlineKeyboardButton("5 часов", callback_data="5h")],
            [InlineKeyboardButton("12 часов", callback_data="12h")],
            [InlineKeyboardButton("24 часа", callback_data="24h")],
            [InlineKeyboardButton("Бессрочно", callback_data="forever")],
            [InlineKeyboardButton("Отменить", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✍️ Введите ваше сообщение. Человек получит его в анонимном виде.\n\n"
            "Поддерживаемые типы сообщений: Текст, голосовые, фото, видео, документы, стикеры, аудио.\n\n"
            "Выберите время удаления сообщения:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Ошибка: неверная ссылка.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in temp_messages:
        return

    target_user_id = temp_messages[user_id]["target_user_id"]

    if update.message.text:
        message = {"type": "text", "content": update.message.text}
    elif update.message.voice:
        message = {"type": "voice", "content": update.message.voice.file_id}
    elif update.message.photo:
        message = {"type": "photo", "content": update.message.photo[-1].file_id}
    elif update.message.video:
        message = {"type": "video", "content": update.message.video.file_id}
    elif update.message.document:
        message = {"type": "document", "content": update.message.document.file_id}
    elif update.message.sticker:
        message = {"type": "sticker", "content": update.message.sticker.file_id}
    elif update.message.audio:
        message = {"type": "audio", "content": update.message.audio.file_id}
    else:
        await update.message.reply_text("❌ Ошибка: неподдерживаемый тип сообщения.")
        return

    temp_messages[user_id]["message"] = message
    await update.message.reply_text(
        "✅ Ваше сообщение готово к отправке. Выберите время удаления:"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "cancel":
        del temp_messages[user_id]
        await query.edit_message_text("❌ Отправка сообщения отменена.")
        return

    if user_id not in temp_messages:
        return

    target_user_id = temp_messages[user_id]["target_user_id"]
    message = temp_messages[user_id]["message"]

    if data in ["1h", "2h", "5h", "12h", "24h"]:
        hours = int(data[:-1])
        delete_time = datetime.now() + timedelta(hours=hours)
        message["delete_time"] = delete_time
        user_messages[target_user_id]["messages"].append(message)
        await query.edit_message_text(f"✅ Сообщение отправлено и будет удалено через {hours} час(ов).")
        if user_notifications.get(target_user_id, False):
            await context.bot.send_message(target_user_id, "🔔 У вас новое анонимное сообщение!")
    elif data == "forever":
        user_messages[target_user_id]["messages"].append(message)
        await query.edit_message_text("✅ Сообщение отправлено и будет храниться бессрочно.")
        if user_notifications.get(target_user_id, False):
            await context.bot.send_message(target_user_id, "🔔 У вас новое анонимное сообщение!")
    del temp_messages[user_id]

async def my_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_messages or not user_messages[user_id]["messages"]:
        await update.message.reply_text("📭 У вас пока нет сообщений.")
        return

    messages = user_messages[user_id]["messages"]
    for msg in messages:
        if msg["type"] == "text":
            await update.message.reply_text(f"✉️ Анонимное сообщение:\n{msg['content']}")
        elif msg["type"] == "voice":
            await update.message.reply_voice(msg["content"])
        elif msg["type"] == "photo":
            await update.message.reply_photo(msg["content"])
        elif msg["type"] == "video":
            await update.message.reply_video(msg["content"])
        elif msg["type"] == "document":
            await update.message.reply_document(msg["content"])
        elif msg["type"] == "sticker":
            await update.message.reply_sticker(msg["content"])
        elif msg["type"] == "audio":
            await update.message.reply_audio(msg["content"])

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in user_messages:
        user_messages[user_id]["messages"] = []
        await update.message.reply_text("🗑 Все сообщения удалены.")
    else:
        await update.message.reply_text("❌ У вас нет сообщений для удаления.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in user_messages:
        count = len(user_messages[user_id]["messages"])
        await update.message.reply_text(f"📊 Количество полученных сообщений: {count}")
    else:
        await update.message.reply_text("❌ У вас пока нет сообщений.")

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    args = context.args
    if args and args[0].lower() == "on":
        user_notifications[user_id] = True
        await update.message.reply_text("🔔 Уведомления включены.")
    elif args and args[0].lower() == "off":
        user_notifications[user_id] = False
        await update.message.reply_text("🔕 Уведомления выключены.")
    else:
        await update.message.reply_text("❌ Используйте /notify on или /notify off.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Ошибка в обработчике: {context.error}")

def main() -> None:
    print("Бот запущен")
    status_thread = threading.Thread(target=print_status)
    status_thread.daemon = True
    status_thread.start()

    application = Application.builder().token("7412234165:AAFDs9rgHnXpFW6hT5R0B5uyZSxaRGrELLE").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_messages", my_messages))
    application.add_handler(CommandHandler("clear", clear_messages))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("notify", notify_command))
    application.add_handler(CommandHandler("start", handle_link))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_message))
    application.add_handler(MessageHandler(filters.AUDIO, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    application.run_polling()

if __name__ == '__main__':
    main()