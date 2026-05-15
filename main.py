"""
بوت إدارة عقود الكلانات – الإصدار النهائي (مجموعات فقط)
=================================================================
- يُضاف البوت إلى أي مجموعة (عادي/سوبر) ويعمل تلقائياً.
- يستخرج اسم الكلان من عنوان المجموعة مهما كانت الرموز (يقبل الأرقام).
- يدعم الفواصل في التاريخ: / - . |
- الجلسة الصامتة (Pyrogram) تقرأ قناة العقود وتزامن البيانات محلياً.
- يدعم تنسيقين للعقود: التنسيق القياسي والتنسيق المعقد.
- عند تنفيذ أمر، يبحث عن أحدث رسالة للكلان في القناة ويعدلها.
- لتنفيذ عملية: يكتب المستخدم (@user تاريخ / رفع قائد ...)
  ثم يرد عليها أي شخص بـ "ادمن" فقط.
"""

import json
import os
import re
import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import Forbidden as TelegramForbidden

from pyrogram import Client, filters as pyro_filters
from pyrogram.handlers import MessageHandler as PyroMessageHandler
from pyrogram.errors import MessageNotModified, RPCError

# ─────────────────────────────────────────────
# الإعدادات (ثوابت)
# ─────────────────────────────────────────────
TOKEN          = "8254791300:AAGA3FmfzD0c_1_lSFPuryxv1br0RQFlVjc"
API_ID         = 26604893
API_HASH       = "b4dad6237531036f1a4bb2580e4985b1"
SESSION_STRING = "BAGV9V0Af_3r8brUqcEEKfZ0pS6m2mi7vBHXvW-WAeAAd2HCL5xluUtUStq0VslHxtbpgfVKIXRKi9CrWRJWudKeOLA1fHXnwt5c2_hYQiAT2OW4IMrGzWCMrKRrTL2E8yA1AAygPnT7J3jejpylQi0HRavgx-CzlDcBPFB-G6-zgnTi5TKzyuFo9LxpOjV0hjna8nIXHGPX4cgC2QxuD2Dmy8_htVb-uxPIiu5MIcD15ErSyT4mP-A6r3nZb0XAlRaJ9K3CM9a01icSCv19BpFl0QbVtdPvY8zBdRba8aFAAuRBGNYI4akLKKRvHAHXXLMa3dNdLBWOsGBu7UTMn6KCNJgavAAAAAHloT2vAA"
CONTRACTS_CHANNEL = "@ClanContracts"

DATA_FILE = "clan_data.json"

MAIN_BOT_USER_ID = int(TOKEN.split(":")[0])

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# عميل Pyrogram مخصص لتجاهل أخطاء Peer id invalid
# ─────────────────────────────────────────────
class SilentClient(Client):
    async def handle_updates(self, updates):
        try:
            await super().handle_updates(updates)
        except ValueError as e:
            if "Peer id invalid" in str(e):
                pass
            else:
                logger.error(f"[Pyrogram] ValueError غير متوقعة: {e}")

# ─────────────────────────────────────────────
# إدارة البيانات المحلية
# ─────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"clans": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_data()
clans: dict = db.setdefault("clans", {})

SILENT_USER_ID = None

# ─────────────────────────────────────────────
# دوال مساعدة
# ─────────────────────────────────────────────
def normalize(s: str) -> str:
    return s.strip().lower()

def get_or_create_clan(abbr: str) -> dict:
    key = normalize(abbr)
    if key not in clans:
        clans[key] = {
            "abbr": abbr,
            "leader": None,
            "assistants": [],
            "contracts": [],
            "contract_message_id": None,
        }
        save_data()
    return clans[key]

def extract_clan_from_title(title: str) -> str | None:
    """
    يستخرج اسم الكلان من عنوان المجموعة.
    يدعم الأقواس، الرموز المتناظرة، والكلمة الأخيرة (حروف وأرقام).
    """
    bracket_pairs = [
        ('<', '>'), ('(', ')'), ('[', ']'), ('{', '}'),
        ('«', '»'), ('‹', '›'), ('【', '】'), ('〈', '〉'),
        ('《', '》'), ('「', '」'), ('『', '』'),
        ('﴾', '﴿'), ('⟨', '⟩'), ('⟪', '⟫'), ('⟬', '⟭'),
    ]

    # 1. محاولة مطابقة الأزواج المعروفة (بالترتيبين)
    for left, right in bracket_pairs:
        pattern = re.escape(left) + r'\s*([A-Za-z0-9_]{2,10})\s*' + re.escape(right)
        m = re.search(pattern, title)
        if m:
            return m.group(1)
        pattern_rev = re.escape(right) + r'\s*([A-Za-z0-9_]{2,10})\s*' + re.escape(left)
        m = re.search(pattern_rev, title)
        if m:
            return m.group(1)

    # 2. رمزان متماثلان (مثل |TAR|)
    m = re.search(r'([^\w\s])\s*([A-Za-z0-9_]{2,10})\s*\1', title)
    if m:
        return m.group(2)

    # 3. كلمة أخيرة (حروف وأرقام) – تُصلح مشكلة الأسماء مثل C4
    m = re.search(r'\b([A-Za-z0-9]{2,10})\b', title)
    if m:
        return m.group(1)

    return None

def is_valid_date_string(date_str: str) -> bool:
    """يقبل أي ثلاثة أجزاء رقمية مفصولة بـ / أو - أو . أو |"""
    if not re.fullmatch(r'[\d]{1,4}[/\-.\|][\d]{1,4}[/\-.\|][\d]{1,4}', date_str.strip()):
        return False
    parts = re.split(r'[/\-.\|]', date_str.strip())
    return len(parts) == 3 and all(p.isdigit() for p in parts)

def clean_username(u: str) -> str:
    u = u.strip()
    return u if u.startswith('@') else f'@{u}'

def format_contract_list(clan: dict) -> str:
    abbr = clan["abbr"]
    lines = ["<b>↢ ━━━━━━❪❆❫━━━━━━ ↢</b>"]
    for i, c in enumerate(clan["contracts"], 1):
        lines.append(f"<b>{i:02d}</b>- {c['username']} - <i>{c['date']}</i>")
    lines.append("<b>↢ ━━━━━━❪❆❫━━━━━━ ↢</b>")
    lines.append("<b>إخـتـصار الكـلان:</b>")
    lines.append(f"<b>{abbr}</b>")
    leader = clan.get("leader") or "@user"
    lines.append(f"<b>القائـد:</b> {leader}")
    assts = clan.get("assistants", [])
    sup_map = str.maketrans("1234567", "¹²³⁴⁵⁶⁷")
    for i, a in enumerate(assts, 1):
        sup = str(i).translate(sup_map)
        lines.append(f"<b>المـسـاعد{sup}:</b> {a}")
    for i in range(len(assts) + 1, 8):
        sup = str(i).translate(sup_map)
        lines.append(f"<b>المـسـاعد{sup}:</b> @user")
    return "\n".join(lines)

async def find_clan_message_id(abbr: str) -> int | None:
    """يبحث عن أحدث رسالة للكلان في القناة (المثبتة أولاً)."""
    try:
        # الرسائل المثبتة أولاً
        pinned_messages = []
        async for m in pyro.get_chat_history(CONTRACTS_CHANNEL, limit=50):
            if m.pinned_message:
                pinned_messages.append(m)
            if len(pinned_messages) >= 10:
                break

        for msg in pinned_messages:
            if msg.text and f"إخـتـصار الكـلان:" in msg.text and abbr in msg.text:
                logger.info(f"تم العثور على رسالة مثبتة للكلان {abbr} (ID: {msg.id})")
                return msg.id

        # ثم أحدث 50 رسالة
        async for msg in pyro.get_chat_history(CONTRACTS_CHANNEL, limit=50):
            if msg.text and f"إخـتـصار الكـلان:" in msg.text and abbr in msg.text:
                logger.info(f"تم العثور على رسالة للكلان {abbr} (ID: {msg.id})")
                return msg.id
    except Exception as e:
        logger.error(f"خطأ أثناء البحث عن رسالة الكلان {abbr}: {e}")
    return None

async def push_to_channel(context: ContextTypes.DEFAULT_TYPE, clan: dict) -> bool:
    text = format_contract_list(clan)
    abbr = clan["abbr"]

    msg_id = await find_clan_message_id(abbr) or clan.get("contract_message_id")

    try:
        if msg_id:
            await context.bot.edit_message_text(
                chat_id=CONTRACTS_CHANNEL,
                message_id=msg_id,
                text=text,
                parse_mode="HTML",
            )
            if clan.get("contract_message_id") != msg_id:
                clan["contract_message_id"] = msg_id
                save_data()
            return True
        else:
            msg = await context.bot.send_message(
                chat_id=CONTRACTS_CHANNEL,
                text=text,
                parse_mode="HTML",
            )
            clan["contract_message_id"] = msg.message_id
            save_data()
            return True
    except MessageNotModified:
        return True
    except TelegramForbidden as e:
        logger.warning(f"تم رفض الوصول إلى القناة: {e}")
        return False
    except Exception as e:
        logger.warning(f"فشل في تحديث/إنشاء رسالة الكلان {abbr}: {e}")
        return False

# ─────────────────────────────────────────────
# دوال تحليل الرسائل (تدعم التنسيقين)
# ─────────────────────────────────────────────
def _parse_complex_format(text: str, message_id: int) -> bool:
    lines = text.split("\n")
    clan_abbr = None
    leader = None
    assistants = []
    contracts = []

    for line in lines:
        clean = line.strip()
        m = re.search(r'(?i)CLAN\s*NAME\s*[-—–]\s*([A-Za-z0-9_]{2,10})', clean)
        if m:
            clan_abbr = m.group(1)
            break

    if not clan_abbr:
        return False

    section = 0
    for line in lines:
        clean = line.strip()

        if "LEADER" in clean.upper() and "-" in clean:
            section = 1
            continue
        if "ASSISTANT" in clean.upper() and "-" in clean:
            section = 2
            continue
        if "CLAN NAME" in clean.upper():
            section = 0
            continue

        if section == 1:
            usernames = re.findall(r'@[A-Za-z0-9_]{3,32}', clean)
            for u in usernames:
                if not leader:
                    leader = u
        elif section == 2:
            usernames = re.findall(r'@[A-Za-z0-9_]{3,32}', clean)
            assistants.extend(usernames)
        elif section == 0:
            date_pattern = r'[\d]{1,4}[/\-.\|][\d]{1,4}[/\-.\|][\d]{1,4}'
            date_match = re.search(date_pattern, clean)
            user_match = re.search(r'@[A-Za-z0-9_]{3,32}', clean)
            if date_match and user_match:
                uname = user_match.group(0)
                date = date_match.group(0)
                contracts.append({"username": uname, "date": date})

    key = normalize(clan_abbr)
    if key not in clans:
        clans[key] = {
            "abbr": clan_abbr,
            "leader": leader,
            "assistants": assistants[:7],
            "contracts": contracts,
            "contract_message_id": message_id,
        }
        logger.info(f"[Pyrogram] استيراد كلان جديد (تنسيق معقد): {clan_abbr}")
    else:
        if leader:
            clans[key]["leader"] = leader
        clans[key]["assistants"] = assistants[:7]
        if contracts:
            clans[key]["contracts"] = contracts
        clans[key]["contract_message_id"] = message_id
        logger.info(f"[Pyrogram] تحديث كلان (تنسيق معقد): {clan_abbr}")
    save_data()
    return True

def _parse_simple_format(text: str, message_id: int) -> bool:
    clan_abbr = None
    leader = None
    assistants = []
    contracts = []
    lines = text.split("\n")

    for idx, line in enumerate(lines):
        clean = re.sub(r"<[^>]+>", "", line).strip()

        if "إخـتـصار الكـلان:" in clean:
            if idx + 1 < len(lines):
                nxt = re.sub(r"<[^>]+>", "", lines[idx + 1]).strip()
                if nxt:
                    clan_abbr = nxt

        if "القائـد:" in clean:
            part = clean.split("القائـد:")[-1].strip()
            if part and part != "@user":
                leader = part if part.startswith("@") else f"@{part}"

        if "المـسـاعد" in clean and ":" in clean:
            part = clean.split(":")[-1].strip()
            if part and part != "@user":
                assistants.append(part if part.startswith("@") else f"@{part}")

        m = re.match(r"^(\d{2})-\s*(.+?)\s*-\s*(.+)$", clean)
        if m:
            uname = m.group(2).strip()
            date  = m.group(3).strip()
            if uname and uname != "@user":
                contracts.append({"username": uname, "date": date})

    if not clan_abbr:
        return False

    key = normalize(clan_abbr)
    if key not in clans:
        clans[key] = {
            "abbr": clan_abbr,
            "leader": leader,
            "assistants": assistants[:7],
            "contracts": contracts,
            "contract_message_id": message_id,
        }
        logger.info(f"[Pyrogram] استيراد كلان جديد (تنسيق بسيط): {clan_abbr}")
    else:
        if leader:
            clans[key]["leader"] = leader
        clans[key]["assistants"] = assistants[:7]
        if contracts:
            clans[key]["contracts"] = contracts
        clans[key]["contract_message_id"] = message_id
        logger.info(f"[Pyrogram] تحديث كلان (تنسيق بسيط): {clan_abbr}")
    save_data()
    return True

def _parse_and_save(text: str, message_id: int):
    if _parse_complex_format(text, message_id):
        return
    _parse_simple_format(text, message_id)

# ─────────────────────────────────────────────
# الجلسة الصامتة (Pyrogram)
# ─────────────────────────────────────────────
pyro = SilentClient(
    name="silent_reader",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
)

def _is_message_from_our_bots(message) -> bool:
    if not message.from_user:
        return False
    user_id = message.from_user.id
    return (user_id == MAIN_BOT_USER_ID) or (SILENT_USER_ID and user_id == SILENT_USER_ID)

async def _pyro_read_history():
    logger.info("[Pyrogram] بدء قراءة تاريخ قناة العقود...")
    try:
        count = 0
        async for msg in pyro.get_chat_history(CONTRACTS_CHANNEL):
            if msg.text and not _is_message_from_our_bots(msg):
                _parse_and_save(msg.text, msg.id)
                count += 1
        logger.info(f"[Pyrogram] انتهت القراءة: تم تحديث {count} كلان")
    except Exception as e:
        logger.error(f"[Pyrogram] خطأ أثناء قراءة التاريخ: {e}")

async def _pyro_new_msg(client, message):
    if not message.text or not message.from_user:
        return
    if _is_message_from_our_bots(message):
        return
    try:
        _parse_and_save(message.text, message.id)
    except Exception as e:
        logger.error(f"[Pyrogram] خطأ أثناء معالجة رسالة جديدة: {e}")

async def start_pyrogram():
    global SILENT_USER_ID
    await pyro.start()
    me = await pyro.get_me()
    SILENT_USER_ID = me.id
    logger.info(f"[Pyrogram] الجلسة الصامتة متصلة (ID: {SILENT_USER_ID})")
    await _pyro_read_history()
    pyro.add_handler(PyroMessageHandler(
        _pyro_new_msg,
        pyro_filters.chat(CONTRACTS_CHANNEL) & pyro_filters.text,
    ))

# ─────────────────────────────────────────────
# معالج رسائل المجموعات (Telegram PTB)
# ─────────────────────────────────────────────
async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    chat = msg.chat
    if chat.type not in ("group", "supergroup"):
        return

    text = msg.text.strip()

    if text == "ادمن" and msg.reply_to_message:
        clan_abbr = extract_clan_from_title(chat.title or "")
        if not clan_abbr:
            await msg.reply_text(
                "⚠️ لم يتم العثور على اسم الكلان في عنوان المجموعة.\n"
                "تأكد من وجوده بين قوسين أو رمزين مثل <TAR> أو [VCC] أو ﴿C4﴾"
            )
            return

        clan = get_or_create_clan(clan_abbr)
        replied_text = msg.reply_to_message.text or ""
        replied_text = replied_text.strip()

        # 1. إضافة / تجديد لاعب (يقبل الفواصل: / - . |)
        player_match = re.match(
            r'^(@?[A-Za-z0-9_]{3,32})\s+([\d]{1,4}[/\-.\|][\d]{1,4}[/\-.\|][\d]{1,4})$',
            replied_text
        )
        if player_match:
            uname = clean_username(player_match.group(1))
            date  = player_match.group(2).strip()

            if not is_valid_date_string(date):
                await msg.reply_text(
                    "⚠️ صيغة التاريخ غير صحيحة.\n"
                    "الرجاء إدخال ثلاثة أرقام مفصولة بـ / أو - أو . أو | مثل: 22|12|2026 أو 2026/9/5",
                    parse_mode="HTML",
                )
                return

            found = False
            for slot in clan["contracts"]:
                if normalize(slot["username"]) == normalize(uname):
                    slot["date"] = date
                    found = True
                    break

            if found:
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم تجديد عقد {uname} في كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من أن البوت مشرف في قناة العقود ويملك صلاحية الإرسال والتعديل.")
            else:
                clan["contracts"].append({"username": uname, "date": date})
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم إضافة {uname} إلى كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            return

        # 2. رفع قائد
        promote_leader = re.match(r'^رفع\s+قائد\s+(@?[A-Za-z0-9_]{3,32})$', replied_text)
        if promote_leader:
            uname = clean_username(promote_leader.group(1))
            clan["leader"] = uname
            save_data()
            success = await push_to_channel(context, clan)
            if success:
                await msg.reply_text(f"✅ تم تعيين {uname} قائداً لكلان <b>{clan_abbr}</b>.", parse_mode="HTML")
            else:
                await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            return

        # 3. تنزيل قائد
        demote_leader = re.match(r'^تنزيل\s+قائد\s+(@?[A-Za-z0-9_]{3,32})$', replied_text)
        if demote_leader:
            if clan["leader"] and normalize(clan["leader"]) == normalize(clean_username(demote_leader.group(1))):
                clan["leader"] = None
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم إزالة القائد من كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            else:
                await msg.reply_text("⚠️ هذا الشخص ليس القائد الحالي، أو الكلان بلا قائد أصلاً.")
            return

        # 4. رفع مساعد
        promote_asst = re.match(r'^رفع\s+مساعد\s+(@?[A-Za-z0-9_]{3,32})$', replied_text)
        if promote_asst:
            uname = clean_username(promote_asst.group(1))
            if len(clan["assistants"]) >= 7:
                await msg.reply_text("⚠️ العدد مكتمل (7 مساعدين كحد أقصى).")
                return
            if uname not in clan["assistants"]:
                clan["assistants"].append(uname)
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم تعيين {uname} مساعداً في كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            else:
                await msg.reply_text(f"ℹ️ {uname} مساعد بالفعل.")
            return

        # 5. تنزيل مساعد
        demote_asst = re.match(r'^تنزيل\s+مساعد\s+(@?[A-Za-z0-9_]{3,32})$', replied_text)
        if demote_asst:
            uname = clean_username(demote_asst.group(1))
            if uname in clan["assistants"]:
                clan["assistants"].remove(uname)
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم إزالة {uname} من المساعدين في كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            else:
                await msg.reply_text(f"⚠️ {uname} ليس مساعداً في هذا الكلان.")
            return

        # 6. إزالة لاعب
        remove_player = re.match(r'^ازال[ةه]\s+لاعب\s+(@?[A-Za-z0-9_]{3,32})$', replied_text)
        if remove_player:
            uname = clean_username(remove_player.group(1))
            before = len(clan["contracts"])
            clan["contracts"] = [
                c for c in clan["contracts"]
                if normalize(c["username"]) != normalize(uname)
            ]
            if len(clan["contracts"]) < before:
                save_data()
                success = await push_to_channel(context, clan)
                if success:
                    await msg.reply_text(f"✅ تم إزالة {uname} من عقود كلان <b>{clan_abbr}</b>.", parse_mode="HTML")
                else:
                    await msg.reply_text("❌ فشل تحديث القناة. تأكد من صلاحية البوت في قناة العقود.")
            else:
                await msg.reply_text(f"⚠️ {uname} غير موجود في قائمة العقود.")
            return

        # رسالة الخطأ العامة
        await msg.reply_text(
            "⚠️ <b>صيغة الرسالة غير مدعومة.</b>\n\n"
            "الأوامر المتاحة عند الرد بـ (ادمن):\n"
            "• <code>@user تاريخ</code> ← إضافة أو تجديد لاعب\n"
            "• <code>رفع قائد @user</code>\n"
            "• <code>تنزيل قائد @user</code>\n"
            "• <code>رفع مساعد @user</code>\n"
            "• <code>تنزيل مساعد @user</code>\n"
            "• <code>ازاله لاعب @user</code>",
            parse_mode="HTML",
        )

# ─────────────────────────────────────────────
# التشغيل الرئيسي
# ─────────────────────────────────────────────
async def run_all():
    await start_pyrogram()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT,
        group_message_handler,
    ))

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=["message"])
        logger.info("✅ البوت يعمل الآن في جميع المجموعات المضاف إليها.")
        await asyncio.Event().wait()
        await app.updater.stop()
        await app.stop()

    await pyro.stop()

if __name__ == "__main__":
    asyncio.run(run_all())