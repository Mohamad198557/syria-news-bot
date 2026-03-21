import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]

print("🚀 بوت أخبار سوريا - 20 وكالة + 14 محافظة")

# 🔥 الكلمات المفتاحية الرئيسية (سوريا + الرئيس + 14 محافظة)
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    "أحمد الشرع", "Ahmed al-Sharaa", "الشرع", "الرئيس السوري",
    # الـ 14 محافظة كاملة
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "السويداء", "Suwayda", "درعا", "Daraa", "القنيطرة", "Quneitra"
]

# 🔥 20 وكالة أنباء شاملة
RSS_FEEDS = [
    # 🇸🇾 سورية رسمية
    "https://sana.sy/?feed=rss2",                    # سانا الرسمية ⭐
    "https://www.syria.tv/feed",                     # تلفزيون سوريا ⭐
    "https://alikhbariah.com/feed/",                 # الإخبارية السورية ⭐
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
    
    # احتياطي موثوق
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines"
]

def contains_syria_keyword(text):
    """فلترة سوريا + 14 محافظة + الرئيس"""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS_SYRIA)

def get_source_name(url):
    """أسماء الوكالات الجميلة"""
    sources = {
        "sana.sy": "🇸🇾 سانا الرسمية",
        "syria.tv": "📺 تلفزيون سوريا",
        "alikhbariah": "📺 الإخبارية السورية",
        "syriasteps": "🇸🇾 سورياستيبس",
        "aljazeera": "🟢 الجزيرة نت",
        "bbc": "🔴 بي بي سي",
        "guardian": "🟠 الغارديان",
        "aa.com.tr": "🇹🇷 الأناضول",
        "skynewsarabia": "🔵 سكاي عربية",
        "aawsat": "🔷 الشرق الأوسط",
        "france24": "🇫🇷 فرانس 24",
        "dw.com": "🇩🇪 دويتشه فيله"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة")

def get_rss_news():
    """20 وكالة مع فلترة ذكية"""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("📰 فحص 20 وكالة أنباء...")
    for i, url in enumerate(RSS_FEEDS, 1):
        if i % 4 == 0:
            print(f"   التقدم: {i}/20")
        
        source_name = get_source_name(url)
        print(f"[{i:2d}] {source_name}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/9.0'}
            r = requests.get(url, headers=headers, timeout=12)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            
            for entry in feed.entries[:4]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
                
                full_text = f"{title} {summary}"
                
                # فلترة سوريا + محافظات + الرئيس
                if contains_syria_keyword(full_text):
                    pub_date = None
                    for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                        if hasattr(entry, date_field):
                            try:
                                pub_date = datetime(*getattr(entry, date_field)[:6])
                                break
                            except:
                                pass
                    
                    if pub_date and pub_date > cutoff:
                        articles.append({
                            'title': title[:125],
                            'link': getattr(entry, 'link', ''),
                            'source': source_name,
                            'date': pub_date
                        })
                        print(f"    ✅ خبر سوري ✓")
                        break
                        
        except Exception as e:
            print(f"    ⏭️ خطأ")
        
        time.sleep(0.7)  # هدوء السيرفرات
    
    return sorted(articles, key=lambda x: x['date'], reverse=True)

def send_telegram(chat_id, message):
    """إرسال آمن"""
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
    print("🎯 بوت أخبار سوريا يعمل...")
    
    # جمع الأخبار
    articles = get_rss_news()
    
    # الرسالة الاحترافية
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = f"<b>🇸🇾 أهم أخبار سوريا</b>\n\n"
    msg += f"<i>⏰ {now_str} | 20 وكالة أنباء</i>\n"
    msg += f"<i>📍 تغطية 14 محافظة + أحمد الشرع</i>\n\n"
    
    if articles:
        msg += "<b>📰 آخر الأخبار:</b>\n\n"
        for i, article in enumerate(articles[:8], 1):
            msg += f"{i}. <b>{article['title']}</b>\n"
            msg += f"{article['source']}\n"
            msg += f"<a href=\"{article['link']}\">🔗 الكامل</a>\n\n"
    else:
        msg += "<b>📭 لا أخبار سورية الـ 24 ساعة الأخيرة</b>\n\n"
        msg += "🔍 تم فحص 20 وكالة أنباء عالمية وعربية\n"
        msg += "🇸🇾 سانا + تلفزيون سوريا + الإخبارية"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم تطويره بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    # الإرسال
    success_count = 0
    for chat_id in TARGET_CHATS:
        if send_telegram(chat_id, msg):
            success_count += 1
            print(f"📱 نجح: {chat_id}")
    
    print(f"\n🎉 النتيجة: {success_count}/2 وجهة | {len(articles)} خبر")

if __name__ == "__main__":
    main()
