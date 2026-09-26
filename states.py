from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    goal = State()
    province = State()
    city = State()
    city_custom = State()
    bio = State()
    traits = State()
    photos = State()
    voice_intro = State()
    mbti_choice = State()
    mbti_test = State()
    mbti_manual = State()


class ReportFlow(StatesGroup):
    reason = State()


class VerifyFlow(StatesGroup):
    selfie = State()


class AdminBroadcast(StatesGroup):
    text = State()
