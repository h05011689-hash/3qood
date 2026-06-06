import os
import re
import sqlite3
import logging
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, LabeledPrice, ContentType
from telethon import TelegramClient, errors

# ================================================================
# الإعدادات
# ================================================================
API_TOKEN         = '8990468137:AAEljfy0vWa6YmTZ9Xa0n1c2Jpy8BcEp4RY'
ADMIN_USERNAME    = 'iiiiiiii_iiiii'
BOT_USERNAME      = 'ooasabot'
TELETHON_API_ID   = 34674538
TELETHON_API_HASH = '633785a3287407336e4c7421307fcbd8'

ACTIVATIONS_CHANNEL = '@ab_osv'
SUBSCRIBE_CHANNELS  = ['@Kaido_TG_KING', '@ab_osv']

ADMIN_ID = None

for folder in ['sessions', 'sessions_good', 'sessions_spam', 'sessions_old', 'uploaded_files']:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(level=logging.INFO)
bot     = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp      = Dispatcher(bot, storage=storage)

active_clients: dict = {}

# ================================================================
# قاعدة البيانات
# ================================================================
conn   = sqlite3.connect('levi_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0,
            referred_by INTEGER DEFAULT NULL,
            verified INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, prefix TEXT, price REAL
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            phone        TEXT,
            session_name TEXT,
            country_id   INTEGER,
            password_2fa TEXT,
            status       TEXT DEFAULT 'available',
            buyer_id     INTEGER,
            otp          TEXT
        );
    ''')
    conn.commit()
    _migrate()

def _migrate():
    cols   = [r[1] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if 'referred_by' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL")
        conn.commit()
    if 'verified' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
        conn.commit()

    cols   = [r[1] for r in cursor.execute("PRAGMA table_info(accounts)").fetchall()]
    needed = {
        'phone':        'ALTER TABLE accounts ADD COLUMN phone TEXT',
        'session_name': 'ALTER TABLE accounts ADD COLUMN session_name TEXT',
        'country_id':   'ALTER TABLE accounts ADD COLUMN country_id INTEGER',
        'password_2fa': 'ALTER TABLE accounts ADD COLUMN password_2fa TEXT',
        'status':       "ALTER TABLE accounts ADD COLUMN status TEXT DEFAULT 'available'",
        'buyer_id':     'ALTER TABLE accounts ADD COLUMN buyer_id INTEGER',
        'otp':          'ALTER TABLE accounts ADD COLUMN otp TEXT',
    }
    for col, sql in needed.items():
        if col not in cols:
            try:
                cursor.execute(sql); conn.commit()
            except Exception as e:
                logging.warning(f"Migration: {e}")

init_db()

# ================================================================
# FSM
# ================================================================
class AdminStates(StatesGroup):
    waiting_for_cat_name      = State()
    waiting_for_cat_prefix    = State()
    waiting_for_cat_price     = State()
    waiting_for_session_file  = State()
    waiting_for_session_phone = State()
    waiting_for_session_2fa   = State()
    checker_phone             = State()
    checker_code              = State()
    checker_2fa               = State()
    checker_cat               = State()
    waiting_for_numbers_file  = State()
    add_to_cat_session_file   = State()
    add_to_cat_phone          = State()
    add_to_cat_code           = State()
    add_to_cat_2fa            = State()
    gift_user_id              = State()
    gift_amount               = State()
    asia_approve_amount       = State()
    asia_reject_reason        = State()

class PaymentStates(StatesGroup):
    waiting_for_stars = State()

class AsiaTopUpStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_screenshot = State()

class CaptchaStates(StatesGroup):
    waiting_for_answer = State()

# ================================================================
# دوال مساعدة
# ================================================================
def get_user_balance(uid):
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    r = cursor.fetchone()
    return r[0] if r else 0.0

def add_user_if_not_exists(uid, username, referrer=None):
    cursor.execute("SELECT id, verified FROM users WHERE id=?", (uid,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO users (id, username, balance, referred_by, verified) VALUES (?,?,0.0,?,0)",
                       (uid, username, referrer))
        conn.commit()
        if referrer:
            cursor.execute("UPDATE users SET balance = balance + 0.01 WHERE id=?", (referrer,))
            conn.commit()
    else:
        cursor.execute("UPDATE users SET username=? WHERE id=?", (username, uid))
        conn.commit()

def is_user_verified(uid):
    cursor.execute("SELECT verified FROM users WHERE id=?", (uid,))
    r = cursor.fetchone()
    return r and r[0] == 1

def set_user_verified(uid):
    cursor.execute("UPDATE users SET verified=1 WHERE id=?", (uid,))
    conn.commit()

def get_accounts_count(cat_id):
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE country_id=? AND status='available'", (cat_id,))
    return cursor.fetchone()[0]

def mask_phone(phone: str) -> str:
    if phone.startswith('+'):
        phone = phone[1:]
    if len(phone) >= 7:
        return phone[:7] + '*' * (len(phone) - 7)
    return phone

def mask_user_id(uid: int) -> str:
    s = str(uid)
    if len(s) >= 5:
        return s[:5] + '*' * (len(s) - 5)
    return s

# --- دوال بناء الأزرار الملونة ---
def colored_button(text, callback_data, color):
    return {"text": text, "callback_data": callback_data, "style": color}

def colored_url_button(text, url, color):
    return {"text": text, "url": url, "style": color}

def colored_inline_keyboard(*rows):
    keyboard = []
    for row in rows:
        kb_row = []
        for btn in row:
            if isinstance(btn, dict):
                kb_row.append(btn)
            else:
                d = {"text": btn.text}
                if btn.callback_data:
                    d["callback_data"] = btn.callback_data
                if btn.url:
                    d["url"] = btn.url
                kb_row.append(d)
        keyboard.append(kb_row)
    return {"inline_keyboard": keyboard}

def cancel_markup():
    return colored_inline_keyboard([
        colored_button("❌ إلغاء", "admin_panel", "danger")
    ])

# --- التحقق من الاشتراك الإجباري في القناتين ---
async def is_subscribed(user_id) -> bool:
    try:
        for ch in SUBSCRIBE_CHANNELS:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except:
        return False

async def send_subscribe_message(chat_id, user_id):
    kb = colored_inline_keyboard(
        [colored_url_button("📢 اشترك في Kaido TG | KING", f"https://t.me/{SUBSCRIBE_CHANNELS[0].lstrip('@')}", "success")],
        [colored_url_button("📢 اشترك في قناة التفعيلات", f"https://t.me/{SUBSCRIBE_CHANNELS[1].lstrip('@')}", "danger")],
        [colored_button("🔄 تحقق من الاشتراك", "check_sub", "danger")]
    )
    await bot.send_message(chat_id,
        "⚠️ <b>يجب الاشتراك في القناتين أولاً لاستخدام البوت.</b>\n\n"
        "بعد الاشتراك، اضغط على زر التحقق.",
        reply_markup=kb)

# --- أسئلة التحقق العشوائية (كابتشا) ---
CAPTCHA_QUESTIONS = [
    {"q": "ما ناتج 5 + 3 ؟", "correct": "8", "wrong": ["6", "7", "9"]},
    {"q": "ما ناتج 12 - 4 ؟", "correct": "8", "wrong": ["7", "9", "6"]},
    {"q": "ما ناتج 3 × 4 ؟", "correct": "12", "wrong": ["10", "14", "9"]},
    {"q": "ما ناتج 15 ÷ 5 ؟", "correct": "3", "wrong": ["2", "4", "5"]},
    {"q": "أي لون هو لون السماء في النهار الصافي؟", "correct": "أزرق", "wrong": ["أخضر", "أحمر", "أصفر"]},
    {"q": "كم عدد الأيام في الأسبوع؟", "correct": "7", "wrong": ["5", "6", "8"]},
    {"q": "ما هو الحيوان الذي يُلقب بسفينة الصحراء؟", "correct": "الجمل", "wrong": ["الحصان", "الفيل", "الأسد"]},
]

def generate_captcha():
    item = random.choice(CAPTCHA_QUESTIONS)
    question = item["q"]
    correct = item["correct"]
    options = item["wrong"] + [correct]
    random.shuffle(options)
    return question, correct, options

def build_captcha_markup(options):
    colors = ["primary", "success", "danger", "primary"]
    buttons = []
    for i, opt in enumerate(options):
        buttons.append([colored_button(opt, f"captcha_{opt}", colors[i % len(colors)])])
    return colored_inline_keyboard(*buttons)

# --- القائمة الرئيسية ---
def get_main_markup(username):
    buttons = [
        [colored_button("🛒 شراء حساب", "buy_account", "success"),
         colored_url_button("📞 الدعم الفني", "https://t.me/Super_Zyrex1", "danger")],
        [colored_button("👥 الوكلاء", "agents_menu", "success"),
         colored_url_button("📢 قناة التفعيلات", "https://t.me/ab_osv", "danger")],
        [colored_button("💰 رصيدي", "my_balance", "success"),
         colored_url_button("👨‍💻 المطورين", "https://t.me/iiiiiiii_iiiii", "danger")],
        [colored_button("🔗 إحالة", "referral_link", "success"),
         colored_button("📦 مشترياتي", "my_purchases", "danger")],
    ]
    if username == ADMIN_USERNAME:
        buttons.append([colored_button("⚙️ لوحة التحكم للمطور", "admin_panel", "danger")])
    buttons.append([colored_button("💳 شحن رصيد", "add_balance", "primary")])
    return colored_inline_keyboard(*buttons)

def get_admin_markup():
    return colored_inline_keyboard(
        [colored_button("➕ إضافة قسم/دولة", "admin_add_cat", "danger")],
        [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "success")],
        [colored_button("📂 رفع ملف جلسة (.session)", "admin_add_session", "danger")],
        [colored_button("🔢 فحص رقم واحد + تسجيل دخول", "admin_check_single", "success")],
        [colored_button("📄 رفع ملف أرقام (numbers.txt)", "admin_upload_numbers", "danger")],
        [colored_button("🎁 منح رصيد لمستخدم", "admin_gift_balance", "success")],
        [colored_button("📊 إحصائيات", "admin_stats", "danger")],
        [colored_button("🔙 رجوع للقائمة", "main_menu", "success")]
    )

# ================================================================
# SpamBot & فحص
# ================================================================
async def check_spambot(client: TelegramClient) -> str:
    try:
        await client.send_message('spambot', '/start')
        await asyncio.sleep(3)
        msgs = await client.get_messages('spambot', limit=1)
        if msgs:
            t = msgs[0].message or ''
            return 'good' if ('Good news' in t or 'لا توجد قيود' in t) else 'spam'
        return 'unknown'
    except Exception:
        return 'error'

async def run_full_check(client: TelegramClient, phone: str, password_2fa: str = None):
    me = await client.get_me()
    is_premium = getattr(me, 'premium', False)
    spam_status = await check_spambot(client)
    groups = channels = 0
    try:
        from telethon.tl.functions.messages import GetDialogsRequest
        from telethon.tl.types import InputPeerEmpty, Channel, Chat as TLChat
        result = await client(GetDialogsRequest(
            offset_date=None, offset_id=0,
            offset_peer=InputPeerEmpty(), limit=500, hash=0
        ))
        for chat in result.chats:
            if isinstance(chat, Channel):
                channels += 1 if chat.broadcast else 0
                groups   += 0 if chat.broadcast else 1
            elif isinstance(chat, TLChat):
                groups += 1
    except Exception as ex:
        logging.warning(f"Dialogs: {ex}")
    is_old = me.id < 6_500_000_000
    spam_text = {
        'good':    '✅ سليم بدون قيود',
        'spam':    '🚫 عليه قيود سبام',
        'unknown': '❓ غير معروف',
        'error':   '⚠️ خطأ في الفحص',
    }.get(spam_status, '❓')
    result_text = (
        f"📊 <b>نتيجة الفحص</b>\n\n"
        f"📞 الرقم      : <code>{phone}</code>\n"
        f"👤 الاسم      : <b>{me.first_name or ''} {me.last_name or ''}</b>\n"
        f"🆔 ID         : <code>{me.id}</code>\n"
        f"⭐ Premium    : {'نعم ✅' if is_premium else 'لا ❌'}\n"
        f"🔎 SpamBot    : {spam_text}\n"
        f"👥 مجموعات   : <b>{groups}</b>\n"
        f"📢 قنوات      : <b>{channels}</b>\n"
        f"📅 العمر      : {'🕰️ قديم (قبل 2024)' if is_old else '🆕 جديد'}\n"
        f"🔐 2FA        : <code>{password_2fa or 'لا يوجد'}</code>\n\n"
    )
    return {
        'me': me,
        'is_premium': is_premium,
        'spam_status': spam_status,
        'groups': groups,
        'channels': channels,
        'is_old': is_old,
        'result_text': result_text,
    }

# ================================================================
# /start مع الاشتراك الإجباري والتحقق البشري
# ================================================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message, state: FSMContext):
    global ADMIN_ID
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_ID = message.chat.id

    if not await is_subscribed(message.from_user.id):
        await send_subscribe_message(message.chat.id, message.from_user.id)
        return

    referrer = None
    args = message.get_args()
    if args and args.startswith('ref'):
        try:
            referrer = int(args[3:])
        except:
            pass
    add_user_if_not_exists(message.from_user.id, message.from_user.username, referrer)

    if is_user_verified(message.from_user.id):
        bal = get_user_balance(message.from_user.id)
        await message.answer(
            f"أهلاً بك في - Kaido TG | KING 👋\n\n"
            f"🚀 وجهتك المميزة لخدمات تيليجرام الاحترافية بأفضل جودة وسرعة ⚡.\n\n"
            f"🆔 ايديك: <code>{message.from_user.id}</code>\n"
            f"💵 رصيدك: <code>{bal:.2f}$</code>\n\n"
            f"👍 ابدأ باستخدام البوت الآن واستمتع بجميع الخدمات المتاحة عبر الأزرار بالأسفل ⬇️.",
            reply_markup=get_main_markup(message.from_user.username)
        )
        return

    question, correct, options = generate_captcha()
    await state.update_data(captcha_correct=correct)
    await message.answer(
        f"🤖 <b>تأكيد أنك إنسان</b>\n\n{question}",
        reply_markup=build_captcha_markup(options)
    )
    await CaptchaStates.waiting_for_answer.set()

@dp.callback_query_handler(lambda c: c.data.startswith('captcha_'), state=CaptchaStates.waiting_for_answer)
async def captcha_answer(call: types.CallbackQuery, state: FSMContext):
    answer = call.data.split('_', 1)[1]
    data = await state.get_data()
    correct = data.get('captcha_correct', '')
    if answer == correct:
        set_user_verified(call.from_user.id)
        await state.finish()
        bal = get_user_balance(call.from_user.id)
        await call.message.edit_text(
            f"✅ <b>تم التحقق بنجاح!</b>\n\n"
            f"أهلاً بك في - Kaido TG | KING 👋\n\n"
            f"🆔 ايديك: <code>{call.from_user.id}</code>\n"
            f"💵 رصيدك: <code>{bal:.2f}$</code>",
            reply_markup=get_main_markup(call.from_user.username)
        )
    else:
        await call.answer("❌ إجابة خاطئة، حاول مرة أخرى.", show_alert=True)

@dp.callback_query_handler(text="check_sub")
async def check_subscription(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        add_user_if_not_exists(call.from_user.id, call.from_user.username)
        if not is_user_verified(call.from_user.id):
            question, correct, options = generate_captcha()
            state = dp.current_state(chat=call.message.chat.id, user=call.from_user.id)
            await state.update_data(captcha_correct=correct)
            await call.message.edit_text(
                f"🤖 <b>تأكيد أنك إنسان</b>\n\n{question}",
                reply_markup=build_captcha_markup(options)
            )
            await CaptchaStates.waiting_for_answer.set()
            return
        bal = get_user_balance(call.from_user.id)
        await call.message.edit_text(
            f"✅ <b>تم التحقق من الاشتراك.</b>\n\n"
            f"أهلاً بك في - Kaido TG | KING 👋\n\n"
            f"🆔 ايديك: <code>{call.from_user.id}</code>\n"
            f"💵 رصيدك: <code>{bal:.2f}$</code>",
            reply_markup=get_main_markup(call.from_user.username)
        )
    else:
        await call.answer("❌ لم تشترك في القناتين بعد. يرجى الاشتراك ثم الضغط على التحقق.", show_alert=True)

@dp.callback_query_handler(text="main_menu", state="*")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
    if not await is_subscribed(call.from_user.id):
        await send_subscribe_message(call.message.chat.id, call.from_user.id)
        await state.finish()
        return
    if not is_user_verified(call.from_user.id):
        await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
        return
    await state.finish()
    client = active_clients.pop(call.from_user.id, None)
    if client and client.is_connected():
        await client.disconnect()
    bal = get_user_balance(call.from_user.id)
    await call.message.edit_text(
        f"أهلاً بك في - Kaido TG | KING 👋\n\n"
        f"🚀 وجهتك المميزة لخدمات تيليجرام الاحترافية بأفضل جودة وسرعة ⚡.\n\n"
        f"🆔 ايديك: <code>{call.from_user.id}</code>\n"
        f"💵 رصيدك: <code>{bal:.2f}$</code>",
        reply_markup=get_main_markup(call.from_user.username)
    )

# ================================================================
# دوال القائمة الرئيسية
# ================================================================
@dp.callback_query_handler(text="my_balance")
async def my_balance(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    bal = get_user_balance(call.from_user.id)
    await call.answer(f"💰 رصيدك: ${bal:.2f}", show_alert=True)

@dp.callback_query_handler(text="referral_link")
async def referral_link(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref{call.from_user.id}"
    await call.message.edit_text(
        f"🔗 <b>رابط الإحالة الخاص بك:</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 عند دخول شخص جديد لأول مرة عبر رابطك، ستكسب <b>$0.01</b> تلقائياً.",
        reply_markup=colored_inline_keyboard([colored_button("🔙 رجوع", "main_menu", "danger")])
    )

@dp.callback_query_handler(text="my_purchases")
async def my_purchases(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    cursor.execute(
        "SELECT a.phone, c.name, c.price FROM accounts a LEFT JOIN categories c ON a.country_id = c.id WHERE a.buyer_id=? AND a.status='sold'",
        (call.from_user.id,)
    )
    purchases = cursor.fetchall()
    if not purchases:
        await call.answer("❌ لم تقم بأي عملية شراء بعد.", show_alert=True)
        return
    text = "📦 <b>مشترياتك:</b>\n\n"
    for p in purchases:
        phone = mask_phone(p[0]) if p[0] else "غير معروف"
        text += f"🌍 {p[1]} | 📞 {phone} | 💵 ${p[2]:.2f}\n"
    text += f"\n🔢 <b>إجمالي المشتريات:</b> {len(purchases)}"
    await call.message.edit_text(
        text,
        reply_markup=colored_inline_keyboard([colored_button("🔙 رجوع", "main_menu", "danger")])
    )

# --- قسم الوكلاء ---
@dp.callback_query_handler(text="agents_menu")
async def agents_menu(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    text = (
        "مرحباً بك في قسم الوكلاء، هنا قائمة بوكلاء Kaido TG | KING تم اعتمادهم من الإدارة شخصياً.\n\n"
        "✅ يمكنك شحن البوت عبرهم بكل ثقة وأمان، وبضمان من الإدارة رسميًا.\n"
        "⚠️ في حال لاحظت من أحدهم أي تصرف غير لائق، يرجى إبلاغنا فورًا."
    )
    kb = colored_inline_keyboard([
        colored_url_button("الوكيل @Super_Zyrex1", "https://t.me/Super_Zyrex1", "primary"),
        colored_button("🔙 رجوع", "main_menu", "danger")
    ])
    await call.message.edit_text(text, reply_markup=kb)

# ================================================================
# لوحة المطور (بما في ذلك إدارة الأقسام مع الحذف)
# ================================================================
@dp.callback_query_handler(text="admin_panel", state="*")
async def admin_panel(call: types.CallbackQuery, state: FSMContext):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔ للمطور فقط.", show_alert=True)
    await state.finish()
    await call.message.edit_text("⚙️ <b>لوحة تحكم المطور</b>", reply_markup=get_admin_markup())

@dp.callback_query_handler(text="admin_stats")
async def admin_stats(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cursor.execute("SELECT COUNT(*) FROM users"); u = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='available'"); av = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'"); so = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM categories"); ca = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance) FROM users"); bal = cursor.fetchone()[0] or 0
    m = colored_inline_keyboard([colored_button("🔙 رجوع", "admin_panel", "danger")])
    await call.message.edit_text(
        f"📊 <b>إحصائيات</b>\n\n"
        f"👥 مستخدمون: <b>{u}</b>\n"
        f"🟢 حسابات متاحة: <b>{av}</b>\n"
        f"✅ مباعة: <b>{so}</b>\n"
        f"🌍 أقسام: <b>{ca}</b>\n"
        f"💵 إجمالي الأرصدة: <b>${bal:.2f}</b>",
        reply_markup=m
    )

@dp.callback_query_handler(text="admin_gift_balance")
async def gift_balance_start(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("🎁 <b>منح رصيد لمستخدم</b>\n\nأرسل آيدي المستخدم الرقمي:", reply_markup=cancel_markup())
    await AdminStates.gift_user_id.set()

@dp.message_handler(state=AdminStates.gift_user_id)
async def gift_balance_get_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ أرسل آيدي رقمي صحيح.")
    uid = int(message.text)
    await state.update_data(gift_uid=uid)
    await message.answer(f"💰 كم المبلغ الذي تريد منحه للمستخدم <code>{uid}</code>؟\nمثال: <code>10.5</code>")
    await AdminStates.gift_amount.set()

@dp.message_handler(state=AdminStates.gift_amount)
async def gift_balance_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError: return await message.answer("❌ أرسل رقماً موجباً صحيحاً.")
    data = await state.get_data()
    uid = data['gift_uid']
    add_user_if_not_exists(uid, None)
    current = get_user_balance(uid)
    new_bal = current + amount
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, uid))
    conn.commit()
    await message.answer(
        f"✅ <b>تم منح الرصيد بنجاح!</b>\n"
        f"👤 المستخدم: <code>{uid}</code>\n"
        f"💵 المبلغ المضاف: ${amount:.2f}\n"
        f"💰 رصيده الحالي: ${new_bal:.2f}",
        reply_markup=get_admin_markup()
    )
    await state.finish()

# ================================================================
# إدارة الأقسام (مع خيار الحذف)
# ================================================================
@dp.callback_query_handler(text="admin_manage_cats")
async def admin_manage_cats(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cursor.execute("SELECT id, name, prefix, price FROM categories")
    cats = cursor.fetchall()
    if not cats:
        m = colored_inline_keyboard([colored_button("🔙 رجوع", "admin_panel", "danger")])
        return await call.message.edit_text("❌ لا توجد أقسام بعد.", reply_markup=m)
    rows = []
    for cat in cats:
        count = get_accounts_count(cat[0])
        rows.append([colored_button(
            f"📁 {cat[1]} ({cat[2]}) | متاح: {count} | ${cat[3]:.2f}",
            f"cat_manage_{cat[0]}", "danger"
        )])
    rows.append([colored_button("🔙 رجوع", "admin_panel", "success")])
    m = colored_inline_keyboard(*rows)
    await call.message.edit_text("📋 <b>اختر قسماً لإدارته:</b>", reply_markup=m)

@dp.callback_query_handler(lambda c: c.data.startswith('cat_manage_'))
async def cat_manage(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    cursor.execute("SELECT name, prefix, price FROM categories WHERE id=?", (cat_id,))
    cat = cursor.fetchone()
    if not cat: return await call.answer("❌ القسم غير موجود.", show_alert=True)
    count = get_accounts_count(cat_id)
    m = colored_inline_keyboard(
        [colored_button("📲 إضافة رقم (تسجيل دخول + فحص)", f"addcat_phone_{cat_id}", "danger")],
        [colored_button("📂 إضافة .session (فحص)", f"addcat_session_{cat_id}", "success")],
        [colored_button("🗑️ حذف القسم", f"delete_cat_{cat_id}", "primary")],
        [colored_button("🔙 رجوع للأقسام", "admin_manage_cats", "danger")]
    )
    await call.message.edit_text(
        f"📁 <b>قسم:</b> {cat[0]}\n"
        f"🔢 البادئة: <code>{cat[1]}</code> | 💵 السعر: <code>${cat[2]:.2f}</code>\n"
        f"🟢 الحسابات المتاحة: <b>{count}</b>\n\n"
        f"اختر العملية:", reply_markup=m
    )

@dp.callback_query_handler(lambda c: c.data.startswith('delete_cat_'))
async def delete_cat_confirm(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    cursor.execute("SELECT name FROM categories WHERE id=?", (cat_id,))
    cat = cursor.fetchone()
    if not cat: return await call.answer("❌ القسم غير موجود.", show_alert=True)
    kb = colored_inline_keyboard([
        colored_button("✅ نعم، احذف", f"confirm_delete_cat_{cat_id}", "danger"),
        colored_button("❌ إلغاء", f"cat_manage_{cat_id}", "success")
    ])
    await call.message.edit_text(
        f"⚠️ <b>هل أنت متأكد من حذف قسم \"{cat[0]}\"؟</b>\n"
        f"سيتم حذف جميع الحسابات المرتبطة به نهائياً.",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_cat_'))
async def confirm_delete_cat(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    cursor.execute("DELETE FROM accounts WHERE country_id=?", (cat_id,))
    cursor.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    await call.message.edit_text("✅ <b>تم حذف القسم وجميع حساباته بنجاح.</b>",
                                 reply_markup=colored_inline_keyboard([colored_button("🔙 رجوع", "admin_manage_cats", "success")]))

# ================================================================
# إضافة رقم لقسم (فحص تلقائي)
# ================================================================
@dp.callback_query_handler(lambda c: c.data.startswith('addcat_phone_'))
async def addcat_phone_start(call: types.CallbackQuery, state: FSMContext):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    await state.update_data(target_cat_id=cat_id)
    await call.message.edit_text("📲 أرسل الرقم مع كود الدولة:", reply_markup=cancel_markup())
    await AdminStates.add_to_cat_phone.set()

@dp.message_handler(state=AdminStates.add_to_cat_phone)
async def addcat_got_phone(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not re.match(r'^\+\d{7,15}$', number):
        return await message.answer("❌ صيغة غير صحيحة.", reply_markup=cancel_markup())
    session_path = os.path.join('sessions', number.replace('+', ''))
    client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)
    try:
        await client.connect()
        sent = await client.send_code_request(number)
        active_clients[message.from_user.id] = client
        await state.update_data(phone=number, phone_code_hash=sent.phone_code_hash, session_path=session_path)
        await message.answer(f"📲 تم إرسال الكود. أرسل الكود:", reply_markup=cancel_markup())
        await AdminStates.add_to_cat_code.set()
    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ خطأ: {e}")
        await state.finish()

@dp.message_handler(state=AdminStates.add_to_cat_code)
async def addcat_got_code(message: types.Message, state: FSMContext):
    code = message.text.strip().replace(' ', '')
    data = await state.get_data()
    client = active_clients.get(message.from_user.id)
    if not client: await state.finish(); return await message.answer("❌ انتهت الجلسة.")
    try:
        await client.sign_in(data['phone'], code, phone_code_hash=data['phone_code_hash'])
        await _addcat_do_check(message, state, client)
    except errors.SessionPasswordNeededError:
        await message.answer("🔐 أرسل 2FA:", reply_markup=cancel_markup())
        await AdminStates.add_to_cat_2fa.set()
    except Exception as e:
        active_clients.pop(message.from_user.id, None); await client.disconnect()
        await message.answer(f"❌ خطأ: {e}"); await state.finish()

@dp.message_handler(state=AdminStates.add_to_cat_2fa)
async def addcat_got_2fa(message: types.Message, state: FSMContext):
    password = message.text.strip()
    client = active_clients.get(message.from_user.id)
    if not client: await state.finish(); return await message.answer("❌ انتهت الجلسة.")
    try:
        await client.sign_in(password=password)
        await state.update_data(password_2fa=password)
        await _addcat_do_check(message, state, client)
    except Exception as e:
        active_clients.pop(message.from_user.id, None); await client.disconnect()
        await message.answer(f"❌ خطأ: {e}"); await state.finish()

async def _addcat_do_check(message, state, client):
    data = await state.get_data()
    phone = data['phone']; cat_id = data['target_cat_id']; password_2fa = data.get('password_2fa', 'لا يوجد')
    try:
        check = await run_full_check(client, phone, password_2fa)
        await client.disconnect(); active_clients.pop(message.from_user.id, None)
        session_name = phone.replace('+', '') + '.session'
        cursor.execute("INSERT INTO accounts (phone, session_name, country_id, password_2fa, status) VALUES (?,?,?,?,?)",
                       (phone, session_name, cat_id, password_2fa, 'available'))
        conn.commit()
        cat_name = cursor.execute("SELECT name FROM categories WHERE id=?", (cat_id,)).fetchone()[0]
        count = get_accounts_count(cat_id)
        m = colored_inline_keyboard(
            [colored_button("➕ إضافة رقم آخر", f"addcat_phone_{cat_id}", "danger")],
            [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "success")],
            [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
        )
        await message.answer(check['result_text'] + f"✅ تم الحفظ في {cat_name}\n🟢 المتاح: {count}", reply_markup=m)
        await state.finish()
    except Exception as e:
        logging.error(f"_addcat_do_check: {e}")
        if client.is_connected(): await client.disconnect()
        active_clients.pop(message.from_user.id, None)
        await message.answer(f"❌ خطأ: {e}"); await state.finish()

# دوال .session للقسم (فحص تلقائي) - اختصار
@dp.callback_query_handler(lambda c: c.data.startswith('addcat_session_'))
async def addcat_session_start(call: types.CallbackQuery, state: FSMContext):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    await state.update_data(target_cat_id=cat_id)
    await call.message.edit_text("📂 أرسل ملف .session:", reply_markup=cancel_markup())
    await AdminStates.add_to_cat_session_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.add_to_cat_session_file)
async def addcat_got_session_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.session'): return await message.answer("❌ أرسل ملف .session فقط.")
    data = await state.get_data(); cat_id = data['target_cat_id']
    fname = message.document.file_name; session_name = fname
    session_path_full = os.path.join('sessions', fname)
    await message.document.download(destination_file=session_path_full)
    raw = fname.replace('.session', ''); phone = f"+{raw}" if raw.isdigit() else None
    session_path_noext = os.path.join('sessions', raw)
    client = TelegramClient(session_path_noext, TELETHON_API_ID, TELETHON_API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect(); await message.answer("❌ الجلسة غير مصرحة.", reply_markup=get_admin_markup()); await state.finish(); return
        me = await client.get_me()
        if not phone: phone = f"+{me.phone}" if me.phone else str(me.id)
        check = await run_full_check(client, phone)
        await client.disconnect()
        cursor.execute("INSERT INTO accounts (phone, session_name, country_id, password_2fa, status) VALUES (?,?,?,?,?)",
                       (phone, session_name, cat_id, 'لا يوجد', 'available'))
        conn.commit()
        cat_name = cursor.execute("SELECT name FROM categories WHERE id=?", (cat_id,)).fetchone()[0]
        count = get_accounts_count(cat_id)
        m = colored_inline_keyboard(
            [colored_button("➕ رفع جلسة أخرى", f"addcat_session_{cat_id}", "danger")],
            [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "success")],
            [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
        )
        await message.answer(check['result_text'] + f"✅ تم الحفظ في {cat_name}\n🟢 المتاح: {count}", reply_markup=m)
        await state.finish()
    except Exception as e:
        logging.error(f"addcat_session: {e}")
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: {e}", reply_markup=get_admin_markup()); await state.finish()

# ================================================================
# CHECKER (فحص رقم واحد)
# ================================================================
@dp.callback_query_handler(text="admin_check_single")
async def checker_start(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("🔢 أرسل الرقم مع كود الدولة:", reply_markup=cancel_markup())
    await AdminStates.checker_phone.set()

@dp.message_handler(state=AdminStates.checker_phone)
async def checker_got_phone(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not re.match(r'^\+\d{7,15}$', number): return await message.answer("❌ صيغة غير صحيحة.")
    session_path = os.path.join('sessions', number.replace('+', ''))
    client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)
    try:
        await client.connect(); sent = await client.send_code_request(number)
        active_clients[message.from_user.id] = client
        await state.update_data(phone=number, phone_code_hash=sent.phone_code_hash, session_path=session_path)
        await message.answer(f"📲 تم إرسال الكود. أرسله هنا:", reply_markup=cancel_markup())
        await AdminStates.checker_code.set()
    except Exception as e: await client.disconnect(); await message.answer(f"❌ خطأ: {e}"); await state.finish()

@dp.message_handler(state=AdminStates.checker_code)
async def checker_got_code(message: types.Message, state: FSMContext):
    code = message.text.strip().replace(' ', '')
    data = await state.get_data(); client = active_clients.get(message.from_user.id)
    if not client: await state.finish(); return await message.answer("❌ انتهت الجلسة.")
    try:
        await client.sign_in(data['phone'], code, phone_code_hash=data['phone_code_hash'])
        await _checker_finish(message, state, client, data['phone'])
    except errors.SessionPasswordNeededError:
        await message.answer("🔐 أرسل 2FA:", reply_markup=cancel_markup())
        await AdminStates.checker_2fa.set()
    except Exception as e: active_clients.pop(message.from_user.id, None); await client.disconnect(); await message.answer(f"❌ خطأ: {e}"); await state.finish()

@dp.message_handler(state=AdminStates.checker_2fa)
async def checker_got_2fa(message: types.Message, state: FSMContext):
    password = message.text.strip(); client = active_clients.get(message.from_user.id)
    data = await state.get_data()
    if not client: await state.finish(); return await message.answer("❌ انتهت الجلسة.")
    try:
        await client.sign_in(password=password); await state.update_data(password_2fa=password)
        await _checker_finish(message, state, client, data['phone'])
    except Exception as e: active_clients.pop(message.from_user.id, None); await client.disconnect(); await message.answer(f"❌ خطأ: {e}"); await state.finish()

async def _checker_finish(message, state, client, phone):
    try:
        data = await state.get_data(); password_2fa = data.get('password_2fa', 'لا يوجد')
        check = await run_full_check(client, phone, password_2fa)
        await client.disconnect(); active_clients.pop(message.from_user.id, None)
        cursor.execute("SELECT id, name FROM categories"); cats = cursor.fetchall()
        if not cats:
            session_name = phone.replace('+', '') + '.session'
            cursor.execute("INSERT INTO accounts (phone,session_name,password_2fa,status) VALUES (?,?,?,?)",
                           (phone, session_name, password_2fa, 'available')); conn.commit()
            await message.answer(check['result_text'] + "⚠️ لا توجد أقسام.", reply_markup=get_admin_markup()); await state.finish(); return
        await state.update_data(spam_status=check['spam_status'], is_old=check['is_old'], is_premium=check['is_premium'],
                                groups=check['groups'], channels=check['channels'], password_2fa=password_2fa, result_text=check['result_text'])
        rows = [[colored_button(c[1], f"checker_cat_{c[0]}", "danger")] for c in cats]
        rows.append([colored_button("🔙 إلغاء الحفظ", "checker_skip", "success")])
        markup = colored_inline_keyboard(*rows)
        await message.answer(check['result_text'] + "🌍 اختر القسم:", reply_markup=markup)
        await AdminStates.checker_cat.set()
    except Exception as e: logging.error(f"checker_finish: {e}"); await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('checker_cat_'), state=AdminStates.checker_cat)
async def checker_save_account(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split('_')[2]); data = await state.get_data(); phone = data['phone']
    session_name = phone.replace('+', '') + '.session'
    cursor.execute("INSERT INTO accounts (phone,session_name,country_id,password_2fa,status) VALUES (?,?,?,?,?)",
                   (phone, session_name, cat_id, data.get('password_2fa','لا يوجد'), 'available')); conn.commit()
    await call.message.edit_text(f"✅ تم حفظ الحساب!\n📞 <code>{phone}</code>", reply_markup=get_admin_markup()); await state.finish()

@dp.callback_query_handler(text="checker_skip", state=AdminStates.checker_cat)
async def checker_skip_save(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("⚠️ تم إلغاء الحفظ."); await state.finish()

# ================================================================
# رفع ملف أرقام / إضافة قسم / رفع جلسة (بدون فحص)
# ================================================================
@dp.callback_query_handler(text="admin_upload_numbers")
async def admin_upload_numbers(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("📄 أرسل ملف .txt:", reply_markup=cancel_markup())
    await AdminStates.waiting_for_numbers_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.waiting_for_numbers_file)
async def process_numbers_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.txt'): return await message.answer("❌ أرسل ملف .txt فقط.")
    await message.document.download(destination_file="numbers.txt"); await state.finish()
    await message.answer("✅ تم حفظ numbers.txt", reply_markup=get_admin_markup())

@dp.callback_query_handler(text="admin_add_cat")
async def admin_add_cat(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("📝 أرسل اسم الدولة:", reply_markup=cancel_markup())
    await AdminStates.waiting_for_cat_name.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_name)
async def process_cat_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text); await message.answer("🔢 أرسل رمز الدولة:"); await AdminStates.waiting_for_cat_prefix.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_prefix)
async def process_cat_prefix(message: types.Message, state: FSMContext):
    await state.update_data(prefix=message.text); await message.answer("💵 أرسل السعر:"); await AdminStates.waiting_for_cat_price.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_price)
async def process_cat_price(message: types.Message, state: FSMContext):
    try: price = float(message.text)
    except ValueError: return await message.answer("❌ أرسل رقم صحيح.")
    data = await state.get_data()
    cursor.execute("INSERT INTO categories (name,prefix,price) VALUES (?,?,?)", (data['name'], data['prefix'], price))
    conn.commit(); new_cat_id = cursor.lastrowid
    m = colored_inline_keyboard(
        [colored_button("📲 إضافة رقم للقسم", f"addcat_phone_{new_cat_id}", "danger")],
        [colored_button("📂 إضافة .session للقسم", f"addcat_session_{new_cat_id}", "success")],
        [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
    )
    await message.answer(f"✅ تم إضافة القسم!\n🌍 {data['name']} | 💵 ${price:.2f}", reply_markup=m); await state.finish()

@dp.callback_query_handler(text="admin_add_session")
async def admin_add_session(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("📂 أرسل ملف .session:", reply_markup=cancel_markup())
    await AdminStates.waiting_for_session_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.waiting_for_session_file)
async def process_session_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.session'): return await message.answer("❌ أرسل ملف .session فقط.")
    file_path = f"sessions/{message.document.file_name}"; await message.document.download(destination_file=file_path)
    await state.update_data(session_name=message.document.file_name); await message.answer("📞 أرسل رقم الهاتف:"); await AdminStates.waiting_for_session_phone.set()

@dp.message_handler(state=AdminStates.waiting_for_session_phone)
async def process_session_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip()); await message.answer("🔐 أرسل 2FA أو اكتب: لا يوجد"); await AdminStates.waiting_for_session_2fa.set()

@dp.message_handler(state=AdminStates.waiting_for_session_2fa)
async def process_session_2fa(message: types.Message, state: FSMContext):
    await state.update_data(password_2fa=message.text.strip())
    cursor.execute("SELECT id, name FROM categories"); cats = cursor.fetchall()
    if not cats: await state.finish(); return await message.answer("❌ لا توجد أقسام.", reply_markup=get_admin_markup())
    rows = [[colored_button(c[1], f"set_cat_{c[0]}", "danger")] for c in cats]
    await message.answer("🌍 اختر الدولة:", reply_markup=colored_inline_keyboard(*rows))
    await state.set_state("waiting_for_category_selection")

@dp.callback_query_handler(lambda c: c.data.startswith('set_cat_'), state="waiting_for_category_selection")
async def save_account_final(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split('_')[2]); data = await state.get_data()
    cursor.execute("INSERT INTO accounts (phone,session_name,country_id,password_2fa,status) VALUES (?,?,?,?,?)",
                   (data['phone'], data['session_name'], cat_id, data['password_2fa'], 'available')); conn.commit()
    await call.message.edit_text("✅ تم حفظ الجلسة!", reply_markup=get_admin_markup()); await state.finish()

# ================================================================
# شراء الحسابات
# ================================================================
@dp.callback_query_handler(text="buy_account")
async def user_buy_account(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    cursor.execute("SELECT id, name, prefix, price FROM categories"); cats = cursor.fetchall()
    if not cats: return await call.answer("❌ لا تتوفر أقسام.", show_alert=True)
    rows = []
    for cat in cats:
        count = get_accounts_count(cat[0])
        emoji = "🟢" if count > 0 else "🔴"
        rows.append([colored_button(f"{emoji} {cat[1]} ({cat[2]}) | متاح: {count} | ${cat[3]:.2f}", f"buy_cat_{cat[0]}", "danger")])
    rows.append([colored_button("🔙 العودة", "main_menu", "success")])
    await call.message.edit_text("🛍️ <b>اختر الدولة:</b>", reply_markup=colored_inline_keyboard(*rows))

@dp.callback_query_handler(lambda c: c.data.startswith('buy_cat_'))
async def process_purchase(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    cat_id = int(call.data.split('_')[2])
    cat_info = cursor.execute("SELECT name, price FROM categories WHERE id=?", (cat_id,)).fetchone()
    if not cat_info: return await call.answer("❌ القسم غير موجود.", show_alert=True)
    account = cursor.execute("SELECT id, phone, session_name, password_2fa FROM accounts WHERE country_id=? AND status='available' LIMIT 1", (cat_id,)).fetchone()
    if not account: return await call.answer("❌ نفذت الأرقام.", show_alert=True)
    bal = get_user_balance(call.from_user.id)
    if bal < cat_info[1]: return await call.answer(f"❌ رصيدك غير كاف. السعر: ${cat_info[1]:.2f}", show_alert=True)
    new_bal = bal - cat_info[1]
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, call.from_user.id))
    cursor.execute("UPDATE accounts SET status='pending', buyer_id=? WHERE id=?", (call.from_user.id, account[0]))
    conn.commit()
    m = colored_inline_keyboard(
        [colored_button("📥 جلب كود التحقق (OTP)", f"get_otp_{account[0]}", "danger")],
        [colored_button("🔐 جلب كلمة السر (2FA)", f"get_2fa_{account[0]}", "success")],
        [colored_button("✅ تم تسجيل الدخول", f"confirm_login_{account[0]}", "danger")]
    )
    await call.message.edit_text(f"🎉 <b>تم الشراء!</b>\n📞 <code>{account[1]}</code>\n💰 رصيدك: ${new_bal:.2f}", reply_markup=m)

@dp.callback_query_handler(lambda c: c.data.startswith('get_otp_'))
async def get_otp_callback(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    acc_id = int(call.data.split('_')[2])
    acc = cursor.execute("SELECT session_name, buyer_id FROM accounts WHERE id=?", (acc_id,)).fetchone()
    if not acc or acc[1] != call.from_user.id: return await call.answer("❌ غير مسموح.", show_alert=True)
    session_path = f"sessions/{acc[0]}"
    try:
        client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH); await client.connect()
        if not await client.is_user_authorized(): await client.disconnect(); return await call.message.answer("❌ الجلسة منتهية.")
        otp = None
        async for msg in client.iter_messages(777000, limit=5):
            if msg.text:
                match = re.search(r'\b(\d{5,6})\b', msg.text)
                if match: otp = match.group(1); break
        await client.disconnect()
        if otp:
            cursor.execute("UPDATE accounts SET otp=? WHERE id=?", (otp, acc_id)); conn.commit()
            await call.message.answer(f"📩 <b>كود التحقق:</b> <code>{otp}</code>")
        else: await call.message.answer("⏳ الكود لم يصل بعد.")
    except Exception as e: await call.message.answer(f"❌ خطأ: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('get_2fa_'))
async def get_2fa_callback(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    acc_id = int(call.data.split('_')[2])
    acc = cursor.execute("SELECT password_2fa, buyer_id FROM accounts WHERE id=?", (acc_id,)).fetchone()
    if not acc or acc[1] != call.from_user.id: return await call.answer("❌ غير مسموح.", show_alert=True)
    await call.message.answer(f"🔐 <b>كلمة السر (2FA):</b> <code>{acc[0]}</code>")

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_login_'))
async def confirm_login_callback(call: types.CallbackQuery):
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    acc_id = int(call.data.split('_')[2])
    acc = cursor.execute("SELECT session_name, buyer_id, phone, country_id, otp FROM accounts WHERE id=?", (acc_id,)).fetchone()
    if not acc or acc[1] != call.from_user.id: return await call.answer("❌ غير مسموح.", show_alert=True)
    session_path = f"sessions/{acc[0]}"
    try:
        client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH); await client.connect()
        if await client.is_user_authorized(): await client.log_out()
        await client.disconnect()
    except Exception as e: logging.error(f"confirm_login: {e}")
    finally:
        if os.path.exists(session_path):
            try: os.remove(session_path)
            except: pass
        cursor.execute("UPDATE accounts SET status='sold' WHERE id=?", (acc_id,)); conn.commit()
        cat_name, price = "", 0.0
        if acc[3]:
            cat_info = cursor.execute("SELECT name, price FROM categories WHERE id=?", (acc[3],)).fetchone()
            if cat_info: cat_name, price = cat_info
        phone_masked = mask_phone(acc[2]) if acc[2] else "غير معروف"
        buyer_masked = mask_user_id(call.from_user.id)
        otp_code = acc[4] if acc[4] else "----"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_text = (
            "✅ تم شراء حساب جديد من البوت\n\n"
            f"🌍 الدولة: {cat_name}\n"
            f"📱 المنصة: تليجرام\n"
            f"📞 الرقم: {phone_masked}\n"
            f"💰 السعر: $ {price:.2f}\n"
            f"👤 العميل: {buyer_masked}\n"
            f"🔑 كود التفعيل: {otp_code}\n"
            f"✅ الحالة: تم التفعيل\n\n"
            f"📅 التاريخ والوقت: {now}"
        )
        try: await bot.send_message(ACTIVATIONS_CHANNEL, msg_text)
        except Exception as e: logging.error(f"Failed to send to channel: {e}")
        await call.message.edit_text("✨ <b>تم تفعيل الحساب بنجاح. شكراً! 🎉</b>")

# ================================================================
# شحن الرصيد (النجوم + آسيا)
# ================================================================
@dp.callback_query_handler(text="add_balance")
async def add_balance_choose(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    m = colored_inline_keyboard(
        [colored_button("⭐ شحن بالنجوم (Telegram Stars)", "pay_stars", "danger")],
        [colored_button("🌏 شحن عبر آسيا", "pay_asia", "success")],
        [colored_button("🔙 رجوع", "main_menu", "danger")]
    )
    await call.message.edit_text("💳 <b>اختر طريقة الشحن:</b>", reply_markup=m)

@dp.callback_query_handler(text="pay_stars")
async def ask_stars(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    m = colored_inline_keyboard([colored_button("🔙 رجوع", "add_balance", "danger")])
    await call.message.edit_text(
        "⭐ <b>شحن بالنجوم</b>\n\n"
        "أدخل عدد النجوم (1 — 10000):\n"
        "<i>كل نجمة = $0.01  (10 نجوم = $0.10)</i>",
        reply_markup=m
    )
    await PaymentStates.waiting_for_stars.set()

@dp.message_handler(state=PaymentStates.waiting_for_stars)
async def process_stars(message: types.Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id): return await message.answer("⚠️ اشترك أولاً")
    if not is_user_verified(message.from_user.id): return await message.answer("يرجى إكمال التحقق البشري أولاً.")
    if not message.text.isdigit() or not (1 <= int(message.text) <= 10000):
        return await message.answer("❌ أدخل رقم بين 1 و 10000.")
    amount = int(message.text)
    added_dollars = amount * 0.01
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="شحن رصيد ZZ",
        description=f"شحن {amount} نجمة (= ${added_dollars:.2f})",
        payload="add_balance_payload",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="النجوم", amount=amount)]
    )
    await state.finish()

@dp.pre_checkout_query_handler(lambda q: True)
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    stars = message.successful_payment.total_amount
    added = stars * 0.01
    new_bal = get_user_balance(message.from_user.id) + added
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, message.from_user.id))
    conn.commit()
    await message.answer(
        f"💳 <b>تم الشحن بنجاح!</b>\n"
        f"✨ النجوم: {stars} | 💵 المضاف: ${added:.2f}\n"
        f"💰 رصيدك الجديد: ${new_bal:.2f}"
    )

# شحن عبر آسيا (بدون كلمة "اسيا" في السؤال، مع دينار)
# ---------- شحن عبر آسيا (الجزء المعدل) ----------

@dp.callback_query_handler(text="pay_asia")
async def pay_asia_start(call: types.CallbackQuery):
    if not await is_subscribed(call.from_user.id): return await call.answer("⚠️ اشترك أولاً", show_alert=True)
    if not is_user_verified(call.from_user.id): return await call.answer("يرجى إكمال التحقق البشري أولاً.", show_alert=True)
    
    text = (
        "شحن الرصيد عبر آسيا سيل:\n"
        "حوّل إلى الرقم: 07705157022\n"
        "الحد الأدنى: 1000 دينار.\n"
        "اضغط على الزر أدناه لتأكيد البيانات."
    )
    kb = colored_inline_keyboard([
        colored_button("✅ تأكيد البيانات", "confirm_asia_data", "success"),
        colored_button("🔙 رجوع", "add_balance", "danger")
    ])
    await call.message.edit_text(text, reply_markup=kb)


@dp.callback_query_handler(text="confirm_asia_data")
async def confirm_asia_data(call: types.CallbackQuery):
    # انتقل إلى إدخال المبلغ
    await call.message.edit_text(
        "أدخل المبلغ الذي تريد شحنه (بالدينار):\nمثال: <code>1000</code>",
        reply_markup=colored_inline_keyboard([colored_button("🔙 رجوع", "add_balance", "danger")])
    )
    await AsiaTopUpStates.waiting_for_amount.set()


# دالة استقبال المبلغ (تبقى كما هي، لكن مع السماح من 1 إلى 500000)
@dp.message_handler(state=AsiaTopUpStates.waiting_for_amount)
async def asia_amount_entered(message: types.Message, state: FSMContext):
    if not is_user_verified(message.from_user.id): return await message.answer("يرجى إكمال التحقق البشري أولاً.")
    try:
        amount = float(message.text)
        if amount <= 0 or amount > 500000:  # الحد الأقصى اختياري، يمكن إزالته
            raise ValueError
    except ValueError:
        return await message.answer("❌ أرسل مبلغاً صحيحاً (1 - 500000 دينار).")
    
    await state.update_data(amount=amount)
    await message.answer(
        f"💵 <b>المبلغ المطلوب:</b> {amount:.2f} دينار\n\n"
        f"📱 <b>يرجى تحويل المبلغ إلى الرقم التالي:</b>\n"
        f"<code>07705157022</code>\n\n"
        f"بعد التحويل، اضغط على <b>تم التحويل</b> وأرسل سكرين شوت.",
        reply_markup=colored_inline_keyboard([
            colored_button("✅ تم التحويل", "asia_done", "danger"),
            colored_button("❌ إلغاء", "main_menu", "success")
        ])
    )
    await AsiaTopUpStates.waiting_for_screenshot.set()

@dp.callback_query_handler(text="asia_done", state=AsiaTopUpStates.waiting_for_screenshot)
async def asia_request_screenshot(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📸 <b>أرسل الآن سكرين شوت لعملية التحويل.</b>",
                                 reply_markup=colored_inline_keyboard([colored_button("❌ إلغاء", "main_menu", "danger")]))

@dp.message_handler(content_types=ContentType.PHOTO, state=AsiaTopUpStates.waiting_for_screenshot)
async def asia_screenshot_received(message: types.Message, state: FSMContext):
    global ADMIN_ID
    data = await state.get_data()
    amount = data['amount']
    user_id = message.from_user.id
    username = message.from_user.username or "بدون معرف"
    photo = message.photo[-1].file_id
    text = (
        f"🔄 <b>طلب شحن رصيد جديد (آسيا)</b>\n\n"
        f"👤 المستخدم: <a href='tg://user?id={user_id}'>{username}</a>\n"
        f"🆔 الآيدي: <code>{user_id}</code>\n"
        f"💰 المبلغ المطلوب: <b>{amount:.2f} دينار</b>\n\n"
        f"📎 الصورة أدناه:"
    )
    kb = colored_inline_keyboard([
        colored_button("✅ موافقة", f"asia_approve_{user_id}", "danger"),
        colored_button("❌ رفض", f"asia_reject_{user_id}", "success")
    ])
    try:
        if ADMIN_ID:
            await bot.send_photo(ADMIN_ID, photo, caption=text, reply_markup=kb)
        else:
            await bot.send_photo(ADMIN_USERNAME, photo, caption=text, reply_markup=kb)
    except Exception as e:
        if "Chat not found" in str(e):
            await message.answer("⚠️ المطور لم يبدأ البوت بعد. يرجى إبلاغه.")
        else:
            await message.answer(f"❌ خطأ: {e}")
        await state.finish()
        return
    await message.answer("✅ <b>تم إرسال طلبك إلى المطور. سنعلمك بالقرار قريباً.</b>",
                         reply_markup=get_main_markup(message.from_user.username))
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('asia_approve_'))
async def asia_approve(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔ للمطور فقط.", show_alert=True)
    uid = int(call.data.split('_')[2])
    await state.update_data(approve_uid=uid)
    await call.message.edit_caption(call.message.caption + "\n\n✏️ <b>أدخل الآن المبلغ الذي ستضيفه لهذا المستخدم:</b>", reply_markup=None)
    await AdminStates.asia_approve_amount.set()

@dp.message_handler(state=AdminStates.asia_approve_amount)
async def asia_approve_amount_entered(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0: raise ValueError
    except ValueError: return await message.answer("❌ أرسل مبلغاً صحيحاً موجباً.")
    data = await state.get_data(); uid = data['approve_uid']
    add_user_if_not_exists(uid, None)
    new_bal = get_user_balance(uid) + amount
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, uid)); conn.commit()
    await message.answer(f"✅ تمت إضافة <b>${amount:.2f}</b> إلى رصيد المستخدم <code>{uid}</code>.")
    try:
        await bot.send_message(uid, f"🎉 <b>تمت الموافقة على طلب الشحن الخاص بك!</b>\nتم إضافة <b>${amount:.2f}</b> إلى رصيدك.\nرصيدك الحالي: <b>${new_bal:.2f}$</b>")
    except Exception as e: logging.error(f"Failed to notify user {uid}: {e}")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('asia_reject_'))
async def asia_reject(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.username != ADMIN_USERNAME: return await call.answer("⛔ للمطور فقط.", show_alert=True)
    uid = int(call.data.split('_')[2])
    await state.update_data(reject_uid=uid)
    await call.message.edit_caption(call.message.caption + "\n\n✏️ <b>اكتب سبب الرفض:</b>", reply_markup=None)
    await AdminStates.asia_reject_reason.set()

@dp.message_handler(state=AdminStates.asia_reject_reason)
async def asia_reject_reason_entered(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data(); uid = data['reject_uid']
    try:
        await bot.send_message(uid, f"❌ <b>تم رفض طلب الشحن الخاص بك.</b>\nالسبب: {reason}")
    except Exception as e: logging.error(f"Failed to notify user {uid}: {e}")
    await message.answer(f"✅ تم إرسال سبب الرفض للمستخدم <code>{uid}</code>.")
    await state.finish()

# ================================================================
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
