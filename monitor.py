import os
import json
import gspread
import requests
import time
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
# Nama TikTok team kau
TARGET_USERS = ["syahmie", "rina_tiktoker", "una_tiktoker", "ehin_tiktoker"]

# NAMA SHEET KAU YANG BARU (Mesti sebijik!)
SHEET_NAME = "YouTube Live Monitoring: Malaysian Creators 2026" 

def get_gspread_client():
    # Ambil kunci dari Secrets
    info = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def check_tiktok_live(username):
    # Header untuk elak kena block dengan TikTok
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        # Mencari room_id dan status 2 (Live)
        return '"status":2' in r.text and '"room_id":' in r.text
    except:
        return False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    print("Mesej Telegram dihantar.")
    except Exception as e:
        print(f"Gagal hantar Telegram: {e}")

# --- MAIN RUN ---
try:
    print(f"Menyambung ke Google Sheet: {SHEET_NAME}...")
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    # Ambil status lama dari status.json
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    for user in TARGET_USERS:
        print(f"Checking @{user}...")
        is_live = check_tiktok_live(user)
        was_live = status_tracker.get(user, False)

        # KES 1: BARU MULA LIVE
        if is_live and not was_live:
            start_time = datetime.now().strftime("%H:%M:%S")
            date_today = datetime.now().strftime("%d/%m/%Y")
            # Append data ke sheet
            ws.append_row([user, "LIVE", start_time, "", "", date_today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user} tengah rancak di TikTok!")
            status_tracker[user] = True
            print(f"@{user} baru mula Live. Data dikemaskini.")

        # KES 2: DAH HABIS LIVE
        elif not is_live and was_live:
            end_time = datetime.now().strftime("%H:%M:%S")
            # Cari row terakhir user ni
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, end_time)
                    
                    # Kira durasi minit secara kasar
                    start_str = ws.cell(last_row, 3).value
                    t1 = datetime.strptime(start_str, "%H:%M:%S")
                    t2 = datetime.strptime(end_time, "%H:%M:%S")
                    duration = int((t2 - t1).total_seconds() / 60)
                    ws.update_cell(last_row, 5, duration)
                    
                    send_telegram(f"⚪ <b>OFFLINE:</b> @{user} dah tamat Live ({duration} min).")
                    print(f"@{user} dah tamat Live.")
            except Exception as e:
                print(f"Gagal kemaskini waktu tamat: {e}")
            
            status_tracker[user] = False

    # Simpan balik status terbaru
    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
    print("Proses selesai.")

except Exception as e:
    print(f"Error Utama: {e}")
