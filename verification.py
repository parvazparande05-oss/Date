from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from config import ADMIN_IDS
from keyboards import verify_prompt_kb, admin_verify_kb, main_menu_kb
from states import VerifyFlow

router = Router()


@router.message(F.text == "/verify")
async def verify_entry(message: Message):
    me = await db.get_user(message.from_user.id)
    if not me or not me["full_name"]:
        await message.answer("اول باید پروفایل بسازی. /start رو بزن.")
        return
    if me["is_verified"]:
        await message.answer("پروفایلت از قبل تأیید شده ✅")
        return
    if me["verification_status"] == "pending":
        await message.answer("سلفی‌ات در صف بررسیه، صبر کن ⏳")
        return
    await message.answer(
        "برای گرفتن بج تأیید ✅، یک سلفی واضح از خودت بفرست (فقط برای بررسی ادمین استفاده می‌شه):",
        reply_markup=verify_prompt_kb(),
    )
    await message.answer("در صورت آماده بودن، عکس رو همینجا بفرست.")


@router.callback_query(F.data == "verify_start")
async def verify_start_cb(call: CallbackQuery, state: FSMContext):
    await call.message.answer("سلفی‌ات رو بفرست:")
    await state.set_state(VerifyFlow.selfie)
    await call.answer()


@router.message(VerifyFlow.selfie, F.photo)
async def verify_receive_selfie(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    await db.upsert_user_field(message.from_user.id, verification_photo=photo_id, verification_status="pending")
    await state.clear()
    await message.answer("سلفی‌ات ثبت شد و در صف بررسی ادمین قرار گرفت ⏳", reply_markup=main_menu_kb())

    me = await db.get_user(message.from_user.id)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo_id,
                caption=f"درخواست تأیید هویت:\n👤 {me['full_name']} (ID: {message.from_user.id})",
                reply_markup=admin_verify_kb(message.from_user.id),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("vok:"))
async def verify_approve(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("فقط ادمین.", show_alert=True)
        return
    user_id = int(call.data.split(":", 1)[1])
    await db.upsert_user_field(user_id, is_verified=1, verification_status="approved")
    await call.message.edit_caption(caption=call.message.caption + "\n\n✅ تأیید شد.")
    await bot.send_message(user_id, "🎉 پروفایلت تأیید شد و بج ✅ گرفتی!")
    await call.answer()


@router.callback_query(F.data.startswith("vno:"))
async def verify_reject(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("فقط ادمین.", show_alert=True)
        return
    user_id = int(call.data.split(":", 1)[1])
    await db.upsert_user_field(user_id, is_verified=0, verification_status="rejected")
    await call.message.edit_caption(caption=call.message.caption + "\n\n❌ رد شد.")
    await bot.send_message(user_id, "متأسفانه سلفی‌ات تأیید نشد. می‌تونی دوباره با /verify امتحان کنی.")
    await call.answer()
