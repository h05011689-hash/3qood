import telebot
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8772212108:AAFUjVvAExDilYsbWA13iuLnVWn0957tyYs"
CHANNEL_ID = "@eFootball_vvvvv"
APPROVAL_GROUP_ID = -1003936886148

bot = telebot.TeleBot(TOKEN)

published_texts = []
pending_approvals = {}
pending_rejection_reason = {}


# ==================== فحص الكليشة ====================

def check_cliche(text):
    if "الاتحاد العربي للكـلانات" in text:
        if "ضد الخصـم" in text:
            checks = [
                (r"فـوز الـلاعب\s+⟵\s+❮(.+?)❯", "فوز اللاعب"),
                (r"ضد الخصـم\s+⟵\s+❮(.+?)❯", "ضد الخصم"),
                (r"الـنوع\s+⟵\s+❴(.+?)❵", "النوع"),
                (r"منظم البطولة\s+\|\s+⟵\s+⦓(.+?)⦔", "منظم البطولة"),
                (r"رابط منشور الفوز\s+\|\s+⟵\s+⦓(.+?)⦔", "رابط منشور الفوز")
            ]
        else:
            checks = [
                (r"فوز اللاعب\s+❴(.+?)❵", "فوز اللاعب"),
                (r"الـنوع\s+⟵\s+❴(.+?)❵", "النوع"),
                (r"منظم البطولة\s+\|\s+⟵\s+⦓(.+?)⦔", "منظم البطولة"),
                (r"رابط منشور الفوز\s+\|\s+⟵\s+⦓(.+?)⦔", "رابط منشور الفوز")
            ]
        for pattern, label in checks:
            m = re.search(pattern, text)
            if not m or not m.group(1).strip():
                return f"⚠️ خطأ في كليشة الاتحاد: حقل ({label}) فارغ."
        return True

    if "#كليشة_تصنيف_الكلانات" not in text:
        return "❌ الخطأ: الهاشتاق #كليشة_تصنيف_الكلانات غير موجود."

    checks = [
        (r"الـنوع\s+⟵\s+❴(.+?)❵", "الـنوع"),
        (r"فوز كلان\s+❴(.+?)❵", "الكلان الفائز"),
        (r"ضد كلان\s+❴(.+?)❵", "الكلان الخاسر"),
        (r"النتيجه\s+⟵\s+❴(.+?)❵", "النتيجه"),
        (r"رابـط منشور البـطولة\s+⟵\s+❴(.+?)❵", "رابط المنشور")
    ]
    if "قوائم" not in text:
        checks.append((r"الحكم\s+\|\s+Judgment\s+⟵\s+⦓(.+?)⦔", "يوزر الحكم"))
        checks.append((r"بقيادة\s+\|\s+⦓(.+?)⦔", "يوزر القائد"))

    for pattern, label in checks:
        m = re.search(pattern, text)
        if not m or not m.group(1).strip():
            return f"⚠️ خطأ في الكليشة: حقل ({label}) فارغ أو غير مكتوب بشكل صحيح."
    return True


# ==================== إرسال طلب الموافقة ====================

def send_approval_request(message, text, is_duplicate):
    username = f"@{message.from_user.username}" if message.from_user.username else f"#{message.from_user.id}"

    dup_warning = "⚠️ هذه الكليشة مكررة!\n\n" if is_duplicate else ""
    header = f"📋 طلب نشر كليشة\n👤 {username}  |  🆔 {message.from_user.id}\n\n{dup_warning}"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ قبول", callback_data=f"approve_{message.from_user.id}_{message.message_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{message.from_user.id}_{message.message_id}")
    )

    try:
        full_caption = f"{header}{text}" if text else header

        if message.photo:
            approval_msg = bot.send_photo(
                APPROVAL_GROUP_ID,
                message.photo[-1].file_id,
                caption=full_caption,
                reply_markup=markup
            )
        elif message.video:
            approval_msg = bot.send_video(
                APPROVAL_GROUP_ID,
                message.video.file_id,
                caption=full_caption,
                reply_markup=markup
            )
        else:
            approval_msg = bot.send_message(
                APPROVAL_GROUP_ID,
                full_caption,
                reply_markup=markup
            )

        pending_approvals[approval_msg.message_id] = {
            "user_id": message.from_user.id,
            "username": username,
            "original_chat_id": message.chat.id,
            "original_message_id": message.message_id,
            "text": text,
            "is_duplicate": is_duplicate,
            "has_media": bool(message.photo or message.video)
        }
        return True
    except Exception as e:
        print(f"خطأ إرسال طلب موافقة: {e}")
        return False


# ==================== أزرار القبول / الرفض ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_approval_callback(call):
    action = call.data.split("_")[0]
    approval_msg_id = call.message.message_id

    if approval_msg_id not in pending_approvals:
        bot.answer_callback_query(call.id, "⚠️ هذا الطلب تمت معالجته مسبقاً.", show_alert=True)
        return

    data = pending_approvals[approval_msg_id]
    admin_name = f"@{call.from_user.username}" if call.from_user.username else f"#{call.from_user.id}"

    if action == "approve":
        bot.answer_callback_query(call.id, "✅ تمت الموافقة")
        try:
            bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=data["original_chat_id"],
                message_id=data["original_message_id"]
            )
            bot.send_message(data["user_id"], "••• ✦ تـــم الـــنـــشـــر ✦ •••\n✅ تمت الموافقة على كليشتك ونُشرت في القناة.")

            if data["text"] and not data["is_duplicate"]:
                published_texts.append(data["text"])

            old = call.message.caption or call.message.text or ""
            new_text = f"{old}\n\n✅ قَبِلَ: {admin_name}"
            if data["has_media"]:
                bot.edit_message_caption(new_text, chat_id=call.message.chat.id, message_id=approval_msg_id)
            else:
                bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=approval_msg_id)
        except Exception as e:
            print(f"خطأ قبول: {e}")
        del pending_approvals[approval_msg_id]

    elif action == "reject":
        bot.answer_callback_query(call.id, "اكتب سبب الرفض كـ Reply على الرسالة")
        old = call.message.caption or call.message.text or ""
        new_text = f"{old}\n\n⏳ {admin_name} يكتب سبب الرفض...\nاكتب السبب كـ Reply على هذه الرسالة."
        try:
            if data["has_media"]:
                bot.edit_message_caption(new_text, chat_id=call.message.chat.id, message_id=approval_msg_id, reply_markup=None)
            else:
                bot.edit_message_text(new_text, chat_id=call.message.chat.id, message_id=approval_msg_id, reply_markup=None)
        except Exception as e:
            print(f"خطأ تعديل رسالة رفض: {e}")

        key = f"{call.message.chat.id}_{approval_msg_id}"
        pending_rejection_reason[key] = {
            **data,
            "approval_msg_id": approval_msg_id,
            "admin_name": admin_name
        }
        del pending_approvals[approval_msg_id]


# ==================== استقبال سبب الرفض ====================

@bot.message_handler(func=lambda m: (
    m.chat.id == APPROVAL_GROUP_ID and
    m.reply_to_message is not None
))
def handle_rejection_reason(message):
    replied_id = message.reply_to_message.message_id
    key = f"{APPROVAL_GROUP_ID}_{replied_id}"
    if key not in pending_rejection_reason:
        return

    data = pending_rejection_reason[key]
    reason = message.text.strip() if message.text else "لم يُذكر سبب."

    try:
        bot.send_message(
            data["user_id"],
            f"❌ تم رفض كليشتك\n\n📝 سبب الرفض:\n{reason}"
        )
        old = message.reply_to_message.caption or message.reply_to_message.text or ""
        new_text = f"{old}\n\n❌ رَفَضَ: {data['admin_name']}\n📝 السبب: {reason}"
        if data["has_media"]:
            bot.edit_message_caption(new_text, chat_id=APPROVAL_GROUP_ID, message_id=replied_id)
        else:
            bot.edit_message_text(new_text, chat_id=APPROVAL_GROUP_ID, message_id=replied_id)
    except Exception as e:
        print(f"خطأ إرسال سبب رفض: {e}")

    del pending_rejection_reason[key]


# ==================== الرسائل الواردة ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "أهلاً! ابعت الكليشة وسيتم فحصها وإرسالها للمراجعة.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_messages(message):
    if message.chat.type != 'private':
        return

    text = message.text or message.caption

    if not text:
        bot.reply_to(message, "⚠️ يرجى إرسال نص الكليشة.")
        return

    # 1) فحص الكليشة
    result = check_cliche(text)
    if result is not True:
        bot.reply_to(message, result)
        return

    # 2) فحص التكرار
    is_duplicate = text in published_texts

    # 3) إرسال طلب الموافقة
    success = send_approval_request(message, text, is_duplicate)

    if success:
        if is_duplicate:
            bot.reply_to(message, "⚠️ هذه الكليشة مكررة، تم إرسالها للمراجعة مع تنبيه المشرفين.")
        else:
            bot.reply_to(message, "📨 تم إرسال كليشتك للمراجعة، سيتم إعلامك بالقرار.")
    else:
        bot.reply_to(message, "❌ حدث خطأ، حاول مجدداً.")


print("✅ البوت يعمل...")
bot.infinity_polling()
