import os
import re
import logging
from datetime import datetime, timedelta
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
    PicklePersistence
)
from telegram.error import BadRequest

# ================= ЛОГИРОВАНИЕ =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@dis_bis"
ADMIN_ID = 8417362954
BOT_LINK = "https://t.me/Kanal_mp_bot" # Жестко заданная ссылка на вашего бота

STEP_PHOTO, STEP_TEXT, STEP_CONTACT, CONFIRM = range(4)

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

# ================= КЛАВИАТУРЫ =================

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

# ================= ХЕЛПЕРЫ =================

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

def check_cooldown(user_id, context):
    """Проверяет, прошло ли 7 дней с момента последней публикации (данные берутся из БД)"""
    last_published_time = context.bot_data.setdefault("last_published_time", {})
    if user_id in last_published_time:
        time_since = datetime.now() - last_published_time[user_id]
        if time_since < timedelta(days=7):
            time_left = timedelta(days=7) - time_since
            days = time_left.days
            hours = time_left.seconds // 3600
            return f"⏳ Вы уже публиковали пост. Следующая публикация будет доступна через {days} дн. {hours} ч."
    return None

async def send_bot_message(chat_id, text, context, reply_markup=None, parse_mode=None):
    """Удаляет старое сообщение бота (кроме стартового) и отправляет новое"""
    old_msg_id = context.user_data.get("last_bot_msg_id")
    if old_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
        except BadRequest:
            pass # Сообщение уже удалено, игнорируем
            
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
    except BadRequest:
        pass


# ================= СТАРТ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    try:
        await context.bot.unpin_all_chat_messages(chat_id=update.effective_chat.id)
    except BadRequest:
        pass

    msg = await update.message.reply_text(
        START_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id, 
            message_id=msg.message_id, 
            disable_notification=True
        )
    except BadRequest:
        pass

    return STEP_PHOTO


# ================= ЛОГИКА ПОЛЬЗОВАТЕЛЯ =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    user_id = update.effective_user.id

    if data == "create":
        cooldown_msg = check_cooldown(user_id, context)
        if cooldown_msg:
            await send_bot_message(chat_id, cooldown_msg, context)
            return ConversationHandler.END

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
        old_msg_id = context.user_data.get("last_bot_msg_id")
        if old_msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=old_msg_id)
            except BadRequest: 
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
        await send_bot_message(chat_id, "🖼️ Шаг 1: Отправьте ОДНО изображение для публикации", context)
        return STEP_PHOTO

    if data == "edit_text":
        context.user_data["editing"] = "text"
        await send_bot_message(chat_id, "📝 Шаг 2: Отправьте текст публикации", context)
        return STEP_TEXT

    if data == "edit_contact":
        context.user_data["editing"] = "contact"
        await send_bot_message(chat_id, "🔗 Шаг 3: Отправьте имя пользователя, по которому заказчик может с Вами связаться", context)
        return STEP_CONTACT

    if data == "send":
        # Сохраняем публикацию в постоянное хранилище
        pending_posts = context.bot_data.setdefault("pending_posts", {})
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


# ================= ПАНЕЛЬ АДМИНА =================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # ЗАЩИТА: Проверяем, что кнопку нажал именно админ
    if update.effective_user.id != ADMIN_ID:
        await query.answer("⛔ У вас нет прав на это действие.", show_alert=True)
        return

    await query.answer()
    data = query.data

    pending_posts = context.bot_data.setdefault("pending_posts", {})
    last_published_time = context.bot_data.setdefault("last_published_time", {})

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
                    InlineKeyboardButton("Связаться", url=post["contact"]),
                    InlineKeyboardButton("Разместить рекламу", url=BOT_LINK)
                ]
            ])
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Ваша публикация размещена!"
        )

        # Фиксируем время успешной публикации и сохраняем
        last_published_time[user_id] = datetime.now()
        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Публикация не прошла модерацию. Вы можете отправить новую прямо сейчас."
        )

        pending_posts.pop(user_id, None)
        await query.message.edit_reply_markup(reply_markup=None)


# ================= ШАГИ СБОРА ДАННЫХ =================

async def photo_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    cooldown_msg = check_cooldown(user_id, context)
    if cooldown_msg:
        await send_bot_message(chat_id, cooldown_msg, context)
        return ConversationHandler.END

    if not update.message.photo:
        await send_bot_message(chat_id, "На данном шаге загрузите ОДНО изображение", context)
        return STEP_PHOTO

    if update.message.media_group_id:
        if update.message.media_group_id == context.user_data.get("last_media_group_id"):
            return STEP_PHOTO
        context.user_data["last_media_group_id"] = update.message.media_group_id

    context.user_data["photo"] = update.message.photo[-1].file_id
    context.user_data["user_id"] = user_id

    if context.user_data.get("editing") == "photo":
        context.user_data.pop("editing")
        return await show_confirm(chat_id, context)

    await send_bot_message(chat_id, "📝 Отправьте текст публикации", context)
    return STEP_TEXT


async def text_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.media_group_id and update.message.media_group_id == context.user_data.get("last_media_group_id"):
        return STEP_TEXT

    if update.message.photo:
        if update.message.caption:
            text = update.message.caption
            if update.message.media_group_id:
                context.user_data["text_media_group_id"] = update.message.media_group_id
        else:
            if update.message.media_group_id:
                if update.message.media_group_id == context.user_data.get("text_media_group_id"):
                    return STEP_TEXT
                context.user_data["text_media_group_id"] = update.message.media_group_id
            
            await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
            return STEP_TEXT
    elif update.message.text:
        text = update.message.text
    else:
        await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
        return STEP_TEXT

    if not text:
        await send_bot_message(update.effective_chat.id, "На данном шаге загрузите ТОЛЬКО текст публикации", context)
        return STEP_TEXT

    # ЗАЩИТА: Проверка лимита символов в Telegram (1024 для подписи к фото)
    if len(text) > 1024:
        await send_bot_message(
            update.effective_chat.id, 
            f"❌ Текст слишком длинный ({len(text)} из 1024 символов).\nПожалуйста, сократите его и отправьте заново.", 
            context
        )
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


# ================= ЗАПУСК =================

# Инициализируем хранилище данных в файл bot_data.pickle
persistence = PicklePersistence(filepath="bot_data.pickle")
app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()

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
    persistent=True, # Включаем сохранение состояний между перезапусками
    name="post_conversation"
)

app.add_handler(conv)
app.add_handler(CallbackQueryHandler(admin_actions, pattern="^(approve_|reject_)"))

if __name__ == "__main__":
    app.run_polling()
