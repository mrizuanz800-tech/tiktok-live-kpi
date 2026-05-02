import os
import json
import gspread
import requests
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
# Masukkan nama TikTok team kau (tanpa @)
TARGET_USERS = ["syahmie", "rina_tiktoker", "una_tiktoker", "ehin_tiktoker"]
# Masukkan NAMA EXACT Google Sheet kau (yang kau dah share dengan service account)
SHEET_NAME = "KPI_TEAM_AITEAM" 

def get_gspread_client():
    info = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def check_tiktok_live(username):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        # Check status 2 bermaksud sedang LIVE
        return '"status":2' in r.text and '"room_id":' in r.text
    except:
        return False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})

# --- MAIN RUN ---
try:
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    # Pastikan kau ada tab bernama 'LIVE_TRACKER' kat Google Sheet tu
    ws = sh.worksheet("LIVE_TRACKER")
    
    # Ambil status lama dari status.json (ingatan robot)
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    for user in TARGET_USERS:
        is_live = check_tiktok_live(user)
        was_live = status_tracker.get(user, False)

        # KES 1: BARU MULA LIVE
        if is_live and not was_live:
            start_time = datetime.now().strftime("%H:%M:%S")
            date_today = datetime.now().strftime("%d/%m/%Y")
            # Simpan rekod baru kat Google Sheets
            ws.append_row([user, "LIVE", start_time, "", "", date_today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user} tengah rancak di TikTok!")
            status_tracker[user] = True

        # KES 2: DAH HABIS LIVE
        elif not is_live and was_live:
            end_time = datetime.now().strftime("%H:%M:%S")
            # Cari row terakhir user ni kat sheet untuk update end time
            cells = ws.findall(user)
            if cells:
                last_row = cells[-1].row
                ws.update_cell(last_row, 2, "OFFLINE")
                ws.update_cell(last_row, 4, end_time)
                # Kira durasi kasar (optional kalau kau nak buat formula kat Sheets terus pun boleh)
            
            send_telegram(f"⚪ <b>OFFLINE:</b> @{user} dah tamat Live.")
            status_tracker[user] = False

    # Simpan balik status terbaru ke status.json
    with open("status.json", "w") as f:
        json.dump(status_tracker, f)

except Exception as e:
    print(f"Error: {e}")
