import os
import json
import gspread
import requests
import time
import random
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_USERS = ["kekanda__", "c.hzrina", "ct.aisyahh", "asslahierah", "keanu.riev", "capikjohari", "nurulaiinaa.a", "urpiqachu", "bukanmiraaaaaa", "memangmiraaa", "s5yer_", "harszanlagi", "najlazulaikha_", "nuarjelaaa", "ehin__", "mdsyhmie", "amriezaidi", "malkodok97", "sofiyahhhs", "azrulharry", "irfndanialb", "lokman6005", "mad_khann", "dausbatjo", "aimnjunaid._", "faeqahkahar", "unalou._"]

SHEET_NAME = "YouTube Live Monitoring: Malaysian Creators 2026"

def get_gspread_client():
    info = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def check_tiktok_live(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Cookie": "tt_webid_v2=7300000000000000000" # Tambah cookie palsu sikit
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        # Delay lebih lama (rawak 10-20 saat) supaya TikTok tak perasan
        time.sleep(random.randint(10, 20))
        r = requests.get(url, headers=headers, timeout=30)
        
        if r.status_code != 200:
            return False

        html = r.text
        
        # LOGIK BARU: 
        # Kalau LIVE, TikTok akan letak tajuk siaran dalam metadata.
        # Kita cari "isPlayerLive":true DAN pastikan bukan "Page Not Found"
        is_live = '"isPlayerLive":true' in html and 'watch live video' in html.lower()
        
        # Double check: Kalau kena redirect ke page login, itu bukan LIVE
        if "login" in r.url:
            return False
            
        return is_live
    except:
        return False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except:
        pass

# --- MAIN RUN ---
print(f"Menyambung ke Google Sheet...")
try:
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    random.shuffle(TARGET_USERS)

    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    for user in TARGET_USERS:
        print(f"Checking @{user}...")
        is_live = check_tiktok_live(user)
        was_live = status_tracker.get(user, False)

        if is_live and not was_live:
            now = datetime.now().strftime("%H:%M:%S")
            today = datetime.now().strftime("%d/%m/%Y")
            ws.append_row([user, "LIVE", now, "", "", today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user}")
            status_tracker[user] = True
            print(f"Status: @{user} is LIVE!")

        elif not is_live and was_live:
            now = datetime.now().strftime("%H:%M:%S")
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, now)
                send_telegram(f"⚪ <b>OFFLINE:</b> @{user}")
            except:
                pass
            status_tracker[user] = False

    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
    print("Selesai.")

except Exception as e:
    print(f"Error: {str(e)}")
