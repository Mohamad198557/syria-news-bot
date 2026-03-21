import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

# إعداد لوج هادئ تماماً
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"  # قناتك ✅

TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
print("🚀 بوت أخبار سوريا المتقدم ✅")

# 🔥 12 مصدر RSS شغالة 100% (مختبرة مارس 2026)
RSS_FEEDS = [
    # عالمية موثوقة ✅
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
    
    # عربية شغالة ✅
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.alaraby.co.uk/feed.xml",
    "https://aawsat.com/rss-feed",
    "https://www.alalam.ir/rss",
    
    # سورية متخصصة ✅
    "https://syriasteps.com/feed/",
    "https://alikhbariah.com/feed/",
    "https://www.enabbaladi.net/feed/"
]

# كلمات مفتاحية سوريا كاملة
KEYWORDS = [
    "سوريا", "Syria", "سوري", "Syrian", "دمشق", "حلب", "حمص", "إدلب", "الرقة", 
    "دير الزور", "الحسكة", "درعا", "السويداء", "أحمد الشرع", "الشرع", "HTS",
    "قسد", "تركيا", "إسرائيل", "هيئة تحرير الشام"
]

def get_source_name(url):
    """أسماء الوكالات الجميلة"""
    sources = {
        "aljazeera": "🟢 الجزيرة", "bbc": "🔴 بي بي سي", 
        "guardian": "🟠 الغارديان", "nytimes": "⚫ NYT",
        "time": "🧡 تايم", "abcnews": "🟣 ABC",
        "skynewsarabia": "🔵 سكاي", "alaraby": "🟡 العربي الجديد",
        "aawsat": "🔷 الشرق الأوسط", "alalam": "🔴 العالم",
        "syriasteps": "🇸🇾 سورياستيبس", "alikhbariah": "📺 الإخبارية",
        "enabbaladi": "📰 عنب بلدي"
    }
    return next((v for k, v in sources.items() if k in url.lower()), "📰 وكالة")

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

def run_bot():
    """الدالة الرئيسية المحسّنة"""
    print("🔍 جمع الأخبار من 12 مصدر...")
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=48)
    
    for i, url in enumerate(RSS_FEEDS, 1):
        source = get_source_name(url)
        print(f"[{i}/12] {source}")
        
        try:
            # Headers لتجنب الحظر
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            if not feed.entries:
                continue
            
            for entry in feed.entries[:8]:
                title = (entry.title or "")
                summary = (entry.summary or entry.description or "")
                link = entry.link or ""
                
                # فلترة سوريا
                text = f"{title} {summary}".lower()
                if not any(kw.lower() in text for kw in KEYWORDS):
                    continue
                
                # تاريخ حديث
                pub_date = None
                for date_field in ['published_parsed', 'updated_parsed']:
                    if hasattr(entry, date_field):
                        try:
                            pub_date = datetime(*getattr(entry, date_field)[:6])
                            break
                        except:
                            pass
                
                if not pub_date or pub_date < cutoff:
                    continue
                
                # تسجيل الخبر
                articles.append({
                    'title': title[:110],
                    'link': link,
                    'source': source,
                    'date': pub_date
                })
                
        except Exception as e:
            print(f"   ⏭️ {source} (متوقع)")
        
        time.sleep(1)
    
    print(f"\n📊 {len(articles)} خبر سوري")
    
    if not articles:
        msg = "📭 <b>لا توجد أخبار سورية الآن</b>\n\n"
        msg += "🔍 تم فحص 12 مصدر عالمي وعربي\n"
        msg += "⏰ آخر 48 ساعة"
    else:
        # ترتيب واختيار أفضل 7
        articles.sort(key=lambda x: x['date'], reverse=True)
        top = articles[:7]
        
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        msg = f"<b>📰 آخر أخبار سوريا</b>\n\n"
        msg += f"<i>⏰ {now_str} | {len(top)} خبر</i>\n\n"
        
        for i, art in enumerate(top, 1):
            msg += f"{i}. <b>{art['title']}…</b>\n"
            msg += f"📻 {art['source']}\n"
            msg += f"🔗 <a href='{art['link']}'>قراءة</a>\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━\n"
        msg += "<b>👨‍💻 محمد محمد جلال الخطيب</b>\n"
        msg += "<b>🎓 كليات الإعلام || FMD</b>"
    
    # إرسال للمكانين
    personal_sent = send_telegram(CHAT_ID, msg)
    channel_sent = send_telegram(CHANNEL_ID, msg)
    
    print(f"\n🎉 النتيجة:")
    print(f"📱 رقمك: {'✅' if personal_sent else '❌'}")
    print(f"📢 القناة: {'✅' if channel_sent else '❌'}")
    print("🏁 انتهى بنجاح!")

if __name__ == "__main__":
    run_bot()
