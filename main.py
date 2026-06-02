import logging
import uuid
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ════════════════════════════════════════════════════════
#  ⚙️  الإعدادات — غيّر هذه القيم فقط
# ════════════════════════════════════════════════════════
BOT_TOKEN      = "8520440293:AAHxlEGixgF2uOdLAgbpB6S5uFWgXrwAHko"
ADMIN_GROUP_ID = -1002588398038
# ════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── حالات المحادثة ────────────────────────────────────
(
    CHANGE_USER_OLD,
    CHANGE_USER_NEW,
    CHANGE_USER_PROOF,
    CHANGE_SERIAL_OLD,
    CHANGE_SERIAL_NEW,
    CHANGE_SERIAL_PROOF,
    ADD_PLAYER_USER,
    ADD_PLAYER_SERIAL,
    ADD_PLAYER_PROOF,
    CONTACT_STATE,
) = range(10)

# ── ربط message_id ↔ user_id ──────────────────────────
message_user_map: dict[int, int] = {}

# ── ردود الأدمن المعلقة ───────────────────────────────
pending_admin_replies: dict[str, dict] = {}

# ════════════════════════════════════════════════════════
#  لوحات المفاتيح
# ════════════════════════════════════════════════════════

def main_reply_keyboard() -> ReplyKeyboardMarkup:
    keys = [
        [KeyboardButton("🔄 تغيير تسلسلي"), KeyboardButton("👤 تغيير يوزر")],
        [KeyboardButton("➕ إضافة لاعب جديد"), KeyboardButton("💬 تواصل")],
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True, is_persistent=True)


def main_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 تغيير تسلسلي", callback_data="change_serial"),
            InlineKeyboardButton("👤 تغيير يوزر",   callback_data="change_user"),
        ],
        [
            InlineKeyboardButton("➕ إضافة لاعب جديد", callback_data="add_player"),
            InlineKeyboardButton("💬 تواصل",             callback_data="contact"),
        ],
    ])


def skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭️ تخطي — بدون إرفاق", callback_data="skip_proof")
    ]])


# ════════════════════════════════════════════════════════
#  دوال مساعدة
# ════════════════════════════════════════════════════════

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━"

async def is_private(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private":
        return True
    try:
        me = await context.bot.get_me()
        await update.effective_message.reply_text(
            "⚠️ <b>هذا البوت يعمل في الخاص فقط!</b>\n"
            "👇 اضغط الزر للتواصل معي:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 فتح الخاص", url=f"https://t.me/{me.username}?start=hi")
            ]]),
        )
    except Exception:
        pass
    return False


async def answer_cb(update: Update) -> None:
    if update.callback_query:
        await update.callback_query.answer()


async def send_welcome(update: Update) -> None:
    user = update.effective_user
    await update.effective_message.reply_text(
        f"✨ <b>أهلاً وسهلاً، {user.first_name}!</b>\n\n"
        f"{DIVIDER}\n"
        "🎮 اختر ما تريد من الأزرار أدناه:",
        parse_mode="HTML",
        reply_markup=main_reply_keyboard(),
    )
    await update.effective_message.reply_text(
        "🔰 <b>القائمة الرئيسية</b>",
        parse_mode="HTML",
        reply_markup=main_inline_keyboard(),
    )


async def send_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    user,
    text: str,
    photo_id: str = None,
    video_id: str = None,
    caption_extra: str = "",
) -> int:
    """إرسال الطلب للأدمنية مع الصورة/الفيديو إن وُجدا"""
    full_cap = text + (f"\n\n📎 {caption_extra}" if caption_extra else "")
    if photo_id:
        msg = await context.bot.send_photo(
            ADMIN_GROUP_ID, photo_id, caption=full_cap, parse_mode="HTML"
        )
    elif video_id:
        msg = await context.bot.send_video(
            ADMIN_GROUP_ID, video_id, caption=full_cap, parse_mode="HTML"
        )
    else:
        msg = await context.bot.send_message(ADMIN_GROUP_ID, text, parse_mode="HTML")
    message_user_map[msg.message_id] = user.id
    return msg.message_id


async def notify_sent(update: Update) -> None:
    await update.effective_message.reply_text(
        f"✅ <b>تم إرسال طلبك بنجاح!</b>\n"
        f"{DIVIDER}\n"
        "⏳ ستصلك ردود الإدارة قريباً.",
        parse_mode="HTML",
        reply_markup=main_reply_keyboard(),
    )
    await update.effective_message.reply_text(
        "🔰 <b>القائمة الرئيسية</b>",
        parse_mode="HTML",
        reply_markup=main_inline_keyboard(),
    )


async def forward_any_media_to_admin(
    context: ContextTypes.DEFAULT_TYPE, user, message, label="💬 رسالة"
) -> int | None:
    header = (
        f"╔══ {label}\n"
        f"║ 👤 {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╚{DIVIDER}"
    )
    sent = None
    if message.text:
        sent = await context.bot.send_message(
            ADMIN_GROUP_ID, f"{header}\n\n📝 {message.text}", parse_mode="HTML"
        )
    elif message.photo:
        cap = f"{header}\n\n💬 {message.caption}" if message.caption else header
        sent = await context.bot.send_photo(
            ADMIN_GROUP_ID, message.photo[-1].file_id, caption=cap, parse_mode="HTML"
        )
    elif message.video:
        cap = f"{header}\n\n💬 {message.caption}" if message.caption else header
        sent = await context.bot.send_video(
            ADMIN_GROUP_ID, message.video.file_id, caption=cap, parse_mode="HTML"
        )
    elif message.document:
        cap = f"{header}\n\n💬 {message.caption}" if message.caption else header
        sent = await context.bot.send_document(
            ADMIN_GROUP_ID, message.document.file_id, caption=cap, parse_mode="HTML"
        )
    elif message.voice:
        sent = await context.bot.send_voice(
            ADMIN_GROUP_ID, message.voice.file_id, caption=header, parse_mode="HTML"
        )
    elif message.audio:
        cap = f"{header}\n\n🎵 {message.caption}" if message.caption else header
        sent = await context.bot.send_audio(
            ADMIN_GROUP_ID, message.audio.file_id, caption=cap, parse_mode="HTML"
        )
    elif message.video_note:
        sent = await context.bot.send_video_note(ADMIN_GROUP_ID, message.video_note.file_id)
    elif message.sticker:
        sent = await context.bot.send_sticker(ADMIN_GROUP_ID, message.sticker.file_id)
    if sent:
        message_user_map[sent.message_id] = user.id
    return sent.message_id if sent else None


# ════════════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_private(update, context):
        return ConversationHandler.END
    context.user_data.clear()
    await send_welcome(update)
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  1. تغيير يوزر
# ════════════════════════════════════════════════════════

async def enter_change_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_private(update, context):
        return ConversationHandler.END
    await answer_cb(update)
    context.user_data.clear()
    context.user_data["mode"] = "change_user"
    await update.effective_message.reply_text(
        f"👤 <b>تغيير يوزر</b>\n{DIVIDER}\n\n"
        "📌 الخطوة <b>1/3</b>\n"
        "📩 أرسل <b>اليوزر القديم</b>:",
        parse_mode="HTML",
    )
    return CHANGE_USER_OLD


async def recv_old_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["old_user"] = msg.text.strip()
    elif msg.photo:
        context.user_data["old_user"] = msg.caption.strip() if msg.caption else "—"
        context.user_data["proof_photo"] = msg.photo[-1].file_id
    elif msg.video:
        context.user_data["old_user"] = msg.caption.strip() if msg.caption else "—"
        context.user_data["proof_video"] = msg.video.file_id
    else:
        await msg.reply_text("⚠️ أرسل نصاً أو صورة بالكلام أو فيديو بالكلام.")
        return CHANGE_USER_OLD
    await msg.reply_text(
        f"📌 الخطوة <b>2/3</b>\n✏️ أرسل <b>اليوزر الجديد</b>:", parse_mode="HTML"
    )
    return CHANGE_USER_NEW


async def recv_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["new_user"] = msg.text.strip()
    elif msg.photo or msg.video:
        context.user_data["new_user"] = msg.caption.strip() if msg.caption else "—"
    else:
        await msg.reply_text("⚠️ أرسل نصاً.")
        return CHANGE_USER_NEW
    await msg.reply_text(
        f"📌 الخطوة <b>3/3</b>\n"
        "📎 أرفق <b>صورة أو فيديو</b> للتوضيح (اختياري):",
        parse_mode="HTML",
        reply_markup=skip_keyboard(),
    )
    return CHANGE_USER_PROOF


async def recv_user_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    msg  = update.message
    old  = context.user_data.get("old_user", "—")
    new  = context.user_data.get("new_user", "—")
    text = (
        f"╔══ 🔔 طلب تغيير يوزر\n"
        f"║ 👤 {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╠{DIVIDER}\n"
        f"║ ❌ اليوزر القديم: <code>{old}</code>\n"
        f"║ ✅ اليوزر الجديد: <code>{new}</code>\n"
        f"╚{DIVIDER}"
    )
    p_id = v_id = None
    if msg:
        if msg.photo:
            p_id = msg.photo[-1].file_id
        elif msg.video:
            v_id = msg.video.file_id
    await send_to_admin(context, user, text, photo_id=p_id, video_id=v_id)
    context.user_data.clear()
    await notify_sent(update)
    return ConversationHandler.END


async def skip_user_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("⏭️ تم تخطي الإرفاق.")
    user = update.effective_user
    old  = context.user_data.get("old_user", "—")
    new  = context.user_data.get("new_user", "—")
    text = (
        f"╔══ 🔔 طلب تغيير يوزر\n"
        f"║ 👤 {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╠{DIVIDER}\n"
        f"║ ❌ اليوزر القديم: <code>{old}</code>\n"
        f"║ ✅ اليوزر الجديد: <code>{new}</code>\n"
        f"╚{DIVIDER}"
    )
    await send_to_admin(context, user, text)
    context.user_data.clear()
    await context.bot.send_message(
        user.id,
        f"✅ <b>تم إرسال طلبك بنجاح!</b>\n{DIVIDER}\n⏳ ستصلك ردود الإدارة قريباً.",
        parse_mode="HTML",
        reply_markup=main_reply_keyboard(),
    )
    await context.bot.send_message(
        user.id, "🔰 <b>القائمة الرئيسية</b>",
        parse_mode="HTML", reply_markup=main_inline_keyboard()
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  2. تغيير تسلسلي
# ════════════════════════════════════════════════════════

async def enter_change_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_private(update, context):
        return ConversationHandler.END
    await answer_cb(update)
    context.user_data.clear()
    context.user_data["mode"] = "change_serial"
    await update.effective_message.reply_text(
        f"🔄 <b>تغيير تسلسلي</b>\n{DIVIDER}\n\n"
        "📌 الخطوة <b>1/3</b>\n"
        "📩 أرسل <b>التسلسلي القديم</b>:",
        parse_mode="HTML",
    )
    return CHANGE_SERIAL_OLD


async def recv_old_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["old_serial"] = msg.text.strip()
    elif msg.photo:
        context.user_data["old_serial"] = msg.caption.strip() if msg.caption else "—"
    elif msg.video:
        context.user_data["old_serial"] = msg.caption.strip() if msg.caption else "—"
    else:
        await msg.reply_text("⚠️ أرسل نصاً.")
        return CHANGE_SERIAL_OLD
    await msg.reply_text(
        f"📌 الخطوة <b>2/3</b>\n✏️ أرسل <b>التسلسلي الجديد</b>:", parse_mode="HTML"
    )
    return CHANGE_SERIAL_NEW


async def recv_new_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["new_serial"] = msg.text.strip()
    elif msg.photo or msg.video:
        context.user_data["new_serial"] = msg.caption.strip() if msg.caption else "—"
    else:
        await msg.reply_text("⚠️ أرسل نصاً.")
        return CHANGE_SERIAL_NEW
    await msg.reply_text(
        f"📌 الخطوة <b>3/3</b>\n"
        "📎 أرفق <b>صورة أو فيديو</b> للتوضيح (اختياري):",
        parse_mode="HTML",
        reply_markup=skip_keyboard(),
    )
    return CHANGE_SERIAL_PROOF


async def recv_serial_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    msg  = update.message
    old  = context.user_data.get("old_serial", "—")
    new  = context.user_data.get("new_serial", "—")
    text = (
        f"╔══ 🔔 طلب تغيير تسلسلي\n"
        f"║ 👤 {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╠{DIVIDER}\n"
        f"║ ❌ التسلسلي القديم: <code>{old}</code>\n"
        f"║ ✅ التسلسلي الجديد: <code>{new}</code>\n"
        f"╚{DIVIDER}"
    )
    p_id = v_id = None
    if msg:
        if msg.photo:
            p_id = msg.photo[-1].file_id
        elif msg.video:
            v_id = msg.video.file_id
    await send_to_admin(context, user, text, photo_id=p_id, video_id=v_id)
    context.user_data.clear()
    await notify_sent(update)
    return ConversationHandler.END


async def skip_serial_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("⏭️ تم تخطي الإرفاق.")
    user = update.effective_user
    old  = context.user_data.get("old_serial", "—")
    new  = context.user_data.get("new_serial", "—")
    text = (
        f"╔══ 🔔 طلب تغيير تسلسلي\n"
        f"║ 👤 {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╠{DIVIDER}\n"
        f"║ ❌ التسلسلي القديم: <code>{old}</code>\n"
        f"║ ✅ التسلسلي الجديد: <code>{new}</code>\n"
        f"╚{DIVIDER}"
    )
    await send_to_admin(context, user, text)
    context.user_data.clear()
    await context.bot.send_message(
        user.id,
        f"✅ <b>تم إرسال طلبك بنجاح!</b>\n{DIVIDER}\n⏳ ستصلك ردود الإدارة قريباً.",
        parse_mode="HTML",
        reply_markup=main_reply_keyboard(),
    )
    await context.bot.send_message(
        user.id, "🔰 <b>القائمة الرئيسية</b>",
        parse_mode="HTML", reply_markup=main_inline_keyboard()
    )
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  3. إضافة لاعب جديد  (صورة/فيديو إجبارية)
# ════════════════════════════════════════════════════════

async def enter_add_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_private(update, context):
        return ConversationHandler.END
    await answer_cb(update)
    context.user_data.clear()
    context.user_data["mode"] = "add_player"
    await update.effective_message.reply_text(
        f"➕ <b>إضافة لاعب جديد</b>\n{DIVIDER}\n\n"
        "📌 الخطوة <b>1/3</b>\n"
        "📩 أرسل <b>يوزر اللاعب</b>:",
        parse_mode="HTML",
    )
    return ADD_PLAYER_USER


async def recv_player_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["player_user"] = msg.text.strip()
    elif msg.photo or msg.video:
        context.user_data["player_user"] = msg.caption.strip() if msg.caption else "—"
    else:
        await msg.reply_text("⚠️ أرسل يوزر اللاعب كنص.")
        return ADD_PLAYER_USER
    await msg.reply_text(
        f"📌 الخطوة <b>2/3</b>\n✏️ أرسل <b>التسلسلي</b>:", parse_mode="HTML"
    )
    return ADD_PLAYER_SERIAL


async def recv_player_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.text:
        context.user_data["player_serial"] = msg.text.strip()
    elif msg.photo or msg.video:
        context.user_data["player_serial"] = msg.caption.strip() if msg.caption else "—"
    else:
        await msg.reply_text("⚠️ أرسل التسلسلي كنص.")
        return ADD_PLAYER_SERIAL
    await msg.reply_text(
        f"📌 الخطوة <b>3/3</b> — <b>إجبارية ✅</b>\n"
        f"{DIVIDER}\n"
        "📸 أرسل <b>صورة أو فيديو</b> يُثبت التسلسلي.\n"
        "⚠️ <i>لن يُقبل الطلب بدون إرفاق صورة أو فيديو.</i>",
        parse_mode="HTML",
    )
    return ADD_PLAYER_PROOF


async def recv_player_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    msg  = update.message

    # ── التحقق: لازم صورة أو فيديو ──
    if not msg.photo and not msg.video:
        await msg.reply_text(
            "🚫 <b>مرفوض!</b>\n"
            f"{DIVIDER}\n"
            "⚠️ يجب إرسال <b>صورة أو فيديو</b> للتسلسلي.\n"
            "📸 أرسل الصورة أو الفيديو الآن:",
            parse_mode="HTML",
        )
        return ADD_PLAYER_PROOF

    p_user   = context.user_data.get("player_user",   "—")
    p_serial = context.user_data.get("player_serial",  "—")
    caption  = msg.caption or ""

    text = (
        f"╔══ 🔔 طلب إضافة لاعب جديد\n"
        f"║ 👤 مقدم الطلب: {user.mention_html()}\n"
        f"║ 🆔 <code>{user.id}</code>\n"
        f"╠{DIVIDER}\n"
        f"║ 🎮 يوزر اللاعب:   <code>{p_user}</code>\n"
        f"║ 🔢 تسلسلي اللاعب: <code>{p_serial}</code>\n"
        f"╚{DIVIDER}"
    )

    if msg.photo:
        m = await context.bot.send_photo(
            ADMIN_GROUP_ID,
            msg.photo[-1].file_id,
            caption=text + (f"\n\n💬 {caption}" if caption else ""),
            parse_mode="HTML",
        )
    else:
        m = await context.bot.send_video(
            ADMIN_GROUP_ID,
            msg.video.file_id,
            caption=text + (f"\n\n💬 {caption}" if caption else ""),
            parse_mode="HTML",
        )

    message_user_map[m.message_id] = user.id
    context.user_data.clear()
    await notify_sent(update)
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  4. تواصل
# ════════════════════════════════════════════════════════

async def enter_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_private(update, context):
        return ConversationHandler.END
    await answer_cb(update)
    context.user_data.clear()
    context.user_data["mode"] = "contact"
    await update.effective_message.reply_text(
        f"💬 <b>تواصل مع الإدارة</b>\n{DIVIDER}\n\n"
        "أرسل رسالتك الآن:\n"
        "✅ نص | صورة | فيديو | صوت | ملف | صورة بكلام | فيديو بكلام\n\n"
        "🔄 للعودة اضغط /start",
        parse_mode="HTML",
    )
    return CONTACT_STATE


async def recv_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    mid  = await forward_any_media_to_admin(context, user, update.message, "💬 رسالة تواصل")
    if mid is None:
        await update.message.reply_text("⚠️ نوع غير مدعوم، جرب نوعاً آخر.")
    else:
        await update.message.reply_text(
            "✅ وصلت رسالتك للإدارة.\nيمكنك إرسال أخرى أو /start للعودة."
        )
    return CONTACT_STATE


# ════════════════════════════════════════════════════════
#  ردود الأدمنية + تأكيد الإرسال
# ════════════════════════════════════════════════════════

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.reply_to_message:
        return
    user_id = message_user_map.get(message.reply_to_message.message_id)
    if not user_id:
        return

    key = uuid.uuid4().hex[:10]
    pending: dict = {"user_id": user_id}

    if message.text:
        pending.update({"type": "text", "content": message.text})
    elif message.photo:
        pending.update({"type": "photo",    "file_id": message.photo[-1].file_id, "caption": message.caption})
    elif message.video:
        pending.update({"type": "video",    "file_id": message.video.file_id,     "caption": message.caption})
    elif message.document:
        pending.update({"type": "document", "file_id": message.document.file_id,  "caption": message.caption})
    elif message.voice:
        pending.update({"type": "voice",    "file_id": message.voice.file_id})
    elif message.audio:
        pending.update({"type": "audio",    "file_id": message.audio.file_id,     "caption": message.caption})
    elif message.video_note:
        pending.update({"type": "video_note", "file_id": message.video_note.file_id})
    elif message.sticker:
        pending.update({"type": "sticker",  "file_id": message.sticker.file_id})
    else:
        await message.reply_text("⚠️ نوع الملف غير مدعوم.")
        return

    pending_admin_replies[key] = pending
    await message.reply_text(
        "📤 <b>هل تريد إيصال هذه الرسالة للمستخدم؟</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ نعم، أوصلها",   callback_data=f"adm_yes_{key}"),
            InlineKeyboardButton("❌ لا توصلها",     callback_data=f"adm_no_{key}"),
        ]]),
    )


async def handle_admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data.startswith("adm_no_"):
        pending_admin_replies.pop(data[7:], None)
        await query.edit_message_text("❌ تم إلغاء الإرسال.")
        return

    key     = data[8:]
    pending = pending_admin_replies.pop(key, None)
    if not pending:
        await query.edit_message_text("⚠️ انتهت صلاحية هذا الطلب.")
        return

    user_id = pending["user_id"]
    admin   = update.effective_user
    header  = f"📩 <b>رد من الإدارة</b> — {admin.first_name}\n{DIVIDER}"

    try:
        t = pending["type"]
        if t == "text":
            await context.bot.send_message(user_id, f"{header}\n\n{pending['content']}", parse_mode="HTML")
        elif t == "photo":
            cap = f"{header}\n\n{pending['caption']}" if pending.get("caption") else header
            await context.bot.send_photo(user_id, pending["file_id"], caption=cap, parse_mode="HTML")
        elif t == "video":
            cap = f"{header}\n\n{pending['caption']}" if pending.get("caption") else header
            await context.bot.send_video(user_id, pending["file_id"], caption=cap, parse_mode="HTML")
        elif t == "document":
            cap = f"{header}\n\n{pending['caption']}" if pending.get("caption") else header
            await context.bot.send_document(user_id, pending["file_id"], caption=cap, parse_mode="HTML")
        elif t == "voice":
            await context.bot.send_voice(user_id, pending["file_id"], caption=header, parse_mode="HTML")
        elif t == "audio":
            cap = f"{header}\n\n{pending['caption']}" if pending.get("caption") else header
            await context.bot.send_audio(user_id, pending["file_id"], caption=cap, parse_mode="HTML")
        elif t == "video_note":
            await context.bot.send_video_note(user_id, pending["file_id"])
        elif t == "sticker":
            await context.bot.send_sticker(user_id, pending["file_id"])
        await query.edit_message_text("✅ تم إيصال الرد للمستخدم بنجاح.")
    except Exception as e:
        logger.error(f"فشل: {e}")
        await query.edit_message_text(f"❌ فشل الإرسال: {e}")


# ════════════════════════════════════════════════════════
#  Fallback
# ════════════════════════════════════════════════════════

async def cancel_and_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.effective_chat.type == "private":
        await send_welcome(update)
    return ConversationHandler.END


# ════════════════════════════════════════════════════════
#  تشغيل البوت
# ════════════════════════════════════════════════════════

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    f_change_user   = filters.Text(["👤 تغيير يوزر",      "تغيير يوزر"])
    f_change_serial = filters.Text(["🔄 تغيير تسلسلي",    "تغيير تسلسلي"])
    f_add_player    = filters.Text(["➕ إضافة لاعب جديد", "اضافه لاعب جديد", "إضافة لاعب جديد"])
    f_contact       = filters.Text(["💬 تواصل",            "تواصل"])

    media_all = (
        filters.TEXT | filters.PHOTO | filters.VIDEO
        | filters.Document.ALL | filters.VOICE | filters.AUDIO
        | filters.Sticker.ALL  | filters.VIDEO_NOTE
    )
    photo_video = filters.PHOTO | filters.VIDEO

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(enter_change_user,   pattern="^change_user$"),
            CallbackQueryHandler(enter_change_serial, pattern="^change_serial$"),
            CallbackQueryHandler(enter_add_player,    pattern="^add_player$"),
            CallbackQueryHandler(enter_contact,       pattern="^contact$"),
            MessageHandler(f_change_user   & ~filters.COMMAND, enter_change_user),
            MessageHandler(f_change_serial & ~filters.COMMAND, enter_change_serial),
            MessageHandler(f_add_player    & ~filters.COMMAND, enter_add_player),
            MessageHandler(f_contact       & ~filters.COMMAND, enter_contact),
        ],
        states={
            # تغيير يوزر
            CHANGE_USER_OLD:   [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_old_user)],
            CHANGE_USER_NEW:   [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_new_user)],
            CHANGE_USER_PROOF: [
                CallbackQueryHandler(skip_user_proof, pattern="^skip_proof$"),
                MessageHandler(photo_video & ~filters.COMMAND, recv_user_proof),
            ],
            # تغيير تسلسلي
            CHANGE_SERIAL_OLD:   [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_old_serial)],
            CHANGE_SERIAL_NEW:   [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_new_serial)],
            CHANGE_SERIAL_PROOF: [
                CallbackQueryHandler(skip_serial_proof, pattern="^skip_proof$"),
                MessageHandler(photo_video & ~filters.COMMAND, recv_serial_proof),
            ],
            # إضافة لاعب
            ADD_PLAYER_USER:   [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_player_user)],
            ADD_PLAYER_SERIAL: [MessageHandler((filters.TEXT | photo_video) & ~filters.COMMAND, recv_player_serial)],
            ADD_PLAYER_PROOF:  [MessageHandler(photo_video & ~filters.COMMAND, recv_player_proof),
                                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_player_proof)],
            # تواصل
            CONTACT_STATE:     [MessageHandler(media_all & ~filters.COMMAND, recv_contact)],
        },
        fallbacks=[
            CommandHandler("start", cancel_and_restart),
            CallbackQueryHandler(enter_change_user,   pattern="^change_user$"),
            CallbackQueryHandler(enter_change_serial, pattern="^change_serial$"),
            CallbackQueryHandler(enter_add_player,    pattern="^add_player$"),
            CallbackQueryHandler(enter_contact,       pattern="^contact$"),
            MessageHandler(f_change_user   & ~filters.COMMAND, enter_change_user),
            MessageHandler(f_change_serial & ~filters.COMMAND, enter_change_serial),
            MessageHandler(f_add_player    & ~filters.COMMAND, enter_add_player),
            MessageHandler(f_contact       & ~filters.COMMAND, enter_contact),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)

    # ردود الأدمنية
    app.add_handler(MessageHandler(
        filters.Chat(ADMIN_GROUP_ID) & filters.REPLY & ~filters.COMMAND,
        handle_admin_reply,
    ))
    app.add_handler(CallbackQueryHandler(handle_admin_confirm, pattern="^adm_(yes|no)_"))

    logger.info("✅ البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
