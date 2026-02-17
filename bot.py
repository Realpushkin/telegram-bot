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
CHANNEL_LINK = "https://t.me/dis_bis"
ADMIN_USERNAME = "@dis_business_ru"

STEP_PHOTO, STEP_TEXT, STEP_CONTACT, CONFIRM = range(4)


# ================= KEYBOARDS =================

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Далее", callback_data="next")],
        [InlineKeyboardButton("Связаться с администратором", url="https://t.me/dis_business_ru")]
    ])


def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Вернуться в начало", callback_data="home")]
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Назад", callback_data="back")],
        [InlineKeyboardButton("Вернуться в начало", callback_data="home")]
    ])


def contact_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Использовать мое имя пользователя", callback_data="use_my_username")],
        [InlineKeyboardButton("Назад", callback_data="back")],
        [InlineKeyboardButton("Вернуться в начало", callback_data="home")]
    ])


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Отправить публикацию", callback_data="send")],
        [InlineKeyboardButton("Редактировать", callback_data="edit")]
    ])


def edit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Изменить фотографию", callback_data="edit_photo")],
        [InlineKeyboardButton("Изменить текст", callback_data="edit_text")],
        [InlineKeyboardButton("Изменить ссылку", callback_data="edit_contact")]
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

Хочу предложить Вам БЕСПЛАТНОЕ размещение рекламы

Вы ищете клиентов.
Селлеры ищут сильных специалистов.

Мы запускаем Telegram-канал MP Connect PRO — площадку, где собираются селлеры, поставщики, дизайнеры и менеджеры маркетплейсов.

📌 Формируем сильную базу специалистов на старте проекта.

Что вы получаете:
✅ Размещение рекламного поста
✅ Выход на аудиторию селлеров
✅ Прямые заказы без посредников
✅ Возможность долгосрочного сотрудничества

🧩 Это старт проекта, поэтому для первых специалистов условия такие:

✔️ 1 публикация — <s>1000 ₽</s>
✔️ Повторная публикация через 14 дней — <s>700 ₽</s>

🛍 Сейчас — <b>БЕСПЛАТНО</b> для первых участников запуска.

⭐️ Если предложение вас заинтересовало, отправьте свою публикацию👇
"""

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_menu_keyboard()
    )

    return STEP_PHOTO


# ================= BUTTON HANDLER =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "home":
        return await start(update, context)

    if data == "next":
        await query.message.reply_text(
            "📷 Шаг 1: Загрузите одну фотографию",
            reply_markup=home_keyboard()
        )
        return STEP_PHOTO

    if data == "back":
        previous = context.user_data.get("previous_step")

        if previous == STEP_PHOTO:
            await query.message.reply_text(
                "📷 Шаг 1: Загрузите одну фотографию",
                reply_markup=home_keyboard()
            )
            return STEP_PHOTO

        if previous == STEP_TEXT:
            await query.message.reply_text(
                "✍️ Шаг 2: Отправьте текст публикации",
                reply_markup=back_keyboard()
            )
            return STEP_TEXT

    if data == "use_my_username":
        username = update.effective_user.username
        if not username:
            await query.message.reply_text("У вас не установлен username в Telegram.")
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

    if data == "edit_photo":
        await query.message.reply_text("Отправьте новую фотографию")
        return STEP_PHOTO

    if data == "edit_text":
        await query.message.reply_text("Отправьте новый текст")
        return STEP_TEXT

    if data == "edit_contact":
        await query.message.reply_text("Отправьте новый username")
        return STEP_CONTACT

    if data == "send":
        user_id = context.user_data["user_id"]

        await context.bot.send_photo(
            chat_id=ADMIN_USERNAME,
            photo=context.user_data["photo"],
            caption=context.user_data["text"],
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Одобрить", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("Отклонить", callback_data=f"reject_{user_id}")
                ]
            ])
        )

        await query.message.reply_text("🤝 Ваша публикация отправлена на модерацию, ожидайте подтверждения")
        return ConversationHandler.END

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])

        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=context.user_data.get("photo"),
            caption=context.user_data.get("text"),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Связаться", url=context.user_data.get("contact")),
                    InlineKeyboardButton("Разместить публикацию", url="https://t.me/dis_business_ru")
                ]
            ])
        )

        await context.bot.send_message(
            chat_id=user_id,
            text='✅ Благодарим за сотрудничество! Ваша публикация размещена в канале <a href="https://t.me/dis_bis">MP Connect Pro</a>. Уже ищем для Вас клиентов 🙃',
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    if data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Ваша публикация не прошла модерацию, пожалуйста отправьте снова"
        )

    return ConversationHandler.END


# ================= STEPS =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("На этом шаге загрузите одну фотографию")
        return STEP_PHOTO

    context.user_data["photo"] = update.message.photo[-1].file_id
    context.user_data["previous_step"] = STEP_PHOTO
    context.user_data["user_id"] = update.effective_user.id

    await update.message.reply_text(
        "✍️ Шаг 2: Отправьте текст публикации",
        reply_markup=back_keyboard()
    )
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("На этом шаге отправьте текст публикации")
        return STEP_TEXT

    context.user_data["text"] = update.message.text
    context.user_data["previous_step"] = STEP_TEXT

    await update.message.reply_text(
        "🔗 Шаг 3: Отправьте username Telegram",
        reply_markup=contact_keyboard()
    )
    return STEP_CONTACT


async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = format_username(update.message.text)

    if not link:
        await update.message.reply_text(
            "Прошу прощения, не могу найти данный контакт в Телеграм, отправьте имя пользователя в формате ссылки или @username"
        )
        return STEP_CONTACT

    context.user_data["contact"] = link
    return await show_confirm(update.message, context)


async def show_confirm(message, context):
    await message.reply_text(
        "✅ Готово, подтвердите, чтобы отправить рекламу на модерацию",
        reply_markup=confirm_keyboard()
    )
    return CONFIRM


# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STEP_PHOTO: [
            MessageHandler(filters.ALL, photo_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_TEXT: [
            MessageHandler(filters.ALL, text_step),
            CallbackQueryHandler(buttons),
        ],
        STEP_CONTACT: [
            MessageHandler(filters.ALL, contact_step),
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
