import os
import time
import logging
import re
from datetime import datetime, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup
import json
import hashlib

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
SEEN_NEWS_FILE = "seen_news.json"

print("🚀 بوت أخبار سوريا - كل 30 دقيقة بدون تكرار")

KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "السوريين", "أحمد الشرع", 
    "الشرع", "الرئيس السوري", "دمشق", "حلب", "حمص"
]

RSS_FEEDS = [
    "https://sana.sy/?feed=rss2",
    "https://www.syria.tv/feed",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.aa.com.tr/ar/rss/default.aspx"
]

def load_seen_news():
    try:
        if os.path.exists(SEEN_NEWS_FILE):
            with open(SEEN_NEWS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_seen_news(seen_hashes):
    try:
        with open(SEEN_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen_hashes), f, ensure_ascii=False)
    except:
        pass

def get_news_hash(title, link):
    content = f"{title}{link}"
    return hashlib.md5(content.encode()).hexdigest()

def get_gold_dollar_prices():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 NewsBot/1.0'}
        response = requests.get("https://sp-today.com/en", 
                              headers=headers, timeout=10)
        text = BeautifulSoup(response.text, 'html.parser').get_text()
        
        gold = re.search(r'1[,d]{6,9}', text)
        dollar = re.search(r'1[1-2],[0-9]{3}', text)
        
        return (gold.group() if gold else "1,484,000",
                dollar.group() if dollar else "11,950")
    except:
        return "1,484,000", "11,950"

def contains_syria_keyword(text):
    if not text: return False
    text = text.lower()
    return any(kw.lower() in text for kw in KEYWORDS_SYRIA)

def get_source_name(url):
    sources = {
        "sana.sy": "🇸🇾 سانا",
        "syria.tv": "📺 سوريا تي في",
        "aljazeera": "🟢 الجزيرة",
        "aa.com.tr": "🇹🇷 Anadolu"
    }
    return next((name for key, name in sources.items() 
                if key in url.lower()), "📰 وكالة")

def get_new_articles(seen_hashes):
    articles = []
    
    for i, url in enumerate(RSS_FEEDS, 1):
        print(f"[{i}] {get_source_name(url)}")
        try:
            response = requests.get(url, timeout=10)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:2]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                if contains_syria_keyword(title):
                    news_hash = get_news_hash(title, link)
                    
                    if news_hash not in seen_hashes:
                        articles.append({
                            'title': title[:100],
                            'link': link,
                            'source': get_source_name(url)
                        })
                        seen_hashes.add(news_hash)
                        print("   ✅ خبر جديد")
                        break
        except:
            pass
        time.sleep(1)
    
    return articles

def send_telegram(chat_id, message):
    if not BOT_TOKEN or not chat_id: return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except:
        return False

def run_cycle():
    print(f"
⏰ {datetime.now().strftime('%H:%M:%S')} - دورة جديدة")
    
    seen_hashes = load_seen_news()
    gold, dollar = get_gold_dollar_prices()
    articles = get_new_articles(seen_hashes)
    
    if articles:
        now_str = datetime.utcnow().strftime("%H:%M UTC")
        message = f"<b>🇸🇾 أخبار جديدة</b>

"
        message += f"<b>💰</b> ذهب: {gold} | دولار: {dollar}

"
        message += "<b>📰 الأخبار:</b>
"
        
        for i, article in enumerate(articles[:5], 1):
            message += f"{i}. <b>{article['title']}</b>
"
            message += f"{article['source']} | "
            message += f"<a href='{article['link']}'>رابط</a>

"
        
        message += f"<i>{now_str}</i>"
        
        sent = 0
        for chat_id in TARGET_CHATS:
            if chat_id and send_telegram(chat_id, message):
                sent += 1
        
        print(f"✅ أُرسل {len(articles)} خبر لـ {sent} قناة")
        save_seen_news(seen_hashes)
    else:
        print("ℹ️ لا توجد أخبار جديدة")

def main():
    print("🔄 يعمل كل 30 دقيقة... Ctrl+C للإيقاف")
    try:
        while True:
            run_cycle()
            print("💤 انتظار 30 دقيقة...")
            time.sleep(1800)  # 30 دقيقة
    except KeyboardInterrupt:
        print("
⏹️ توقف")

if __name__ == "__main__":
    main()
