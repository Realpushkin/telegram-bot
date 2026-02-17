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
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@dis_bis"
ADMIN_ID = 8417362954  # твой Telegram ID
BOT_USERNAME = "Kanal_mp_bot"  # username бота без @


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class PostCreation(StatesGroup):
    waiting_photo = State()
    waiting_text = State()
    waiting_contact = State()


@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.set_state(PostCreation.waiting_photo)
    await message.answer("📸 Шаг 1: Отправьте одну фотографию.")


@dp.message(PostCreation.waiting_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(PostCreation.waiting_text)
    await message.answer("✍ Шаг 2: Отправьте текст публикации.")


@dp.message(PostCreation.waiting_text, F.text)
async def get_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(PostCreation.waiting_contact)
    await message.answer("📩 Шаг 3: Отправьте контакт (@username или ссылку).")


def format_contact(text: str):
    text = text.strip()

    if "t.me/" in text:
        username = text.split("t.me/")[-1]
    else:
        username = text.replace("@", "")

    username = re.sub(r"[^a-zA-Z0-9_]", "", username)
    return f"https://t.me/{username}"


@dp.message(PostCreation.waiting_contact)
async def get_contact(message: Message, state: FSMContext):
    contact_link = format_contact(message.text)

    data = await state.get_data()
    photo = data["photo"]
    text = data["text"]

    keyboard_admin = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve|{photo}|{contact_link}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data="reject"
                )
            ]
        ]
    )

    await bot.send_photo(
        ADMIN_ID,
        photo=photo,
        caption=text,
        reply_markup=keyboard_admin
    )

    await state.clear()
    await message.answer("✅ Публикация отправлена на модерацию.")


@dp.callback_query(F.data.startswith("approve"))
async def approve_post(callback: CallbackQuery):
    _, photo, contact_link = callback.data.split("|")
    caption = callback.message.caption

    keyboard_channel = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Связаться",
                    url=contact_link
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
        photo=photo,
        caption=caption,
        reply_markup=keyboard_channel
    )

    await callback.message.edit_caption(
        caption=caption + "\n\n✅ Опубликовано"
    )

    await callback.answer("Опубликовано!")


@dp.callback_query(F.data == "reject")
async def reject_post(callback: CallbackQuery):
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ Отклонено"
    )
    await callback.answer("Отклонено.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
