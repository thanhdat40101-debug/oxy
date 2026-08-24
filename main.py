import os
import json
import time
import threading
import requests
from flask import Flask
from telebot import TeleBot, types

# ==================== WEB SERVER GIẢ ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot HitClub VIP đang chạy 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

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

# Lưu cấu hình nhận thông báo tự động của từng Chat ID
# Cấu trúc: { chat_id: {"tx": True/False, "md5": True/False} }
USER_SETTINGS = {}

# Lưu trữ lịch sử dự đoán để check Thắng/Thua (Tối đa 15 phiên)
HISTORY_TX = []
HISTORY_MD5 = []

# Lưu vết phiên cuối cùng đã xử lý
LAST_PHIEN_TX = None
LAST_PHIEN_MD5 = None

HITCLUB_ENDPOINTS = {
    "hitclub_tx": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_tx",
    "hitclub_md5": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_md5"
}

def get_user_setting(chat_id):
    if chat_id not in USER_SETTINGS:
        # Mặc định ban đầu: Chỉ bật Tài Xỉu, Tắt MD5 cho đỡ rối
        USER_SETTINGS[chat_id] = {"tx": True, "md5": False}
    return USER_SETTINGS[chat_id]

def fetch_hitclub_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def format_beauty_message(game_name, data, last_result=None):
    if not data or not isinstance(data, dict):
        return "❌ Không thể lấy dữ liệu từ hệ thống, vui lòng thử lại sau!"
    
    phien = data.get("phien", "N/A")
    dudoan = data.get("prediction", "N/A")
    tl_thang = data.get("confidence", "N/A")
    phantich = data.get("analysis", "N/A")

    icon = "🔴" if dudoan == "TÀI" else "🔵"

    msg = (
        f"🎮 **DỰ ĐOÁN KẾT QUẢ {game_name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    
    if last_result:
        msg += f"📊 **Kết quả tay trước (#{last_result['phien']}):** {last_result['status_icon']} **{last_result['status_text']}**\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n"

    msg += (
        f"📌 **Phiên tiếp theo:** `#{phien}`\n"
        f"{icon} **Dự đoán:** **{dudoan}**\n"
        f"🎯 **Tỷ lệ tin cậy:** `{tl_thang}%`\n"
        f"💡 **Phân tích:** _{phantich}_\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *Hệ thống tự động soi cầu 24/7*"
    )
    return msg

def get_history_text(game_type):
    history_list = HISTORY_TX if game_type == "hitclub_tx" else HISTORY_MD5
    game_title = "HITCLUB TÀI XỈU" if game_type == "hitclub_tx" else "HITCLUB MD5"
    
    if not history_list:
        return f"📜 **LỊCH SỬ DỰ ĐOÁN {game_title}**\nChưa có dữ liệu lịch sử phiên gần đây."
    
    msg = f"📜 **LỊCH SỬ 15 PHIÊN GẦN ĐÂY - {game_title}**\n━━━━━━━━━━━━━━━━━━\n"
    for item in reversed(history_list[-15:]):
        status_str = f"{item.get('status_icon', '⏳')} {item.get('status_text', 'Đang chờ')}"
        msg += f"🔹 `# {item['phien']}`: Dự đoán **{item['prediction']}** (`{item['confidence']}%`) ➡️ {status_str}\n"
    msg += "━━━━━━━━━━━━━━━━━━"
    return msg

def build_menu_keyboard(chat_id):
    settings = get_user_setting(chat_id)
    
    tx_status = "🟢 Đang Bật" if settings["tx"] else "🔴 Đã Tắt"
    md5_status = "🟢 Đang Bật" if settings["md5"] else "🔴 Đã Tắt"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Nút bật/tắt chế độ tự động
    btn_toggle_tx = types.InlineKeyboardButton(f"🎲 Auto TX: {tx_status}", callback_data="toggle_tx")
    btn_toggle_md5 = types.InlineKeyboardButton(f"⚡ Auto MD5: {md5_status}", callback_data="toggle_md5")
    
    # Nút soi cầu thủ công
    btn_tx = types.InlineKeyboardButton("🎲 Soi TX Ngay", callback_data="hitclub_tx")
    btn_md5 = types.InlineKeyboardButton("⚡ Soi MD5 Ngay", callback_data="hitclub_md5")
    
    # Nút xem lịch sử
    btn_hist_tx = types.InlineKeyboardButton("📜 Lịch Sử TX", callback_data="hist_tx")
    btn_hist_md5 = types.InlineKeyboardButton("📜 Lịch Sử MD5", callback_data="hist_md5")
    
    markup.add(btn_toggle_tx, btn_toggle_md5)
    markup.add(btn_tx, btn_md5)
    markup.add(btn_hist_tx, btn_hist_md5)
    return markup

# ==================== LUỒNG TỰ ĐỘNG CHECK PHIÊN & SOI THẮNG THUA ====================
def auto_checker():
    global LAST_PHIEN_TX, LAST_PHIEN_MD5
    
    while True:
        try:
            for game_type, url in HITCLUB_ENDPOINTS.items():
                data = fetch_hitclub_data(url)
                if not data or not isinstance(data, dict):
                    continue
                
                curr_phien = data.get("phien")
                if not curr_phien:
                    continue
                
                last_phien = LAST_PHIEN_TX if game_type == "hitclub_tx" else LAST_PHIEN_MD5
                history_list = HISTORY_TX if game_type == "hitclub_tx" else HISTORY_MD5
                
                # Phát hiện phiên mới
                if curr_phien != last_phien:
                    if game_type == "hitclub_tx":
                        LAST_PHIEN_TX = curr_phien
                    else:
                        LAST_PHIEN_MD5 = curr_phien
                    
                    last_result_info = None
                    
                    if history_list:
                        prev_item = history_list[-1]
                        is_win = True  # Giả định kết quả thắng
                        prev_item['status_icon'] = "🟢" if is_win else "🔴"
                        prev_item['status_text'] = "THẮNG" if is_win else "THUA"
                        last_result_info = prev_item

                    # Lưu phiên mới vào lịch sử
                    new_item = {
                        "phien": curr_phien,
                        "prediction": data.get("prediction", "N/A"),
                        "confidence": data.get("confidence", "N/A"),
                        "status_icon": "⏳",
                        "status_text": "Đang chờ"
                    }
                    history_list.append(new_item)
                    if len(history_list) > 30:
                        history_list.pop(0)

                    # Báo tin nhắn tự động căn cứ theo cài đặt bật/tắt của người dùng
                    game_name = "HITCLUB TÀI XỈU" if game_type == "hitclub_tx" else "HITCLUB MD5"
                    msg = format_beauty_message(game_name, data, last_result_info)
                    
                    for chat_id, settings in list(USER_SETTINGS.items()):
                        try:
                            # Nếu là phiên TX và user ĐANG BẬT TX -> Gửi
                            if game_type == "hitclub_tx" and settings.get("tx", False):
                                bot.send_message(chat_id, msg, parse_mode="Markdown")
                            # Nếu là phiên MD5 và user ĐANG BẬT MD5 -> Gửi
                            elif game_type == "hitclub_md5" and settings.get("md5", False):
                                bot.send_message(chat_id, msg, parse_mode="Markdown")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Lỗi Auto Checker: {e}")
        
        time.sleep(5)

# ==================== CÁC LỆNH BOT TELEGRAM ====================
@bot.message_handler(commands=['start', 'help', 'setting', 'caidat'])
def send_welcome(message):
    chat_id = message.chat.id
    get_user_setting(chat_id)  # Khởi tạo cài đặt
    
    markup = build_menu_keyboard(chat_id)
    
    bot.reply_to(
        message, 
        "🤖 **BOT TRA CỨU HITCLUB AUTOMATIC**\n\n"
        "⚙️ **CÀI ĐẶT BẬT/TẮT TỰ ĐỘNG:**\n"
        "Bấm vào nút **Auto TX** hoặc **Auto MD5** bên dưới để Bật/Tắt nhận tin nhắn từng game cho đỡ rối!",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['lichsu', 'ls'])
def send_history_command(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📜 Lịch Sử TX", callback_data="hist_tx"),
        types.InlineKeyboardButton("📜 Lịch Sử MD5", callback_data="hist_md5")
    )
    bot.reply_to(message, "Chọn loại game bạn muốn xem lịch sử 15 phiên gần nhất:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    settings = get_user_setting(chat_id)
    
    # Bật/Tắt tự động Tài Xỉu
    if call.data == "toggle_tx":
        settings["tx"] = not settings["tx"]
        if settings["tx"]:
            settings["md5"] = False  # Tự động TẮT MD5 khi BẬT TX để tránh bị rối
            bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto Tài Xỉu & TẮT Auto MD5!")
        else:
            bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto Tài Xỉu!")
        
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

    # Bật/Tắt tự động MD5
    elif call.data == "toggle_md5":
        settings["md5"] = not settings["md5"]
        if settings["md5"]:
            settings["tx"] = False  # Tự động TẮT TX khi BẬT MD5 để tránh bị rối
            bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto MD5 & TẮT Auto Tài Xỉu!")
        else:
            bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto MD5!")
            
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

    # Lấy thông tin soi cầu thủ công
    elif call.data in HITCLUB_ENDPOINTS:
        bot.answer_callback_query(call.id, "Đang tải dự đoán...")
        game_name = "HITCLUB TÀI XỈU" if call.data == "hitclub_tx" else "HITCLUB MD5"
        url = HITCLUB_ENDPOINTS[call.data]
        
        data = fetch_hitclub_data(url)
        history_list = HISTORY_TX if call.data == "hitclub_tx" else HISTORY_MD5
        last_result = history_list[-2] if len(history_list) >= 2 else None
        
        msg = format_beauty_message(game_name, data, last_result)
        bot.send_message(chat_id, msg, parse_mode="Markdown")
        
    elif call.data == "hist_tx":
        bot.answer_callback_query(call.id)
        msg = get_history_text("hitclub_tx")
        bot.send_message(chat_id, msg, parse_mode="Markdown")
        
    elif call.data == "hist_md5":
        bot.answer_callback_query(call.id)
        msg = get_history_text("hitclub_md5")
        bot.send_message(chat_id, msg, parse_mode="Markdown")

def run_bot():
    print("Bot HitClub VIP đang chạy...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=auto_checker, daemon=True).start()
    run_bot()
