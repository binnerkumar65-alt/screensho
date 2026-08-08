import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Render के लिए पोर्ट सर्वर (ताकि Deploy कैंसिल न हो)
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    # Render का पोर्ट पढ़ेगा (डिफ़ॉल्ट 8080)
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# टेलीग्राम बॉट टोकन
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("हेलो! मुझे कोई वीडियो या डायरेक्ट वीडियो लिंक भेजें, मैं स्क्रीनशॉट जनरेट कर दूंगा।")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("स्क्रीनशॉट जनरेट हो रहा है, कृपया प्रतीक्षा करें...")
    
    video_url = None
    
    # फ़ाइल या लिंक चेक करना
    if update.message.video or update.message.document:
        file_obj = await (update.message.video or update.message.document).get_file()
        video_url = file_obj.file_path
    elif update.message.text and update.message.text.startswith("http"):
        video_url = update.message.text
        
    if not video_url:
        await msg.edit_text("कृपया एक वैध वीडियो फ़ाइल या लिंक भेजें।")
        return

    output_image = f"ss_{update.message.message_id}.jpg"

    # FFmpeg स्क्रीनशॉट कमांड (5वें सेकंड का स्क्रीनशॉट)
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
        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        with open(output_image, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="यह रहा आपका स्क्रीनशॉट!")
            
        await msg.delete()

    except Exception as e:
        await msg.edit_text("स्क्रीनशॉट जनरेट करने में विफलता हुई।")
        logging.error(f"Error: {e}")

    finally:
        # सर्वर साफ़ करना (Auto-Delete Image)
        if os.path.exists(output_image):
            os.remove(output_image)

if __name__ == '__main__':
    # Flask पोर्ट सर्वर चालू करना
    Thread(target=run_flask).start()
    
    # Telegram Bot चालू करना
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.TEXT, process_video))
    
    bot_app.run_polling()
