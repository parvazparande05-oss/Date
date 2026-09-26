from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import db
from keyboards import chat_active_kb, main_menu_kb

router = Router()

MENU_TEXTS = {
    "👀 دیدن پروفایل‌ها", "💌 مچ‌های من", "👤 پروفایل من", "🔗 دعوت دوستان",
    "❓ سوال امروز", "🏆 ستاره هفته", "💎 پریمیوم", "💛 مچ طلایی امروز", "🧠 ویرایش MBTI",
}


@router.callback_query(F.data.startswith("start_chat:"))
async def start_chat(call: CallbackQuery, bot: Bot):
    partner_id = int(call.data.split(":", 1)[1])
    partner = await db.get_user(partner_id)
    if not partner:
        await call.answer("این کاربر دیگر در دسترس نیست.", show_alert=True)
        return
    await db.start_chat(call.from_user.id, partner_id)
    await call.message.answer(
        f"💬 چت با {partner['full_name']} شروع شد.\n"
        "هر پیامی بفرستی مستقیم براش می‌ره (بدون افشای یوزرنیمت).",
        reply_markup=chat_active_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "end_chat")
async def end_chat(call: CallbackQuery, bot: Bot):
    partner_id = await db.end_chat(call.from_user.id)
    await call.message.answer("چت پایان یافت.", reply_markup=main_menu_kb())
    if partner_id:
        await bot.send_message(partner_id, "طرف مقابل چت را پایان داد.", reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "block_chat")
async def block_current_chat(call: CallbackQuery, bot: Bot):
    partner_id = await db.get_active_partner(call.from_user.id)
    if partner_id:
        await db.block_user(call.from_user.id, partner_id)
        await call.message.answer("این کاربر بلاک شد و دیگه پیامی ازش نمی‌بینی.", reply_markup=main_menu_kb())
        await bot.send_message(partner_id, "طرف مقابل چت را بست.", reply_markup=main_menu_kb())
    await call.answer()


@router.message(Command("block"))
async def block_command(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("استفاده: /block USER_ID")
        return
    await db.block_user(message.from_user.id, int(parts[1]))
    await message.answer("کاربر بلاک شد.")


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(MENU_TEXTS))
async def relay_message(message: Message, bot: Bot):
    partner_id = await db.get_active_partner(message.from_user.id)
    if not partner_id:
        return
    await bot.send_message(partner_id, message.text)


@router.message(F.photo)
async def relay_photo(message: Message, bot: Bot):
    partner_id = await db.get_active_partner(message.from_user.id)
    if not partner_id:
        return
    await bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)


@router.message(F.voice)
async def relay_voice(message: Message, bot: Bot):
    partner_id = await db.get_active_partner(message.from_user.id)
    if not partner_id:
        return
    await bot.send_voice(partner_id, message.voice.file_id)
