import os
import subprocess
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# बॉट टोकन यहाँ डालें या Render Environment Variable में सेट करें
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("हेलो! मुझे कोई वीडियो फ़ाइल या डायरेक्ट वीडियो लिंक भेजें, मैं उसका स्क्रीनशॉट जनरेट कर दूंगा।")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("स्क्रीनशॉट जनरेट हो रहा है, कृपया प्रतीक्षा करें...")
    
    video_url = None
    
    # अगर यूजर ने फ़ाइल भेजी है
    if update.message.video or update.message.document:
        file_obj = await (update.message.video or update.message.document).get_file()
        video_url = file_obj.file_path # Telegram Direct Stream URL
    # अगर यूजर ने टेक्स्ट लिंक भेजा है
    elif update.message.text and update.message.text.startswith("http"):
        video_url = update.message.text
        
    if not video_url:
        await msg.edit_text("कृपया एक वैध वीडियो या लिंक भेजें।")
        return

    output_image = f"ss_{update.message.message_id}.jpg"

    # FFmpeg कमांड: बिना पूरा डाउनलोड किए 5वें सेकंड का फ्रेम निकालना
    # -ss 00:00:05 (समय)
    ffmpeg_cmd = [
        "ffmpeg",
        "-ss", "00:00:05", 
        "-i", video_url,
        "-vframes", "1",
        "-q:v", "2",
        output_image,
        "-y"
    ]

    try:
        # FFmpeg प्रोसेस चलाना
        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        # इमेज भेजना
        with open(output_image, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="यह रहा आपका स्क्रीनशॉट!")
            
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"स्क्रीनशॉट जनरेट करने में विफलता हुई।")
        logging.error(f"Error: {e}")

    finally:
        # सर्वर साफ़ करना (Auto-Delete Image File)
        if os.path.exists(output_image):
            os.remove(output_image)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.TEXT, process_video))
    
    app.run_polling()
