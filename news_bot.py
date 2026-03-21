import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

print(f"🧪 اختبار القناة: {CHANNEL_ID}")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHANNEL_ID,
    "text": "✅ اختبار نجح! البوت Admin كامل\nالآن رجّع الكود الأصلي",
    "parse_mode": "HTML"
}

r = requests.post(url, data=data)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
