import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, LabeledPrice
from telethon import TelegramClient, errors

# ================================================================
# الإعدادات
# ================================================================
API_TOKEN         = '8502404654:AAEnJitLJwbvzRSJ1ZaaKufm01o0pEzVDQA'
ADMIN_USERNAME    = 'm_h7_e'
TELETHON_API_ID   = 34674538
TELETHON_API_HASH = '633785a3287407336e4c7421307fcbd8'

# ⬇️ ضع هنا الـ ID أو username لقناة التفعيلات (مثال: -1001234567890 أو @mychannel)
ACTIVATIONS_CHANNEL = '@mychannel'

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
            id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0
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

class PaymentStates(StatesGroup):
    waiting_for_stars = State()

# ================================================================
# دوال مساعدة
# ================================================================
def get_user_balance(uid):
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    r = cursor.fetchone()
    return r[0] if r else 0.0

def add_user_if_not_exists(uid, username):
    cursor.execute("INSERT OR IGNORE INTO users (id,username,balance) VALUES (?,?,0.0)", (uid, username))
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
    """إرجاع زر Inline ملون كـ dict. الألوان: primary, danger, success"""
    return {"text": text, "callback_data": callback_data, "style": color}

def colored_inline_keyboard(*rows):
    """بناء InlineKeyboardMarkup من قوائم أزرار ملونة.
       rows: كل عنصر قائمة أزرار (كل زر dict أو InlineKeyboardButton عادي).
       يُرجع dict جاهز للإرسال.
    """
    keyboard = []
    for row in rows:
        kb_row = []
        for btn in row:
            if isinstance(btn, dict):
                kb_row.append(btn)
            else:
                # زر عادي غير ملون (مثلاً InlineKeyboardButton)
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

def get_main_markup(username):
    """القائمة الرئيسية بألوان مختلفة"""
    buttons = [
        [colored_button("🛒 شراء حساب", "buy_account", "primary"),
         colored_button("💳 شحن رصيد", "add_balance", "primary")],
        [colored_button("💰 رصيدي", "my_balance", "success")]
    ]
    if username == ADMIN_USERNAME:
        buttons.append([colored_button("⚙️ لوحة التحكم للمطور", "admin_panel", "danger")])
    return colored_inline_keyboard(*buttons)

def get_admin_markup():
    return colored_inline_keyboard(
        [colored_button("➕ إضافة قسم/دولة", "admin_add_cat", "primary")],
        [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "primary")],
        [colored_button("📂 رفع ملف جلسة (.session)", "admin_add_session", "primary")],
        [colored_button("🔢 فحص رقم واحد + تسجيل دخول", "admin_check_single", "success")],
        [colored_button("📄 رفع ملف أرقام (numbers.txt)", "admin_upload_numbers", "primary")],
        [colored_button("🎁 منح رصيد لمستخدم", "admin_gift_balance", "danger")],
        [colored_button("📊 إحصائيات", "admin_stats", "success")],
        [colored_button("🔙 رجوع للقائمة", "main_menu", "danger")]
    )

# ================================================================
# SpamBot
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

# ================================================================
# دالة الفحص المشترك
# ================================================================
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
# /start
# ================================================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    add_user_if_not_exists(message.from_user.id, message.from_user.username)
    bal = get_user_balance(message.from_user.id)
    await message.answer(
        f"أهلاً بك في - Kaido TG | KING 👋\n\n"
        f"🚀 وجهتك المميزة لخدمات تيليجرام الاحترافية بأفضل جودة وسرعة ⚡.\n\n"
        f"🆔 ايديك: <code>{message.from_user.id}</code>\n"
        f"💵 رصيدك: <code>{bal:.2f}$</code>\n\n"
        f"👍 ابدأ باستخدام البوت الآن واستمتع بجميع الخدمات المتاحة عبر الأزرار بالأسفل ⬇️.",
        reply_markup=get_main_markup(message.from_user.username)
    )

@dp.callback_query_handler(text="main_menu", state="*")
async def back_to_main(call: types.CallbackQuery, state: FSMContext):
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

@dp.callback_query_handler(text="my_balance")
async def my_balance(call: types.CallbackQuery):
    bal = get_user_balance(call.from_user.id)
    await call.answer(f"💰 رصيدك: ${bal:.2f}", show_alert=True)

# ================================================================
# لوحة المطور
# ================================================================
@dp.callback_query_handler(text="admin_panel", state="*")
async def admin_panel(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔ للمطور فقط.", show_alert=True)
    await state.finish()
    await call.message.edit_text("⚙️ <b>لوحة تحكم المطور</b>", reply_markup=get_admin_markup())

@dp.callback_query_handler(text="admin_stats")
async def admin_stats(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    cursor.execute("SELECT COUNT(*) FROM users")
    u = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")
    av = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'")
    so = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM categories")
    ca = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance) FROM users")
    bal = cursor.fetchone()[0] or 0
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

# ================================================================
# منح رصيد لمستخدم
# ================================================================
@dp.callback_query_handler(text="admin_gift_balance")
async def gift_balance_start(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    await call.message.edit_text(
        "🎁 <b>منح رصيد لمستخدم</b>\n\nأرسل آيدي المستخدم الرقمي:",
        reply_markup=cancel_markup()
    )
    await AdminStates.gift_user_id.set()

@dp.message_handler(state=AdminStates.gift_user_id)
async def gift_balance_get_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ أرسل آيدي رقمي صحيح.")
    uid = int(message.text)
    await state.update_data(gift_uid=uid)
    await message.answer(f"💰 كم المبلغ الذي تريد منحه للمستخدم <code>{uid}</code>؟\nمثال: <code>10.5</code>")
    await AdminStates.gift_amount.set()

@dp.message_handler(state=AdminStates.gift_amount)
async def gift_balance_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("❌ أرسل رقماً موجباً صحيحاً.")
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
# إدارة الأقسام — عرض قائمة الأقسام مع زرار إضافة حسابات
# ================================================================
@dp.callback_query_handler(text="admin_manage_cats")
async def admin_manage_cats(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)

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
            f"cat_manage_{cat[0]}",
            "primary"
        )])
    rows.append([colored_button("🔙 رجوع", "admin_panel", "danger")])
    m = colored_inline_keyboard(*rows)
    await call.message.edit_text("📋 <b>اختر قسماً لإدارته:</b>", reply_markup=m)

@dp.callback_query_handler(lambda c: c.data.startswith('cat_manage_'))
async def cat_manage(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)

    cat_id = int(call.data.split('_')[2])
    cursor.execute("SELECT name, prefix, price FROM categories WHERE id=?", (cat_id,))
    cat = cursor.fetchone()
    if not cat:
        return await call.answer("❌ القسم غير موجود.", show_alert=True)

    count = get_accounts_count(cat_id)
    m = colored_inline_keyboard(
        [colored_button("📲 إضافة رقم (تسجيل دخول + فحص تلقائي)", f"addcat_phone_{cat_id}", "primary")],
        [colored_button("📂 إضافة ملف .session (فحص تلقائي)", f"addcat_session_{cat_id}", "primary")],
        [colored_button("🔙 رجوع للأقسام", "admin_manage_cats", "danger")]
    )
    await call.message.edit_text(
        f"📁 <b>قسم:</b> {cat[0]}\n"
        f"🔢 البادئة: <code>{cat[1]}</code> | 💵 السعر: <code>${cat[2]:.2f}</code>\n"
        f"🟢 الحسابات المتاحة: <b>{count}</b>\n\n"
        f"اختر طريقة إضافة حساب:",
        reply_markup=m
    )

# ================================================================
# إضافة رقم لقسم → تسجيل دخول + فحص تلقائي
# ================================================================
@dp.callback_query_handler(lambda c: c.data.startswith('addcat_phone_'))
async def addcat_phone_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)

    cat_id = int(call.data.split('_')[2])
    await state.update_data(target_cat_id=cat_id)

    await call.message.edit_text(
        "📲 <b>إضافة رقم لهذا القسم</b>\n\n"
        "أرسل الرقم مع كود الدولة:\n"
        "مثال: <code>+201234567890</code>",
        reply_markup=cancel_markup()
    )
    await AdminStates.add_to_cat_phone.set()

@dp.message_handler(state=AdminStates.add_to_cat_phone)
async def addcat_got_phone(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not re.match(r'^\+\d{7,15}$', number):
        return await message.answer(
            "❌ صيغة غير صحيحة.\nمثال: <code>+201234567890</code>",
            reply_markup=cancel_markup()
        )

    session_path = os.path.join('sessions', number.replace('+', ''))
    client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)

    try:
        await client.connect()
        sent = await client.send_code_request(number)

        code_type = type(sent.type).__name__
        if 'App' in code_type:
            where = "📱 <b>تطبيق تيليجرام (Saved Messages)</b>"
        elif 'Sms' in code_type:
            where = "📩 <b>رسالة SMS</b>"
        elif 'Call' in code_type:
            where = "📞 <b>مكالمة صوتية</b>"
        else:
            where = f"<code>{code_type}</code>"

        active_clients[message.from_user.id] = client
        await state.update_data(
            phone=number,
            phone_code_hash=sent.phone_code_hash,
            session_path=session_path,
        )
        await message.answer(
            f"📲 تم إرسال كود التحقق للرقم <code>{number}</code>\n"
            f"📬 وصل عبر: {where}\n\n"
            f"أرسل الكود هنا (مثال: <code>12345</code>):",
            reply_markup=cancel_markup()
        )
        await AdminStates.add_to_cat_code.set()

    except errors.PhoneNumberBannedError:
        await client.disconnect()
        await message.answer(f"🚫 الرقم <code>{number}</code> محظور نهائياً.")
        await state.finish()
    except errors.FloodWaitError as e:
        await client.disconnect()
        await message.answer(f"⏳ انتظر <b>{e.seconds}</b> ثانية.")
        await state.finish()
    except errors.PhoneNumberInvalidError:
        await client.disconnect()
        await message.answer("❌ الرقم غير صالح.")
        await state.finish()
    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

@dp.message_handler(state=AdminStates.add_to_cat_code)
async def addcat_got_code(message: types.Message, state: FSMContext):
    code = message.text.strip().replace(' ', '')
    if not code.isdigit() or len(code) < 4:
        return await message.answer("❌ أرسل الكود أرقاماً فقط.", reply_markup=cancel_markup())

    data   = await state.get_data()
    client = active_clients.get(message.from_user.id)
    if not client:
        await state.finish()
        return await message.answer("❌ انتهت الجلسة. ابدأ من جديد.")

    try:
        await client.sign_in(data['phone'], code, phone_code_hash=data['phone_code_hash'])
        await _addcat_do_check(message, state, client)

    except errors.SessionPasswordNeededError:
        await message.answer(
            "🔐 <b>الحساب عنده 2FA</b>\n\nأرسل كلمة السر:",
            reply_markup=cancel_markup()
        )
        await AdminStates.add_to_cat_2fa.set()

    except errors.PhoneCodeInvalidError:
        await message.answer("❌ الكود غير صحيح. أرسل الكود الصحيح:", reply_markup=cancel_markup())

    except errors.PhoneCodeExpiredError:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer("⏰ انتهت صلاحية الكود. ابدأ من جديد.")
        await state.finish()

    except Exception as e:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

@dp.message_handler(state=AdminStates.add_to_cat_2fa)
async def addcat_got_2fa(message: types.Message, state: FSMContext):
    password = message.text.strip()
    client   = active_clients.get(message.from_user.id)
    if not client:
        await state.finish()
        return await message.answer("❌ انتهت الجلسة.")

    try:
        await client.sign_in(password=password)
        await state.update_data(password_2fa=password)
        await _addcat_do_check(message, state, client)

    except errors.PasswordHashInvalidError:
        await message.answer("❌ كلمة السر غير صحيحة. حاول مجدداً:", reply_markup=cancel_markup())

    except Exception as e:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

async def _addcat_do_check(message: types.Message, state: FSMContext, client: TelegramClient):
    data = await state.get_data()
    phone        = data['phone']
    cat_id       = data['target_cat_id']
    password_2fa = data.get('password_2fa', 'لا يوجد')

    try:
        await message.answer("⏳ <b>جاري الفحص التلقائي...</b>")
        check = await run_full_check(client, phone, password_2fa)
        await client.disconnect()
        active_clients.pop(message.from_user.id, None)

        session_name = phone.replace('+', '') + '.session'
        cursor.execute(
            "INSERT INTO accounts (phone, session_name, country_id, password_2fa, status) VALUES (?,?,?,?,?)",
            (phone, session_name, cat_id, password_2fa, 'available')
        )
        conn.commit()

        cursor.execute("SELECT name FROM categories WHERE id=?", (cat_id,))
        cat_name = cursor.fetchone()[0]
        count = get_accounts_count(cat_id)

        m = colored_inline_keyboard(
            [colored_button("➕ إضافة رقم آخر لنفس القسم", f"addcat_phone_{cat_id}", "primary")],
            [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "primary")],
            [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
        )

        await message.answer(
            check['result_text'] +
            f"✅ <b>تم حفظ الحساب في قسم:</b> {cat_name}\n"
            f"🟢 إجمالي الحسابات المتاحة في القسم: <b>{count}</b>",
            reply_markup=m
        )
        await state.finish()

    except Exception as e:
        logging.error(f"_addcat_do_check: {e}")
        if client.is_connected(): await client.disconnect()
        active_clients.pop(message.from_user.id, None)
        await message.answer(f"❌ خطأ أثناء الفحص: <code>{e}</code>")
        await state.finish()

# ================================================================
# إضافة .session لقسم → فحص تلقائي
# ================================================================
@dp.callback_query_handler(lambda c: c.data.startswith('addcat_session_'))
async def addcat_session_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)

    cat_id = int(call.data.split('_')[2])
    await state.update_data(target_cat_id=cat_id)

    await call.message.edit_text(
        "📂 <b>رفع ملف جلسة لهذا القسم</b>\n\n"
        "أرسل ملف <code>.session</code>:",
        reply_markup=cancel_markup()
    )
    await AdminStates.add_to_cat_session_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.add_to_cat_session_file)
async def addcat_got_session_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.session'):
        return await message.answer("❌ أرسل ملف <code>.session</code> فقط.")

    data   = await state.get_data()
    cat_id = data['target_cat_id']

    fname        = message.document.file_name
    session_name = fname
    session_path_full = os.path.join('sessions', fname)

    await message.document.download(destination_file=session_path_full)

    raw    = fname.replace('.session', '')
    phone  = f"+{raw}" if raw.isdigit() else None
    session_path_noext = os.path.join('sessions', raw)

    await message.answer("⏳ <b>جاري الفحص التلقائي للجلسة...</b>")

    client = TelegramClient(session_path_noext, TELETHON_API_ID, TELETHON_API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            await message.answer(
                "❌ الجلسة غير مصرحة (منتهية أو غير مكتملة).",
                reply_markup=get_admin_markup()
            )
            await state.finish()
            return

        me = await client.get_me()
        if not phone:
            phone = f"+{me.phone}" if me.phone else str(me.id)

        check = await run_full_check(client, phone)
        await client.disconnect()

        cursor.execute(
            "INSERT INTO accounts (phone, session_name, country_id, password_2fa, status) VALUES (?,?,?,?,?)",
            (phone, session_name, cat_id, 'لا يوجد', 'available')
        )
        conn.commit()

        cursor.execute("SELECT name FROM categories WHERE id=?", (cat_id,))
        cat_name = cursor.fetchone()[0]
        count = get_accounts_count(cat_id)

        m = colored_inline_keyboard(
            [colored_button("➕ رفع جلسة أخرى لنفس القسم", f"addcat_session_{cat_id}", "primary")],
            [colored_button("📋 إدارة الأقسام", "admin_manage_cats", "primary")],
            [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
        )

        await message.answer(
            check['result_text'] +
            f"✅ <b>تم حفظ الجلسة في قسم:</b> {cat_name}\n"
            f"🟢 إجمالي الحسابات المتاحة في القسم: <b>{count}</b>",
            reply_markup=m
        )
        await state.finish()

    except Exception as e:
        logging.error(f"addcat_session: {e}")
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>", reply_markup=get_admin_markup())
        await state.finish()

# ================================================================
# CHECKER — فحص رقم واحد (الأصلي)
# ================================================================
@dp.callback_query_handler(text="admin_check_single")
async def checker_start(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    await call.message.edit_text(
        "🔢 <b>فحص رقم واحد</b>\n\n"
        "أرسل الرقم مع كود الدولة:\n"
        "مثال: <code>+201234567890</code>",
        reply_markup=cancel_markup()
    )
    await AdminStates.checker_phone.set()

@dp.message_handler(state=AdminStates.checker_phone)
async def checker_got_phone(message: types.Message, state: FSMContext):
    number = message.text.strip()
    if not re.match(r'^\+\d{7,15}$', number):
        return await message.answer("❌ صيغة غير صحيحة.\nمثال: <code>+201234567890</code>", reply_markup=cancel_markup())

    session_path = os.path.join('sessions', number.replace('+', ''))
    client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)

    try:
        await client.connect()
        sent = await client.send_code_request(number)

        code_type = type(sent.type).__name__
        if 'App' in code_type:
            where = "📱 <b>تطبيق تيليجرام على التليفون</b> (Saved Messages)"
        elif 'Sms' in code_type:
            where = "📩 <b>رسالة SMS</b>"
        elif 'Call' in code_type:
            where = "📞 <b>مكالمة صوتية</b>"
        else:
            where = f"<code>{code_type}</code>"

        active_clients[message.from_user.id] = client
        await state.update_data(
            phone=number,
            phone_code_hash=sent.phone_code_hash,
            session_path=session_path,
        )
        await message.answer(
            f"📲 تم إرسال كود التحقق للرقم <code>{number}</code>\n"
            f"📬 وصل عبر: {where}\n\n"
            f"أرسل الكود هنا (مثال: <code>12345</code>):",
            reply_markup=cancel_markup()
        )
        await AdminStates.checker_code.set()

    except errors.PhoneNumberBannedError:
        await client.disconnect()
        await message.answer(f"🚫 الرقم <code>{number}</code> محظور نهائياً.")
        await state.finish()
    except errors.FloodWaitError as e:
        await client.disconnect()
        await message.answer(f"⏳ انتظر <b>{e.seconds}</b> ثانية.")
        await state.finish()
    except errors.PhoneNumberInvalidError:
        await client.disconnect()
        await message.answer("❌ الرقم غير صالح.")
        await state.finish()
    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

@dp.message_handler(state=AdminStates.checker_code)
async def checker_got_code(message: types.Message, state: FSMContext):
    code = message.text.strip().replace(' ', '')
    if not code.isdigit() or len(code) < 4:
        return await message.answer("❌ أرسل الكود أرقاماً فقط.", reply_markup=cancel_markup())

    data   = await state.get_data()
    client = active_clients.get(message.from_user.id)
    if not client:
        await state.finish()
        return await message.answer("❌ انتهت الجلسة. ابدأ من جديد.")

    try:
        await client.sign_in(data['phone'], code, phone_code_hash=data['phone_code_hash'])
        await _checker_finish(message, state, client, data['phone'])

    except errors.SessionPasswordNeededError:
        await message.answer("🔐 <b>الحساب عنده 2FA</b>\n\nأرسل كلمة السر:", reply_markup=cancel_markup())
        await AdminStates.checker_2fa.set()

    except errors.PhoneCodeInvalidError:
        await message.answer("❌ الكود غير صحيح. أرسل الكود الصحيح:", reply_markup=cancel_markup())

    except errors.PhoneCodeExpiredError:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer("⏰ انتهت صلاحية الكود. ابدأ من جديد.")
        await state.finish()

    except Exception as e:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

@dp.message_handler(state=AdminStates.checker_2fa)
async def checker_got_2fa(message: types.Message, state: FSMContext):
    password = message.text.strip()
    client   = active_clients.get(message.from_user.id)
    data     = await state.get_data()
    if not client:
        await state.finish()
        return await message.answer("❌ انتهت الجلسة.")

    try:
        await client.sign_in(password=password)
        await state.update_data(password_2fa=password)
        await _checker_finish(message, state, client, data['phone'])

    except errors.PasswordHashInvalidError:
        await message.answer("❌ كلمة السر غير صحيحة. حاول مجدداً:", reply_markup=cancel_markup())

    except Exception as e:
        active_clients.pop(message.from_user.id, None)
        if client.is_connected(): await client.disconnect()
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

async def _checker_finish(message: types.Message, state: FSMContext, client: TelegramClient, phone: str):
    try:
        data         = await state.get_data()
        password_2fa = data.get('password_2fa', 'لا يوجد')

        await message.answer("⏳ جاري الفحص التلقائي...")
        check = await run_full_check(client, phone, password_2fa)

        await client.disconnect()
        active_clients.pop(message.from_user.id, None)

        cursor.execute("SELECT id, name FROM categories")
        cats = cursor.fetchall()

        if not cats:
            session_name = phone.replace('+', '') + '.session'
            cursor.execute(
                "INSERT INTO accounts (phone,session_name,password_2fa,status) VALUES (?,?,?,?)",
                (phone, session_name, password_2fa, 'available')
            )
            conn.commit()
            await message.answer(
                check['result_text'] + "⚠️ لا توجد أقسام. تم الحفظ بدون قسم.",
                reply_markup=get_admin_markup()
            )
            await state.finish()
            return

        await state.update_data(
            spam_status=check['spam_status'],
            is_old=check['is_old'],
            is_premium=check['is_premium'],
            groups=check['groups'],
            channels=check['channels'],
            password_2fa=password_2fa,
            result_text=check['result_text']
        )

        rows = []
        for cat in cats:
            rows.append([colored_button(cat[1], f"checker_cat_{cat[0]}", "primary")])
        rows.append([colored_button("🔙 إلغاء الحفظ", "checker_skip", "danger")])
        markup = colored_inline_keyboard(*rows)

        await message.answer(check['result_text'] + "🌍 <b>اختر القسم لحفظ الحساب:</b>", reply_markup=markup)
        await AdminStates.checker_cat.set()

    except Exception as e:
        logging.error(f"checker_finish: {e}")
        if client.is_connected(): await client.disconnect()
        active_clients.pop(message.from_user.id, None)
        await message.answer(f"❌ خطأ: <code>{e}</code>")
        await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('checker_cat_'), state=AdminStates.checker_cat)
async def checker_save_account(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split('_')[2])
    data   = await state.get_data()
    phone  = data['phone']
    session_name = phone.replace('+', '') + '.session'
    session_src  = os.path.join('sessions', session_name)

    if not os.path.exists(session_src):
        await call.message.edit_text(f"❌ ملف الجلسة غير موجود: <code>{session_src}</code>")
        await state.finish()
        return

    cursor.execute(
        "INSERT INTO accounts (phone,session_name,country_id,password_2fa,status) VALUES (?,?,?,?,?)",
        (phone, session_name, cat_id, data.get('password_2fa','لا يوجد'), 'available')
    )
    conn.commit()
    await call.message.edit_text(
        f"✅ <b>تم حفظ الحساب!</b>\n"
        f"📞 <code>{phone}</code>\n"
        f"📁 <code>sessions/{session_name}</code>",
        reply_markup=get_admin_markup()
    )
    await state.finish()

@dp.callback_query_handler(text="checker_skip", state=AdminStates.checker_cat)
async def checker_skip_save(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("⚠️ تم إلغاء الحفظ. الجلسة في <code>sessions/</code> فقط.")
    await state.finish()

# ================================================================
# رفع ملف أرقام
# ================================================================
@dp.callback_query_handler(text="admin_upload_numbers")
async def admin_upload_numbers(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    await call.message.edit_text(
        "📄 <b>رفع ملف أرقام</b>\n\nأرسل ملف <code>.txt</code>:",
        reply_markup=cancel_markup()
    )
    await AdminStates.waiting_for_numbers_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.waiting_for_numbers_file)
async def process_numbers_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.txt'):
        return await message.answer("❌ أرسل ملف <code>.txt</code> فقط.")
    await message.document.download(destination_file="numbers.txt")
    await state.finish()
    await message.answer("✅ تم حفظ <code>numbers.txt</code>", reply_markup=get_admin_markup())

# ================================================================
# إضافة قسم
# ================================================================
@dp.callback_query_handler(text="admin_add_cat")
async def admin_add_cat(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("📝 أرسل اسم الدولة:\nمثال: <code>أمريكا 🇺🇸</code>", reply_markup=cancel_markup())
    await AdminStates.waiting_for_cat_name.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_name)
async def process_cat_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🔢 أرسل رمز الدولة:\nمثال: <code>+1</code>")
    await AdminStates.waiting_for_cat_prefix.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_prefix)
async def process_cat_prefix(message: types.Message, state: FSMContext):
    await state.update_data(prefix=message.text)
    await message.answer("💵 أرسل السعر بالدولار:\nمثال: <code>2.5</code>")
    await AdminStates.waiting_for_cat_price.set()

@dp.message_handler(state=AdminStates.waiting_for_cat_price)
async def process_cat_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
    except ValueError:
        return await message.answer("❌ أرسل رقم صحيح.")
    data = await state.get_data()
    cursor.execute("INSERT INTO categories (name,prefix,price) VALUES (?,?,?)", (data['name'], data['prefix'], price))
    conn.commit()
    new_cat_id = cursor.lastrowid

    m = colored_inline_keyboard(
        [colored_button("📲 إضافة رقم للقسم الجديد", f"addcat_phone_{new_cat_id}", "primary")],
        [colored_button("📂 إضافة .session للقسم الجديد", f"addcat_session_{new_cat_id}", "primary")],
        [colored_button("⚙️ لوحة التحكم", "admin_panel", "danger")]
    )
    await message.answer(
        f"✅ <b>تم إضافة القسم!</b>\n"
        f"🌍 {data['name']} | 🔢 {data['prefix']} | 💵 ${price:.2f}\n\n"
        f"هل تريد إضافة حسابات للقسم الجديد الآن؟",
        reply_markup=m
    )
    await state.finish()

# ================================================================
# رفع ملف جلسة (الطريقة الأصلية — بدون فحص)
# ================================================================
@dp.callback_query_handler(text="admin_add_session")
async def admin_add_session(call: types.CallbackQuery):
    if call.from_user.username != ADMIN_USERNAME:
        return await call.answer("⛔", show_alert=True)
    await call.message.edit_text("📂 أرسل ملف <code>.session</code>:", reply_markup=cancel_markup())
    await AdminStates.waiting_for_session_file.set()

@dp.message_handler(content_types=['document'], state=AdminStates.waiting_for_session_file)
async def process_session_file(message: types.Message, state: FSMContext):
    if not message.document.file_name.endswith('.session'):
        return await message.answer("❌ أرسل ملف <code>.session</code> فقط.")
    file_path = f"sessions/{message.document.file_name}"
    await message.document.download(destination_file=file_path)
    await state.update_data(session_name=message.document.file_name)
    await message.answer("📞 أرسل رقم الهاتف:\nمثال: <code>+201234567890</code>")
    await AdminStates.waiting_for_session_phone.set()

@dp.message_handler(state=AdminStates.waiting_for_session_phone)
async def process_session_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("🔐 أرسل 2FA أو اكتب: <code>لا يوجد</code>")
    await AdminStates.waiting_for_session_2fa.set()

@dp.message_handler(state=AdminStates.waiting_for_session_2fa)
async def process_session_2fa(message: types.Message, state: FSMContext):
    await state.update_data(password_2fa=message.text.strip())
    cursor.execute("SELECT id, name FROM categories")
    cats = cursor.fetchall()
    if not cats:
        await state.finish()
        return await message.answer("❌ لا توجد أقسام.", reply_markup=get_admin_markup())
    rows = []
    for cat in cats:
        rows.append([colored_button(cat[1], f"set_cat_{cat[0]}", "primary")])
    markup = colored_inline_keyboard(*rows)
    await message.answer("🌍 اختر الدولة:", reply_markup=markup)
    await state.set_state("waiting_for_category_selection")

@dp.callback_query_handler(lambda c: c.data.startswith('set_cat_'), state="waiting_for_category_selection")
async def save_account_final(call: types.CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split('_')[2])
    data   = await state.get_data()
    cursor.execute(
        "INSERT INTO accounts (phone,session_name,country_id,password_2fa,status) VALUES (?,?,?,?,?)",
        (data['phone'], data['session_name'], cat_id, data['password_2fa'], 'available')
    )
    conn.commit()
    await call.message.edit_text("✅ تم حفظ الجلسة وجاهزة للبيع!", reply_markup=get_admin_markup())
    await state.finish()

# ================================================================
# شراء الحسابات
# ================================================================
@dp.callback_query_handler(text="buy_account")
async def user_buy_account(call: types.CallbackQuery):
    cursor.execute("SELECT id, name, prefix, price FROM categories")
    cats = cursor.fetchall()
    if not cats:
        return await call.answer("❌ لا تتوفر أقسام حالياً.", show_alert=True)
    rows = []
    for cat in cats:
        count = get_accounts_count(cat[0])
        emoji = "🟢" if count > 0 else "🔴"
        rows.append([colored_button(
            f"{emoji} {cat[1]} ({cat[2]}) | المتوفر: {count} | السعر: ${cat[3]:.2f}",
            f"buy_cat_{cat[0]}",
            "primary"
        )])
    rows.append([colored_button("🔙 العودة", "main_menu", "danger")])
    markup = colored_inline_keyboard(*rows)
    await call.message.edit_text("🛍️ <b>اختر الدولة:</b>", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('buy_cat_'))
async def process_purchase(call: types.CallbackQuery):
    cat_id = int(call.data.split('_')[2])
    cursor.execute("SELECT name, price FROM categories WHERE id=?", (cat_id,))
    cat_info = cursor.fetchone()
    if not cat_info:
        return await call.answer("❌ القسم غير موجود.", show_alert=True)
    cursor.execute(
        "SELECT id, phone, session_name, password_2fa FROM accounts WHERE country_id=? AND status='available' LIMIT 1",
        (cat_id,)
    )
    account = cursor.fetchone()
    if not account:
        return await call.answer("❌ نفذت الأرقام من هذا القسم.", show_alert=True)
    bal = get_user_balance(call.from_user.id)
    if bal < cat_info[1]:
        return await call.answer(
            f"❌ رصيدك غير كافٍ.\nالسعر: ${cat_info[1]:.2f} | رصيدك: ${bal:.2f}",
            show_alert=True
        )
    new_bal = bal - cat_info[1]
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, call.from_user.id))
    cursor.execute("UPDATE accounts SET status='pending', buyer_id=? WHERE id=?", (call.from_user.id, account[0]))
    conn.commit()
    m = colored_inline_keyboard(
        [colored_button("📥 جلب كود التحقق (OTP)", f"get_otp_{account[0]}", "primary")],
        [colored_button("🔐 جلب كلمة السر (2FA)", f"get_2fa_{account[0]}", "primary")],
        [colored_button("✅ تم تسجيل الدخول", f"confirm_login_{account[0]}", "success")]
    )
    await call.message.edit_text(
        f"🎉 <b>تم الشراء بنجاح!</b>\n\n"
        f"📞 <b>الرقم:</b> <code>{account[1]}</code>\n"
        f"💰 <b>رصيدك المتبقي:</b> <code>${new_bal:.2f}</code>\n\n"
        f"⚙️ <b>خطوات التفعيل:</b>\n"
        f"1️⃣ ضع الرقم في تليجرام واطلب كود التفعيل.\n"
        f"2️⃣ اضغط <b>جلب كود التحقق</b>.\n"
        f"3️⃣ إذا طلب 2FA اضغط <b>جلب كلمة السر</b>.\n"
        f"4️⃣ بعد الدخول اضغط <b>تم تسجيل الدخول</b>.",
        reply_markup=m
    )

@dp.callback_query_handler(lambda c: c.data.startswith('get_otp_'))
async def get_otp_callback(call: types.CallbackQuery):
    acc_id = int(call.data.split('_')[2])
    cursor.execute("SELECT session_name, buyer_id FROM accounts WHERE id=?", (acc_id,))
    acc = cursor.fetchone()
    if not acc or acc[1] != call.from_user.id:
        return await call.answer("❌ غير مسموح.", show_alert=True)
    await call.answer("🔄 جاري الفحص...", show_alert=False)
    session_path = f"sessions/{acc[0]}"
    try:
        client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return await call.message.answer("❌ الجلسة منتهية.")
        otp = None
        async for msg in client.iter_messages(777000, limit=5):
            if msg.text:
                match = re.search(r'\b(\d{5,6})\b', msg.text)
                if match:
                    otp = match.group(1)
                    break
        await client.disconnect()
        if otp:
            cursor.execute("UPDATE accounts SET otp=? WHERE id=?", (otp, acc_id))
            conn.commit()
            await call.message.answer(f"📩 <b>كود التحقق:</b> <code>{otp}</code>")
        else:
            await call.message.answer("⏳ الكود لم يصل بعد. أعد المحاولة.")
    except Exception as e:
        await call.message.answer(f"❌ خطأ: <code>{e}</code>")

@dp.callback_query_handler(lambda c: c.data.startswith('get_2fa_'))
async def get_2fa_callback(call: types.CallbackQuery):
    acc_id = int(call.data.split('_')[2])
    cursor.execute("SELECT password_2fa, buyer_id FROM accounts WHERE id=?", (acc_id,))
    acc = cursor.fetchone()
    if not acc or acc[1] != call.from_user.id:
        return await call.answer("❌ غير مسموح.", show_alert=True)
    await call.message.answer(f"🔐 <b>كلمة السر (2FA):</b> <code>{acc[0]}</code>")

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_login_'))
async def confirm_login_callback(call: types.CallbackQuery):
    acc_id = int(call.data.split('_')[2])
    cursor.execute("SELECT session_name, buyer_id, phone, country_id, otp FROM accounts WHERE id=?", (acc_id,))
    acc = cursor.fetchone()
    if not acc or acc[1] != call.from_user.id:
        return await call.answer("❌ غير مسموح.", show_alert=True)
    session_path = f"sessions/{acc[0]}"
    try:
        client = TelegramClient(session_path, TELETHON_API_ID, TELETHON_API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            await client.log_out()
        await client.disconnect()
    except Exception as e:
        logging.error(f"confirm_login: {e}")
    finally:
        if os.path.exists(session_path):
            try: os.remove(session_path)
            except: pass
        cursor.execute("UPDATE accounts SET status='sold' WHERE id=?", (acc_id,))
        conn.commit()

        # إرسال إشعار إلى قناة التفعيلات
        cat_name = ""
        price = 0.0
        if acc[3]:  # country_id
            cat_info = cursor.execute("SELECT name, price FROM categories WHERE id=?", (acc[3],)).fetchone()
            if cat_info:
                cat_name, price = cat_info
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
        try:
            await bot.send_message(ACTIVATIONS_CHANNEL, msg_text)
        except Exception as e:
            logging.error(f"Failed to send to channel: {e}")

        await call.message.edit_text("✨ <b>تم تفعيل الحساب بنجاح. شكراً! 🎉</b>")

# ================================================================
# شحن الرصيد
# ================================================================
@dp.callback_query_handler(text="add_balance")
async def add_balance_choose(call: types.CallbackQuery):
    m = colored_inline_keyboard(
        [colored_button("⭐ شحن بالنجوم (Telegram Stars)", "pay_stars", "primary")],
        [colored_button("🌏 شحن عبر آسيا", "pay_asia", "primary")],
        [colored_button("🔙 رجوع", "main_menu", "danger")]
    )
    await call.message.edit_text("💳 <b>اختر طريقة الشحن:</b>", reply_markup=m)

@dp.callback_query_handler(text="pay_stars")
async def ask_stars(call: types.CallbackQuery):
    m = colored_inline_keyboard([colored_button("🔙 رجوع", "add_balance", "danger")])  # تم الإصلاح
    await call.message.edit_text(
        "⭐ <b>شحن بالنجوم</b>\n\nأدخل عدد النجوم (1 — 10000):\n<i>كل نجمة = $0.01</i>",
        reply_markup=m
    )
    await PaymentStates.waiting_for_stars.set()

@dp.message_handler(state=PaymentStates.waiting_for_stars)
async def process_stars(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 10000):
        return await message.answer("❌ أدخل رقم بين 1 و 10000.")
    amount = int(message.text)
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="شحن رصيد ZZ",
        description=f"شحن {amount} نجمة (= ${amount * 0.01:.2f})",
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
    stars   = message.successful_payment.total_amount
    added   = stars * 0.01
    new_bal = get_user_balance(message.from_user.id) + added
    cursor.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, message.from_user.id))
    conn.commit()
    await message.answer(
        f"💳 <b>تم الشحن بنجاح!</b>\n"
        f"✨ النجوم: <code>{stars}</code> | 💵 المضاف: <code>${added:.2f}</code>\n"
        f"💰 رصيدك الجديد: <code>${new_bal:.2f}</code>"
    )

@dp.callback_query_handler(text="pay_asia")
async def pay_asia(call: types.CallbackQuery):
    m = colored_inline_keyboard(
        [InlineKeyboardButton("💬 تواصل مع الدعم", url="https://t.me/kkcofg")],
        [colored_button("🔙 رجوع", "add_balance", "danger")]
    )  # تم الإصلاح – تمرير صفين كوسيطين منفصلين
    await call.message.edit_text(
        "🌏 <b>شحن عبر آسيا</b>\n\nتواصل مع الدعم لإتمام عملية الشحن.",
        reply_markup=m
    )

# ================================================================
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    
