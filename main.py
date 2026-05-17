import telebot
import re
import base64
import requests
from groq import Groq
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8772212108:AAFUjVvAExDilYsbWA13iuLnVWn0957tyYs"
CHANNEL_ID = "@eFootball_vvvvv"
LOG_GROUP_ID = -1003936886148          # جروب التكرار / القبول والرفض / المحتوى المسيء (كلهم نفس الجروب)
REPORT_GROUP_ID = -1003936886148
APPROVAL_GROUP_ID = -1003936886148     # نفس الجروب للموافقة

bot = telebot.TeleBot(TOKEN)

# إعداد Groq API
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

# قائمة لتخزين النصوص المنشورة لمنع التكرار
published_texts = []

# قاموس لتخزين الكليشات المعلقة انتظاراً للموافقة
# المفتاح: message_id في جروب الموافقة
# القيمة: dict يحتوي على بيانات الرسالة الأصلية
pending_approvals = {}

# قاموس لتخزين المشرفين الذين ينتظرون كتابة سبب الرفض
# المفتاح: admin_chat_id (جروب الموافقة) + "_" + approval_msg_id
# القيمة: dict ببيانات الكليشة
pending_rejection_reason = {}


# ==================== دوال التحميل والتحليل ====================

def download_file(file_id):
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    response = requests.get(file_url)
    return response.content

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def analyze_image_with_grok(image_base64):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "أنت مساعد تدقيق محتوى. حلل هذه الصورة وأجب فقط بـ 'yes' أو 'no' بدون أي كلام آخر.\n"
                                "أجب بـ 'yes' إذا كانت الصورة تحتوي على أي مما يلي: مشاهد إباحية، عُري فاضح، عنف دموي مفرط، أو صور صادمة جداً.\n"
                                "أجب بـ 'no' إذا كانت الصورة عادية ولا تحتوي على أي من هذه المحتويات."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0,
            max_tokens=5
        )
        response = completion.choices[0].message.content.strip().lower()
        return 'no' in response
    except Exception as e:
        print(f"خطأ في تحليل الصورة: {e}")
        return False

def analyze_text_with_grok(text):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "أنت مدقق محتوى. أجب فقط بـ 'yes' أو 'no'."
                },
                {
                    "role": "user",
                    "content": (
                        f"هل يحتوي هذا النص على كلام مسيء، بذيء، عنصري، شتائم، أو وصف إباحي؟\n"
                        f"أجب بـ 'yes' إذا كان كذلك، وإلا 'no'.\n\n"
                        f"النص: {text}"
                    )
                }
            ],
            temperature=0,
            max_tokens=5
        )
        response = completion.choices[0].message.content.strip().lower()
        return 'no' in response
    except Exception as e:
        print(f"خطأ في تحليل النص: {e}")
        return False

def moderate_content(message):
    has_text = bool(message.text or message.caption)
    file_id = None

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        thumb = message.video.thumb
        if thumb:
            file_id = thumb.file_id
        else:
            return False

    if file_id:
        try:
            media_bytes = download_file(file_id)
            media_base64 = encode_image(media_bytes)
            if not analyze_image_with_grok(media_base64):
                return False
        except Exception as e:
            print(f"خطأ في تحميل/فحص الوسائط: {e}")
            return False

    if has_text:
        text_to_check = message.text if message.text else message.caption
        if not analyze_text_with_grok(text_to_check):
            return False

    return True


# ==================== فحص الكليشة ====================

def check_cliche(text):
    if "الاتحاد العربي للكـلانات" in text:
        new_checks = []
        if "ضد الخصـم" in text:
            new_checks = [
                (r"فـوز الـلاعب\s+⟵\s+❮(.+?)❯", "فوز اللاعب"),
                (r"ضد الخصـم\s+⟵\s+❮(.+?)❯", "ضد الخصم"),
                (r"الـنوع\s+⟵\s+❴(.+?)❵", "النوع"),
                (r"منظم البطولة\s+\|\s+⟵\s+⦓(.+?)⦔", "منظم البطولة"),
                (r"رابط منشور الفوز\s+\|\s+⟵\s+⦓(.+?)⦔", "رابط منشور الفوز")
            ]
        else:
            new_checks = [
                (r"فوز اللاعب\s+❴(.+?)❵", "فوز اللاعب"),
                (r"الـنوع\s+⟵\s+❴(.+?)❵", "النوع"),
                (r"منظم البطولة\s+\|\s+⟵\s+⦓(.+?)⦔", "منظم البطولة"),
                (r"رابط منشور الفوز\s+\|\s+⟵\s+⦓(.+?)⦔", "رابط منشور الفوز")
            ]

        for pattern, label in new_checks:
            match = re.search(pattern, text)
            if not match or not match.group(1).strip():
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
        match = re.search(pattern, text)
        if not match or not match.group(1).strip() or match.group(1).strip() in ["", " "]:
            return f"⚠️ خطأ في الكليشة: حقل ({label}) فارغ أو غير مكتوب بشكل صحيح."

    return True


# ==================== إرسال طلب الموافقة ====================

def send_approval_request(message, text, is_duplicate):
    """إرسال الكليشة إلى جروب الموافقة مع أزرار قبول/رفض"""

    username = f"@{message.from_user.username}" if message.from_user.username else f"#{message.from_user.id}"
    duplicate_warning = "\n\n⚠️ **تحذير: هذه الكليشة مكررة (تم نشرها من قبل)**" if is_duplicate else ""

    info_text = (
        f"📋 **طلب نشر كليشة جديدة**\n\n"
        f"👤 المستخدم: {username}\n"
        f"🆔 المعرف: {message.from_user.id}"
        f"{duplicate_warning}"
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ قبول", callback_data=f"approve_{message.from_user.id}_{message.message_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{message.from_user.id}_{message.message_id}")
    )

    try:
        # إرسال معلومات المستخدم
        bot.send_message(APPROVAL_GROUP_ID, info_text, parse_mode="Markdown")

        # إعادة توجيه الرسالة الأصلية (الكليشة)
        forwarded = bot.forward_message(APPROVAL_GROUP_ID, message.chat.id, message.message_id)

        # إرسال أزرار القبول/الرفض
        approval_msg = bot.send_message(APPROVAL_GROUP_ID, "اختر القرار:", reply_markup=markup)

        # تخزين بيانات الكليشة المعلقة
        pending_approvals[approval_msg.message_id] = {
            "user_id": message.from_user.id,
            "username": username,
            "original_chat_id": message.chat.id,
            "original_message_id": message.message_id,
            "text": text,
            "forwarded_msg_id": forwarded.message_id,
            "is_duplicate": is_duplicate
        }

        return True
    except Exception as e:
        print(f"خطأ في إرسال طلب الموافقة: {e}")
        return False


# ==================== معالجة أزرار القبول/الرفض ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def handle_approval_callback(call):
    parts = call.data.split("_")
    action = parts[0]         # approve أو reject
    user_id = int(parts[1])   # معرف المستخدم

    approval_msg_id = call.message.message_id

    # البحث عن بيانات الكليشة
    if approval_msg_id not in pending_approvals:
        bot.answer_callback_query(call.id, "⚠️ هذا الطلب لم يعد موجوداً أو تمت معالجته.", show_alert=True)
        return

    data = pending_approvals[approval_msg_id]

    if action == "approve":
        bot.answer_callback_query(call.id, "✅ تمت الموافقة على النشر")

        try:
            # النشر في القناة
            bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=data["original_chat_id"],
                message_id=data["original_message_id"]
            )

            # إبلاغ المستخدم
            bot.send_message(data["user_id"], "••• ✦ تـــم الـــنـــشـــر ✦ •••\n\n✅ تمت الموافقة على كليشتك ونُشرت في القناة.")

            # إضافة النص للقائمة لمنع التكرار
            if data["text"] and not data["is_duplicate"]:
                published_texts.append(data["text"])

            # تحديث رسالة الأزرار
            admin_name = f"@{call.from_user.username}" if call.from_user.username else f"#{call.from_user.id}"
            bot.edit_message_text(
                f"✅ **تمت الموافقة بواسطة:** {admin_name}",
                chat_id=call.message.chat.id,
                message_id=approval_msg_id,
                parse_mode="Markdown"
            )

        except Exception as e:
            bot.send_message(data["user_id"], f"❌ حدث خطأ أثناء النشر: {e}")

        # حذف من القائمة المعلقة
        del pending_approvals[approval_msg_id]

    elif action == "reject":
        bot.answer_callback_query(call.id, "🔴 اكتب سبب الرفض في رسالة في الجروب")

        # تحديث رسالة الأزرار
        admin_name = f"@{call.from_user.username}" if call.from_user.username else f"#{call.from_user.id}"
        bot.edit_message_text(
            f"⏳ **{admin_name}** بصدد كتابة سبب الرفض...\n\nاكتب سبب الرفض كرد (Reply) على هذه الرسالة.",
            chat_id=call.message.chat.id,
            message_id=approval_msg_id,
            parse_mode="Markdown"
        )

        # تخزين انتظار سبب الرفض
        key = f"{call.message.chat.id}_{approval_msg_id}"
        pending_rejection_reason[key] = {
            **data,
            "approval_msg_id": approval_msg_id,
            "admin_id": call.from_user.id,
            "admin_name": admin_name
        }

        # حذف من القائمة المعلقة
        del pending_approvals[approval_msg_id]


# ==================== استقبال سبب الرفض (رد على رسالة الأزرار) ====================

@bot.message_handler(func=lambda message: (
    message.chat.id == APPROVAL_GROUP_ID and
    message.reply_to_message is not None
))
def handle_rejection_reason(message):
    replied_msg_id = message.reply_to_message.message_id
    key = f"{APPROVAL_GROUP_ID}_{replied_msg_id}"

    if key not in pending_rejection_reason:
        return  # ليس رداً على طلب رفض معلق

    data = pending_rejection_reason[key]
    reason = message.text.strip() if message.text else "لم يُذكر سبب."

    try:
        # إرسال الرفض مع السبب للمستخدم في رسالة واحدة
        rejection_msg = (
            f"❌ **تم رفض كليشتك**\n\n"
            f"📝 **سبب الرفض:**\n{reason}"
        )
        bot.send_message(data["user_id"], rejection_msg, parse_mode="Markdown")

        # تحديث رسالة الجروب
        bot.edit_message_text(
            f"❌ **تم الرفض بواسطة:** {data['admin_name']}\n\n📝 **السبب:** {reason}",
            chat_id=APPROVAL_GROUP_ID,
            message_id=replied_msg_id,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"خطأ في إرسال سبب الرفض: {e}")

    # حذف من قائمة انتظار الرفض
    del pending_rejection_reason[key]


# ==================== معالجة الرسائل الواردة ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "أهلاً بك! ابعت الكليشة كاملة (صورة بنص أو نص فقط) وسيتم فحصها قبل إرسالها للموافقة.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_messages(message):
    # فقط في الخاص
    if message.chat.type != 'private':
        return

    text = message.text if message.text else message.caption

    if not text and not (message.photo or message.video):
        bot.reply_to(message, "⚠️ يرجى إرسال نص الكليشة مع الصورة أو الفيديو.")
        return

    # فحص المحتوى غير اللائق
    if not moderate_content(message):
        bot.reply_to(message, "⛔ تم رفض النشر بسبب محتوى غير لائق (إباحي/دموي/مسيء).")
        try:
            report = (
                f"🚨 **محاولة نشر محتوى غير لائق**\n\n"
                f"👤 المستخدم: @{message.from_user.username}\n"
                f"🆔 المعرف: {message.from_user.id}\n"
                f"📝 النص: {text if text else 'لا يوجد نص'}"
            )
            bot.forward_message(REPORT_GROUP_ID, message.chat.id, message.message_id)
            bot.send_message(REPORT_GROUP_ID, report, parse_mode="Markdown")
        except Exception as e:
            print(f"خطأ في إرسال بلاغ المحتوى المسيء: {e}")
        return

    # فحص الكليشة
    result = check_cliche(text)
    if result is not True:
        bot.reply_to(message, result)
        return

    # فحص التكرار (إبلاغ المستخدم فقط، لكن نكمل)
    is_duplicate = text in published_texts if text else False
    if is_duplicate:
        bot.reply_to(
            message,
            "⚠️ **تنبيه:** هذه الكليشة مكررة (تم نشرها من قبل).\n\nسيتم إرسالها للمراجعة مع تنبيه المشرفين بذلك.",
            parse_mode="Markdown"
        )
    
    # إرسال طلب الموافقة للجروب
    success = send_approval_request(message, text, is_duplicate)

    if success:
        if not is_duplicate:
            bot.reply_to(message, "📨 تم إرسال كليشتك للمراجعة، سيتم إعلامك بالقرار قريباً.")
    else:
        bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الكليشة للمراجعة، حاول مجدداً.")


print("البوت يعمل بنظام القبول والرفض مع إبلاغ المستخدم بسبب الرفض...")
bot.infinity_polling()
