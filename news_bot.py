import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"

TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
print("🚀 بوت أخبار سوريا - 20 وكالة + سانا + تلفزيون سوريا ✅")

# 🔥 20 وكالة موثوقة (سورية + تركية + عربية + عالمية)
RSS_FEEDS = [
    # 🇸🇾 سورية رسمية
    "https://sana.sy/?feed=rss2",                    # سانا الرسمية
    "https://www.syria.tv/feed",                     # تلفزيون سوريا
    "https://syriasteps.com/feed/",                  # سورياستيبس
    "https://alikhbariah.com/feed/",                 # الإخبارية السورية
    
    # 🇹🇷 تركية موثوقة
    "https://www.aa.com.tr/ar/rss/default.aspx",     # الأناضول عربي
    "https://trt.global/arabi/rss/",                 # TRT عربي
    "https://www.yenisafak.com/rss",                 # يني شفق عربي
    
    # 🌍 عالمية
    "https://www.aljazeera.com/xml/rss/all.xml",     # الجزيرة
    "http://feeds.bbci.co.uk/news/world/rss.xml",    # بي بي سي
    "https://www.theguardian.com/world/rss",         # الغارديان
    
    # 🇸🇦 عربية
    "https://aawsat.com/rss-feed",                   # الشرق الأوسط
    "https://www.alaraby.co.uk/feed.xml",            # العربي الجديد
    "https://www.skynewsarabia.com/rss/world.xml",   # سكاي
    "https://www.alalam.ir/rss",                     # العالم
    
    # احتياطي
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
    "https://www.independent.co.uk/news/world/rss",
    "https://www.france24.com/en/rss",
]

KEYWORDS = [
    "سوريا", "Syria", "دمشق", "حلب", "حمص", "إدلب", "الرقة", "دير الزور", 
    "الحسكة", "درعا", "السويداء", "أحمد الشرع", "الشرع", "HTS", "قسد"
]

def get_source_name(url):
    sources = {
        "sana.sy": "🇸🇾 سانا الرسمية", "syria.tv": "📺 تلفزيون سوريا",
        "syriasteps": "🇸🇾 سورياستيبس", "alikhbariah": "📺 الإخبارية",
        "aa.com.tr": "🇹🇷 الأناضول", "trt.global": "🇹🇷 TRT عربي",
        "yenisafak": "🇹🇷 يني شفق", "aljazeera": "🟢 الجزيرة",
        "bbc": "🔴 بي بي سي", "guardian": "🟠 الغارديان"
    }
    return next((v for k, v in sources.items() if k in url.lower()), "📰 وكالة")

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def run_bot():
    print("🔍 20 وكالة (سانا + تلفزيون سوريا + تركية + عالمية)")
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=48)
    
    for i, url in enumerate(RSS_FEEDS, 1):
        source = get_source_name(url)
        print(f"[{i:2d}/20] {source}")
        
        try:
            r = requests.get(url, headers={'User-Agent': 'NewsBot/3.0'}, timeout=12)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            for entry in feed.entries[:5]:
                title = (entry.title or "")
                summary = (entry.summary or entry.description or "")
                
                if any(kw.lower() in f"{title} {summary}".lower() for kw in KEYWORDS):
                    pub_date = None
                    for date_field in ['published_parsed', 'updated_parsed']:
                        if hasattr(entry, date_field):
                            try:
                                pub_date = datetime(*getattr(entry, date_field)[:6])
                                break
                            except:
                                pass
                    
                    if pub_date and pub_date > cutoff:
                        articles.append({
                            'title': title[:105],
                            'link': entry.link or '',
                            'source': source,
                            'date': pub_date
                        })
                        print(f"     ✅ خبر سوري ✓")
                        break
                        
        except:
            print(f"     ⏭️")
        
        time.sleep(0.8)
    
    print(f"\n📊 {len(articles)} خبر سوري")
    
    if not articles:
        msg = "📭 <b>لا أخبار سورية الآن</b>\n\n🔍 20 وكالة | ⏰ آخر 48 ساعة"
    else:
        articles.sort(key=lambda x: x['date'], reverse=True)
        top = articles[:12]
        
        now_str = datetime.utcnow().strftime("%H:%M UTC")
        msg = f"<b>📰 أخبار سوريا الآن</b>\n\n⏰ {now_str}\n\n"
        for i, art in enumerate(top, 1):
            msg += f"{i}. <b>{art['title']}…</b>\n📻 {art['source']}\n🔗 <a href='{art['link']}'>الكامل</a>\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "<b>👨‍💻 محمد محمد جلال الخطيب</b>\n"
        msg += "<b>🎓 طلاب كليات الإعلام || FMD</b>"
    
    personal = send_telegram(CHAT_ID, msg)
    channel = send_telegram(CHANNEL_ID, msg)
    
    print(f"\n🎉 نجح: رقمك={personal} | قناة={channel}")

if __name__ == "__main__":
    run_bot()
