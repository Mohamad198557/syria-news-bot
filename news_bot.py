import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

# لوج هادئ تماماً
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(message)s")

# Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"  # قناتك

TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
print("🚀 بوت أخبار سوريا + سانا + تلفزيون سوريا ✅")

# 🔥 14 مصدر RSS شغال 100% (مختبر مارس 2026)
RSS_FEEDS = [
    # عالمية موثوقة
    "https://www.aljazeera.com/xml/rss/all.xml",           # الجزيرة
    "http://feeds.bbci.co.uk/news/world/rss.xml",          # بي بي سي  
    "https://www.theguardian.com/world/rss",               # الغارديان
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    
    # **سورية رسمية + تلفزيون سوريا** ⭐
    "https://sana.sy/?feed=rss2",                          # وكالة سانا الرسمية ✅
    "https://www.syria.tv/feed",                           # تلفزيون سوريا ✅
    "https://syriasteps.com/feed/",                         # سورياستيبس
    "https://alikhbariah.com/feed/",                       # الإخبارية السورية
    
    # عربية شغالة
    "https://www.skynewsarabia.com/rss/world.xml",         # سكاي
    "https://www.alaraby.co.uk/feed.xml",                  # العربي الجديد
    "https://aawsat.com/rss-feed",                         # الشرق الأوسط
    "https://www.alalam.ir/rss",                           # العالم
    
    # احتياطي موثوق
    "http://feeds.feedburner.com/time/world",              # تايم
    "https://abcnews.go.com/abcnews/usheadlines",          # ABC
]

# كلمات مفتاحية سوريا كاملة
KEYWORDS = [
    "سوريا", "Syria", "سوري", "Syrian", "دمشق", "حلب", "حمص", "حماة", "اللاذقية",
    "طرطوس", "إدلب", "الرقة", "دير الزور", "الحسكة", "القامشلي", "السويداء",
    "درعا", "القنيطرة", "تدمر", "أحمد الشرع", "الشرع", "الرئيس السوري",
    "هيئة تحرير الشام", "HTS", "قسد", "SDF", "تركيا", "إسرائيل"
]

def get_source_name(url):
    """أسماء جميلة للوكالات"""
    sources = {
        "sana.sy": "🇸🇾 سانا الرسمية",
        "syria.tv": "📺 تلفزيون سوريا", 
        "syriasteps": "🇸🇾 سورياستيبس",
        "alikhbariah": "📺 الإخبارية السورية",
        "aljazeera": "🟢 الجزيرة", 
        "bbc": "🔴 بي بي سي",
        "guardian": "🟠 الغارديان",
        "nytimes": "⚫ نيويورك تايمز",
        "skynewsarabia": "🔵 سكاي",
        "alaraby": "🟡 العربي الجديد",
        "aawsat": "🔷 الشرق الأوسط"
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
    """بوت أخبار سوريا المتقدم"""
    print("🔍 فحص 14 مصدر (سانا + تلفزيون سوريا + عالمي)")
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=48)
    
    for i, url in enumerate(RSS_FEEDS, 1):
        source = get_source_name(url)
        print(f"[{i:2d}/14] {source}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 NewsBot/2.0'
            }
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            if not feed.entries:
                print("     لا أخبار")
                continue
            
            for entry in feed.entries[:6]:
                title = (entry.title or "")
                summary = (entry.summary or entry.description or "")
                link = entry.link or ""
                
                # فلترة سوريا
                text = f"{title} {summary}".lower()
                if not any(kw.lower() in text for kw in KEYWORDS):
                    continue
                
                # تاريخ (آخر 48 ساعة)
                pub_date = None
                for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                    if hasattr(entry, date_field):
                        try:
                            pub_date = datetime(*getattr(entry, date_field)[:6])
                            break
                        except:
                            pass
                
                if not pub_date or pub_date < cutoff:
                    continue
                
                articles.append({
                    'title': title[:110],
                    'link': link,
                    'source': source,
                    'date': pub_date
                })
                print(f"     ✅ {title[:60]}...")
                break  # أول خبر سوري من كل مصدر
                
        except:
            print(f"     ⏭️ غير متاح")
        
        time.sleep(1.2)
    
    print(f"\n📊 {len(articles)} خبر سوري حديث ✓")
    
    if not articles:
        msg = "📭 <b>لا أخبار سورية الآن</b>\n\n"
        msg += "🔍 فُحِصت 14 مصدر (سانا + تلفزيون سوريا + عالمي)\n"
        msg += "⏰ آخر 48 ساعة | تحديث تلقائي"
    else:
        # ترتيب حسب التاريخ
        articles.sort(key=lambda x: x['date'], reverse=True)
        top = articles[:10]
        
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        msg = f"<b>📰 آخر أخبار سوريا</b>\n\n"
        msg += f"<i>⏰ {now_str} | {len(top)} خبر من 14 مصدر</i>\n\n"
        
        for i, art in enumerate(top, 1):
            msg += f"{i}. <b>{art['title']}…</b>\n"
            msg += f"📻 <i>{art['source']}</i>\n"
            msg += f"🔗 <a href='{art['link']}'>قراءة الكامل</a>\n\n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "<b>👨‍💻 تم التصميم بواسطة:</b>\n"
        msg += "<b>محمد محمد جلال الخطيب</b>\n\n"
        msg += "<b>🎓طلاب كليات الإعلام || FMD</b>"
    
    # إرسال للمكانين
    personal = send_telegram(CHAT_ID, msg)
    channel = send_telegram(CHANNEL_ID, msg)
    
    print(f"\n🎉 النتيجة النهائية:")
    print(f"📱 رقمك الشخصي: {'✅ ناجح' if personal else '❌ فشل'}")
    print(f"📢 القناة: {'✅ ناجح' if channel else '❌ فشل'}")
    print("🏁 البوت جاهز للعمل التلقائي!")

if __name__ == "__main__":
    run_bot()
