import os
import re
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_USERNAME = "@dis_bis"  # можно оставить username канала
ADMIN_ID = 8417362954  # твой реальный user_id

STEP_PHOTO, STEP_TEXT, STEP_CONTACT, CONFIRM = range(4)

pending_posts = {}


# ================= KEYBOARDS =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Создать публикацию", callback_data="create")],
        [InlineKeyboardButton("📩 Связаться с администратором", url="https://t.me/dis_business_ru")]
    ])


def contact_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Использовать мое имя пользователя", callback_data="use_my_username")]
    ])


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Отправить публикацию", callback_data="send")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")]
    ])


def edit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Изменить фотографию", callback_data="edit_photo")],
        [InlineKeyboardButton("📝 Изменить текст", callback_data="edit_text")],
        [InlineKeyboardButton("🔗 Изменить ссылку", callback_data="edit_contact")],
        [InlineKeyboardButton("✅ Не изменять", callback_data="cancel_edit")]
    ])


# ================= HELPERS =================

def format_username(text: str):
    text = text.strip()

    if "t.me/" in text:
        username = text.split("t.me/")[-1].replace("/", "").strip()
    elif text.startswith("@"):
        username = text[1:]
    else:
        username = text

    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        return f"https://t.me/{username}"

    return None


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    text = """
👋 Здравствуйте! Я бот канала <a href="https://t.me/dis_bis">MP Connect Pro</a>

🛍 Сейчас размещение <b>БЕСПЛАТНО</b>

Нажмите кнопку ниже, чтобы создать публикацию 👇
"""

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard()
    )

    return STEP_PHOTO


# ================= BUTTONS =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "create":
        await query.message.reply_text("📷 Загрузите одну фотографию")
        return STEP_PHOTO

    if data == "use_my_username":
        username = update.effective_user.username
        if not username:
            await query.message.reply_text("❌ У вас не установлен username в Telegram.")
            return STEP_CONTACT

        context.user_data["contact"] = f"https://t.me/{username}"
        return await show_confirm(query.message, context)

    if data == "edit":
        await query.message.reply_photo(
            photo=context.user_data["photo"],
            caption=context.user_data["text"],
            reply_markup=edit_keyboard()
        )
        return CONFIRM

    if data == "cancel_edit":
        return await show_confirm(query.message, context)

    if data == "edit_photo":
        context.user_data["editing"] = "photo"
        await query.message.reply_text("🖼 Отправьте новую фотографию")
        return STEP_PHOTO

    if data == "edit_text":
        context.user_data["editing"] = "text"
        await query.message.reply_text("📝 Отправьте новый текст")
        return STEP_TEXT

    if data == "edit_contact":
        context.user_data["editing"] = "contact"
        await query.message.reply_text("🔗 Отправьте новый username")
        return STEP_CONTACT

    if data == "send":
        user_id = context.user_data["user_id"]

        pending_posts[user_id] = {
            "photo": context.user_data["photo"],
            "text": context.user_data["text"],
            "contact": context.user_data["contact"],
        }

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=context.user_data["photo"],
            caption=context.user_data["text"],
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
                ]
            ])
        )

        await query.message.reply_text("🤝 Публикация отправлена на модерацию")
        return ConversationHandler.END

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        post = pending_posts.get(user_id)

        if not post:
            await query.message.reply_text("❌ Данные публикации не найдены.")
            return ConversationHandler.END

        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=post["photo"],
            caption=post["text"],
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📩 Связаться", url=post["contact"]),
                    InlineKeyboardButton("🚀 Разместить публикацию", url="https://t.me/dis_business_ru")
                ]
            ])
        )

        await context.bot.send_message(
            chat_id=user_id,
            text='✅ Ваша публикация размещена 🙃',
            parse_mode="HTML"
        )

        pending_posts.pop(user_id, None)

    if data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        pending_posts.pop(user_id, None)

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Публикация не прошла модерацию, отправьте заново"
        )

    return ConversationHandler.END


# ================= STEPS =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❗ Пожалуйста, загрузите фотографию")
        return STEP_PHOTO

    context.user_data["photo"] = update.message.photo[-1].file_id
    context.user_data["user_id"] = update.effective_user.id

    if context.user_data.get("editing") == "photo":
        context.user_data.pop("editing")
        return await show_confirm(update.message, context)

    await update.message.reply_text("📝 Отправьте текст публикации")
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("❗ Пожалуйста, отправьте текст")
        return STEP_TEXT

    context.user_data["text"] = update.message.text

    if context.user_data.get("editing") == "text":
        context.user_data.pop("editing")
        return await show_confirm(update.message, context)

    await update.message.reply_text("🔗 Отправьте username Telegram", reply_markup=contact_keyboard())
    return STEP_CONTACT


async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = format_username(update.message.text)

    if not link:
        await update.message.reply_text("❌ Отправьте username в формате @username или ссылкой")
        return STEP_CONTACT

    context.user_data["contact"] = link

    if context.user_data.get("editing") == "contact":
        context.user_data.pop("editing")
        return await show_confirm(update.message, context)

    return await show_confirm(update.message, context)


async def show_confirm(message, context):
    await message.reply_text(
        "✅ Готово. Подтвердите отправку:",
        reply_markup=confirm_keyboard()
    )
    return CONFIRM


# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STEP_PHOTO: [
            MessageHandler(filters.PHOTO, photo_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, text_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_CONTACT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, contact_step),
            CallbackQueryHandler(buttons),
        ],
        CONFIRM: [
            CallbackQueryHandler(buttons)
        ],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(conv)

if __name__ == "__main__":
    app.run_polling()
