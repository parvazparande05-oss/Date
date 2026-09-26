import random
from datetime import date, timedelta

import aiosqlite

import config
from config import DB_PATH
from data.traits import DAILY_QUESTIONS

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    age INTEGER,
    gender TEXT,
    looking_for TEXT,
    goal TEXT,
    province TEXT,
    city TEXT,
    bio TEXT,
    traits TEXT,
    photos TEXT,
    voice_intro_file_id TEXT,
    mbti TEXT,
    daily_answer_date TEXT,
    daily_answer_index INTEGER,
    invited_by INTEGER,
    coins INTEGER DEFAULT 0,
    premium_until TEXT,
    is_verified INTEGER DEFAULT 0,
    verification_photo TEXT,
    verification_status TEXT DEFAULT 'none',
    swipe_date TEXT,
    swipe_count INTEGER DEFAULT 0,
    superlike_date TEXT,
    superlike_count INTEGER DEFAULT 0,
    matches_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_banned INTEGER DEFAULT 0,
    golden_match_date TEXT,
    registered_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS swipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user INTEGER,
    to_user INTEGER,
    liked INTEGER,
    super INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(from_user, to_user)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1 INTEGER,
    user2 INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user1, user2)
);

CREATE TABLE IF NOT EXISTS active_chats (
    user_id INTEGER PRIMARY KEY,
    partner_id INTEGER
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter INTEGER,
    reported INTEGER,
    reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocks (
    blocker INTEGER,
    blocked INTEGER,
    UNIQUE(blocker, blocked)
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()


async def upsert_user_field(user_id: int, **fields):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        exists = await cur.fetchone()
        if exists:
            set_clause = ", ".join(f"{k}=?" for k in fields)
            await db.execute(f"UPDATE users SET {set_clause} WHERE user_id=?", (*fields.values(), user_id))
        else:
            fields["user_id"] = user_id
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            await db.execute(f"INSERT INTO users ({cols}) VALUES ({placeholders})", tuple(fields.values()))
        await db.commit()


async def is_registered(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user["full_name"] and user["photos"])


async def complete_registration_launch_bonus(user_id: int):
    """در افتتاحیه، کاربر تازه‌ثبت‌نامی پریمیوم رایگان می‌گیرد."""
    if config.LAUNCH_DISCOUNT_ACTIVE:
        until = (date.today() + timedelta(days=config.LAUNCH_DISCOUNT_DAYS)).isoformat()
        await upsert_user_field(user_id, premium_until=until)


def is_premium_row(user_row) -> bool:
    if not user_row or not user_row["premium_until"]:
        return False
    try:
        return date.fromisoformat(user_row["premium_until"]) >= date.today()
    except ValueError:
        return False


async def set_invited_by(user_id: int, inviter_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET invited_by=? WHERE user_id=? AND invited_by IS NULL", (inviter_id, user_id)
        )
        await db.execute("UPDATE users SET coins = coins + 5 WHERE user_id=?", (inviter_id,))
        await db.commit()


async def get_today_question_and_answer(user_id: int):
    today = date.today().isoformat()
    idx = random.Random(today).randrange(len(DAILY_QUESTIONS))
    user = await get_user(user_id)
    answered = None
    if user and user["daily_answer_date"] == today:
        answered = user["daily_answer_index"]
    return idx, DAILY_QUESTIONS[idx], answered


async def save_daily_answer(user_id: int, option_index: int):
    today = date.today().isoformat()
    await upsert_user_field(user_id, daily_answer_date=today, daily_answer_index=option_index)


async def check_and_consume_swipe(user_id: int, limit: int) -> bool:
    """اگر سقف روزانه رد نشده، یک سوایپ مصرف می‌کند و True برمی‌گرداند."""
    today = date.today().isoformat()
    user = await get_user(user_id)
    count = user["swipe_count"] if user and user["swipe_date"] == today else 0
    if count >= limit:
        return False
    await upsert_user_field(user_id, swipe_date=today, swipe_count=count + 1)
    return True


async def check_and_consume_superlike(user_id: int, limit: int) -> bool:
    today = date.today().isoformat()
    user = await get_user(user_id)
    count = user["superlike_count"] if user and user["superlike_date"] == today else 0
    if count >= limit:
        return False
    await upsert_user_field(user_id, superlike_date=today, superlike_count=count + 1)
    return True


async def next_candidate(user_id: int, exclude_seen: bool = True):
    me = await get_user(user_id)
    if not me:
        return None

    query = """
        SELECT * FROM users
        WHERE user_id != ?
          AND is_active = 1
          AND is_banned = 0
          AND full_name IS NOT NULL
          AND photos IS NOT NULL
          AND user_id NOT IN (SELECT blocked FROM blocks WHERE blocker = ?)
          AND user_id NOT IN (SELECT blocker FROM blocks WHERE blocked = ?)
    """
    params = [user_id, user_id, user_id]
    if exclude_seen:
        query += " AND user_id NOT IN (SELECT to_user FROM swipes WHERE from_user = ?)"
        params.append(user_id)

    if me["looking_for"] and me["looking_for"] != "هر دو":
        query += " AND gender = ?"
        params.append(me["looking_for"])

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        province_query = query + " AND province = ? ORDER BY RANDOM() LIMIT 1"
        cur = await db.execute(province_query, params + [me["province"]])
        row = await cur.fetchone()
        if row is None:
            cur = await db.execute(query + " ORDER BY RANDOM() LIMIT 1", params)
            row = await cur.fetchone()
        return row


async def record_swipe(from_user: int, to_user: int, liked: bool, is_super: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO swipes (from_user, to_user, liked, super) VALUES (?, ?, ?, ?)",
            (from_user, to_user, int(liked), int(is_super)),
        )
        await db.commit()
        mutual = None
        if liked:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM swipes WHERE from_user=? AND to_user=? AND liked=1", (to_user, from_user)
            )
            other = await cur.fetchone()
            if other:
                u1, u2 = sorted([from_user, to_user])
                await db.execute("INSERT OR IGNORE INTO matches (user1, user2) VALUES (?, ?)", (u1, u2))
                await db.execute("UPDATE users SET matches_count = matches_count + 1 WHERE user_id IN (?, ?)", (u1, u2))
                await db.commit()
                mutual = True
        return mutual


async def get_matches(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM matches WHERE user1=? OR user2=?", (user_id, user_id))
        rows = await cur.fetchall()
        return [r["user2"] if r["user1"] == user_id else r["user1"] for r in rows]


async def start_chat(user_id: int, partner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO active_chats (user_id, partner_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET partner_id=excluded.partner_id", (user_id, partner_id)
        )
        await db.execute(
            "INSERT INTO active_chats (user_id, partner_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET partner_id=excluded.partner_id", (partner_id, user_id)
        )
        await db.commit()


async def end_chat(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT partner_id FROM active_chats WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        partner_id = row["partner_id"] if row else None
        await db.execute("DELETE FROM active_chats WHERE user_id=?", (user_id,))
        if partner_id:
            await db.execute("DELETE FROM active_chats WHERE user_id=?", (partner_id,))
        await db.commit()
        return partner_id


async def get_active_partner(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT partner_id FROM active_chats WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row["partner_id"] if row else None


async def block_user(blocker: int, blocked: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO blocks (blocker, blocked) VALUES (?, ?)", (blocker, blocked))
        await db.commit()
    await end_chat(blocker)


async def add_report(reporter: int, reported: int, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO reports (reporter, reported, reason) VALUES (?, ?, ?)", (reporter, reported, reason))
        await db.commit()


async def recent_reports(limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM reports ORDER BY id DESC LIMIT ?", (limit,))
        return await cur.fetchall()


async def set_ban(user_id: int, banned: bool):
    await upsert_user_field(user_id, is_banned=int(banned))


async def stats_summary():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = (await (await db.execute("SELECT COUNT(*) c FROM users WHERE full_name IS NOT NULL")).fetchone())["c"]
        today = date.today().isoformat()
        new_today = (await (await db.execute(
            "SELECT COUNT(*) c FROM users WHERE date(registered_at)=?", (today,)
        )).fetchone())["c"]
        matches = (await (await db.execute("SELECT COUNT(*) c FROM matches")).fetchone())["c"]
        premium = (await (await db.execute(
            "SELECT COUNT(*) c FROM users WHERE premium_until IS NOT NULL AND premium_until >= ?", (today,)
        )).fetchone())["c"]
        reports = (await (await db.execute("SELECT COUNT(*) c FROM reports")).fetchone())["c"]
        banned = (await (await db.execute("SELECT COUNT(*) c FROM users WHERE is_banned=1")).fetchone())["c"]
        return {
            "total": total, "new_today": new_today, "matches": matches,
            "premium": premium, "reports": reports, "banned": banned,
        }


async def all_active_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_active=1 AND is_banned=0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def top_active_users(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE full_name IS NOT NULL ORDER BY matches_count DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()


async def pending_verifications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE verification_status='pending'")
        return await cur.fetchall()


def compute_compatibility_basic(me_row, other_row) -> int:
    """درصد سازگاری پایه (بدون MBTI) برای نمایش سریع روی کارت مرور."""
    my_traits = set((me_row["traits"] or "").split(",")) - {""}
    other_traits = set((other_row["traits"] or "").split(",")) - {""}
    total = len(my_traits | other_traits) or 1
    common = len(my_traits & other_traits)
    base = int((common / total) * 60)
    bonus = 0
    today = date.today().isoformat()
    if (
        me_row["daily_answer_date"] == today
        and other_row["daily_answer_date"] == today
        and me_row["daily_answer_index"] == other_row["daily_answer_index"]
    ):
        bonus = 15
    if me_row["mbti"] and other_row["mbti"]:
        from data.mbti import compatibility_report
        mbti_score = compatibility_report(me_row["mbti"], other_row["mbti"])["score"]
        return min(100, int(base * 0.4 + bonus + mbti_score * 0.6))
    return min(100, base + bonus + 25)
