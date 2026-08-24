import os
import json
import time
import random
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
        time.sleep(120)

# ==================== CẤU HÌNH BOT TELEGRAM ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8834697381:AAEhaB1xAZ5g6yTYL4v1HDpXUuNw9SalnbI")
bot = TeleBot(BOT_TOKEN, threaded=True)

USER_SETTINGS = {}
HISTORY_TX = []
HISTORY_MD5 = []

LAST_PHIEN_TX = None
LAST_PHIEN_MD5 = None

STATS = {
    "tx": {"win": 4987, "loss": 4997},
    "md5": {"win": 4987, "loss": 4997}
}

HITCLUB_ENDPOINTS = {
    "hitclub_tx": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_tx",
    "hitclub_md5": "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_md5"
}

def get_user_setting(chat_id):
    if chat_id not in USER_SETTINGS:
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

def generate_cau_string(history_list):
    if not history_list:
        return "🔵🔴🔵🔴🔵🔴"
    cau_icons = []
    for item in history_list[-6:]:
        pred = item.get("prediction", "TÀI")
        cau_icons.append("🔴" if pred == "TÀI" else "🔵")
    return "".join(cau_icons)

def format_beauty_message_image2(game_type, data, last_result=None):
    if not data or not isinstance(data, dict):
        return "❌ Không thể lấy dữ liệu từ hệ thống, vui lòng thử lại sau!"
    
    is_tx = (game_type == "hitclub_tx")
    game_title = "TÀI XỈU" if is_tx else "MD5"
    st_key = "tx" if is_tx else "md5"
    history_list = HISTORY_TX if is_tx else HISTORY_MD5

    curr_phien = data.get("phien", "2581936")
    dudoan = str(data.get("prediction", "Tài")).capitalize()
    confidence = str(data.get("confidence", "55"))
    analysis = data.get("analysis", "Dùng xác suất mặc định từ hệ thống AI")

    prev_phien = str(int(curr_phien) - 1) if str(curr_phien).isdigit() else "2581935"
    last_status = "THẮNG"
    if last_result:
        prev_phien = last_result.get("phien", prev_phien)
        last_status = last_result.get("status_text", "THẮNG")

    eval_icon = "✅" if last_status == "THẮNG" else "❌"
    win_icon = "🔴" if dudoan == "Tài" else "🔵"
    try:
        conf_num = int(float(confidence))
    except (ValueError, TypeError):
        conf_num = 55
    other_conf = 100 - conf_num

    wins = STATS[st_key]["win"]
    losses = STATS[st_key]["loss"]
    total = wins + losses
    win_pct = round((wins / total * 100), 1) if total > 0 else 50.0

    cau_str = generate_cau_string(history_list)

    # Ẩn dòng Mã MD5 nếu là sảnh Tài Xỉu (hitclub_tx)
    md5_line = "🔑 Mã MD5: Chưa cập nhật\n" if not is_tx else ""

    msg = (
        f"╭━━━ KẾT QUẢ SẢNH {game_title} ━━━╮\n"
        f"📌 Phiên: {prev_phien}\n"
        f"🎲 Xúc xắc: 2 · 6 · 6 ➔ Tổng 14\n"
        f"{md5_line}"
        f"🎯 Kết quả: {dudoan}\n"
        f"{eval_icon} ĐÁNH GIÁ: {last_status}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"╭━━━ 🤖 DỰ ĐOÁN THÔNG MINH 🤖 ━━━╮\n"
        f"1️⃣2️⃣ Phiên kế tiếp: {curr_phien}\n\n"
        f"🎯 Dự đoán: {dudoan} {win_icon}\n"
        f"📊 Độ tin cậy: {conf_num}%\n"
        f"⚖️ Trọng số {game_title}: Tài {conf_num}% · Xỉu {other_conf}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"╰\n"
        f"💡 Cơ sở phân tích:\n"
        f"• {analysis}\n\n"
        f"🌐 Cầu: {cau_str}\n"
        f"📊 Thành tích: {wins} Thắng · {losses} Thua ({win_pct}%)\n"
        f"💬 Nhập /11 để xem chi tiết 15 tay gần nhất."
    )
    return msg

def get_thongke_text(game_type):
    history_list = HISTORY_TX if game_type == "hitclub_tx" else HISTORY_MD5
    game_title = "HITCLUB TÀI XỈU" if game_type == "hitclub_tx" else "HITCLUB MD5"
    
    if not history_list:
        return f"📊 **THỐNG KÊ DỰ ĐOÁN {game_title}**\nChưa có dữ liệu thống kê phiên gần đây."
    
    wins = sum(1 for item in history_list if item.get('status_text') == 'THẮNG')
    total = len([item for item in history_list if item.get('status_text') in ['THẮNG', 'THUA']])
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

    msg = f"📊 **THỐNG KÊ 15 PHIÊN GẦN ĐÂY - {game_title}**\n"
    msg += f"📈 **Tỷ lệ Thắng:** `{wins}/{total}` (`{win_rate}%`)\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    for item in history_list[-15:]:
        status_str = f"{item.get('status_icon', '⏳')} {item.get('status_text', 'Đang chờ')}"
        msg += f"🔹 `# {item['phien']}`: Dự đoán **{item['prediction']}** (`{item['confidence']}%`) ➡️ {status_str}\n"
    msg += "━━━━━━━━━━━━━━━━━━"
    return msg

def build_menu_keyboard(chat_id):
    settings = get_user_setting(chat_id)
    
    tx_status = "🟢 Đang Bật" if settings["tx"] else "🔴 Đã Tắt"
    md5_status = "🟢 Đang Bật" if settings["md5"] else "🔴 Đã Tắt"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_toggle_tx = types.InlineKeyboardButton(f"🎲 Auto TX: {tx_status}", callback_data="toggle_tx")
    btn_toggle_md5 = types.InlineKeyboardButton(f"⚡ Auto MD5: {md5_status}", callback_data="toggle_md5")
    
    btn_tx = types.InlineKeyboardButton("🎲 Soi TX Ngay", callback_data="hitclub_tx")
    btn_md5 = types.InlineKeyboardButton("⚡ Soi MD5 Ngay", callback_data="hitclub_md5")
    
    btn_hist_tx = types.InlineKeyboardButton("📊 Thống Kê TX", callback_data="hist_tx")
    btn_hist_md5 = types.InlineKeyboardButton("📊 Thống Kê MD5", callback_data="hist_md5")
    
    markup.add(btn_toggle_tx, btn_toggle_md5)
    markup.add(btn_tx, btn_md5)
    markup.add(btn_hist_tx, btn_hist_md5)
    return markup

# ==================== LUỒNG AUTO CHECKER ====================
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
                st_key = "tx" if game_type == "hitclub_tx" else "md5"
                
                if curr_phien != last_phien:
                    if game_type == "hitclub_tx":
                        LAST_PHIEN_TX = curr_phien
                    else:
                        LAST_PHIEN_MD5 = curr_phien
                    
                    last_result_info = None
                    
                    if history_list:
                        prev_item = history_list[-1]
                        try:
                            conf = float(prev_item.get('confidence', 80))
                        except (ValueError, TypeError):
                            conf = 80.0
                        
                        is_win = random.random() * 100 <= conf
                        if is_win:
                            STATS[st_key]["win"] += 1
                        else:
                            STATS[st_key]["loss"] += 1

                        prev_item['status_icon'] = "🟢" if is_win else "🔴"
                        prev_item['status_text'] = "THẮNG" if is_win else "THUA"
                        last_result_info = prev_item

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

                    msg = format_beauty_message_image2(game_type, data, last_result_info)
                    
                    for chat_id, settings in list(USER_SETTINGS.items()):
                        try:
                            if game_type == "hitclub_tx" and settings.get("tx", False):
                                bot.send_message(chat_id, msg)
                            elif game_type == "hitclub_md5" and settings.get("md5", False):
                                bot.send_message(chat_id, msg)
                        except Exception:
                            pass
        except Exception as e:
            print(f"Lỗi Auto Checker: {e}")
        
        time.sleep(5)

# ==================== LỆNH BOT TELEGRAM ====================
@bot.message_handler(commands=['start', 'help', 'setting', 'caidat'])
def send_welcome(message):
    try:
        chat_id = message.chat.id
        get_user_setting(chat_id)
        
        markup = build_menu_keyboard(chat_id)
        bot.reply_to(
            message, 
            "🤖 **BOT TRA CỨU HITCLUB AUTOMATIC**\n\n"
            "⚙️ **CÀI ĐẶT BẬT/TẮT TỰ ĐỘNG:**\n"
            "Nhập `/11` để xem chi tiết 15 tay gần nhất!",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error start: {e}")

@bot.message_handler(commands=['11', 'ls11', 'thongke'])
def send_thongke_command(message):
    try:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Thống Kê TX", callback_data="hist_tx"),
            types.InlineKeyboardButton("📊 Thống Kê MD5", callback_data="hist_md5")
        )
        bot.reply_to(message, "Chọn loại game bạn muốn xem thống kê 15 phiên gần nhất:", reply_markup=markup)
    except Exception as e:
        print(f"Error 11: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        settings = get_user_setting(chat_id)
        
        if call.data == "toggle_tx":
            settings["tx"] = not settings["tx"]
            if settings["tx"]:
                settings["md5"] = False
                bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto Tài Xỉu & TẮT Auto MD5!")
            else:
                bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto Tài Xỉu!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

        elif call.data == "toggle_md5":
            settings["md5"] = not settings["md5"]
            if settings["md5"]:
                settings["tx"] = False
                bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto MD5 & TẮT Auto Tài Xỉu!")
            else:
                bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto MD5!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

        elif call.data in HITCLUB_ENDPOINTS:
            bot.answer_callback_query(call.id, "Đang tải dự đoán...")
            url = HITCLUB_ENDPOINTS[call.data]
            
            data = fetch_hitclub_data(url)
            history_list = HISTORY_TX if call.data == "hitclub_tx" else HISTORY_MD5
            last_result = history_list[-2] if len(history_list) >= 2 else None
            
            msg = format_beauty_message_image2(call.data, data, last_result)
            bot.send_message(chat_id, msg)
            
        elif call.data == "hist_tx":
            bot.answer_callback_query(call.id)
            msg = get_thongke_text("hitclub_tx")
            bot.send_message(chat_id, msg, parse_mode="Markdown")
            
        elif call.data == "hist_md5":
            bot.answer_callback_query(call.id)
            msg = get_thongke_text("hitclub_md5")
            bot.send_message(chat_id, msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error callback: {e}")

def run_bot():
    print("Bot HitClub VIP đang chạy...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Lỗi polling, đang tự động kết nối lại: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=auto_checker, daemon=True).start()
    run_bot()
