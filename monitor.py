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
    # Gunakan User-Agent yang lebih moden
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        # Delay rawak antara 3 ke 8 saat
        time.sleep(random.randint(3, 8))
        r = requests.get(url, headers=headers, timeout=20)
        
        # DEBUG: Kalau kau nak tengok apa yang TikTok hantar (uncomment jika perlu)
        # print(f"Status untuk {username}: {r.status_code}") 
        
        # TikTok simpan status LIVE dalam beberapa keyword berbeza
        html_content = r.text.lower()
        is_live = '"status":2' in html_content or 'live-status' in html_content or 'isplayerlive":true' in html_content
        
        return is_live
    except Exception as e:
        print(f"Gagal akses akaun {username}: {e}")
        return False

# --- MAIN RUN (Baiki Isu Error 200) ---
try:
    print(f"Menghubung ke Sheet: {SHEET_NAME}...")
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    # Randomize urutan setiap kali run untuk elak redflag
    random.shuffle(TARGET_USERS)

    # Muat status lama
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    for user in TARGET_USERS:
        print(f"Menyemak @{user}...")
        is_live = check_tiktok_live(user)
        
        # LOGIK BARU: Bandingkan dengan status lama
        was_live = status_tracker.get(user, False)

        if is_live and not was_live:
            # Mula LIVE
            now = datetime.now().strftime("%H:%M:%S")
            date = datetime.now().strftime("%d/%m/%Y")
            ws.append_row([user, "LIVE", now, "", "", date])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user} tengah rancak di TikTok!")
            status_tracker[user] = True
            print(f">>> @{user} dikesan LIVE!")

        elif not is_live and was_live:
            # Tamat LIVE
            now = datetime.now().strftime("%H:%M:%S")
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, now)
                    # (Opsional: Tambah kiraan durasi di sini)
                send_telegram(f"⚪ <b>OFFLINE:</b> @{user} dah tamat Live.")
            except:
                pass
            status_tracker[user] = False

    # Simpan balik status
    with open("status.json", "w") as f:
        json.dump(status_tracker, f)

except Exception as e:
    print(f"Ralat pada sistem: {e}")
    
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
    
    if os.path.exists("status.json"):
        with open("status.json", "r") as f:
            status_tracker = json.load(f)
    else:
        status_tracker = {}

    # --- SHUFFLE DI SINI (SEKALI SAHAJA) ---
    random.shuffle(TARGET_USERS)
    print(f"Urutan check kali ini telah dirawakkan.")

    for user in TARGET_USERS:
        print(f"Checking @{user}...")
        is_live = check_tiktok_live(user)
        was_live = status_tracker.get(user, False)

        if is_live and not was_live:
            start_time = datetime.now().strftime("%H:%M:%S")
            date_today = datetime.now().strftime("%d/%m/%Y")
            ws.append_row([user, "LIVE", start_time, "", "", date_today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user} tengah rancak di TikTok!")
            status_tracker[user] = True
            print(f"@{user} baru mula Live.")

        elif not is_live and was_live:
            end_time = datetime.now().strftime("%H:%M:%S")
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, end_time)
                    
                    # Ambil start_time untuk kira durasi
                    start_str = ws.cell(last_row, 3).value
                    if start_str:
                        t1 = datetime.strptime(start_str, "%H:%M:%S")
                        t2 = datetime.strptime(end_time, "%H:%M:%S")
                        duration = int((t2 - t1).total_seconds() / 60)
                        ws.update_cell(last_row, 5, duration)
                        send_telegram(f"⚪ <b>OFFLINE:</b> @{user} dah tamat Live ({duration} min).")
            except Exception as e:
                print(f"Gagal kemaskini waktu tamat: {e}")
            
            status_tracker[user] = False

    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
    print("Proses selesai.")

except Exception as e:
    print(f"Error Utama: {e}")
