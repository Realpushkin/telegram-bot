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

START_TEXT = """👋 Здравствуйте! Я бот канала MP Connect Pro

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

🛍 Сейчас — БЕСПЛАТНО для первых участников запуска.

⭐️ Если предложение вас заинтересовало, отправьте свою публикацию👇"""

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

async def send_bot_message(chat_id, text, context, reply_markup=None, parse_mode=None):
    """Удаляет старое сообщение бота (кроме стартового) и отправляет новое"""
    old_msg_id = context.user_data.get("last_bot_msg_id")
    if old_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
        except Exception:
            pass
            
    msg = await context.bot.send_message(
        chat_id=chat_id, 
        text=text, 
        reply_markup=reply_markup, 
        parse_mode=parse_mode
    )
    context.user_data["last_bot_msg_id"] = msg.message_id
    return msg

async def delete_system_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет сервисное сообщение о закреплении"""
    try:
        await update.message.delete()
    except Exception:
        pass


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    # Открепляем все старые стартовые сообщения, если пользователь нажал /start снова
    try:
        await context.bot.unpin_all_chat_messages(chat_id=update.effective_chat.id)
    except Exception:
        pass

    msg = await update.message.reply_text(
        START_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

    # Закрепляем стартовое сообщение (оно никогда не удалится из-за логики send_bot_message)
    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id, 
            message_id=msg.message_id, 
            disable_notification=True
        )
    except Exception:
        pass

    return STEP_PHOTO


# ================= USER FLOW =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "create":
        await send_bot_message(chat_id, "🖼️ Отправьте ОДНО изображение для публикации", context)
        return STEP_PHOTO

    if data == "use_my_username":
        username = update.effective_user.username
        if not username:
            await send_bot_message(
                chat_id, 
                "❌ У вас нет username в Telegram.\nНа данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи", 
                context, 
                reply_markup=contact_keyboard()
            )
            return STEP_CONTACT

        context.user_data["contact"] = f"https://t.me/{username}"
        return await show_confirm(chat_id, context)

    if data == "edit":
        # Удаляем предыдущее сообщение с меню
        old_msg_id = context.user_data.get("last_bot_msg_id")
        if old_msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
            except Exception: 
                pass
                
        msg = await context.bot.send_photo(
            chat_id=chat_id,
            photo=context.user_data["photo"],
            caption=context.user_data["text"],
            reply_markup=edit_keyboard()
        )
        context.user_data["last_bot_msg_id"] = msg.message_id
        return CONFIRM

    if data == "cancel_edit":
        return await show_confirm(chat_id, context)

    if data == "edit_photo":
        context.user_data["editing"] = "photo"
        await send_bot_message(chat_id, "🖼️ Отправьте ОДНО изображение для публикации", context)
        return STEP_PHOTO

    if data == "edit_text":
        context.user_data["editing"] = "text"
        await send_bot_message(chat_id, "📝 Отправьте текст публикации", context)
        return STEP_TEXT

    if data == "edit_contact":
        context.user_data["editing"] = "contact"
        await send_bot_message(chat_id, "🔗 Отправьте имя пользователя, по которому заказчик может с Вами связаться", context)
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

        await send_bot_message(chat_id, "🤝 Отправлено на модерацию", context)
        return ConversationHandler.END

    return CONFIRM


# ================= ADMIN HANDLER =================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        post = pending_posts.get(user_id)

        if not post:
            await query.message.reply_text("❌ Публикация не найдена.")
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

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Ваша публикация размещена!"
        )

        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Публикация не прошла модерацию."
        )

        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)


# ================= STEPS =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ОДНО изображение", context)
        return STEP_PHOTO

    # Если отправлено несколько фото (медиагруппа), берем первое, остальные тихо игнорируем
    if update.message.media_group_id:
        if update.message.media_group_id == context.user_data.get("last_media_group_id"):
            return STEP_PHOTO
        context.user_data["last_media_group_id"] = update.message.media_group_id

    # Даже если отправлен текст с фото, мы берем только файл фото ([-1] это макс. разрешение)
    context.user_data["photo"] = update.message.photo[-1].file_id
    context.user_data["user_id"] = update.effective_user.id

    if context.user_data.get("editing") == "photo":
        context.user_data.pop("editing")
        return await show_confirm(update.effective_chat.id, context)

    await send_bot_message(update.effective_chat.id, "📝 Отправьте текст публикации", context)
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем остатки медиагруппы (доп. фото) с предыдущего шага, чтобы не сыпать ошибки
    if update.message.media_group_id and update.message.media_group_id == context.user_data.get("last_media_group_id"):
        return STEP_TEXT

    if update.message.photo:
        if update.message.caption:
            # Прислали фото и текст — берем только текст
            text = update.message.caption
            if update.message.media_group_id:
                context.user_data["text_media_group_id"] = update.message.media_group_id
        else:
            # Прислали просто фото
            if update.message.media_group_id:
                if update.message.media_group_id == context.user_data.get("text_media_group_id"):
                    return STEP_TEXT
                context.user_data["text_media_group_id"] = update.message.media_group_id
            
            await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
            return STEP_TEXT
    elif update.message.text:
        text = update.message.text
    else:
        # Любые другие форматы (файлы, видео и тд)
        await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
        return STEP_TEXT

    if not text:
        await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
        return STEP_TEXT

    context.user_data["text"] = text

    if context.user_data.get("editing") == "text":
        context.user_data.pop("editing")
        return await show_confirm(update.effective_chat.id, context)

    await send_bot_message(
        update.effective_chat.id, 
        "🔗 Отправьте имя пользователя, по которому заказчик может с Вами связаться", 
        context, 
        reply_markup=contact_keyboard()
    )
    return STEP_CONTACT


async def contact_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo or not update.message.text:
        # Игнорируем остатки медиагрупп, чтобы не дублировать ошибку
        if update.message.media_group_id:
            if update.message.media_group_id == context.user_data.get("contact_media_group_id"):
                return STEP_CONTACT
            context.user_data["contact_media_group_id"] = update.message.media_group_id
        
        await send_bot_message(
            update.effective_chat.id, 
            "На данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи", 
            context, 
            reply_markup=contact_keyboard()
        )
        return STEP_CONTACT

    link = format_username(update.message.text)

    if not link:
        await send_bot_message(
            update.effective_chat.id, 
            "На данном шаге загрузите ТОЛЬКО ссылку на Телеграм для связи", 
            context, 
            reply_markup=contact_keyboard()
        )
        return STEP_CONTACT

    context.user_data["contact"] = link

    if context.user_data.get("editing") == "contact":
        context.user_data.pop("editing")
        return await show_confirm(update.effective_chat.id, context)

    return await show_confirm(update.effective_chat.id, context)


async def show_confirm(chat_id, context):
    await send_bot_message(
        chat_id, 
        "✅ Подтвердите отправку:", 
        context, 
        reply_markup=confirm_keyboard()
    )
    return CONFIRM


# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

# Обработчик, который удаляет системное сообщение "Бот закрепил сообщение"
app.add_handler(MessageHandler(filters.StatusUpdate.PINNED_MESSAGE, delete_system_message))

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

# отдельный обработчик для админских кнопок
app.add_handler(CallbackQueryHandler(admin_actions, pattern="^(approve_|reject_)"))

if __name__ == "__main__":
    app.run_polling()
