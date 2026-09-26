import os

# توکن ربات را از BotFather بگیرید و به عنوان متغیر محیطی BOT_TOKEN تنظیم کنید.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("متغیر محیطی BOT_TOKEN تنظیم نشده است. راهنمای README.md را ببینید.")

DB_PATH = os.environ.get("DB_PATH", "dating_bot.db")

# آی‌دی عددی ادمین‌ها (از @userinfobot بگیرید)، با کاما جدا کنید: "111111,222222"
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}

# سن مجاز
MIN_AGE = 18
MAX_AGE = 70

# --- محدودیت‌های نسخه رایگان (freemium) ---
DAILY_FREE_SWIPES = 15          # تعداد مشاهده پروفایل رایگان در روز
DAILY_FREE_SUPERLIKES = 1       # سوپرلایک رایگان در روز
DAILY_PREMIUM_SUPERLIKES = 5

# --- تخفیف افتتاحیه: همه کاربران جدید N روز اول پریمیوم رایگان می‌گیرند ---
LAUNCH_DISCOUNT_DAYS = int(os.environ.get("LAUNCH_DISCOUNT_DAYS", "30"))
LAUNCH_DISCOUNT_ACTIVE = os.environ.get("LAUNCH_DISCOUNT_ACTIVE", "1") == "1"

# --- قیمت پریمیوم با Telegram Stars (ارز داخلی تلگرام، نیاز به درگاه بانکی ندارد) ---
PREMIUM_PRICE_STARS_MONTH = int(os.environ.get("PREMIUM_PRICE_STARS_MONTH", "150"))

# رفرال
REFERRAL_BONUS_COINS = 5

# ساعت ارسال «مچ طلایی» روزانه (بر اساس ساعت سرور، ۲۴ ساعته)
GOLDEN_MATCH_HOUR = int(os.environ.get("GOLDEN_MATCH_HOUR", "12"))
