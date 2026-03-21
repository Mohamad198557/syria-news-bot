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

print("🚀 بوت سوريا الشامل  ")

# 🔥 الكلمات المفتاحية الرئيسية (سوريا + الرئيس + 14 محافظة)
KEYWORDS_SYRIA = [
    # سوريا عام
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    # الرئيس أحمد الشرع
    "أحمد الشرع", "Ahmed al-Sharaa", "أحمد الشّرع", "الشرع", "الرئيس السوري",
    # الـ 14 محافظة كاملة ✅
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "إدلب", "Idlib", "ادلب", "الرقة", "Raqqa",
    "دير الزور", "ديرالزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "القامشلي", "Qamishli", "السويداء", "Suwayda", "درعا", "Daraa",
    "القنيطرة", "Quneitra"
]

# 🔥 20 وكالة أنباء شاملة
RSS_FEEDS = [
    # 🇸🇾 سورية رسمية ⭐
    "https://sana.sy/?feed=rss2",                    # سانا الرسمية
    "https://www.syria.tv/feed",                     # تلفزيون سوريا
    "https://alikhbariah.com/feed/",                 # الإخبارية السورية
    "https://syriasteps.com/feed/",                  # سورياستيبس
    
    # 🌍 عالمية كبرى
    "https://www.aljazeera.com/xml/rss/all.xml",     # الجزيرة
    "http://feeds.bbci.co.uk/news/world/rss.xml",    # بي بي سي
    "https://www.theguardian.com/world/rss",         # الغارديان
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    
    # 🇹🇷 تركية موثوقة
    "https://www.aa.com.tr/ar/rss/default.aspx",     # الأناضول
    "https://trt.global/arabi/rss/",                 # TRT عربي
    
    # 🇸🇦 عربية
    "https://aawsat.com/rss-feed",                   # الشرق الأوسط
    "https://www.alaraby.co.uk/feed.xml",            # العربي الجديد
    "https://www.skynewsarabia.com/rss/world.xml",   # سكاي
    "https://www.alalam.ir/rss",                     # العالم
    "https://asharq.com/rss/feed/1/",                # الشرق
    
    # 🇪🇺 أوروبية
    "https://www.france24.com/en/rss",               # فرانس 24
    "https://www.dw.com/en/rss-top-stories",         # دويتشه فيله
    "https://www.euronews.com/rss.xml",              # يورونيوز
    
    # احتياطي
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
]

# 🔥 10 حسابات X رسمية سورية
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

def contains_syria_keyword(text):
    """فلترة شاملة"""
    return any(kw.lower() in text.lower() for kw in KEYWORDS_SYRIA)

def get_source_name(url):
    """أسماء الوكالات"""
    sources = {
        "sana.sy": "🇸🇾 سانا الرسمية",
        "syria.tv": "📺 تلفزيون سوريا", 
        "alikhbariah": "📺 الإخبارية السورية",
        "aljazeera": "🟢 الجزيرة نت",
        "bbc": "🔴 بي بي سي", 
        "guardian": "🟠 الغارديان",
        "aa.com.tr": "🇹🇷 الأناضول",
        "skynewsarabia": "🔵 سكاي عربية",
        "aawsat": "🔷 الشرق الأوسط"
    }
    return next((v for k, v in sources.items() if k in url.lower()), "📰 وكالة")

def get_rss_news():
    """20 وكالة مع فلترة سوريا"""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("📰 فحص 20 وكالة...")
    for i, url in enumerate(RSS_FEEDS, 1):
        if i % 5 == 0: print(f"   [{i}/20]")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 NewsBot/6.0'}
            r = requests.get(url, headers=headers, timeout=12)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            source = get_source_name(url)
            
            for entry in feed.entries[:3]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
                
                if contains_syria_keyword(f"{title} {summary}"):
                    pub_date = None
                    for date_field in ['published_parsed', 'updated_parsed']:
                        if hasattr(entry, date_field):
                            try:
                                pub_date = datetime(*getattr(entry, date_field)[:6])
                                break
                            except: pass
                    
                    if pub_date and pub_date > cutoff:
                        articles.append({
                            'title': title[:120],
                            'link': getattr(entry, 'link', ''),
                            'source': source,
                            'date': pub_date
                        })
                        print(f"     ✅ {source}")
                        break
        except:
            pass
        
        time.sleep(0.6)
    
    return sorted(articles, key=lambda x: x['date'], reverse=True)[:8]

def get_x_tweets():
    """10 حسابات X"""
    tweets = []
    print("🐦 فحص 10 حسابات X...")
    
    for i, account in enumerate(X_ACCOUNTS, 1):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/6.0'
            }
            url = f"https://x.com/{account['user']}"
            r = requests.get(url, headers=headers, timeout=15)
            
            if r.status_code == 200:
                tweets.append({
                    'name': account['name'],
                    'username': account['user'],
                    'url': url,
                    'status': '✅ نشط'
                })
                print(f"  {i}. {account['name']}")
        except:
            pass
        
        time.sleep(1.8)
    
    return tweets

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
    print("🎯 البوت الشامل يعمل...")
    
    rss_articles = get_rss_news()
    x_accounts = get_x_tweets()
    
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = f"<b>🇸🇾 تحديث سوريا الشامل</b>\n\n"
    msg += f"<i>⏰ {now_str} | 20 وكالة + 10 X | 14 محافظة</i>\n\n"
    
    # الحسابات الرسمية
    if x_accounts:
        msg += "<b>👥 الجهات الرسمية (10):</b>\n\n"
        for i, acc in enumerate(x_accounts[:8], 1):
            msg += f"{i}. <b>{acc['name']}</b>\n"
            msg += f"<code>@{acc['username']}</code> {acc['status']}\n"
            msg += f"<a href='{acc['url']}'>🔗 آخر نشاط</a>\n\n"
    
    # الأخبار
    if rss_articles:
        msg += "<b>📰 أهم الأخبار:</b>\n\n"
        for i, article in enumerate(rss_articles, 1):
            msg += f"{i}. <b>{article['title']}</b>\n"
            msg += f"<i>{article['source']}</i>\n"
            msg += f"<a href='{article['link']}'>🔗 الكامل</a>\n\n"
    
    if not rss_articles:
        msg += "<i>📭 لا أخبار سورية الـ 24 ساعة الأخيرة</i>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم تطويره بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    # الإرسال
    success = sum(send_telegram(chat_id, msg) for chat_id in TARGET_CHATS)
    print(f"\n🎉 نجح: {success}/2 وجهة | {len(rss_articles)} خبر + {len(x_accounts)} X")

if __name__ == "__main__":
    main()
