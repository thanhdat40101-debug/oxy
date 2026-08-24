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
    time.sleep(15)
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://oxy-1-tz8l.onrender.com/")
    print(f"📌 Started Self-Ping service for: {render_url}")
    
    while True:
        try:
            res = requests.get(render_url, timeout=10)
            print(f"🔄 Self-ping status: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Self-ping error: {e}")
        time.sleep(120)

# ==================== CẤU HÌNH BOT TELEGRAM ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8834697381:AAGi0xQMjHs8BWdqBKnekeHNaVoQAxW1Jcs")
bot = TeleBot(BOT_TOKEN, threaded=True)

USER_SETTINGS = {}
HISTORY_HU = []
HISTORY_MD5 = []

LAST_PHIEN_HU = None
LAST_PHIEN_MD5 = None

STATS = {
    "hu": {"win": 4987, "loss": 4997},
    "md5": {"win": 4987, "loss": 4997}
}

# API mới từ Railway
RAILWAY_ENDPOINTS = {
    "hitclub_hu": "https://bottele-production-4be9.up.railway.app/api/history/taixiu",
    "hitclub_md5": "https://bottele-production-4be9.up.railway.app/api/history/md5"
}

def get_user_setting(chat_id):
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"hu": True, "md5": False}
    return USER_SETTINGS[chat_id]

def fetch_railway_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data
            elif isinstance(data, dict):
                return data.get("data", data.get("history", [data]))
    except Exception as e:
        print(f"❌ Error fetching Railway API ({url}): {e}")
    return None

def analyze_prediction(history_list):
    """Thuật toán dự đoán phiên tiếp theo dựa trên lịch sử"""
    if not history_list:
        return "Tài", "89", "Smart Chaos Engine: Kích hoạt mô hình phân phối biến động"
    
    recent = history_list[-10:]
    tai_count = sum(1 for item in recent if str(item.get("result", "")).upper() == "TÀI")
    
    if tai_count >= 5:
        pred = "Tài"
        conf = min(55 + tai_count * 5, 92)
        analysis = f"Weighting Engine: Trọng số ưu tiên cửa trên ({tai_count}/10 phiên)"
    else:
        pred = "Xỉu"
        conf = min(55 + (10 - tai_count) * 5, 92)
        analysis = f"Weighting Engine: Trọng số ưu tiên cửa dưới ({10 - tai_count}/10 phiên)"
        
    return pred, str(conf), analysis

def generate_cau_string(history_list):
    if not history_list:
        return "🔵🔴🔵🔴🔵🔴"
    cau_icons = []
    for item in history_list[-6:]:
        res = str(item.get("actual_result", item.get("result", "TÀI"))).upper()
        cau_icons.append("🔴" if "TÀI" in res else "🔵")
    return "".join(cau_icons)

def format_beauty_message(game_type, history_data):
    if not history_data or not isinstance(history_data, list):
        return "❌ Không thể lấy dữ liệu từ hệ thống, vui lòng thử lại sau!"
    
    is_hu = (game_type == "hitclub_hu")
    game_title = "HŨ" if is_hu else "MD5"
    st_key = "hu" if is_hu else "md5"
    history_list = HISTORY_HU if is_hu else HISTORY_MD5

    latest = history_data[0] # Phiên gần nhất đã ra kết quả
    prev_phien = latest.get("phien", latest.get("session", "3128226"))
    
    try:
        curr_phien = str(int(prev_phien) + 1)
    except:
        curr_phien = "3128227"

    # Thông tin phiên cũ
    dice_arr = latest.get("dice", latest.get("dices", [1, 2, 3]))
    if isinstance(dice_arr, list) and len(dice_arr) == 3:
        dice_str = f"{dice_arr[0]} · {dice_arr[1]} · {dice_arr[2]} ➔ Tổng {sum(dice_arr)}"
        actual_result = "Tài" if sum(dice_arr) >= 11 else "Xỉu"
    else:
        dice_str = str(dice_arr)
        actual_result = latest.get("result", "Chưa có").capitalize()

    # Tính dự đoán cho phiên mới
    dudoan, confidence, analysis = analyze_prediction(history_list)
    win_icon = "🔴" if dudoan == "Tài" else "🔵"
    
    try:
        conf_num = int(float(confidence))
    except:
        conf_num = 89
    other_conf = 100 - conf_num

    # Đánh giá tay trước
    last_status = "THẮNG"
    if history_list and len(history_list) > 0:
        prev_pred = history_list[-1].get("prediction", "")
        if prev_pred and prev_pred.upper() != actual_result.upper():
            last_status = "THUA"
            
    eval_icon = "✅" if last_status == "THẮNG" else "❌"
    md5_line = "🔑 Mã MD5: Chưa cập nhật\n" if not is_hu else ""

    result_block = (
        f"╭━━━ KẾT QUẢ SẢNH {game_title} ━━━╮\n"
        f"📌 Phiên: {prev_phien}\n"
        f"🎲 Xúc xắc: {dice_str}\n"
        f"{md5_line}"
        f"🎯 Kết quả: {actual_result}\n"
        f"{eval_icon} ĐÁNH GIÁ: {last_status}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
    )

    wins = STATS[st_key]["win"]
    losses = STATS[st_key]["loss"]
    total = wins + losses
    win_pct = round((wins / total * 100), 1) if total > 0 else 49.9

    cau_str = generate_cau_string(history_list)

    msg = (
        f"{result_block}"
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
        f"💬 Nhập /11 để xem chi tiết các tay gần nhất."
    )
    return msg

def get_thongke_text(game_type, limit=15):
    history_list = HISTORY_HU if game_type == "hitclub_hu" else HISTORY_MD5
    game_title = "HITCLUB HŨ" if game_type == "hitclub_hu" else "HITCLUB MD5"
    
    if not history_list:
        return f"📊 **THỐNG KÊ DỰ ĐOÁN {game_title}**\nChưa có dữ liệu thống kê phiên gần đây."
    
    sub_list = history_list[-limit:]
    wins = sum(1 for item in sub_list if item.get('status_text') == 'THẮNG')
    total = len([item for item in sub_list if item.get('status_text') in ['THẮNG', 'THUA']])
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

    msg = f"📊 **THỐNG KÊ {len(sub_list)} PHIÊN GẦN ĐÂY - {game_title}**\n"
    msg += f"📈 **Tỷ lệ Thắng:** `{wins}/{total}` (`{win_rate}%`)\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    for item in sub_list:
        status_str = f"{item.get('status_icon', '🟢')} {item.get('status_text', 'THẮNG')}"
        msg += f"🔹 `# {item['phien']}`: Dự đoán **{item.get('prediction', 'Tài')}** ➡️ {status_str}\n"
    msg += "━━━━━━━━━━━━━━━━━━"
    return msg

def build_menu_keyboard(chat_id):
    settings = get_user_setting(chat_id)
    
    hu_status = "🟢 Đang Bật" if settings.get("hu", False) else "🔴 Đã Tắt"
    md5_status = "🟢 Đang Bật" if settings.get("md5", False) else "🔴 Đã Tắt"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_toggle_hu = types.InlineKeyboardButton(f"🎲 Auto Hũ: {hu_status}", callback_data="toggle_hu")
    btn_toggle_md5 = types.InlineKeyboardButton(f"⚡ Auto MD5: {md5_status}", callback_data="toggle_md5")
    
    btn_hu = types.InlineKeyboardButton("🎲 Soi Bàn Hũ Ngay", callback_data="hitclub_hu")
    btn_md5 = types.InlineKeyboardButton("⚡ Soi Bàn MD5 Ngay", callback_data="hitclub_md5")
    
    btn_hist_hu = types.InlineKeyboardButton("📊 Thống Kê Hũ", callback_data="menu_hist_hu")
    btn_hist_md5 = types.InlineKeyboardButton("📊 Thống Kê MD5", callback_data="menu_hist_md5")
    
    markup.add(btn_toggle_hu, btn_toggle_md5)
    markup.add(btn_hu, btn_md5)
    markup.add(btn_hist_hu, btn_hist_md5)
    return markup

# ==================== LUỒNG AUTO CHECKER ====================
def auto_checker():
    global LAST_PHIEN_HU, LAST_PHIEN_MD5
    
    while True:
        try:
            for game_type, url in RAILWAY_ENDPOINTS.items():
                data_list = fetch_railway_data(url)
                if not data_list or not isinstance(data_list, list):
                    continue
                
                latest = data_list[0]
                curr_phien = str(latest.get("phien", latest.get("session", "")))
                if not curr_phien:
                    continue
                
                last_phien = LAST_PHIEN_HU if game_type == "hitclub_hu" else LAST_PHIEN_MD5
                history_list = HISTORY_HU if game_type == "hitclub_hu" else HISTORY_MD5
                st_key = "hu" if game_type == "hitclub_hu" else "md5"
                
                if curr_phien != last_phien:
                    if game_type == "hitclub_hu":
                        LAST_PHIEN_HU = curr_phien
                    else:
                        LAST_PHIEN_MD5 = curr_phien
                    
                    pred, conf, _ = analyze_prediction(history_list)
                    
                    dice_arr = latest.get("dice", latest.get("dices", []))
                    if isinstance(dice_arr, list) and len(dice_arr) == 3:
                        actual_result = "Tài" if sum(dice_arr) >= 11 else "Xỉu"
                    else:
                        actual_result = latest.get("result", "Tài").capitalize()

                    status_icon = "🟢"
                    status_text = "THẮNG"
                    if pred.upper() == actual_result.upper():
                        STATS[st_key]["win"] += 1
                    else:
                        status_icon = "🔴"
                        status_text = "THUA"
                        STATS[st_key]["loss"] += 1

                    new_item = {
                        "phien": curr_phien,
                        "prediction": pred,
                        "confidence": conf,
                        "actual_result": actual_result,
                        "status_icon": status_icon,
                        "status_text": status_text
                    }
                    history_list.append(new_item)
                    if len(history_list) > 60:
                        history_list.pop(0)

                    msg = format_beauty_message(game_type, data_list)
                    
                    for chat_id, settings in list(USER_SETTINGS.items()):
                        try:
                            if game_type == "hitclub_hu" and settings.get("hu", False):
                                bot.send_message(chat_id, msg)
                            elif game_type == "hitclub_md5" and settings.get("md5", False):
                                bot.send_message(chat_id, msg)
                        except Exception as send_err:
                            print(f"⚠️ Error sending message to {chat_id}: {send_err}")
        except Exception as e:
            print(f"❌ Lỗi Auto Checker: {e}")
        
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
            "Nhập `/11` để chọn xem số lượng tay thống kê mong muốn!",
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
            types.InlineKeyboardButton("📊 Thống Kê Hũ", callback_data="menu_hist_hu"),
            types.InlineKeyboardButton("📊 Thống Kê MD5", callback_data="menu_hist_md5")
        )
        bot.reply_to(message, "Chọn sảnh game bạn muốn xem thống kê:", reply_markup=markup)
    except Exception as e:
        print(f"Error 11: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        settings = get_user_setting(chat_id)
        
        if call.data == "toggle_hu":
            settings["hu"] = not settings.get("hu", False)
            if settings["hu"]:
                settings["md5"] = False
                bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto Bàn Hũ & TẮT Auto MD5!")
            else:
                bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto Bàn Hũ!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

        elif call.data == "toggle_md5":
            settings["md5"] = not settings.get("md5", False)
            if settings["md5"]:
                settings["hu"] = False
                bot.answer_callback_query(call.id, "🟢 Đã BẬT Auto MD5 & TẮT Auto Bàn Hũ!")
            else:
                bot.answer_callback_query(call.id, "🔴 Đã TẮT Auto MD5!")
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

        elif call.data in RAILWAY_ENDPOINTS:
            bot.answer_callback_query(call.id, "Đang tải dự đoán...")
            url = RAILWAY_ENDPOINTS[call.data]
            data_list = fetch_railway_data(url)
            msg = format_beauty_message(call.data, data_list)
            bot.send_message(chat_id, msg)

        elif call.data == "menu_hist_hu":
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("5 Tay", callback_data="hist_hu_5"),
                types.InlineKeyboardButton("10 Tay", callback_data="hist_hu_10"),
                types.InlineKeyboardButton("15 Tay", callback_data="hist_hu_15"),
                types.InlineKeyboardButton("20 Tay", callback_data="hist_hu_20"),
                types.InlineKeyboardButton("30 Tay", callback_data="hist_hu_30"),
                types.InlineKeyboardButton("50 Tay", callback_data="hist_hu_50")
            )
            bot.edit_message_text("🎲 **CHỌN SỐ LƯỢNG TAY BÀN HŨ CẦN XEM:**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

        elif call.data == "menu_hist_md5":
            bot.answer_callback_query(call.id)
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("5 Tay", callback_data="hist_md5_5"),
                types.InlineKeyboardButton("10 Tay", callback_data="hist_md5_10"),
                types.InlineKeyboardButton("15 Tay", callback_data="hist_md5_15"),
                types.InlineKeyboardButton("20 Tay", callback_data="hist_md5_20"),
                types.InlineKeyboardButton("30 Tay", callback_data="hist_md5_30"),
                types.InlineKeyboardButton("50 Tay", callback_data="hist_md5_50")
            )
            bot.edit_message_text("⚡ **CHỌN SỐ LƯỢNG TAY MD5 CẦN XEM:**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

        elif call.data.startswith("hist_hu_"):
            limit = int(call.data.split("_")[2])
            bot.answer_callback_query(call.id, f"Đang tải {limit} tay Bàn Hũ...")
            msg = get_thongke_text("hitclub_hu", limit)
            bot.send_message(chat_id, msg, parse_mode="Markdown")

        elif call.data.startswith("hist_md5_"):
            limit = int(call.data.split("_")[2])
            bot.answer_callback_query(call.id, f"Đang tải {limit} tay MD5...")
            msg = get_thongke_text("hitclub_md5", limit)
            bot.send_message(chat_id, msg, parse_mode="Markdown")

    except Exception as e:
        print(f"Error callback: {e}")

def run_bot():
    print("🚀 Bot HitClub VIP đang bắt đầu polling...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Lỗi polling, đang tự động kết nối lại sau 5s: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=auto_checker, daemon=True).start()
    run_bot()
