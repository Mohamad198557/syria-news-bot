import os
import time
import logging
import re
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]

# 🔥 10 حسابات X رسمية سورية (كاملة)
X_ACCOUNTS = [
    {"user": "Ahmadmuaffaq", "name": "أحمد معفق"},
    {"user": "AH_AlSharaa", "name": "أحمد الشرع الرئيس"},
    {"user": "syrianmofaex", "name": "خارجية سوريا"},
    {"user": "Sy_Defense", "name": "وزارة الدفاع"},
    {"user": "SyMOEADM", "name": "وزارة الإعلام"},
    {"user": "mocsyr", "name": "وزارة الثقافة"},
    {"user": "SyPresidency", "name": "الرئاسة السورية"},
    {"user": "syrianmoi", "name": "وزارة الداخلية"},
    {"user": "SyrMOfH", "name": "وزارة الصحة"},
    {"user": "SyMOIGov", "name": "الحكومة السورية"}
]

print("🚀 بوت سوريا: 10 حسابات X رسمية + RSS")

def get_latest_tweet(username):
    """آخر تغريدة من view.x.com (مجاني 100%)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = f"https://view.x.com/{username}"
        r = requests.get(url, headers=headers, timeout=15)
        
        # استخراج آخر تغريدة من HTML
        if "data-testid=\"tweetText\"" in r.text:
            # البحث عن أول تغريدة
            tweet_match = re.search(r'data-testid="tweetText"[^>]*>(.*?)<', r.text, re.DOTALL)
            if tweet_match:
                text = re.sub(r'<[^>]+>', '', tweet_match.group(1)).strip()
                if len(text) > 10:
                    return {
                        'text': text[:140] + "…" if len(text) > 140 else text,
                        'url': f"https://x.com/{username}",
                        'username': username
                    }
    except:
        pass
    return None

def get_x_tweets():
    """كل الـ 10 حسابات"""
    tweets = []
    print("🐦 فحص 10 حسابات X...")
    
    for account in X_ACCOUNTS:
        tweet = get_latest_tweet(account['user'])
        if tweet:
            tweets.append({
                'username': account['user'],
                'name': account['name'],
                'text': tweet['text'],
                'url': tweet['url']
            })
            print(f"  ✅ {account['name']}")
        else:
            print(f"  ⏭️ {account['name']}")
        time.sleep(2)  # تجنب الحظر
    
    return tweets[:10]

def get_rss_news():
    """أخبار RSS مختصرة"""
    RSS_FEEDS = [
        "https://sana.sy/?feed=rss2",
        "https://www.syria.tv/feed",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ]
    
    news = []
    for url in RSS_FEEDS:
        try:
            r = requests.get(url, timeout=10)
            feed = feedparser.parse(r.content)
            for entry in feed.entries[:1]:
                if any(kw in str(entry).lower() for kw in ["سوريا", "syria"]):
                    news.append({
                        'title': (entry.title or "")[:100],
                        'link': entry.link or ""
                    })
                    break
        except:
            pass
        time.sleep(1)
    
    return news[:2]

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def main():
    print("🔍 البدء...")
    
    # جمع البيانات
    tweets = get_x_tweets()
    rss_news = get_rss_news()
    
    # الرسالة الاحترافية
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = f"<b>🇸🇾 تحديث سوريا الرسمي</b>\n\n"
    msg += f"<i>⏰ {now_str} | 10 حسابات رسمية</i>\n\n"
    
    if tweets:
        msg += "<b>🐦 آخر النشاطات:</b>\n\n"
        for i, tweet in enumerate(tweets, 1):
            msg += f"<b>{i}.</b> {tweet['name']}\n"
            msg += f"<code>@{tweet['username']}</code>\n"
            msg += f"{tweet['text']}\n"
            msg += f"<a href='{tweet['url']}'>🔗 رابط</a>\n\n"
    else:
        msg += "<b>🐦 لا نشاطات جديدة</b>\n\n"
    
    if rss_news:
        msg += "<b>📰 أخبار إضافية:</b>\n\n"
        for i, news_item in enumerate(rss_news, 1):
            msg += f"{i}. <b>{news_item['title']}</b>\n"
            msg += f"<a href='{news_item['link']}'>قراءة الكامل</a>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>👨‍💻 محمد محمد جلال الخطيب</b>\n"
    msg += "<b>🎓 طلاب كليات الإعلام || FMD</b>"
    
    # الإرسال
    success_count = 0
    for chat_id in TARGET_CHATS:
        if send_telegram(chat_id, msg):
            success_count += 1
            print(f"📱 إرسال ناجح لـ {chat_id}")
    
    print(f"\n🎉 النتيجة: {success_count}/2 | {len(tweets)} X + {len(rss_news)} RSS")

if __name__ == "__main__":
    main()
