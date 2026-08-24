import os
import json
import threading
import requests
from flask import Flask
from telebot import TeleBot, types

# Tạo web server giả để Render không báo lỗi Port
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Telegram đang chạy 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Token và logic Bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8834697381:AAEhaB1xAZ5g6yTYL4v1HDpXUuNw9SalnbI")
API_KEY = os.getenv("API_KEY", "YOUR_KEY")  # Thay YOUR_KEY thành key kwinstore của bạn
BASE_URL = "https://kwinstore.com"

bot = TeleBot(BOT_TOKEN, threaded=True)

def fetch_data(endpoint):
    url = f"{BASE_URL}{endpoint}/{API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        return f"Lỗi HTTP {response.status_code}: Không thể lấy dữ liệu."
    except Exception as e:
        return f"Lỗi kết nối API: {str(e)}"

def format_response(title, data):
    if isinstance(data, (dict, list)):
        formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
        return f"📊 **{title}**\n```json\n{formatted_json}\n```"
    return f"📊 **{title}**\n{data}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_tx = types.InlineKeyboardButton("🎲 TX Mới Nhất", callback_data="tx")
    btn_tx_hist = types.InlineKeyboardButton("📜 Lịch Sử TX", callback_data="tx_history")
    btn_md5 = types.InlineKeyboardButton("⚡ MD5 Mới Nhất", callback_data="md5")
    btn_md5_hist = types.InlineKeyboardButton("📜 Lịch Sử MD5", callback_data="md5_history")
    
    markup.add(btn_tx, btn_tx_hist, btn_md5, btn_md5_hist)
    bot.reply_to(message, "🤖 **Bot Tra Cứu SUMCLUB**\nChọn chức năng bạn muốn xem bên dưới:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    bot.answer_callback_query(call.id, "Đang tải dữ liệu...")
    endpoints = {
        "tx": ("/sumclub/tx", "Kết Quả TX"),
        "tx_history": ("/sumclub/tx/history", "Lịch Sử TX"),
        "md5": ("/sumclub/md5", "Kết Quả MD5"),
        "md5_history": ("/sumclub/md5/history", "Lịch Sử MD5")
    }
    if call.data in endpoints:
        endpoint, title = endpoints[call.data]
        data = fetch_data(endpoint)
        msg = format_response(title, data)
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

def run_bot():
    print("Bot Sumclub đang chạy...")
    # Đã bỏ tham số non_stop=True để hết lỗi
    bot.infinity_polling(timeout=60, long_polling_timeout=30)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
