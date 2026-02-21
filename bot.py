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


# ================= HELPERS =================

async def send_and_replace(update: Update, context: ContextTypes.DEFAULT_TYPE, text=None, photo=None, reply_markup=None, pin=False):
    chat_id = update.effective_chat.id

    # удаляем старое сообщение бота (кроме закрепленного первого)
    last_bot_message_id = context.user_data.get("last_bot_message_id")
    pinned_message_id = context.user_data.get("pinned_message_id")

    if last_bot_message_id and last_bot_message_id != pinned_message_id:
        try:
            await context.bot.delete_message(chat_id, last_bot_message_id)
        except:
            pass

    if photo:
        msg = await context.bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=reply_markup)
    else:
        msg = await context.bot.send_message(chat_id, text=text, reply_markup=reply_markup)

    context.user_data["last_bot_message_id"] = msg.message_id

    if pin:
        try:
            await msg.pin(disable_notification=True)
            context.user_data["pinned_message_id"] = msg.message_id
        except:
            pass

    return msg


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


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    first_message = (
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

    msg = await update.message.reply_text(
        first_message,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )

    await msg.pin(disable_notification=True)
    context.user_data["pinned_message_id"] = msg.message_id
    context.user_data["last_bot_message_id"] = msg.message_id

    return STEP_PHOTO


# ================= USER FLOW =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "create":
        await send_and_replace(update, context, "🖼️ Отправьте ОДНО изображение для публикации")
        return STEP_PHOTO

    return CONFIRM


# ================= STEPS =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.photo:
        await send_and_replace(update, context, "❌ На данном шаге загрузите ОДНО изображение")
        return STEP_PHOTO

    # берём только первое фото
    context.user_data["photo"] = update.message.photo[0].file_id
    context.user_data["user_id"] = update.effective_user.id

    await send_and_replace(update, context, "📝 Отправьте текст публикации")
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        await send_and_replace(update, context, "❌ На данном шаге загрузите ТОЛЬКО текст публикации")
        return STEP_TEXT

    if not update.message.text:
        await send_and_replace(update, context, "❌ На данном шаге загрузите ТОЛЬКО текст публикации")
        return STEP_TEXT

    context.user_data["text"] = update.message.text

    await send_and_replace(update, context, "🔗 Отправьте имя пользователя, по которому заказчик может с Вами связаться")
    return STEP_CONTACT


async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.photo:
        await send_and_replace(update, context, "❌ На данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи")
        return STEP_CONTACT

    if not update.message.text:
        await send_and_replace(update, context, "❌ На данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи")
        return STEP_CONTACT

    link = format_username(update.message.text)

    if not link:
        await send_and_replace(update, context, "❌ Неверная ссылка или username.")
        return STEP_CONTACT

    context.user_data["contact"] = link

    await send_and_replace(
        update,
        context,
        "✅ Подтвердите отправку:",
        reply_markup=confirm_keyboard()
    )

    return CONFIRM


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
        ],
        STEP_CONTACT: [
            MessageHandler(filters.ALL & ~filters.COMMAND, contact_step),
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
