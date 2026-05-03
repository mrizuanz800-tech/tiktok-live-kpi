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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code != 200 or "login" in r.url: return username, False
        is_live = '"isPlayerLive":true' in r.text and 'watch live video' in r.text.lower()
        return username, is_live
    except: return username, False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except: pass

def write_github_log(sh, status, remark=""):
    try:
        ws_list = [w.title for w in sh.worksheets()]
        if "GITHUB_LOGS" in ws_list:
            log_ws = sh.worksheet("GITHUB_LOGS")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_ws.append_row([now, status, remark])
            
            # Auto cleanup > 500 rows
            rows = log_ws.get_all_values()
            if len(rows) > 500:
                log_ws.delete_rows(2, len(rows) - 499)
    except Exception as e:
        print(f"Gagal tulis log: {str(e)}")

# --- MAIN RUN ---
print(f"Menyambung ke Google Sheet...")
start_time = time.time()
try:
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    random.shuffle(TARGET_USERS)
    status_tracker = json.load(open("status.json", "r")) if os.path.exists("status.json") else {}

    print(f"Checking {len(TARGET_USERS)} users...")
    with requests.Session() as session:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda u: check_tiktok_live(session, u), TARGET_USERS))

    updates = 0
    for user, is_live in results:
        was_live = status_tracker.get(user, False)
        now_t = datetime.now().strftime("%H:%M:%S")
        today = datetime.now().strftime("%d/%m/%Y")
        
        if is_live and not was_live:
            ws.append_row([user, "LIVE", now_t, "", "", today])
            send_telegram(f"🔴 <b>LIVE:</b> @{user}")
            status_tracker[user], updates = True, updates + 1
        elif not is_live and was_live:
            # Cari entri terakhir untuk user ini secara efisien
            cells = ws.findall(user)
            if cells:
                r = cells[-1].row
                ws.update_cell(r, 2, "OFFLINE")
                ws.update_cell(r, 4, now_t)
            send_telegram(f"⚪ <b>OFFLINE:</b> @{user}")
            status_tracker[user], updates = False, updates + 1

    # Simpan status terbaru
    with open("status.json", "w") as f:
        json.dump(status_tracker, f)
        
    duration = round(time.time() - start_time, 2)
    write_github_log(sh, "SUCCESS", f"Duration: {duration}s | Updates: {updates}")
    print(f"Selesai dalam {duration}s.")

except Exception as e:
    print(f"Error: {str(e)}")
    try:
        sh_err = gc.open(SHEET_NAME)
        write_github_log(sh_err, "ERROR", str(e))
    except: pass
