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

CHANNEL_USERNAME = "@dis_bis"
ADMIN_ID = 8417362954

STEP_PHOTO, STEP_TEXT, STEP_CONTACT, CONFIRM = range(4)

pending_posts = {}


# ================= KEYBOARDS =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 СОЗДАТЬ ПУБЛИКАЦИЮ", callback_data="create")],
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

async def send_and_replace(message, text=None, photo=None, reply_markup=None, parse_mode=None):
    chat_id = message.chat_id
    last_id = message.bot_data.get(f"last_msg_{chat_id}")

    if last_id:
        try:
            await message.bot.delete_message(chat_id, last_id)
        except:
            pass

    if photo:
        sent = await message.bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        sent = await message.bot.send_message(chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)

    message.bot_data[f"last_msg_{chat_id}"] = sent.message_id
    return sent


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

    first_text = (
        "👋 Здравствуйте! Я бот канала MP Connect Pro\n\n"
        "Хочу предложить Вам БЕСПЛАТНОЕ размещение рекламы\n\n"
        "Вы ищете клиентов.\n"
        "Селлеры ищут сильных специалистов.\n\n"
        "Мы запускаем Telegram-канал MP Connect PRO — площадку, где собираются селлеры, поставщики, дизайнеры и менеджеры маркетплейсов.\n\n"
        "📌 Формируем сильную базу специалистов на старте проекта.\n\n"
        "Что вы получаете:\n"
        "✅ Размещение рекламного поста\n"
        "✅ Выход на аудиторию селлеров\n"
        "✅ Прямые заказы без посредников\n"
        "✅ Возможность долгосрочного сотрудничества\n\n"
        "🧩 Это старт проекта, поэтому для первых специалистов условия такие:\n\n"
        "✔️ 1 публикация — <s>1000 ₽</s>\n"
        "✔️ Повторная публикация через 14 дней — <s>700 ₽</s>\n\n"
        "🛍 Сейчас — БЕСПЛАТНО для первых участников запуска.\n\n"
        "⭐️ Если предложение вас заинтересовало, отправьте свою публикацию👇"
    )

    sent = await update.message.reply_text(
        first_text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

    try:
        await sent.pin(disable_notification=True)
    except:
        pass

    return STEP_PHOTO


# ================= BUTTONS =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "create":
        await send_and_replace(query.message, "🖼️ Отправьте ОДНО изображение для публикации")
        return STEP_PHOTO

    if data == "use_my_username":
        username = update.effective_user.username
        if not username:
            await send_and_replace(query.message, "❌ У вас нет username в Telegram.")
            return STEP_CONTACT

        context.user_data["contact"] = f"https://t.me/{username}"
        return await show_confirm(query.message, context)

    if data == "edit":
        await send_and_replace(
            query.message,
            text=context.user_data["text"],
            photo=context.user_data["photo"],
            reply_markup=edit_keyboard()
        )
        return CONFIRM

    if data == "cancel_edit":
        return await show_confirm(query.message, context)

    if data == "edit_photo":
        context.user_data["editing"] = "photo"
        await send_and_replace(query.message, "🖼️ Отправьте ОДНО изображение для публикации")
        return STEP_PHOTO

    if data == "edit_text":
        context.user_data["editing"] = "text"
        await send_and_replace(query.message, "📝 Отправьте текст публикации")
        return STEP_TEXT

    if data == "edit_contact":
        context.user_data["editing"] = "contact"
        await send_and_replace(query.message, "🔗 Отправьте имя пользователя, по которому заказчик может с Вами связаться")
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

        await send_and_replace(query.message, "🤝 Отправлено на модерацию")
        return ConversationHandler.END

    return CONFIRM


# ================= STEPS =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.photo:
        await send_and_replace(update.message, "❌ На данном шаге загрузите ОДНО изображение")
        return STEP_PHOTO

    context.user_data["photo"] = update.message.photo[0].file_id
    context.user_data["user_id"] = update.effective_user.id

    if context.user_data.get("editing") == "photo":
        context.user_data.pop("editing")
        return await show_confirm(update.message, context)

    await send_and_replace(update.message, "📝 Отправьте текст публикации")
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        await send_and_replace(update.message, "❌ На данном шаге загрузите ТОЛЬКО текст публикации")
        return STEP_TEXT

    context.user_data["text"] = update.message.text

    if context.user_data.get("editing") == "text":
        context.user_data.pop("editing")
        return await show_confirm(update.message, context)

    await send_and_replace(
        update.message,
        "🔗 Отправьте имя пользователя, по которому заказчик может с Вами связаться",
        reply_markup=contact_keyboard()
    )
    return STEP_CONTACT


async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        await send_and_replace(update.message, "❌ На данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи")
        return STEP_CONTACT

    link = format_username(update.message.text)

    if not link:
        await send_and_replace(update.message, "❌ Неверный username.")
        return STEP_CONTACT

    context.user_data["contact"] = link

    if context.user_data.get("editing") == "contact":
        context.user_data.pop("editing")

    return await show_confirm(update.message, context)


async def show_confirm(message, context):
    await send_and_replace(
        message,
        "✅ Подтвердите отправку:",
        reply_markup=confirm_keyboard()
    )
    return CONFIRM


# ================= ADMIN =================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        post = pending_posts.get(user_id)

        if not post:
            return

        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=post["photo"],
            caption=post["text"],
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📩 Связаться", url=post["contact"]),
                    InlineKeyboardButton("🚀 Разместить рекламу", url="https://t.me/dis_business_ru")
                ]
            ])
        )

        await context.bot.send_message(user_id, "✅ Ваша публикация размещена!")
        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])
        await context.bot.send_message(user_id, "❌ Публикация не прошла модерацию.")
        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)


# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STEP_PHOTO: [
            MessageHandler(filters.ALL & ~filters.COMMAND, photo_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_TEXT: [
            MessageHandler(filters.ALL & ~filters.COMMAND, text_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_CONTACT: [
            MessageHandler(filters.ALL & ~filters.COMMAND, contact_step),
            CallbackQueryHandler(buttons),
        ],
        CONFIRM: [
            CallbackQueryHandler(buttons)
        ],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(conv)
app.add_handler(CallbackQueryHandler(admin_actions, pattern="^(approve_|reject_)"))

if __name__ == "__main__":
    app.run_polling()
