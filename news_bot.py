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

# إعدادات الـ logging
logging.basicConfig(level=logging.WARNING)

# متغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]

# ملف حفظ الأخبار السابقة
SEEN_NEWS_FILE = "seen_news.json"

print("🚀 بوت أخبار سوريا - يعمل كل 30 دقيقة بدون تكرار!")
print("🔄 اضغط Ctrl+C للإيقاف")

# الكلمات المفتاحية السورية
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    "أحمد الشرع", "Ahmed al-Sharaa", "الشرع", "الرئيس السوري",
    "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس",
    "إدلب", "الرقة", "دير الزور", "الحسكة", "السويداء", "درعا"
]

# 25 وكالة أنباء
RSS_FEEDS = [
    "https://sana.sy/?feed=rss2", "https://www.syria.tv/feed",
    "https://alikhbariah.com/feed/", "https://syriasteps.com/feed/",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://trt.global/arabi/rss/",
    "https://aawsat.com/rss-feed",
    "https://www.alaraby.co.uk/feed.xml",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.alalam.ir/rss",
    "https://asharq.com/rss/feed/1/",
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories",
    "https://www.wam.ae/ar/rss",
    "https://www.bna.bh/rss/?lang=ar",
    "https://www.petra.gov.jo/rss/JoSiteAr.aspx",
    "https://www.aps.dz/rss",
    "https://www.saba.ye/rss/feed.xml",
    "https://www.spa.gov.sa/rss"
]

def load_seen_news():
    """تحميل الأخبار المشاهدة سابقاً"""
    try:
        if os.path.exists(SEEN_NEWS_FILE):
            with open(SEEN_NEWS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_seen_news(seen_hashes):
    """حفظ الأخبار المشاهدة"""
    try:
        with open(SEEN_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen_hashes), f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def get_news_hash(title, link):
    """إنشاء hash فريد للخبر"""
    content = f"{title.lower().strip()}{link}"
    return hashlib.md5(content.encode()).hexdigest()

def get_gold_dollar_prices():
    """استخراج أسعار الذهب والدولار"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/1.0'}
        url = "https://sp-today.com/en"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        gold_pattern = r'1[,d]{6,9}'
        dollar_pattern = r'1[1-2],[0-9]{3}'
        
        gold_price = "1,484,000"
        dollar_price = "11,950"
        
        gold_matches = re.findall(gold_pattern, text)
        dollar_matches = re.findall(dollar_pattern, text)
        
        if gold_matches:
            gold_price = gold_matches[0]
        if dollar_matches:
            dollar_price = dollar_matches[0]
            
        print(f"💰 الأسعار: ذهب {gold_price} | دولار {dollar_price}")
        return gold_price, dollar_price
    except:
        print("⚠️ أسعار افتراضية")
        return "1,484,000", "11,950"

def contains_syria_keyword(text):
    """التحقق من كلمات سوريا"""
    if not text:
        return False
    return any(kw.lower() in text.lower() for kw in KEYWORDS_SYRIA)

def get_source_name(url):
    """اسم الوكالة"""
    sources = {
        "sana": "🇸🇾 سانا", "syria.tv": "📺 سوريا تي في",
        "alikhbariah": "📺 الإخبارية", "syriasteps": "🇸🇾 خطوات",
        "aljazeera": "🟢 الجزيرة", "bbc": "🔴 بي بي سي",
        "guardian": "🟠 الغارديان", "aa.com.tr": "🇹🇷 الأناضول",
        "skynewsarabia": "🔵 سكاي", "aawsat": "🔷 الشرق الأوسط",
        "wam.ae": "🟢 وام", "spa.gov.sa": "⚫ واس"
    }
    url_lower = url.lower()
    for key, name in sources.items():
        if key in url_lower:
            return name
    return "📰 وكالة"

def get_new_rss_news(seen_hashes):
    """جمع الأخبار الجديدة فقط"""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("📰 فحص الوكالات...")
    
    for i, url in enumerate(RSS_FEEDS[:15], 1):  # 15 وكالة فقط للسرعة
        if i % 5 == 0:
            print(f"   التقدم: {i}/15")
            
        source_name = get_source_name(url)
        print(f"[{i}] {source_name}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 NewsBot/2.0'}
            response = requests.get(url, headers=headers, timeout=12)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                continue
                
            for entry in feed.entries[:2]:
                title = getattr(entry, 'title', '') or ''
                link = getattr(entry, 'link', '')
                
                if not contains_syria_keyword(title):
                    continue
                    
                news_hash = get_news_hash(title, link)
                
                if news_hash in seen_hashes:
                    continue
                    
                pub_date = None
                for date_field in ['published_parsed', 'updated_parsed']:
                    if hasattr(entry, date_field) and getattr(entry, date_field):
                        try:
                            pub_date = datetime(*getattr(entry, date_field)[:6])
                            break
                        except:
                            pass
                
                if pub_date is None or pub_date > cutoff:
                    articles.append({
                        'title': title[:110] + "..." if len(title) > 110 else title,
                        'link': link,
                        'source': source_name
                    })
                    seen_hashes.add(news_hash)
                    print(f"    ✅ خبر جديد!")
                    break
                    
        except:
            pass
            
        time.sleep(0.8)
    
    return articles

def send_telegram(chat_id, message):
    """إرسال لتيليجرام"""
    if not BOT_TOKEN or not chat_id:
        return False
        
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true"
        }
        response = requests.post(url, data=data, timeout=15)
        return response.status_code == 200
    except:
        return False

def run_once():
    """دورة واحدة"""
    print(f"
⏰ [{datetime.now().strftime('%H:%M:%S')}] دورة جديدة")
    
    seen_hashes = load_seen_news()
    print(f"📊 أخبار سابقة: {len(seen_hashes):,}")
    
    gold_price, dollar_price = get_gold_dollar_prices()
    new_articles = get_new_rss_news(seen_hashes)
    
    if new_articles:
        now_str = datetime.utcnow().strftime("%H:%M UTC")
        
        # بناء الرسالة خطوة بخطوة (بدون مشاكل syntax)
        message = "<b>🇸🇾 أخبار سوريا الجديدة</b>

"
        message += "<b>💰 السوق:</b>
"
        message += f"🪙 ذهب 21: {gold_price}
"
        message += f"💵 دولار: {dollar_price}

"
        message += "<b>📰 الأخبار الجديدة:</b>
"
        message += "═" * 25 + "
"
        
        for i, article in enumerate(new_articles[:6], 1):
            message += f"{i}. <b>{article['title']}</b>
"
            message += f"   {article['source']}
"
            message += f"   <a href="{article['link']}">🔗 الكامل</a>

"
        
        message += "═" * 25 + "
"
        message += f"<i>⏰ {now_str} | {len(new_articles)} خبر جديد</i>"
        
        # الإرسال
        success_count = 0
        for chat_id in TARGET_CHATS:
            if chat_id and send_telegram(chat_id, message):
                success_count += 1
                print(f"📱 نجح: {chat_id}")
        
        print(f"✅ أُرسل {len(new_articles)} خبر إلى {success_count} قناة")
        save_seen_news(seen_hashes)
    else:
        print("ℹ️ لا أخبار جديدة")

def main():
    """الحلقة الرئيسية"""
    print("🔄 بدء العمل كل 30 دقيقة...")
    print("=" * 50)
    
    try:
        while True:
            run_once()
            print("
💤 انتظار 30 دقيقة...")
            time.sleep(1800)  # 30 دقيقة
    except KeyboardInterrupt:
        print("
⏹️ توقف")

if __name__ == "__main__":
    main()
