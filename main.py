import os
import subprocess
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Render Port Server (ताकि Deploy न रुके)
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Screenshot Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("हेलो! मुझे Direct Stream Link भेजें, मैं वीडियो पूरी तरह लोड होकर स्टार्ट होने के बाद 5th सेकंड का फ़्रेम निकाल दूंगा।")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("वीडियो स्ट्रीम से कनेक्ट हो रहा है, प्ले होने का इंतज़ार जारी है...")
    
    video_url = None
    
    if update.message.text and update.message.text.startswith("http"):
        video_url = update.message.text.strip()
    elif update.message.video or update.message.document:
        video_obj = update.message.video or update.message.document
        if video_obj.file_size > 20 * 1024 * 1024:
            await msg.edit_text("यह फ़ाइल बहुत बड़ी है। कृपया Direct Stream Link भेजें।")
            return
        file_obj = await video_obj.get_file()
        video_url = file_obj.file_path
        
    if not video_url:
        await msg.edit_text("कृपया एक सही Stream Link भेजें।")
        return

    output_image = f"ss_{update.message.message_id}.jpg"

    # FFmpeg Command:
    # 1. -reconnect ऑप्शंस ताकि स्लो कनेक्शन पर रुके नहीं
    # 2. -i video_url पहले रखा है ताकि स्ट्रीम पहले स्टार्ट और डिकोड हो
    # 3. -ss 00:00:05 को -i के BAD रखा है ताकि जब वीडियो चलना चालू हो, उसके बाद 5th सेकंड का फ्रेम कटे!
    ffmpeg_cmd = [
        "ffmpeg",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "10",
        "-i", video_url,               # वीडियो इनपुट पहले
        "-ss", "00:00:05",              # वीडियो डिकोड होने/चलने के 5वें सेकंड पर
        "-vframes", "1",
        "-q:v", "2",
        output_image,
        "-y"
    ]

    try:
        # FFmpeg को 45 सेकंड का समय दिया ताकि स्ट्रीम लोड होकर वीडियो डिकोड हो सके
        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=45)

        with open(output_image, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="यह रहा वीडियो चालू होने के 5वें सेकंड का स्क्रीनशॉट!")
            
        await msg.delete()

    except subprocess.TimeoutExpired:
        await msg.edit_text("वीडियो स्ट्रीम स्टार्ट होने में बहुत समय लग रहा है। (Render Server Slow)")
    except Exception as e:
        await msg.edit_text("स्क्रीनशॉट जनरेट नहीं हो सका।")
        logging.error(f"Error: {e}")

    finally:
        # स्टोरेज साफ़ करना
        if os.path.exists(output_image):
            os.remove(output_image)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT | filters.VIDEO | filters.Document.VIDEO, process_video))
    
    bot_app.run_polling()
