import os
import json
import gspread
import requests
import time
import random
from datetime import datetime
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor

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

def check_tiktok_live(session, username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code != 200 or "login" in r.url:
            return username, False
        html = r.text
        is_live = '"isPlayerLive":true' in html and 'watch live video' in html.lower()
        return username, is_live
    except:
        return username, False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except:
        pass

def write_github_log(sh, status, remark=""):
    try:
        log_ws = sh.worksheet("GITHUB_LOGS")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Append log baru
        log_ws.append_row([now, status, remark])
        
        # --- AUTO DELETE (Limit 500 Rows) ---
        # Kita simpan header (1) + 499 data
        all_rows = log_ws.get_all_values()
        if len(all_rows) > 500:
            # Padam baris ke-2 (data paling lama)
            log_ws.delete_rows(2)
    except Exception as e:
        print(f"Gagal tulis log: {e}")

# --- MAIN RUN ---
print(f"Menyambung ke Google Sheet...")
start_time = time.time()
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

    print(f"Memulakan semakan pantas untuk {len(TARGET_USERS)} akaun...")
    
    results = []
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda u: check_tiktok_live(session, u), TARGET_USERS))

    updates_count = 0
    for user, is_live in results:
        was_live = status_tracker.get(user, False)
        if is_live and not was_live:
            now_time = datetime.now().strftime("%H:%M:%S")
            today = datetime.now().strftime("%d/%m/%Y")
            ws.append_row([user, "LIVE", now_time, "", "", today])
            send_telegram(f"🔴 <b>LIVE SEKARANG!</b>\n👤 @{user}")
            status_tracker[user] = True
            updates_count += 1
        elif not is_live and was_live:
            now_time = datetime.now().strftime("%H:%M:%S")
            try:
                cells = ws.findall(user)
                if cells:
                    last_row = cells[-1].row
                    ws.update_cell(last_row, 2, "OFFLINE")
                    ws.update_cell(last_row, 4, now_time)
                send_telegram(f"⚪ <b>OFFLINE:</b> @{user}")
            except: pass
            status_tracker[user] = False
            updates_count += 1

    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
    
    duration = round(time.time() - start_time, 2)
    write_github_log(sh, "SUCCESS", f"Check {len(TARGET_USERS)} users in {duration}s. Updates: {updates_count}")
    print("Selesai.")

except Exception as e:
    # Log error kalau skrip crash
    try:
        gc = get_gspread_client()
        sh = gc.open(SHEET_NAME)
        write_github_log(sh, "ERROR", str(e))
    except: pass
    print(f"Error: {str(e)}")
