from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.locations import PROVINCE_LIST, PROVINCES
from data.traits import TRAITS


def gender_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👨 مرد", callback_data="gender:مرد")
    b.button(text="👩 زن", callback_data="gender:زن")
    b.adjust(2)
    return b.as_markup()


def looking_for_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👨 مرد", callback_data="look:مرد")
    b.button(text="👩 زن", callback_data="look:زن")
    b.button(text="هر دو", callback_data="look:هر دو")
    b.adjust(2, 1)
    return b.as_markup()


def goal_kb():
    b = InlineKeyboardBuilder()
    for g in ["دوستی", "رابطه جدی", "فقط چت", "هرکدوم پیش بیاد"]:
        b.button(text=g, callback_data=f"goal:{g}")
    b.adjust(2)
    return b.as_markup()


def province_kb():
    b = InlineKeyboardBuilder()
    for p in PROVINCE_LIST:
        b.button(text=p, callback_data=f"prov:{p}")
    b.adjust(2)
    return b.as_markup()


def city_kb(province: str):
    b = InlineKeyboardBuilder()
    for c in PROVINCES.get(province, []):
        b.button(text=c, callback_data=f"city:{c}")
    b.adjust(2)
    return b.as_markup()


def traits_kb(selected: set):
    b = InlineKeyboardBuilder()
    for t in TRAITS:
        label = f"✅ {t}" if t in selected else t
        b.button(text=label, callback_data=f"trait:{t}")
    b.adjust(3)
    b.row(InlineKeyboardButton(text="✔️ تمام شد", callback_data="traits_done"))
    return b.as_markup()


def photos_done_kb(count: int):
    b = InlineKeyboardBuilder()
    if count >= 1:
        b.button(text=f"✔️ پایان آپلود عکس ({count}/5)", callback_data="photos_done")
    return b.as_markup()


def voice_intro_kb():
    b = InlineKeyboardBuilder()
    b.button(text="⏭ رد کردن این مرحله", callback_data="skip_voice")
    return b.as_markup()


def mbti_choice_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🧠 آزمون کوتاه بگیرم (۲ دقیقه)", callback_data="mbti:test")
    b.button(text="✍️ تایپم رو می‌دونم، خودم وارد می‌کنم", callback_data="mbti:manual")
    b.button(text="⏭ فعلاً رد کن", callback_data="mbti:skip")
    b.adjust(1)
    return b.as_markup()


def mbti_question_kb(axis: str, opt_a: str, opt_b: str, qidx: int):
    b = InlineKeyboardBuilder()
    b.button(text=opt_a, callback_data=f"mbtiq:{qidx}:a")
    b.button(text=opt_b, callback_data=f"mbtiq:{qidx}:b")
    b.adjust(1)
    return b.as_markup()


def daily_question_kb(idx: int, options: list):
    b = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        b.button(text=opt, callback_data=f"daily:{idx}:{i}")
    b.adjust(1)
    return b.as_markup()


def browse_kb(target_id: int, photo_count: int = 1, photo_idx: int = 0, has_voice: bool = False):
    b = InlineKeyboardBuilder()
    b.button(text="👎 رد کردن", callback_data=f"pass:{target_id}")
    b.button(text="❤️ پسندیدم", callback_data=f"like:{target_id}")
    b.button(text="⭐️ سوپرلایک", callback_data=f"super:{target_id}")
    if photo_count > 1:
        b.button(text="🖼 عکس بعدی", callback_data=f"nextphoto:{target_id}:{(photo_idx + 1) % photo_count}")
    if has_voice:
        b.button(text="🎙 معرفی صوتی", callback_data=f"voice:{target_id}")
    b.button(text="🚩 گزارش", callback_data=f"report:{target_id}")
    b.adjust(2, 1, 1, 1)
    return b.as_markup()


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👀 دیدن پروفایل‌ها"), KeyboardButton(text="💛 مچ طلایی امروز")],
            [KeyboardButton(text="💌 مچ‌های من"), KeyboardButton(text="👤 پروفایل من")],
            [KeyboardButton(text="🔗 دعوت دوستان"), KeyboardButton(text="❓ سوال امروز")],
            [KeyboardButton(text="🏆 ستاره هفته"), KeyboardButton(text="💎 پریمیوم")],
            [KeyboardButton(text="🧠 ویرایش MBTI")],
        ],
        resize_keyboard=True,
    )


def chat_active_kb():
    b = InlineKeyboardBuilder()
    b.button(text="⛔️ پایان چت", callback_data="end_chat")
    b.button(text="🚫 بلاک", callback_data="block_chat")
    b.adjust(2)
    return b.as_markup()


def match_notify_kb(partner_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="💬 شروع چت", callback_data=f"start_chat:{partner_id}")
    return b.as_markup()


def premium_kb(stars_price: int):
    b = InlineKeyboardBuilder()
    b.button(text=f"⭐️ خرید پریمیوم ۱ ماهه ({stars_price} Stars)", callback_data="buy_premium")
    return b.as_markup()


def verify_prompt_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📸 ارسال سلفی برای تأیید", callback_data="verify_start")
    return b.as_markup()


def admin_verify_kb(user_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="✅ تأیید", callback_data=f"vok:{user_id}")
    b.button(text="❌ رد", callback_data=f"vno:{user_id}")
    b.adjust(2)
    return b.as_markup()
