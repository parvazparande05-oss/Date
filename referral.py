from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

import db
from keyboards import daily_question_kb

router = Router()


@router.message(F.text == "🔗 دعوت دوستان")
async def invite_link(message: Message, bot: Bot):
    me = await db.get_user(message.from_user.id)
    me_info = await bot.get_me()
    link = f"https://t.me/{me_info.username}?start=ref_{message.from_user.id}"
    coins = me["coins"] if me else 0
    await message.answer(
        "🚀 با دعوت هر دوستت، ۵ سکه هدیه می‌گیری و شانس دیده شدن پروفایلت بیشتر می‌شه!\n\n"
        f"🪙 سکه‌های فعلی تو: {coins}\n\n"
        f"لینک اختصاصی تو:\n{link}\n\n"
        "این لینک رو برای دوستات بفرست 🙌"
    )


@router.message(F.text == "❓ سوال امروز")
async def daily_question(message: Message):
    idx, q, answered = await db.get_today_question_and_answer(message.from_user.id)
    if answered is not None:
        await message.answer(
            f"❓ {q['q']}\n\nامروز قبلاً جواب دادی: «{q['options'][answered]}»\nفردا سوال جدید میاد!"
        )
        return
    await message.answer(
        f"❓ سوال امروز:\n{q['q']}\n\nجواب تو به این سوال، درصد سازگاریت با بقیه رو دقیق‌تر می‌کنه:",
        reply_markup=daily_question_kb(idx, q["options"]),
    )


@router.callback_query(F.data.startswith("daily:"))
async def daily_answer(call: CallbackQuery):
    _, idx, opt = call.data.split(":")
    await db.save_daily_answer(call.from_user.id, int(opt))
    await call.message.edit_text("✅ جوابت ثبت شد! فردا سوال جدید میاد.")
    await call.answer()
