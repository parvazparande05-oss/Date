from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import db
from config import DAILY_FREE_SWIPES, DAILY_FREE_SUPERLIKES, DAILY_PREMIUM_SUPERLIKES
from data.mbti import compatibility_report
from keyboards import browse_kb, match_notify_kb, main_menu_kb
from states import ReportFlow

router = Router()


def _photo_list(user_row):
    return (user_row["photos"] or "").split(",") if user_row["photos"] else []


async def send_candidate(target, user_id: int, bot: Bot, photo_idx: int = 0, edit_message: Message = None, candidate_id: int = None):
    me = await db.get_user(user_id)

    if candidate_id:
        candidate = await db.get_user(candidate_id)
    else:
        is_premium = db.is_premium_row(me)
        limit = 10_000 if is_premium else DAILY_FREE_SWIPES
        allowed = await db.check_and_consume_swipe(user_id, limit)
        if not allowed:
            text = (
                f"سقف {DAILY_FREE_SWIPES} پروفایل رایگان امروزت تموم شد 😅\n"
                "با پریمیوم (💎 از منو) مرور نامحدود داشته باش!"
            )
            chat_id = target.message.chat.id if isinstance(target, CallbackQuery) else target.chat.id
            await bot.send_message(chat_id, text, reply_markup=main_menu_kb())
            return
        candidate = await db.next_candidate(user_id)

    chat_id = target.message.chat.id if isinstance(target, CallbackQuery) else target.chat.id

    if candidate is None:
        await bot.send_message(chat_id, "فعلاً پروفایل جدیدی برای نمایش نیست. بعداً دوباره سر بزن! 🙌", reply_markup=main_menu_kb())
        return

    score = db.compute_compatibility_basic(me, candidate)
    traits = candidate["traits"].replace(",", " • ") if candidate["traits"] else "—"
    verified_badge = " ✅" if candidate["is_verified"] else ""
    mbti_line = f"🧠 MBTI: {candidate['mbti']}\n" if candidate["mbti"] else ""

    caption = (
        f"👤 {candidate['full_name']}{verified_badge}, {candidate['age']}\n"
        f"📍 {candidate['province']} - {candidate['city']}\n"
        f"🎯 هدف: {candidate['goal'] or '—'}\n"
        f"{mbti_line}"
        f"🧩 ویژگی‌ها: {traits}\n\n"
        f"📝 {candidate['bio']}\n\n"
        f"🔥 درصد سازگاری با شما: {score}%"
    )

    photos = _photo_list(candidate)
    photo_idx = photo_idx % max(len(photos), 1)
    photo = photos[photo_idx] if photos else None
    kb = browse_kb(candidate["user_id"], photo_count=len(photos), photo_idx=photo_idx, has_voice=bool(candidate["voice_intro_file_id"]))

    if edit_message and photo:
        try:
            from aiogram.types import InputMediaPhoto
            await edit_message.edit_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=kb)
            return
        except Exception:
            pass

    if photo:
        await bot.send_photo(chat_id, photo=photo, caption=caption, reply_markup=kb)
    else:
        await bot.send_message(chat_id, caption, reply_markup=kb)


@router.message(F.text == "👀 دیدن پروفایل‌ها")
async def browse_start(message: Message, bot: Bot):
    if not await db.is_registered(message.from_user.id):
        await message.answer("اول باید پروفایلت رو بسازی. /start رو بزن.")
        return
    await send_candidate(message, message.from_user.id, bot)


@router.callback_query(F.data.startswith("nextphoto:"))
async def on_next_photo(call: CallbackQuery, bot: Bot):
    _, target_id, idx = call.data.split(":")
    await send_candidate(call, call.from_user.id, bot, photo_idx=int(idx), edit_message=call.message, candidate_id=int(target_id))
    await call.answer()


@router.callback_query(F.data.startswith("voice:"))
async def on_voice(call: CallbackQuery, bot: Bot):
    target_id = int(call.data.split(":", 1)[1])
    candidate = await db.get_user(target_id)
    if candidate and candidate["voice_intro_file_id"]:
        await bot.send_voice(call.message.chat.id, candidate["voice_intro_file_id"])
    await call.answer()


@router.callback_query(F.data.startswith("pass:"))
async def on_pass(call: CallbackQuery, bot: Bot):
    target_id = int(call.data.split(":", 1)[1])
    await db.record_swipe(call.from_user.id, target_id, liked=False)
    await call.message.delete()
    await send_candidate(call, call.from_user.id, bot)
    await call.answer()


async def _announce_match(bot: Bot, user_id: int, target_id: int):
    me = await db.get_user(user_id)
    other = await db.get_user(target_id)
    report = None
    if me["mbti"] and other["mbti"]:
        report = compatibility_report(me["mbti"], other["mbti"])

    for a, b, chat_id in [(me, other, user_id), (other, me, target_id)]:
        text = f"🎉 مچ جدید! تو و {b['full_name']} همدیگه رو پسندیدید.\n"
        if report:
            text += f"\n🔥 سازگاری MBTI: {report['score']}%\n"
            text += "\n💪 نقاط قوت:\n" + "\n".join(f"• {s}" for s in report["strengths"][:2])
            is_premium = db.is_premium_row(a)
            if is_premium:
                if report["weaknesses"]:
                    text += "\n\n⚠️ نکات قابل توجه:\n" + "\n".join(f"• {w}" for w in report["weaknesses"])
                text += f"\n\n💡 پیشنهاد: {report['suggestion']}"
            else:
                text += "\n\n🔒 نقاط ضعف و چالش‌های احتمالی فقط برای کاربران پریمیوم نمایش داده می‌شه."
        await bot.send_message(chat_id, text, reply_markup=match_notify_kb(target_id if chat_id == user_id else user_id))


@router.callback_query(F.data.startswith("like:"))
async def on_like(call: CallbackQuery, bot: Bot):
    target_id = int(call.data.split(":", 1)[1])
    mutual = await db.record_swipe(call.from_user.id, target_id, liked=True)
    await call.message.delete()
    if mutual:
        await _announce_match(bot, call.from_user.id, target_id)
    else:
        await call.answer("لایک ثبت شد ❤️")
    await send_candidate(call, call.from_user.id, bot)


@router.callback_query(F.data.startswith("super:"))
async def on_superlike(call: CallbackQuery, bot: Bot):
    target_id = int(call.data.split(":", 1)[1])
    me = await db.get_user(call.from_user.id)
    limit = DAILY_PREMIUM_SUPERLIKES if db.is_premium_row(me) else DAILY_FREE_SUPERLIKES
    allowed = await db.check_and_consume_superlike(call.from_user.id, limit)
    if not allowed:
        await call.answer(f"سوپرلایک امروزت تموم شد (سقف: {limit}). فردا دوباره امتحان کن یا پریمیوم بگیر 💎", show_alert=True)
        return
    mutual = await db.record_swipe(call.from_user.id, target_id, liked=True, is_super=True)
    await bot.send_message(target_id, f"⭐️ {me['full_name']} بهت سوپرلایک زد! برو ببین کیه 👀")
    await call.message.delete()
    if mutual:
        await _announce_match(bot, call.from_user.id, target_id)
    else:
        await call.answer("سوپرلایک ارسال شد ⭐️")
    await send_candidate(call, call.from_user.id, bot)


@router.callback_query(F.data.startswith("report:"))
async def on_report_start(call: CallbackQuery, state: FSMContext):
    target_id = int(call.data.split(":", 1)[1])
    await state.update_data(report_target=target_id)
    await state.set_state(ReportFlow.reason)
    await call.message.answer("دلیل گزارش رو کوتاه بنویس (یا /cancel برای انصراف):")
    await call.answer()


@router.message(ReportFlow.reason)
async def on_report_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("report_target")
    if message.text == "/cancel" or not target_id:
        await state.clear()
        await message.answer("گزارش لغو شد.", reply_markup=main_menu_kb())
        return
    await db.add_report(message.from_user.id, target_id, message.text)
    await state.clear()
    await message.answer("گزارش شما ثبت شد. ممنون که به امنیت جامعه کمک می‌کنی 🙏", reply_markup=main_menu_kb())


@router.message(F.text == "💌 مچ‌های من")
async def my_matches(message: Message, bot: Bot):
    partners = await db.get_matches(message.from_user.id)
    if not partners:
        await message.answer("هنوز مچی نداری. برو پروفایل‌ها رو ببین 👀")
        return
    for pid in partners:
        p = await db.get_user(pid)
        if not p:
            continue
        photos = _photo_list(p)
        await bot.send_photo(
            message.chat.id,
            photo=photos[0] if photos else None,
            caption=f"👤 {p['full_name']}, {p['age']} — {p['city']}",
            reply_markup=match_notify_kb(pid),
        )


@router.message(F.text == "👤 پروفایل من")
async def my_profile(message: Message, bot: Bot):
    me = await db.get_user(message.from_user.id)
    if not me or not me["full_name"]:
        await message.answer("هنوز پروفایل نساختی. /start رو بزن.")
        return
    traits = me["traits"].replace(",", " • ") if me["traits"] else "—"
    premium_txt = "💎 پریمیوم فعال" if db.is_premium_row(me) else "🆓 رایگان"
    verified_txt = "✅ تأییدشده" if me["is_verified"] else "⚪️ تأیید نشده"
    caption = (
        f"👤 {me['full_name']}, {me['age']} ({me['gender']})\n"
        f"📍 {me['province']} - {me['city']}\n"
        f"🎯 هدف: {me['goal'] or '—'}\n"
        f"🧠 MBTI: {me['mbti'] or 'ثبت‌نشده'}\n"
        f"🧩 {traits}\n"
        f"🪙 سکه: {me['coins']}\n"
        f"{premium_txt} | {verified_txt}\n\n"
        f"📝 {me['bio']}"
    )
    photos = _photo_list(me)
    await bot.send_photo(message.chat.id, photo=photos[0] if photos else None, caption=caption)
    if not me["mbti"]:
        await message.answer("💡 هنوز MBTI ثبت نکردی؛ برای ثبتش «🧠 ویرایش MBTI» رو بفرست.")


@router.message(F.text == "💛 مچ طلایی امروز")
async def golden_match_manual(message: Message, bot: Bot):
    me = await db.get_user(message.from_user.id)
    if not me:
        return
    candidate = await db.next_candidate(message.from_user.id)
    if not candidate:
        await message.answer("امروز کاندیدای جدیدی برات پیدا نکردم. بعداً دوباره امتحان کن 💛")
        return
    score = db.compute_compatibility_basic(me, candidate)
    photos = _photo_list(candidate)
    await bot.send_photo(
        message.chat.id,
        photo=photos[0] if photos else None,
        caption=(
            f"💛 مچ طلایی امروز شما:\n\n"
            f"👤 {candidate['full_name']}, {candidate['age']} — {candidate['city']}\n"
            f"🔥 سازگاری: {score}%"
        ),
        reply_markup=browse_kb(candidate["user_id"], photo_count=len(photos)),
    )


@router.message(F.text == "🏆 ستاره هفته")
async def leaderboard(message: Message):
    top = await db.top_active_users(5)
    if not top:
        await message.answer("هنوز آماری ثبت نشده.")
        return
    lines = ["🏆 پرافتخارترین کاربران (بر اساس تعداد مچ):\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, u in enumerate(top):
        lines.append(f"{medals[i]} {u['full_name']} — {u['matches_count']} مچ")
    await message.answer("\n".join(lines))
