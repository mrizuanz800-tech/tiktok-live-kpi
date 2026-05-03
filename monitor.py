import os
import json
import gspread
import requests
import time
import random
from datetime import datetime, timedelta 
from google.oauth2.service_account import Credentials

# --- CONFIG ---
TARGET_USERS = ["smart_elek", "kekanda__", "c.hzrina", "ct.aisyahh", "asslahierah", "keanu.riev", "capikjohari", "nurulaiinaa.a", "urpiqachu", "bukanmiraaaaaa", "memangmiraaa", "s5yer_", "harszanlagi", "najlazulaikha_", "nuarjelaaa", "ehin__", "mdsyhmie", "amriezaidi", "malkodok97", "sofiyahhhs", "azrulharry", "irfndanialb", "lokman6005", "mad_khann", "dausbatjo", "aimnjunaid._", "faeqahkahar", "unalou._"]

SHEET_NAME = "YouTube Live Monitoring: Malaysian Creators 2026"

def get_gspread_client():
    info = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
    creds = Credentials.from_service_account_info(
        info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

def check_tiktok_live(session, username):
    # Kita guna User-Agent mobile supaya TikTok bagi paparan yang lebih 'direct'
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    url = f"https://www.tiktok.com/@{username}/live"
    try:
        r = session.get(url, headers=headers, timeout=15)
        
        # Kalau kena block atau suruh login, kita skip
        if r.status_code != 200 or "login" in r.url: 
            return username, False
        
        html = r.text
        
        # --- LOGIK BARU: CARI TANDA HIDUP ---
        
        # 1. Tanda utama: roomId mesti ada dan bukan 0
        # Format TikTok biasanya: "roomId":"73645251..."
        has_room_id = '"roomId":"' in html and '"roomId":"0"' not in html
        
        # 2. Tanda kedua: Cari keyword 'broadcast' atau 'isPlayerLive'
        is_live_status = '"isPlayerLive":true' in html or '"status":2' in html
        
        # 3. Double check: Pastikan bukan 'LIVE has ended'
        not_ended = 'LIVE has ended' not in html and 'LIVE ended' not in html

        # KEPUTUSAN: Kalau ada room_id DAN tak tulis 'ended', kita sahkan LIVE
        if has_room_id and not_ended:
            return username, True
            
        # Backup plan: Kalau room_id tak jumpa tapi isPlayerLive ada
        if is_live_status and not_ended:
            return username, True

        return username, False
    except: 
        return username, False

def send_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    try:
        # Tambah disable_web_page_preview=False kalau nak biar ada gambar preview TikTok
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={
                          "chat_id": chat_id, 
                          "text": message, 
                          "parse_mode": "HTML",
                          "disable_web_page_preview": False
                      })
    except: pass

def write_github_log(sh, status, remark=""):
    try:
        ws_list = [w.title for w in sh.worksheets()]
        if "GITHUB_LOGS" in ws_list:
            log_ws = sh.worksheet("GITHUB_LOGS")
            now = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            log_ws.append_row([now, status, remark])
            
            rows = log_ws.get_all_values()
            if len(rows) > 500:
                log_ws.delete_rows(2, len(rows) - 499)
    except Exception as e:
        print(f"Gagal tulis log: {str(e)}")

# --- MAIN RUN ---
print(f"Memulakan Strategi Halimun...")
start_time = time.time()

try:
    # 1. RANDOM START DELAY (1 - 60 saat)
    delay_awal = random.randint(1, 60)
    print(f"Menunggu secara rawak selama {delay_awal}s sebelum bermula...")
    time.sleep(delay_awal)

    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    ws = sh.worksheet("LIVE_TRACKER")
    
    # 2. SHUFFLE TARGET USERS
    random.shuffle(TARGET_USERS)
    status_tracker = json.load(open("status.json", "r")) if os.path.exists("status.json") else {}

    print(f"Menyemak {len(TARGET_USERS)} pengguna...")
    
    results = []
    with requests.Session() as session:
        for user in TARGET_USERS:
            print(f"Menyemak: {user}")
            res = check_tiktok_live(session, user)
            results.append(res)
            
            # 3. DELAY RAWAK ANTARA USER (1.0 - 3.5 saat)
            # Meniru kelajuan skrol manusia
            time.sleep(random.uniform(1.0, 3.5))

    updates = 0
    now_malaysia = datetime.utcnow() + timedelta(hours=8)
    now_t = now_malaysia.strftime("%H:%M:%S")
    today = now_malaysia.strftime("%d/%m/%Y")

    for user, is_live in results:
        was_live = status_tracker.get(user, False)
        
        if is_live and not was_live:
            # 1. Update Sheet
            ws.append_row([user, "LIVE", now_t, "", "", today])
            
            # 2. Hantar Telegram dengan Hyperlink Padu
            link_live = f"https://www.tiktok.com/@{user}/live"
            mesej_live = (
                f"🔴 <b>LIVE SEKARANG!</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>@{user}</b> tengah rancak di TikTok!\n\n"
                f"🔗 <a href='{link_live}'>KLIK SINI UNTUK TONTON</a>"
            )
            send_telegram(mesej_live)
            
            status_tracker[user], updates = True, updates + 1
            
        elif not is_live and was_live:
            # 1. Cari entri terakhir & Update Sheet jadi OFFLINE
            cells = ws.findall(user)
            if cells:
                r = cells[-1].row
                ws.update_cell(r, 2, "OFFLINE")
                ws.update_cell(r, 4, now_t)
            
            # 2. Hantar Noti Offline dengan Link Profil (Just in case nak check)
            link_profile = f"https://www.tiktok.com/@{user}"
            mesej_offline = (
                f"⚪ <b>SUDAH OFFLINE</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>@{user}</b> telah tamat sesi LIVE.\n\n"
                f"🔗 <a href='{link_profile}'>LIHAT PROFIL</a>"
            )
            send_telegram(mesej_offline)
            
            status_tracker[user], updates = False, updates + 1

    # --- SIMPAN STATUS & LOG ---
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
