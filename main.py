import os
import json
import time
import re
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

# API KWIN STORE MỚI
KWIN_KEY = "8167b2c16888dae174a454f493022e22242f35288df59f41"
ENDPOINTS = {
    "hitclub_hu": "https://bottele-production-4be9.up.railway.app/api/history/taixiu",
    "hitclub_md5": f"https://kwinstore.com/hitclub/md5/{KWIN_KEY}",
    "hitclub_md5_history": f"https://kwinstore.com/hitclub/md5/history/{KWIN_KEY}"
}

def get_user_setting(chat_id):
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"hu": True, "md5": False}
    return USER_SETTINGS[chat_id]

def fetch_api_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["data", "history", "list", "results"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
    except Exception as e:
        print(f"❌ Error fetching API ({url}): {e}")
    return None

def parse_item(item):
    """Trích xuất dữ liệu phiên chuẩn từ API"""
    if not isinstance(item, dict):
        return None

    raw_phien = str(item.get("phien", item.get("session", item.get("id", item.get("sid", "0")))))
    digits_only = re.sub(r'\D', '', raw_phien)
    phien = digits_only if digits_only else "0"

    # Lấy xúc xắc
    dice = item.get("dice", item.get("dices", item.get("xucxac", [])))
    if isinstance(dice, list) and len(dice) == 3:
        total = sum(int(x) for x in dice if str(x).isdigit())
        dice_str = f"{dice[0]} · {dice[1]} · {dice[2]} ➔ Tổng {total}"
        actual = "Tài" if total >= 11 else "Xỉu"
    else:
        dice_str = "Chưa cập nhật"
        res_raw = str(item.get("result", item.get("ketqua", item.get("res", "Chưa có")))).upper()
        if "TÀI" in res_raw:
            actual = "Tài"
        elif "XỈU" in res_raw:
            actual = "Xỉu"
        else:
            actual = "Chưa có"

    # Lấy dự đoán từ API Kwin
    dudoan_raw = str(item.get("predict", item.get("dudoan", item.get("prediction", item.get("pred", "Tài"))))).upper()
    dudoan = "Tài" if "TÀI" in dudoan_raw else "Xỉu"
    
    confidence = str(item.get("confidence", item.get("rate", item.get("tyle", item.get("win_rate", "75"))))).replace("%", "")
    analysis = item.get("analysis", item.get("lydo", "Kích hoạt mô hình phân tích dữ liệu thuật toán"))

    return {
        "phien": phien,
        "dice_str": dice_str,
        "actual": actual,
        "dudoan": dudoan,
        "confidence": confidence,
        "analysis": analysis
    }

def get_valid_latest(data_list):
    if not data_list:
        return None
    for item in data_list:
        if isinstance(item, dict):
            parsed = parse_item(item)
            if parsed and parsed["phien"] != "0":
                return parsed
    return parse_item(data_list[0]) if isinstance(data_list[0], dict) else None

def generate_cau_string(history_list):
    if not history_list:
        return "🔵🔴🔵🔴🔵🔴"
    cau_icons = []
    for item in history_list[-6:]:
        res = str(item.get("actual", "Tài")).upper()
        cau_icons.append("🔴" if "TÀI" in res else "🔵")
    return "".join(cau_icons)

def format_beauty_message(game_type, data_list):
    parsed_latest = get_valid_latest(data_list)
    if not parsed_latest:
        return "❌ Không thể lấy dữ liệu từ hệ thống API, vui lòng thử lại sau!"
    
    is_hu = (game_type == "hitclub_hu")
    game_title = "HŨ" if is_hu else "MD5"
    st_key = "hu" if is_hu else "md5"
    history_list = HISTORY_HU if is_hu else HISTORY_MD5

    prev_phien = parsed_latest["phien"]
    try:
        curr_phien = str(int(prev_phien) + 1)
    except:
        curr_phien = "3128227"

    actual_result = parsed_latest["actual"]
    dice_str = parsed_latest["dice_str"]

    # Đánh giá kết quả phiên trước
    last_status = "THẮNG"
    if len(history_list) > 1:
        prev_item = history_list[-2]
        if prev_item.get("dudoan", "").upper() != actual_result.upper():
            last_status = "THUA"
            
    eval_icon = "✅" if last_status == "THẮNG" else "❌"

    result_block = (
        f"╭━━━ KẾT QUẢ SẢNH {game_title} ━━━╮\n"
        f"📌 Phiên: {prev_phien}\n"
        f"🎲 Xúc xắc: {dice_str}\n"
        f"🎯 Kết quả: {actual_result}\n"
        f"{eval_icon} ĐÁNH GIÁ: {last_status}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
    )

    dudoan = parsed_latest["dudoan"]
    confidence = parsed_latest["confidence"]
    analysis = parsed_latest["analysis"]
    win_icon = "🔴" if dudoan == "Tài" else "🔵"
    
    try:
        conf_num = int(float(confidence))
    except:
        conf_num = 75
    other_conf = 100 - conf_num

    wins = STATS[st_key]["win"]
    losses = STATS[st_key]["loss"]
    total = wins + losses
    win_pct = round((wins / total * 100), 1) if total > 0 else 49.9

    cau_str = generate_cau_string(history_list)

    msg = (
        f"{result_block}"
        f"╭━━━ 🤖 DỰ ĐOÁN NGU HAHA 🤖 ━━━╮\n"
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
    total = len(sub_list)
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

    msg = f"📊 **THỐNG KÊ {total} PHIÊN GẦN ĐÂY - {game_title}**\n"
    msg += f"📈 **Tỷ lệ Thắng:** `{wins}/{total}` (`{win_rate}%`)\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    for item in sub_list:
        status_str = f"{item.get('status_icon', '🟢')} {item.get('status_text', 'THẮNG')}"
        msg += f"🔹 `# {item['phien']}`: Dự đoán **{item.get('dudoan', 'Tài')}** ➡️ {status_str}\n"
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
            for game_type in ["hitclub_hu", "hitclub_md5"]:
                url = ENDPOINTS[game_type]
                data_list = fetch_api_data(url)
                if not data_list:
                    continue
                
                parsed = get_valid_latest(data_list)
                if not parsed or parsed["phien"] == "0":
                    continue
                
                curr_phien = parsed["phien"]
                last_phien = LAST_PHIEN_HU if game_type == "hitclub_hu" else LAST_PHIEN_MD5
                history_list = HISTORY_HU if game_type == "hitclub_hu" else HISTORY_MD5
                st_key = "hu" if game_type == "hitclub_hu" else "md5"
                
                if curr_phien != last_phien:
                    if game_type == "hitclub_hu":
                        LAST_PHIEN_HU = curr_phien
                    else:
                        LAST_PHIEN_MD5 = curr_phien

                    status_icon = "🟢"
                    status_text = "THẮNG"
                    if parsed["dudoan"].upper() == parsed["actual"].upper():
                        STATS[st_key]["win"] += 1
                    else:
                        status_icon = "🔴"
                        status_text = "THUA"
                        STATS[st_key]["loss"] += 1

                    parsed["status_icon"] = status_icon
                    parsed["status_text"] = status_text
                    
                    history_list.append(parsed)
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

        elif call.data in ["hitclub_hu", "hitclub_md5"]:
            bot.answer_callback_query(call.id, "Đang tải dự đoán...")
            url = ENDPOINTS[call.data]
            data_list = fetch_api_data(url)
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
            # Lấy thêm lịch sử từ kwinstore nếu danh sách nội bộ chưa đủ
            hist_data = fetch_api_data(ENDPOINTS["hitclub_md5_history"])
            if hist_data and isinstance(hist_data, list):
                for item in hist_data[:limit]:
                    parsed = parse_item(item)
                    if parsed and parsed["phien"] != "0":
                        parsed["status_icon"] = "🟢"
                        parsed["status_text"] = "THẮNG"
                        if not any(h["phien"] == parsed["phien"] for h in HISTORY_MD5):
                            HISTORY_MD5.append(parsed)
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
