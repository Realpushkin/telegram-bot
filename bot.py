import asyncio
import os
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@dis_bis"
ADMIN_ID = 8417362954
BOT_USERNAME = "Kanal_mp_bot"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# временное хранилище постов
pending_posts = {}


# ================= START =================

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("📸 Отправьте одну фотографию.")


@dp.message(F.photo)
async def get_photo(message: Message):
    photo_id = message.photo[-1].file_id
    pending_posts[message.from_user.id] = {
        "photo": photo_id
    }
    await message.answer("✍ Теперь отправьте текст публикации.")


@dp.message(F.text)
async def get_text(message: Message):
    user_id = message.from_user.id

    if user_id not in pending_posts:
        return

    if "text" not in pending_posts[user_id]:
        pending_posts[user_id]["text"] = message.text
        await message.answer("📩 Теперь отправьте контакт (@username или ссылку).")
        return

    # если это контакт
    contact_link = format_contact(message.text)
    pending_posts[user_id]["contact"] = contact_link

    post_data = pending_posts[user_id]

    keyboard_admin = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{user_id}"
                )
            ]
        ]
    )

    await bot.send_photo(
        ADMIN_ID,
        photo=post_data["photo"],
        caption=post_data["text"],
        reply_markup=keyboard_admin
    )

    await message.answer("✅ Публикация отправлена на модерацию.")


# ================= CONTACT FORMAT =================

def format_contact(text: str):
    text = text.strip()

    if "t.me/" in text:
        username = text.split("t.me/")[-1]
    else:
        username = text.replace("@", "")

    username = re.sub(r"[^a-zA-Z0-9_]", "", username)
    return f"https://t.me/{username}"


# ================= APPROVE =================

@dp.callback_query(F.data.startswith("approve_"))
async def approve_post(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    if user_id not in pending_posts:
        await callback.answer("Данные не найдены")
        return

    post_data = pending_posts[user_id]

    keyboard_channel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Связаться",
                    url=post_data["contact"]
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Разместить публикацию",
                    url=f"https://t.me/{BOT_USERNAME}"
                )
            ]
        ]
    )

    await bot.send_photo(
        CHANNEL_ID,
        photo=post_data["photo"],
        caption=post_data["text"],
        reply_markup=keyboard_channel
    )

    await callback.message.edit_caption(
        caption=post_data["text"] + "\n\n✅ Опубликовано"
    )

    del pending_posts[user_id]
    await callback.answer("Опубликовано!")


# ================= REJECT =================

@dp.callback_query(F.data.startswith("reject_"))
async def reject_post(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    if user_id in pending_posts:
        del pending_posts[user_id]

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ Отклонено"
    )

    await callback.answer("Отклонено.")


# ================= RUN =================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
