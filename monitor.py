import os
import requests
import json
import sys

# Ambil data daripada arguments yang dihantar oleh GAS
def main():
    if len(sys.argv) < 2:
        print("Tiada data diterima.")
        return

    # Data dihantar dalam bentuk JSON string: '{"username": "xxx", "is_live": true}'
    try:
        task_data = json.loads(sys.argv[1])
        username = task_data['username']
        is_live = task_data['is_live']
    except:
        print("Gagal proses data.")
        return

    # Load status semasa
    with open('status.json', 'r') as f:
        status_data = json.load(f)

    old_status = status_data.get(username, False)

    if is_live and not old_status:
        # HANTAR NOTIFIKASI TELEGRAM
        TOKEN = os.environ.get('TELEGRAM_TOKEN')
        CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
        msg = f"🔴 **LIVE SEKARANG!**\n━━━━━━━━━━━━━━━\n👤 **@{username}** tengah live!\n\n🔗 https://www.tiktok.com/@{username}/live"
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url)
        
        status_data[username] = True
        print(f"NOTI: {username} sedang LIVE!")
    
    elif not is_live:
        status_data[username] = False
        print(f"{username} OFFLINE.")

    # Simpan status baru
    with open('status.json', 'w') as f:
        json.dump(status_data, f)

if __name__ == "__main__":
    main()
