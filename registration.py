from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import db
from config import MIN_AGE, MAX_AGE
from keyboards import (
    gender_kb, looking_for_kb, goal_kb, province_kb, city_kb, traits_kb,
    photos_done_kb, voice_intro_kb, mbti_choice_kb, main_menu_kb,
)
from states import Registration

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    inviter_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            inviter_id = int(args[1].replace("ref_", ""))
        except ValueError:
            inviter_id = None

    already = await db.is_registered(message.from_user.id)

    if inviter_id and inviter_id != message.from_user.id and not already:
        await db.upsert_user_field(message.from_user.id, username=message.from_user.username)
        await db.set_invited_by(message.from_user.id, inviter_id)

    if already:
        await message.answer("خوش اومدی! 👋 از منوی پایین یکی رو انتخاب کن.", reply_markup=main_menu_kb())
        return

    await message.answer(
        "سلام! 👋 به ربات دوستیابی خوش اومدی.\n\n"
        "🎉 در حال حاضر همه‌ی امکانات پریمیوم برای کاربران جدید <b>رایگان</b>ه (تخفیف افتتاحیه)!\n\n"
        "بذار پروفایلت رو بسازیم. اول بگو: اسمت (یا اسم مستعارت) چیه؟"
    )
    await state.set_state(Registration.name)


@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name or len(name) > 40:
        await message.answer("یه اسم معتبر (حداکثر ۴۰ حرف) بفرست.")
        return
    await state.update_data(full_name=name)
    await message.answer(f"چند سالته؟ (باید {MIN_AGE} سال یا بیشتر باشی)")
    await state.set_state(Registration.age)


@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("لطفاً سن رو فقط با عدد بفرست، مثلاً 25")
        return
    age = int(text)
    if age < MIN_AGE:
        await message.answer(f"متأسفانه این ربات فقط برای افراد {MIN_AGE} سال به بالاست.")
        await state.clear()
        return
    if age > MAX_AGE:
        await message.answer("سن واردشده معتبر به نظر نمی‌رسه. دوباره امتحان کن.")
        return
    await state.update_data(age=age)
    await message.answer("جنسیتت چیه؟", reply_markup=gender_kb())
    await state.set_state(Registration.gender)


@router.callback_query(Registration.gender, F.data.startswith("gender:"))
async def reg_gender(call: CallbackQuery, state: FSMContext):
    gender = call.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    await call.message.edit_text(f"جنسیت: {gender} ✅")
    await call.message.answer("دنبال چه کسی می‌گردی؟", reply_markup=looking_for_kb())
    await state.set_state(Registration.looking_for)
    await call.answer()


@router.callback_query(Registration.looking_for, F.data.startswith("look:"))
async def reg_looking_for(call: CallbackQuery, state: FSMContext):
    look = call.data.split(":", 1)[1]
    await state.update_data(looking_for=look)
    await call.message.edit_text(f"دنبال: {look} ✅")
    await call.message.answer("هدفت از آشنایی چیه؟", reply_markup=goal_kb())
    await state.set_state(Registration.goal)
    await call.answer()


@router.callback_query(Registration.goal, F.data.startswith("goal:"))
async def reg_goal(call: CallbackQuery, state: FSMContext):
    goal = call.data.split(":", 1)[1]
    await state.update_data(goal=goal)
    await call.message.edit_text(f"هدف: {goal} ✅")
    await call.message.answer("کدوم استان هستی؟", reply_markup=province_kb())
    await state.set_state(Registration.province)
    await call.answer()


@router.callback_query(Registration.province, F.data.startswith("prov:"))
async def reg_province(call: CallbackQuery, state: FSMContext):
    province = call.data.split(":", 1)[1]
    await state.update_data(province=province)
    await call.message.edit_text(f"استان: {province} ✅")
    await call.message.answer("کدوم شهر؟", reply_markup=city_kb(province))
    await state.set_state(Registration.city)
    await call.answer()


@router.callback_query(Registration.city, F.data.startswith("city:"))
async def reg_city(call: CallbackQuery, state: FSMContext):
    city = call.data.split(":", 1)[1]
    if city == "شهر دیگر":
        await call.message.edit_text("اسم شهرت رو تایپ کن:")
        await state.set_state(Registration.city_custom)
        await call.answer()
        return
    await state.update_data(city=city)
    await call.message.edit_text(f"شهر: {city} ✅")
    await call.message.answer("چند خط درباره خودت بنویس (علایق، سبک زندگی...):")
    await state.set_state(Registration.bio)
    await call.answer()


@router.message(Registration.city_custom)
async def reg_city_custom(message: Message, state: FSMContext):
    city = (message.text or "").strip()
    if not city or len(city) > 30:
        await message.answer("یه اسم شهر معتبر بفرست.")
        return
    await state.update_data(city=city)
    await message.answer("چند خط درباره خودت بنویس (علایق، سبک زندگی...):")
    await state.set_state(Registration.bio)


@router.message(Registration.bio)
async def reg_bio(message: Message, state: FSMContext):
    bio = (message.text or "").strip()
    if not bio or len(bio) > 500:
        await message.answer("متن باید بین ۱ تا ۵۰۰ کاراکتر باشه.")
        return
    await state.update_data(bio=bio, selected_traits=set())
    await message.answer(
        "چند ویژگی اخلاقی/شخصیتی که خودت رو توصیف می‌کنه انتخاب کن (در آخر «تمام شد» بزن):",
        reply_markup=traits_kb(set()),
    )
    await state.set_state(Registration.traits)


@router.callback_query(Registration.traits, F.data.startswith("trait:"))
async def reg_trait_toggle(call: CallbackQuery, state: FSMContext):
    trait = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("selected_traits", set()))
    if trait in selected:
        selected.discard(trait)
    elif len(selected) < 6:
        selected.add(trait)
    else:
        await call.answer("حداکثر ۶ ویژگی می‌تونی انتخاب کنی.", show_alert=True)
        return
    await state.update_data(selected_traits=selected)
    await call.message.edit_reply_markup(reply_markup=traits_kb(selected))
    await call.answer()


@router.callback_query(Registration.traits, F.data == "traits_done")
async def reg_traits_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_traits", set())
    if not selected:
        await call.answer("حداقل یک ویژگی انتخاب کن.", show_alert=True)
        return
    await call.message.edit_text(f"ویژگی‌ها: {', '.join(selected)} ✅")
    await state.update_data(photos=[])
    await call.message.answer("حالا ۱ تا ۵ عکس خوب از خودت بفرست 📸 (بعد از هر عکس، اگه کافیه دکمه پایین رو بزن).")
    await state.set_state(Registration.photos)
    await call.answer()


@router.message(Registration.photos, F.photo)
async def reg_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) >= 5:
        await message.answer("حداکثر ۵ عکس مجازه. اگه کافیه دکمه پایان رو بزن.")
        return
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"عکس {len(photos)} ثبت شد ✅", reply_markup=photos_done_kb(len(photos)))


@router.callback_query(Registration.photos, F.data == "photos_done")
async def reg_photos_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("photos"):
        await call.answer("حداقل یک عکس لازمه.", show_alert=True)
        return
    await call.message.edit_text(f"عکس‌ها ثبت شد ({len(data['photos'])} عکس) ✅")
    await call.message.answer(
        "می‌خوای یک ویس معرفی کوتاه (حداکثر ۳۰ ثانیه) هم اضافه کنی؟ خیلی‌ها با این بیشتر جلب توجه می‌کنن 🎙",
        reply_markup=voice_intro_kb(),
    )
    await state.set_state(Registration.voice_intro)
    await call.answer()


@router.message(Registration.voice_intro, F.voice)
async def reg_voice(message: Message, state: FSMContext):
    if message.voice.duration > 35:
        await message.answer("ویس باید حداکثر ۳۰ ثانیه باشه. دوباره بفرست.")
        return
    await state.update_data(voice_intro_file_id=message.voice.file_id)
    await ask_mbti(message, state)


@router.callback_query(Registration.voice_intro, F.data == "skip_voice")
async def reg_voice_skip(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("باشه، ویس معرفی نداری. هر وقت خواستی بعداً اضافه‌ش کن.")
    await ask_mbti(call.message, state)
    await call.answer()


async def ask_mbti(message: Message, state: FSMContext):
    await message.answer(
        "🧠 یکی از جذاب‌ترین بخش‌های این ربات: تایپ شخصیتی MBTI!\n"
        "با دونستن تایپت، سیستم می‌تونه دقیق‌تر سازگاریت رو با بقیه بسنجه.",
        reply_markup=mbti_choice_kb(),
    )
    await state.set_state(Registration.mbti_choice)


async def finish_registration(message: Message, state: FSMContext, bot: Bot, user_id: int, username: str = None):
    data = await state.get_data()
    await db.upsert_user_field(
        user_id,
        username=username,
        full_name=data["full_name"],
        age=data["age"],
        gender=data["gender"],
        looking_for=data["looking_for"],
        goal=data.get("goal"),
        province=data["province"],
        city=data["city"],
        bio=data["bio"],
        traits=",".join(data.get("selected_traits", set())),
        photos=",".join(data.get("photos", [])),
        voice_intro_file_id=data.get("voice_intro_file_id"),
        mbti=data.get("mbti"),
        is_active=1,
    )
    await db.complete_registration_launch_bonus(user_id)
    await state.clear()
    await message.answer(
        "🎉 پروفایلت با موفقیت ساخته شد! و پریمیوم افتتاحیه هم فعال شد 💎\n\n"
        "حالا می‌تونی پروفایل‌های دیگران رو ببینی و در صورت مچ شدن چت کنی.",
        reply_markup=main_menu_kb(),
    )
