from datetime import date, timedelta

from aiogram import Router, F, Bot
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, CallbackQuery

import db
import config
from config import PREMIUM_PRICE_STARS_MONTH, DAILY_PREMIUM_SUPERLIKES
from keyboards import premium_kb, main_menu_kb

router = Router()


@router.message(F.text == "💎 پریمیوم")
async def premium_menu(message: Message):
    me = await db.get_user(message.from_user.id)
    if db.is_premium_row(me):
        until = me["premium_until"]
        await message.answer(
            f"💎 پریمیوم شما فعاله تا تاریخ {until}.\n"
            f"مزایا: مرور نامحدود، {DAILY_PREMIUM_SUPERLIKES} سوپرلایک روزانه، تحلیل کامل نقاط ضعف MBTI، اولویت نمایش."
        )
        return

    text = "💎 مزایای پریمیوم:\n• مرور نامحدود پروفایل\n• ۵ سوپرلایک در روز\n• دیدن تحلیل کامل نقاط ضعف MBTI\n• اولویت نمایش پروفایلت\n\n"
    if config.LAUNCH_DISCOUNT_ACTIVE:
        text += f"🎉 در تخفیف افتتاحیه، همه‌ی کاربران جدید {config.LAUNCH_DISCOUNT_DAYS} روز پریمیوم رایگان می‌گیرن (خودکار بعد از ثبت‌نام).\n\n"
    text += "برای تمدید/خرید بیشتر می‌تونی با Telegram Stars بخری (نیازی به کارت بانکی نیست):"
    await message.answer(text, reply_markup=premium_kb(PREMIUM_PRICE_STARS_MONTH))


@router.callback_query(F.data == "buy_premium")
async def buy_premium(call: CallbackQuery, bot: Bot):
    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="پریمیوم ۱ ماهه",
        description="مرور نامحدود، سوپرلایک بیشتر، تحلیل کامل سازگاری MBTI",
        payload="premium_month",
        provider_token="",  # برای Telegram Stars همیشه خالی می‌مونه
        currency="XTR",
        prices=[LabeledPrice(label="پریمیوم ۱ ماهه", amount=PREMIUM_PRICE_STARS_MONTH)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    me = await db.get_user(message.from_user.id)
    base = date.today()
    if me and me["premium_until"]:
        try:
            existing = date.fromisoformat(me["premium_until"])
            if existing > base:
                base = existing
        except ValueError:
            pass
    new_until = (base + timedelta(days=30)).isoformat()
    await db.upsert_user_field(message.from_user.id, premium_until=new_until)
    await message.answer(f"🎉 پریمیوم فعال شد تا {new_until}! ممنون از حمایتت 💎", reply_markup=main_menu_kb())
