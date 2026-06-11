import logging
import io
import requests
from aiogram import Bot, Dispatcher, executor, types

# 🛑 توكن البوت الخاص بك جاهز ومثبت
BOT_TOKEN = "8813517184:AAFVc8wiWbUHsAHKDQuF6w4DzghUHUOzHyo"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.reply(
        "👋 أهلاً بك في بوت رفع الصور السريع والمستقر!\n\n"
        "📸 أرسل لي أي صورة الآن، وسأقوم برفعها فوراً وأعطيك رابطاً مباشراً ينتهي بـ (.jpg) ومتوافق مع شروط اللعبة."
    )

@dp.message_handler(content_types=['photo', 'document'])
async def handle_image(message: types.Message):
    if message.document and not message.document.mime_type.startswith("image/"):
        return

    status_msg = await message.reply("⚡ جاري رفع الصورة وتوليد الرابط المباشر الصافي...")
    
    try:
        # 1. تحميل الصورة من تليجرام في الذاكرة
        if message.photo:
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id
            
        file_info = await bot.get_file(file_id)
        
        image_bytes = io.BytesIO()
        await bot.download_file(file_info.file_path, destination=image_bytes)
        image_bytes.seek(0)
        
        # 2. الرفع إلى سيرفر Catbox المفتوح والسريع جداً
        upload_url = "https://catbox.moe/user/api.php"
        
        payload = {
            "reqtype": "fileupload"
        }
        files = {
            "fileToUpload": ("avatar.jpg", image_bytes.read(), "image/jpeg")
        }
        
        response = requests.post(upload_url, data=payload, files=files, timeout=20)
        
        if response.status_code == 200:
            raw_url = response.text.strip()
            
            # 3. تعديل الرابط لينتهي بـ .jpg إجبارياً لإرضاء كود فحص اللعبة
            if not raw_url.endswith(('.jpg', '.png', '.jpeg', '.webp')):
                direct_url = f"{raw_url}?file=.jpg"
            else:
                direct_url = raw_url
            
            # النص الجديد والمطلوب فقط بالملي
            text = (
                f"✅ **تم الرفع بنجاح!**\n\n"
                f"🔗 `{direct_url}`\n\n"
                f"خذه وضعه في التطبيق الخاص بالاتحاد وستحدث صورتك فوراً.\n\n"
                f"استمتع بتجربه البوت ✨"
            )
            await status_msg.edit_text(text, parse_mode="Markdown")
        else:
            await status_msg.edit_text(f"❌ حدثت مشكلة في السيرفر. كود الرد: {response.status_code}")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ غير متوقع أثناء معالجة الصورة.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
