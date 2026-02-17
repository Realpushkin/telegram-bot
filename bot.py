import logging
import re
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_LINK = "https://t.me/dis_bis"
CHANNEL_NAME = "MP Connect Pro"
ADMIN_ID = 123456789  # <-- ВСТАВЬ СВОЙ ID

PHOTO, TEXT, CONTACT, CONFIRM = range(4)

logging.basicConfig(level=logging.INFO)


# ======== START ========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Далее", callback_data="next")],
        [InlineKeyboardButton("Связаться с администратором", url="https://t.me/dis_business_ru")]
    ]
    text = f"""
👋 Здравствуйте! Я бот канала {CHANNEL_NAME}
{CHANNEL_LINK}

Хочу предложить Вам БЕСПЛАТНОЕ размещение рекламы

Вы ищете клиентов.
Селлеры ищут сильных специалистов.

Мы запускаем Telegram-канал MP Connect PRO — площадку, где собираются селлеры, поставщики, дизайнеры, фулфилмент-компании и менеджеры маркетплейсов, и мы сводим их напрямую.

📌 Формируем сильную базу специалистов на старте проекта.

Что вы получаете:
✅ Размещение рекламного поста
✅ Выход на аудиторию селлеров
✅ Прямые заказы
✅ Возможность долгосрочного сотрудничества

🛍 Сейчас - БЕСПЛАТНО для первых участников запуска.

⭐️ Если предложение вас заинтересовало, отправьте свою публикацию👇
"""
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# ======== STEP 1 PHOTO ========

async def step_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Вернуться в начало", callback_data="start")]]
    await update.callback_query.message.reply_text(
        "📷 На этом шаге загрузите ОДНУ фотографию.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHOTO


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠ На этом шаге загрузите фотографию.")
        return PHOTO

    context.user_data["photo"] = update.message.photo[-1].file_id

    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back_photo")],
        [InlineKeyboardButton("Вернуться в начало", callback_data="start")]
    ]
    await update.message.reply_text(
        "✏ Теперь отправьте текст публикации.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TEXT


# ======== STEP 2 TEXT ========

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⚠ На этом шаге отправьте текст публикации.")
        return TEXT

    context.user_data["text"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("Использовать мое имя пользователя", callback_data="use_my_username")],
        [InlineKeyboardButton("Назад", callback_data="back_text")],
        [InlineKeyboardButton("Вернуться в начало", callback_data="start")]
    ]

    await update.message.reply_text(
        "🔗 Отправьте имя пользователя Telegram (@username или ссылку).",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONTACT


# ======== STEP 3 CONTACT ========

def extract_username(text):
    if text.startswith("@"):
        return text[1:]
    if "t.me/" in text:
        return text.split("t.me/")[1].split("?")[0]
    return text.strip()


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⚠ Отправьте имя пользователя Telegram.")
        return CONTACT

    username = extract_username(update.message.text)

    try:
        chat = await context.bot.get_chat(username)
        if not chat.username:
            raise Exception("Нет username")
    except:
        await update.message.reply_text(
            "❌ Прошу прощения, не могу найти данный контакт в Телеграм.\n"
            "Отправьте имя пользователя в формате ссылки или @username"
        )
        return CONTACT

    context.user_data["contact"] = f"https://t.me/{username}"

    return await show_confirm(update, context)


# ======== CONFIRM SCREEN ========

async def show_confirm(update, context):
    keyboard = [
        [InlineKeyboardButton("Отправить публикацию", callback_data="send")],
        [InlineKeyboardButton("Редактировать", callback_data="edit")]
    ]
    await update.message.reply_text(
        "✅ Готово, подтвердите, чтобы отправить рекламу на модерацию",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM


# ======== SEND TO ADMIN ========

async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user
    data = context.user_data

    keyboard = [
        [
            InlineKeyboardButton("Одобрить", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_{user.id}")
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        data["photo"],
        caption=data["text"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.callback_query.message.reply_text(
        "🤝 Ваша публикация отправлена на модерацию, ожидайте подтверждения"
    )

    return ConversationHandler.END


# ======== ADMIN ACTION ========

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if action == "approve":
        data = context.user_data
        await context.bot.send_photo(
            chat_id="@dis_bis",
            photo=data["photo"],
            caption=data["text"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Связаться", url=data["contact"])],
                [InlineKeyboardButton("Разместить публикацию", url="https://t.me/ТВОЙ_БОТ")]
            ])
        )
        await context.bot.send_message(
            user_id,
            f"✅ Благодарим за сотрудничество.\n"
            f"Ваша публикация размещена в канале {CHANNEL_NAME}.\n{CHANNEL_LINK}\n"
            "Уже ищем для Вас клиентов 🙃"
        )

    else:
        await context.bot.send_message(
            user_id,
            "❌ Ваша публикация не прошла модерацию, пожалуйста отправьте снова"
        )

    await query.answer()


# ======== MAIN ========

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(step_photo, pattern="next")],
    states={
        PHOTO: [MessageHandler(filters.ALL, receive_photo)],
        TEXT: [MessageHandler(filters.ALL, receive_text)],
        CONTACT: [MessageHandler(filters.ALL, receive_contact)],
        CONFIRM: [CallbackQueryHandler(send_to_admin, pattern="send")]
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(admin_decision, pattern="approve_|reject_"))

app.run_polling()
