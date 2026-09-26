import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import db
import config
from states import AdminBroadcast

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not _is_admin(message.from_user.id):
        return
    s = await db.stats_summary()
    discount_state = "روشن ✅" if config.LAUNCH_DISCOUNT_ACTIVE else "خاموش ⛔️"
    await message.answer(
        "🛠 پنل ادمین\n\n"
        f"👥 کل کاربران: {s['total']}\n"
        f"🆕 ثبت‌نام امروز: {s['new_today']}\n"
        f"💞 تعداد مچ‌ها: {s['matches']}\n"
        f"💎 پریمیوم فعال: {s['premium']}\n"
        f"🚩 گزارش‌ها: {s['reports']}\n"
        f"🚫 بن‌شده‌ها: {s['banned']}\n\n"
        f"تخفیف افتتاحیه: {discount_state} ({config.LAUNCH_DISCOUNT_DAYS} روز)\n\n"
        "دستورات:\n"
        "/broadcast — ارسال پیام همگانی\n"
        "/ban USER_ID — مسدود کردن کاربر\n"
        "/unban USER_ID — رفع مسدودی\n"
        "/reports — آخرین گزارش‌ها\n"
        "/pending — سلفی‌های در انتظار تأیید\n"
        "/discount_on یا /discount_off — روشن/خاموش کردن تخفیف افتتاحیه\n"
    )


@router.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("متن پیام همگانی رو بفرست (به همه‌ی کاربران فعال ارسال می‌شه):")
    await state.set_state(AdminBroadcast.text)


@router.message(AdminBroadcast.text)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = await db.all_active_user_ids()
    sent, failed = 0, 0
    status_msg = await message.answer(f"در حال ارسال به {len(user_ids)} کاربر...")
    for uid in user_ids:
        try:
            await bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # جلوگیری از محدودیت نرخ تلگرام
    await status_msg.edit_text(f"✅ ارسال شد به {sent} نفر. ({failed} ناموفق)")


@router.message(Command("ban"))
async def ban_cmd(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("استفاده: /ban USER_ID")
        return
    await db.set_ban(int(parts[1]), True)
    await message.answer(f"کاربر {parts[1]} مسدود شد.")


@router.message(Command("unban"))
async def unban_cmd(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("استفاده: /unban USER_ID")
        return
    await db.set_ban(int(parts[1]), False)
    await message.answer(f"مسدودیت کاربر {parts[1]} برداشته شد.")


@router.message(Command("reports"))
async def reports_cmd(message: Message):
    if not _is_admin(message.from_user.id):
        return
    reports = await db.recent_reports(15)
    if not reports:
        await message.answer("گزارشی ثبت نشده.")
        return
    lines = ["🚩 آخرین گزارش‌ها:\n"]
    for r in reports:
        lines.append(f"#{r['id']} | گزارش‌دهنده: {r['reporter']} | گزارش‌شده: {r['reported']}\nدلیل: {r['reason']}\n")
    await message.answer("\n".join(lines))


@router.message(Command("pending"))
async def pending_cmd(message: Message, bot: Bot):
    if not _is_admin(message.from_user.id):
        return
    from keyboards import admin_verify_kb
    users = await db.pending_verifications()
    if not users:
        await message.answer("هیچ سلفی‌ای در انتظار بررسی نیست.")
        return
    for u in users:
        await bot.send_photo(
            message.chat.id,
            u["verification_photo"],
            caption=f"👤 {u['full_name']} (ID: {u['user_id']})",
            reply_markup=admin_verify_kb(u["user_id"]),
        )


@router.message(Command("discount_on"))
async def discount_on(message: Message):
    if not _is_admin(message.from_user.id):
        return
    config.LAUNCH_DISCOUNT_ACTIVE = True
    await message.answer("تخفیف افتتاحیه روشن شد ✅ (توجه: بعد از ری‌استارت ربات، مقدار اولیه از متغیر محیطی خونده می‌شه)")


@router.message(Command("discount_off"))
async def discount_off(message: Message):
    if not _is_admin(message.from_user.id):
        return
    config.LAUNCH_DISCOUNT_ACTIVE = False
    await message.answer("تخفیف افتتاحیه خاموش شد ⛔️ (توجه: بعد از ری‌استارت ربات، مقدار اولیه از متغیر محیطی خونده می‌شه)")
