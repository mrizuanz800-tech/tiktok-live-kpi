import os
import json
import gspread
import requests
import time
import random
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_USERS = ["hanzonurrz", "kekanda__", "c.hzrina", "ct.aisyahh", "asslahierah", "keanu.riev", "capikjohari", "nurulaiinaa.a", "urpiqachu", "bukanmiraaaaaa", "memangmiraaa", "s5yer_", "harszanlagi", "najlazulaikha_", "nuarjelaaa", "ehin__", "mdsyhmie", "amriezaidi", "malkodok97", "sofiyahhhs", "azrulharry", "irfndanialb", "lokman6005", "mad_khann", "dausbatjo", "aimnjunaid._", "faeqahkahar", "unalou._"]

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
        "Accept-Language": "en-US,en;q=0.9",
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        # Rehat sekejap antara 4-8 saat (elak bot detection)
        time.sleep(random.randint(4, 8))
        r = requests.get(url, headers=headers, timeout=20)
        
        # Kalau TikTok sekat (403 atau 429), kita akan tahu
        if r.status_code != 200:
            print(f"Akses dihalang untuk {username} (Status: {r.status_code})")
            return False

        html = r.text
        # TikTok simpan status LIVE dalam beberapa jenis keyword
        # Kita check semua sekali untuk lebih selamat
        is_live = (
            '"status":2' in html or 
            'live-status' in html.lower() or 
            '"liveRoom":' in html or 
            'isPlayerLive":true' in html
        )
        return is_live
    except Exception as e:
        print(f"Error pada {username}: {e}")
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
    print(f"Menyambung ke Sheet: {SHEET_NAME}...")
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    # Shuffle list supaya check urutan berbeza setiap kali
    random.shuffle(TARGET_USERS)

    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    for user in TARGET_USERS:
        print(f"Semak @{user}...")
        is_live = check_tiktok_live(user)
        was_live = status_tracker.get(user, False)

        if is_live and not was_live:
            # Rekod mula LIVE
            start_time = datetime.now().strftime("%H:%M:%S")
            date_today = datetime.now().strftime("%d/%m/%Y")
            ws.append_row([user, "LIVE", start_time, "", "", date_today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user} tengah rancak di TikTok!")
            status_tracker[user] = True
            print(f"Confirmed: @{user} tengah LIVE.")

        elif not is_live and was_live:
            # Rekod tamat LIVE
            end_time = datetime.now().strftime("%H:%M:%S")
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, end_time)
                    # (Kiraan durasi boleh ditambah di sini nanti)
                send_telegram(f"⚪ <b>OFFLINE:</b> @{user} dah tamat Live.")
            except:
                pass
            status_tracker[user] = False

    # Simpan status ke fail JSON
    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
    print("Semua akaun telah disemak.")

except Exception as e:
    # Ini akan print ralat yang sebenar, bukan sekadar 'Response 200'
    import traceback
    print(f"Ralat Utama: {e}")
    traceback.print_exc()
