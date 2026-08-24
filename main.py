import os
import json
import time
import threading
import requests
from flask import Flask
from telebot import TeleBot, types

# ==================== WEB SERVER GIẢ ĐỂ RENDER CHẠY 24/7 ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot HitClub Telegram đang chạy 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Self-ping giữ nhịp chống ngủ đông
def self_ping():
    time.sleep(10)
    url = "https://oxy-1-tz8l.onrender.com/"
    while True:
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass
        time.sleep(600)

# ==================== CẤU HÌNH BOT TELEGRAM ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8834697381:AAEhaB1xAZ5g6yTYL4v1HDpXUuNw9SalnbI")
bot = TeleBot(BOT_TOKEN, threaded=True)

# URL API HitClub theo ảnh
HITCLUB_ENDPOINTS = {
    "hitclub_tx": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_tx",
    "hitclub_md5": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_md5"
}

def fetch_hitclub_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        return f"Lỗi HTTP {response.status_code}: Không thể lấy dữ liệu từ HitClub."
    except Exception as e:
        return f"Lỗi kết nối API: {str(e)}"

def format_response(title, data):
    if isinstance(data, (dict, list)):
        formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
        return f"🔥 **{title}**\n```json\n{formatted_json}\n```"
    return f"🔥 **{title}**\n{data}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_tx = types.InlineKeyboardButton("🎲 HITCLUB TX", callback_data="hitclub_tx")
    btn_md5 = types.InlineKeyboardButton("⚡ HITCLUB MD5", callback_data="hitclub_md5")
    
    markup.add(btn_tx, btn_md5)
    
    bot.reply_to(
        message, 
        "🤖 **Bot Tra Cứu HITCLUB**\nChọn loại dự đoán/dữ liệu bạn muốn tra cứu:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    bot.answer_callback_query(call.id, "Đang lấy dữ liệu HitClub...")
    
    if call.data in HITCLUB_ENDPOINTS:
        title = "Dữ Liệu HitClub TX" if call.data == "hitclub_tx" else "Dữ Liệu HitClub MD5"
        url = HITCLUB_ENDPOINTS[call.data]
        
        data = fetch_hitclub_data(url)
        msg = format_response(title, data)
        
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

def run_bot():
    print("Bot HitClub đang chạy...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    run_bot()
