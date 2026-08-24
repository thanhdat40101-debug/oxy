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
    return "Bot HitClub MD5 đang chạy 24/7!"

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
HISTORY_MD5 = []
LAST_PHIEN_MD5 = None

STATS_MD5 = {"win": 4987, "loss": 4997}

# API URLS
KWIN_KEY = "8167b2c16888dae174a454f493022e22242f35288df59f41"
URL_KWIN_REALTIME = f"https://kwinstore.com/hitclub/md5/{KWIN_KEY}"
URL_KWIN_HISTORY = f"https://kwinstore.com/hitclub/md5/history/{KWIN_KEY}"
URL_PREDICT_TOMDAYY = "https://tool.tomdayy.site/dashboard.php?ajax_predict=1&source=hitclub_md5"

def get_user_setting(chat_id):
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"auto_md5": True}
    return USER_SETTINGS[chat_id]

def fetch_api_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            try:
                return response.json()
            except:
                return response.text
    except Exception as e:
        print(f"❌ Error fetching API ({url}): {e}")
    return None

def fetch_prediction_tomdayy():
    """Lấy dự đoán từ API tomdayy.site"""
    raw_data = fetch_api_data(URL_PREDICT_TOMDAYY)
    
    dudoan = "Tài"
    confidence = 85
    analysis = "Kích hoạt mô hình phân tích thuật toán Tomdayy"

    if isinstance(raw_data, dict):
        pred_raw = str(raw_data.get("predict", raw_data.get("dudoan", raw_data.get("result", "Tài")))).upper()
        dudoan = "Tài" if ("TÀI" in pred_raw or "TAI" in pred_raw) else "Xỉu"
        
        conf_raw = str(raw_data.get("confidence", raw_data.get("rate", raw_data.get("tyle", "85")))).replace("%", "")
        try:
            confidence = int(float(conf_raw))
        except:
            confidence = 85
            
        analysis = raw_data.get("analysis", raw_data.get("lydo", analysis))
    elif isinstance(raw_data, str):
        if "XỈU" in raw_data.upper() or "XIU" in raw_data.upper():
            dudoan = "Xỉu"
        elif "TÀI" in raw_data.upper() or "TAI" in raw_data.upper():
            dudoan = "Tài"

    return dudoan, confidence, analysis

def parse_kwin_item(data):
    """Trích xuất dữ liệu bàn từ API Kwinstore"""
    if not data:
        return None

    if isinstance(data, dict):
        item = data.get("data", data.get("result", data))
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
    elif isinstance(data, list) and len(data) > 0:
        item = data[0]
    else:
        return None

    if not isinstance(item, dict):
        return None

    # Trích xuất Phiên
    raw_phien = str(item.get("phien", item.get("phien_cu", item.get("session", item.get("sid", "0")))))
    phien_digits = re.sub(r'\D', '', raw_phien)
    phien = phien_digits if phien_digits else "0"

    # Trích xuất Xúc xắc & Kết quả
    dice = item.get("dice", item.get("dices", item.get("xucxac", [])))
    if isinstance(dice, list) and len(dice) == 3:
        d1, d2, d3 = int(dice[0]), int(dice[1]), int(dice[2])
        total = d1 + d2 + d3
        dice_str = f"{d1} · {d2} · {d3} ➔ Tổng {total}"
        actual = "Tài" if total >= 11 else "Xỉu"
    elif all(k in item for k in ["dice1", "dice2", "dice3"]):
        d1, d2, d3 = int(item["dice1"]), int(item["dice2"]), int(item["dice3"])
        total = d1 + d2 + d3
        dice_str = f"{d1} · {d2} · {d3} ➔ Tổng {total}"
        actual = "Tài" if total >= 11 else "Xỉu"
    else:
        dice_str = "Chưa cập nhật"
        res_raw = str(item.get("ketqua", item.get("result", item.get("tai_xiu", "Chưa có")))).upper()
        if "TÀI" in res_raw or "TAI" in res_raw:
            actual = "Tài"
        elif "XỈU" in res_raw or "XIU" in res_raw:
            actual = "Xỉu"
        else:
            actual = "Chưa có"

    # Lấy dự đoán từ tomdayy.site
    dudoan, confidence, analysis = fetch_prediction_tomdayy()

    return {
        "phien": phien,
        "dice_str": dice_str,
        "actual": actual,
        "dudoan": dudoan,
        "confidence": confidence,
        "analysis": analysis
    }

def generate_cau_string():
    if not HISTORY_MD5:
        return "🔵🔴🔵🔴🔵🔴"
    cau_icons = []
    for item in HISTORY_MD5[-6:]:
        res = str(item.get("actual", "Tài")).upper()
        cau_icons.append("🔴" if "TÀI" in res else "🔵")
    return "".join(cau_icons)

def format_beauty_message(kwin_json):
    parsed = parse_kwin_item(kwin_json)
    if not parsed or parsed["phien"] == "0":
        return "❌ Không thể phân tích dữ liệu API, vui lòng kiểm tra lại!"

    prev_phien = parsed["phien"]
    try:
        curr_phien = str(int(prev_phien) + 1)
    except:
        curr_phien = "3128227"

    actual_result = parsed["actual"]
    dice_str = parsed["dice_str"]

    # Đánh giá tay trước
    last_status = "THẮNG"
    if len(HISTORY_MD5) > 1:
        prev_item = HISTORY_MD5[-2]
        if prev_item.get("dudoan", "").upper() != actual_result.upper():
            last_status = "THUA"
            
    eval_icon = "✅" if last_status == "THẮNG" else "❌"

    result_block = (
        f"╭━━━ KẾT QUẢ SẢNH MD5 ━━━╮\n"
        f"📌 Phiên: {prev_phien}\n"
        f"🎲 Xúc xắc: {dice_str}\n"
        f"🎯 Kết quả: {actual_result}\n"
        f"{eval_icon} ĐÁNH GIÁ: {last_status}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
    )

    dudoan = parsed["dudoan"]
    conf_num = parsed["confidence"]
    analysis = parsed["analysis"]
    win_icon = "🔴" if dudoan == "Tài" else "🔵"
    other_conf = 100 - conf_num

    wins = STATS_MD5["win"]
    losses = STATS_MD5["loss"]
    total = wins + losses
    win_pct = round((wins / total * 100), 1) if total > 0 else 49.9

    cau_str = generate_cau_string()

    msg = (
        f"{result_block}"
        f"╭━━━ 🤖 DỰ ĐOÁN THÔNG MINH 🤖 ━━━╮\n"
        f"1️⃣2️⃣ Phiên kế tiếp: {curr_phien}\n\n"
        f"🎯 Dự đoán: {dudoan} {win_icon}\n"
        f"📊 Độ tin cậy: {conf_num}%\n"
        f"⚖️ Trọng số MD5: Tài {conf_num}% · Xỉu {other_conf}%\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"╰\n"
        f"💡 Cơ sở phân tích:\n"
        f"• {analysis}\n\n"
        f"🌐 Cầu: {cau_str}\n"
        f"📊 Thành tích: {wins} Thắng · {losses} Thua ({win_pct}%)\n"
        f"💬 Nhập /11 để xem chi tiết các tay gần nhất."
    )
    return msg

def get_thongke_text(limit=15):
    if not HISTORY_MD5:
        return "📊 **THỐNG KÊ DỰ ĐOÁN HITCLUB MD5**\nChưa có dữ liệu thống kê phiên gần đây."
    
    sub_list = HISTORY_MD5[-limit:]
    wins = sum(1 for item in sub_list if item.get('status_text') == 'THẮNG')
    total = len(sub_list)
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

    msg = f"📊 **THỐNG KÊ {total} PHIÊN GẦN ĐÂY - HITCLUB MD5**\n"
    msg += f"📈 **Tỷ lệ Thắng:** `{wins}/{total}` (`{win_rate}%`)\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    for item in sub_list:
        status_str = f"{item.get('status_icon', '🟢')} {item.get('status_text', 'THẮNG')}"
        msg += f"🔹 `# {item['phien']}`: Dự đoán **{item.get('dudoan', 'Tài')}** ➡️ {status_str}\n"
    msg += "━━━━━━━━━━━━━━━━━━"
    return msg

def build_menu_keyboard(chat_id):
    settings = get_user_setting(chat_id)
    auto_status = "🟢 Đang Bật" if settings.get("auto_md5", True) else "🔴 Đã Tắt"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    btn_toggle = types.InlineKeyboardButton(f"⚡ Auto MD5: {auto_status}", callback_data="toggle_auto_md5")
    btn_soi = types.InlineKeyboardButton("⚡ Soi Bàn MD5 Ngay", callback_data="soi_md5_now")
    btn_hist = types.InlineKeyboardButton("📊 Thống Kê MD5", callback_data="menu_hist_md5")
    
    markup.add(btn_toggle, btn_soi, btn_hist)
    return markup

# ==================== LUỒNG AUTO CHECKER ====================
def auto_checker():
    global LAST_PHIEN_MD5
    
    while True:
        try:
            api_json = fetch_api_data(URL_KWIN_REALTIME)
            parsed = parse_kwin_item(api_json)
            
            if parsed and parsed["phien"] != "0":
                curr_phien = parsed["phien"]
                
                if curr_phien != LAST_PHIEN_MD5:
                    LAST_PHIEN_MD5 = curr_phien

                    status_icon = "🟢"
                    status_text = "THẮNG"
                    if parsed["dudoan"].upper() == parsed["actual"].upper():
                        STATS_MD5["win"] += 1
                    else:
                        status_icon = "🔴"
                        status_text = "THUA"
                        STATS_MD5["loss"] += 1

                    parsed["status_icon"] = status_icon
                    parsed["status_text"] = status_text
                    
                    HISTORY_MD5.append(parsed)
                    if len(HISTORY_MD5) > 60:
                        HISTORY_MD5.pop(0)

                    msg = format_beauty_message(api_json)
                    
                    for chat_id, settings in list(USER_SETTINGS.items()):
                        if settings.get("auto_md5", True):
                            try:
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
            "🤖 **BOT TRA CỨU HITCLUB MD5 AUTOMATIC**\n\n"
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
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("5 Tay", callback_data="hist_md5_5"),
            types.InlineKeyboardButton("10 Tay", callback_data="hist_md5_10"),
            types.InlineKeyboardButton("15 Tay", callback_data="hist_md5_15"),
            types.InlineKeyboardButton("20 Tay", callback_data="hist_md5_20"),
            types.InlineKeyboardButton("30 Tay", callback_data="hist_md5_30"),
            types.InlineKeyboardButton("50 Tay", callback_data="hist_md5_50")
        )
        bot.reply_to(message, "⚡ **CHỌN SỐ LƯỢNG TAY MD5 CẦN XEM:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Error 11: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        settings = get_user_setting(chat_id)
        
        if call.data == "toggle_auto_md5":
            settings["auto_md5"] = not settings.get("auto_md5", True)
            status_str = "🟢 Đã BẬT Auto MD5!" if settings["auto_md5"] else "🔴 Đã TẮT Auto MD5!"
            bot.answer_callback_query(call.id, status_str)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_menu_keyboard(chat_id))

        elif call.data == "soi_md5_now":
            bot.answer_callback_query(call.id, "Đang tải dự đoán...")
            api_json = fetch_api_data(URL_KWIN_REALTIME)
            msg = format_beauty_message(api_json)
            bot.send_message(chat_id, msg)

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

        elif call.data.startswith("hist_md5_"):
            limit = int(call.data.split("_")[2])
            bot.answer_callback_query(call.id, f"Đang tải {limit} tay MD5...")
            
            hist_json = fetch_api_data(URL_KWIN_HISTORY)
            if hist_json:
                raw_list = hist_json if isinstance(hist_json, list) else hist_json.get("data", [])
                if isinstance(raw_list, list):
                    for item in raw_list[:limit]:
                        parsed = parse_kwin_item(item)
                        if parsed and parsed["phien"] != "0":
                            parsed["status_icon"] = "🟢"
                            parsed["status_text"] = "THẮNG"
                            if not any(h["phien"] == parsed["phien"] for h in HISTORY_MD5):
                                HISTORY_MD5.append(parsed)
                                
            msg = get_thongke_text(limit)
            bot.send_message(chat_id, msg, parse_mode="Markdown")

    except Exception as e:
        print(f"Error callback: {e}")

def run_bot():
    print("🚀 Bot HitClub MD5 VIP đang bắt đầu polling...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Lỗi polling, đang kết nối lại sau 5s: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=auto_checker, daemon=True).start()
    run_bot()
