import os
import asyncio
import shutil
import sqlite3
import logging
import phonenumbers
from telethon import TelegramClient, errors
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel, Chat

# ================================================================
# الإعدادات
# ================================================================
API_ID   = 34674538
API_HASH = '633785a3287407336e4c7421307fcbd8'
DB_PATH  = 'levi_bot.db'

logging.basicConfig(level=logging.WARNING, format='%(asctime)s | %(levelname)s | %(message)s')

for folder in ['sessions', 'sessions_good', 'sessions_spam', 'sessions_old']:
    os.makedirs(folder, exist_ok=True)

# ================================================================
# قاعدة البيانات
# ================================================================
conn   = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def get_or_create_category(country_code: str, country_name: str) -> int:
    cursor.execute("SELECT id FROM categories WHERE prefix=?", (country_code,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO categories (name, prefix, price) VALUES (?,?,?)",
        (country_name, country_code, 1.00)
    )
    conn.commit()
    return cursor.lastrowid

def save_account_to_db(phone, session_name, country_id, password_2fa='لا يوجد'):
    cursor.execute("SELECT id FROM accounts WHERE phone=?", (phone,))
    if cursor.fetchone():
        return False
    cursor.execute(
        "INSERT INTO accounts (phone, session_name, country_id, password_2fa, status) VALUES (?,?,?,?,?)",
        (phone, session_name, country_id, password_2fa, 'available')
    )
    conn.commit()
    return True

# ================================================================
# فحص SpamBot
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
    except Exception as e:
        logging.warning(f"SpamBot error: {e}")
        return 'error'

# ================================================================
# فحص المجموعات والقنوات
# ================================================================
async def get_dialogs_stats(client: TelegramClient) -> dict:
    groups   = 0
    channels = 0
    try:
        result = await client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=500,
            hash=0
        ))
        for chat in result.chats:
            if isinstance(chat, Channel):
                if chat.broadcast:
                    channels += 1
                else:
                    groups += 1
            elif isinstance(chat, Chat):
                groups += 1
    except Exception as e:
        logging.warning(f"Dialogs error: {e}")
    return {'groups': groups, 'channels': channels}

# ================================================================
# طباعة نتيجة الفحص
# ================================================================
def print_result(number, me, country_name, country_code,
                 is_premium, spam_status, stats, is_old,
                 saved_db, dest_folder, password_2fa):

    spam_text = {
        'good':    '✅ سليم بدون قيود',
        'spam':    '🚫 عليه قيود سبام',
        'unknown': '❓ غير معروف',
        'error':   '⚠️ خطأ في الفحص',
    }.get(spam_status, '❓')

    print(f"""
╔══════════════════════════════════════════╗
  📊 نتيجة فحص: {number}
╠══════════════════════════════════════════╣
  👤 الاسم      : {(me.first_name or '') + ' ' + (me.last_name or '')}
  🆔 ID         : {me.id}
  📞 الرقم      : {number}
  🌍 الدولة     : {country_name} ({country_code})
  ⭐ Premium    : {'نعم ✅' if is_premium else 'لا ❌'}
  🔎 SpamBot    : {spam_text}
  👥 مجموعات   : {stats['groups']}
  📢 قنوات      : {stats['channels']}
  📅 العمر      : {'🕰️ قديم (قبل 2024)' if is_old else '🆕 حساب جديد'}
  🔐 2FA        : {password_2fa or 'لا يوجد'}
  💾 DB         : {'تم الحفظ ✅' if saved_db else 'موجود مسبقاً ⚠️'}
  📁 المجلد     : {dest_folder}
╚══════════════════════════════════════════╝""")

# ================================================================
# الفاحص الرئيسي — يشتغل على أي مصدر (جلسة / رقم جديد)
# ================================================================
async def process_account(
    session_path: str,
    number: str = None,
    password_2fa: str = None,
    from_file: bool = False
):
    """
    session_path : المسار الكامل للجلسة بدون .session
    number       : رقم الهاتف (اختياري لو الجلسة موجودة)
    password_2fa : كلمة سر 2FA إن وجدت
    from_file    : True لو الجلسة جاية من مجلد sessions/
    """
    client = TelegramClient(session_path, API_ID, API_HASH)

    try:
        await client.connect()

        # ─── تسجيل دخول لو محتاج ───
        if not await client.is_user_authorized():
            if not number:
                print(f"⚠️ الجلسة {session_path} غير مصرح بها ولا يوجد رقم. تخطي.")
                await client.disconnect()
                return

            sent = await client.send_code_request(number)
            code_type = type(sent.type).__name__

            if 'App' in code_type:
                print(f"📱 [{number}] الكود راح لتطبيق تيليجرام على التليفون (Saved Messages)")
            elif 'Sms' in code_type:
                print(f"📩 [{number}] الكود راح SMS")
            elif 'Call' in code_type:
                print(f"📞 [{number}] سيأتي الكود عبر مكالمة")
            else:
                print(f"📲 [{number}] نوع الكود: {code_type}")

            code = input("📥 أدخل الكود: ").strip()

            try:
                await client.sign_in(number, code, phone_code_hash=sent.phone_code_hash)
            except errors.SessionPasswordNeededError:
                if not password_2fa:
                    password_2fa = input("🔐 أدخل كلمة سر 2FA: ").strip()
                await client.sign_in(password=password_2fa)

        # ─── جلب المعلومات ───
        me = await client.get_me()
        if not number:
            number = f"+{me.phone}" if me.phone else str(me.id)

        # الدولة
        country_code = 'unknown'
        country_name = 'Unknown'
        try:
            parsed = phonenumbers.parse(number)
            region = phonenumbers.region_code_for_number(parsed)
            if region:
                country_code = f"+{parsed.country_code}"
                country_name = region
        except Exception:
            pass

        # Premium
        is_premium = getattr(me, 'premium', False)

        # SpamBot
        spam_status = await check_spambot(client)

        # مجموعات وقنوات
        stats = await get_dialogs_stats(client)

        # عمر الحساب
        is_old = me.id < 6_500_000_000

        await client.disconnect()

        # ─── تصنيف ونقل الجلسة ───
        session_name = os.path.basename(session_path) + '.session'
        session_file = session_path + '.session'

        if spam_status == 'spam':
            dest_folder = 'sessions_spam'
            cat_label   = f"Spam-{country_name}"
            log_file    = 'spam_accounts.txt'
        elif is_old:
            dest_folder = 'sessions_old'
            cat_label   = f"Old-{country_name}"
            log_file    = 'old_accounts.txt'
        else:
            dest_folder = os.path.join('sessions_good', country_name)
            cat_label   = country_name
            log_file    = f'good_{country_name}.txt'

        os.makedirs(dest_folder, exist_ok=True)
        dest = os.path.join(dest_folder, session_name)
        if os.path.exists(session_file) and os.path.abspath(session_file) != os.path.abspath(dest):
            shutil.copy2(session_file, dest)

        # تسجيل في ملف نصي
        with open(log_file, 'a', encoding='utf-8') as lf:
            lf.write(
                f"{number} | id={me.id} | premium={is_premium} | "
                f"spam={spam_status} | groups={stats['groups']} | "
                f"channels={stats['channels']} | old={is_old} | "
                f"2fa={password_2fa or 'لا يوجد'}\n"
            )

        # حفظ في DB
        cat_id   = get_or_create_category(country_code, cat_label)
        saved_db = save_account_to_db(
            number, session_name, cat_id, password_2fa or 'لا يوجد'
        )

        # طباعة النتيجة
        print_result(
            number, me, country_name, country_code,
            is_premium, spam_status, stats, is_old,
            saved_db, dest_folder, password_2fa
        )

    except errors.PhoneNumberBannedError:
        print(f"❌ [{number}] محظور نهائياً.")
        with open('banned_numbers.txt', 'a', encoding='utf-8') as f:
            f.write((number or session_path) + '\n')
        if client.is_connected(): await client.disconnect()
        _clean_session(session_path)

    except errors.FloodWaitError as e:
        print(f"⏳ [{number}] FloodWait {e.seconds}s.")
        if client.is_connected(): await client.disconnect()

    except errors.PhoneNumberInvalidError:
        print(f"❌ [{number}] رقم غير صالح.")
        if client.is_connected(): await client.disconnect()

    except errors.PhoneCodeInvalidError:
        print(f"❌ [{number}] الكود خاطئ.")
        if client.is_connected(): await client.disconnect()
        _clean_session(session_path)

    except KeyboardInterrupt:
        print("\n⛔ إيقاف يدوي.")
        if client.is_connected(): await client.disconnect()
        raise

    except Exception as e:
        print(f"⚠️ خطأ مع {number or session_path}: {e}")
        if client.is_connected(): await client.disconnect()
        _clean_session(session_path)

def _clean_session(session_path: str):
    f = session_path + '.session'
    if os.path.exists(f):
        try: os.remove(f)
        except: pass

# ================================================================
# 1) فحص ملف أرقام (numbers.txt)
# ================================================================
async def run_from_numbers_file(file_path: str = 'numbers.txt'):
    if not os.path.exists(file_path):
        print(f"❌ الملف '{file_path}' غير موجود.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        numbers = [ln.strip() for ln in f if ln.strip()]

    print(f"📋 إجمالي الأرقام: {len(numbers)}")

    for i, number in enumerate(numbers, 1):
        print(f"\n[{i}/{len(numbers)}] ──────────────────────")
        session_path = os.path.join('sessions', number.replace('+', ''))
        try:
            await process_account(session_path=session_path, number=number)
        except KeyboardInterrupt:
            print("\n⛔ توقف.")
            break
        await asyncio.sleep(3)   # تجنب FloodWait بين الأرقام

    print("\n🎯 انتهى فحص جميع الأرقام!")

# ================================================================
# 2) فحص مجلد جلسات موجودة (sessions/)
# ================================================================
async def run_from_sessions_folder(folder: str = 'sessions'):
    files = [f for f in os.listdir(folder) if f.endswith('.session')]
    if not files:
        print(f"❌ لا توجد جلسات في مجلد '{folder}'.")
        return

    print(f"📂 عدد الجلسات: {len(files)}")

    for i, fname in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] ──────────────────────")
        session_path = os.path.join(folder, fname.replace('.session', ''))
        # استخراج الرقم من اسم الملف إن أمكن
        raw = fname.replace('.session', '')
        number = f"+{raw}" if raw.isdigit() else None
        try:
            await process_account(session_path=session_path, number=number)
        except KeyboardInterrupt:
            print("\n⛔ توقف.")
            break
        await asyncio.sleep(2)

    print("\n🎯 انتهى فحص جميع الجلسات!")

# ================================================================
# نقطة الدخول
# ================================================================
if __name__ == '__main__':
    import sys

    print("""
╔══════════════════════════════════╗
   🔍 Telegram Account Checker
╠══════════════════════════════════╣
  [1] فحص ملف numbers.txt
  [2] فحص مجلد sessions/
  [3] فحص رقم واحد
╚══════════════════════════════════╝""")

    if len(sys.argv) > 1:
        # python checker.py +201234567890 [2fa]
        number = sys.argv[1]
        pwd    = sys.argv[2] if len(sys.argv) > 2 else None
        session_path = os.path.join('sessions', number.replace('+', ''))
        asyncio.run(process_account(session_path=session_path, number=number, password_2fa=pwd))
    else:
        choice = input("اختر [1/2/3]: ").strip()
        if choice == '1':
            asyncio.run(run_from_numbers_file('numbers.txt'))
        elif choice == '2':
            asyncio.run(run_from_sessions_folder('sessions'))
        elif choice == '3':
            num = input("أدخل الرقم (+countryCode): ").strip()
            pwd = input("2FA (اضغط Enter لو مفيش): ").strip() or None
            session_path = os.path.join('sessions', num.replace('+', ''))
            asyncio.run(process_account(session_path=session_path, number=num, password_2fa=pwd))
        else:
            print("❌ اختيار غير صحيح.")
