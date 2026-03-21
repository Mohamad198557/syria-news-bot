import os
import requests
import json

# التحقق من Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("🔍 تشخيص Telegram Secrets:")
print(f"BOT_TOKEN موجود: {'✅' if BOT_TOKEN else '❌'}")
print(f"BOT_TOKEN يبدأ بـ: {BOT_TOKEN[:20]}..." if BOT_TOKEN else "❌ فارغ")
print(f"CHAT_ID: {CHAT_ID}")
print(f"CHAT_ID رقم صحيح: {'✅' if CHAT_ID and CHAT_ID.isdigit() else '❌'}")

if not BOT_TOKEN or not CHAT_ID:
    print("💥 خطأ Secrets - تأكد من Settings → Secrets and variables → Actions")
    exit(1)

# اختبار 1: getMe (التحقق من صحة البوت)
print("\n1️⃣ اختبار البوت...")
me_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
me_resp = requests.get(me_url, timeout=10)
print(f"getMe status: {me_resp.status_code}")
print(f"البوت: {me_resp.json().get('result', {}).get('first_name', '❌ خطأ')}")

if me_resp.status_code != 200:
    print("💥 BOT_TOKEN خطأ!")
    exit(1)

# اختبار 2: getChat (التحقق من Chat ID)
print("\n2️⃣ اختبار Chat ID...")
chat_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat?chat_id={CHAT_ID}"
chat_resp = requests.get(chat_url, timeout=10)
print(f"getChat status: {chat_resp.status_code}")
if chat_resp.status_code == 200:
    chat_info = chat_resp.json().get('result', {})
    print(f"القناة/المحادثة: {chat_info.get('title', chat_info.get('first_name', 'شخص'))}")
else:
    print(f"💥 Chat ID خطأ: {chat_resp.json()}")

# اختبار 3: إرسال رسالة بسيطة
print("\n3️⃣ إرسال رسالة اختبار...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": "🧪 اختبار GitHub Actions\nالبوت شغال ✅\nSecrets صحيحة ✅",
    "parse_mode": "HTML"
}
resp = requests.post(url, data=data, timeout=15)
print(f"إرسال status: {resp.status_code}")
print(f"الرد الكامل: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")

if resp.status_code == 200:
    print("🎉 Telegram شغال 100%! جرب news_bot.py الأصلي")
else:
    print("💥 فشل الإرسال - شوف الرد أعلاه")
