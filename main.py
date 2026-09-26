import asyncio
import logging
from datetime import date, datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, GOLDEN_MATCH_HOUR
import db
from handlers import registration, mbti, verification, admin, referral, browsing, premium, chatting

logging.basicConfig(level=logging.INFO)


async def golden_match_job(bot: Bot):
    """هر روز یک بار (در ساعت تنظیم‌شده)، به کاربران فعال یک «مچ طلایی» پیشنهاد می‌ده."""
    while True:
        now = datetime.now()
        if now.hour == GOLDEN_MATCH_HOUR:
            today = date.today().isoformat()
            user_ids = await db.all_active_user_ids()
            for uid in user_ids:
                me = await db.get_user(uid)
                if not me or not me["full_name"] or me["golden_match_date"] == today:
                    continue
                candidate = await db.next_candidate(uid)
                if not candidate:
                    continue
                score = db.compute_compatibility_basic(me, candidate)
                photos = (candidate["photos"] or "").split(",") if candidate["photos"] else []
                try:
                    from keyboards import browse_kb
                    await bot.send_photo(
                        uid,
                        photo=photos[0] if photos else None,
                        caption=(
                            f"💛 مچ طلایی امروزت آماده‌ست!\n\n"
                            f"👤 {candidate['full_name']}, {candidate['age']} — {candidate['city']}\n"
                            f"🔥 سازگاری: {score}%"
                        ),
                        reply_markup=browse_kb(candidate["user_id"], photo_count=len(photos)),
                    )
                    await db.upsert_user_field(uid, golden_match_date=today)
                except Exception:
                    pass
            await asyncio.sleep(3600)  # یک ساعت صبر تا دوباره چک نکنه توی همون ساعت
        await asyncio.sleep(300)  # هر ۵ دقیقه ساعت رو چک کن


async def main():
    await db.init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # ترتیب مهم است: هندلرهای مبتنی بر state (ثبت‌نام، mbti، تأیید، ادمین) باید قبل از
    # هندلرهای عمومی متن (چت رله‌شده) بررسی شوند.
    dp.include_router(registration.router)
    dp.include_router(mbti.router)
    dp.include_router(verification.router)
    dp.include_router(admin.router)
    dp.include_router(referral.router)
    dp.include_router(browsing.router)
    dp.include_router(premium.router)
    dp.include_router(chatting.router)

    await bot.delete_webhook(drop_pending_updates=True)

    asyncio.create_task(golden_match_job(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
