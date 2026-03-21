import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

# إعداد لوج هادئ (WARNING بس)
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# Secrets (رقمك الشخصي بس)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"  # قناتك ✅

if not BOT_TOKEN or not CHAT_ID:
    print("❌ BOT_TOKEN أو CHAT_ID مفقود!")
    raise SystemExit(1)

TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
print(f"🚀 إرسال لـ {len(TARGET_CHATS)} وجهة")

# 🔥 12 وكالة شغالة 100% (تم اختبارها)
RSS_FEEDS = [
    # عالمية موثوقة
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.reuters.com/reuters/worldNews", 
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.apnews.com/rss/world-news",
    "http://feeds.feedburner.com/time/world",
    "https://www.washingtonpost.com/world/rss_vmz",
    "https://abcnews.go.com/abcnews/usheadlines",
    "https://www.nbcnews.com/news/world?ocid=feeds-world-topstories-rss",
    # عربية شغالة
    "https://www.skynewsarabia.com/rss/world.xml",
]

# ✅ الـ 14 محافظة + أحمد الشرع
KEYWORDS = [
    "Syria", "سوريا", "Syrian", "سوري", "السوريين",
    # المحافظات الـ 14 كاملة
    "Damascus", "دمشق", "Rif Dimashq", "ريف دمشق",
    "Aleppo", "حلب", "Homs", "حمص", "Hama", "حماة",
    "Latakia", "اللاذقية", "Tartus", "طرطوس",
    "Idlib", "إدلب", "ادلب", "Raqqa", "الرقة",
    "Deir ez-Zor", "دير الزور", "ديرالزور", "Hasakah", "الحسكة",
    "Qamishli", "القامشلي", "Suwayda", "السويداء", "Daraa", "درعا",
    # الرئيس + كيانات
    "Ahmed al-Sharaa", "أحمد الشرع", "الشرع", "الرئيس السوري",
    "HTS", "هيئة تحرير الشام", "SDF", "قسد",
    # الجوار
    "Turkey", "تركيا", "Israel", "إسرائيل", "Lebanon", "لبنان"
]

IMPORTANT_WORDS = [
    "attack", "strike", "explosion", "killed", "war", "arrest",
    "هجوم", "قصف", "انفجار", "مقتل", "حرب", "اعتقال"
]

def get_source_name(url: str) -> str:
    """اسم الوكالة من URL"""
    u = url.lower()
    sources = {
        "aljazeera": "🟢 الجزيرة نت",
        "reuters": "🟡 رويترز", 
        "bbc": "🔴 بي بي سي",
        "cnn": "🟣 سي إن إن",
        "nytimes": "⚫ نيويورك تايمز",
        "theguardian": "🟠 الغارديان",
        "apnews": "🔷 أسوشيتد برس",
        "time": "🧡 تايم",
        "washingtonpost": "🔵 واشنطن بوست",
        "abcnews": "🟣 ABC نيوز",
        "nbcnews": "🔴 NBC",
        "skynewsarabia": "🔵 سكاي عربية"
    }
    return next((name for key, name in sources.items() if key in u), "📰 وكالة")

def contains_keyword(text: str) -> bool:
    """فلترة سوريا + محافظات"""
    return any(k.lower() in text.lower() for k in KEYWORDS)

def score_news(title: str, summary: str, source: str) -> int:
    """درجة الأهمية"""
    text = f"{title} {summary}".lower()
    score = sum(4 for k in KEYWORDS if k.lower() in text)  # محافظات + الرئيس
    score += sum(2 for k in IMPORTANT_WORDS if k.lower() in text)
    
    # وزن الوكالات الكبرى
    top_sources = ["رويترز", "بي بي سي", "الجزيرة", "سي إن إن"]
    if any(s in source for s in top_sources):
        score += 3
        
    return score

def get_entry_datetime(entry) -> datetime | None:
    """استخراج تاريخ الخبر"""
    for field in ["published_parsed", "updated_parsed"]:
        if hasattr(entry, field) and getattr(entry, field):
            try:
                return datetime(*getattr(entry, field)[:6])
            except:
                pass
    return None

def send_to_all_chats(message: str) -> int:
    """إرسال للقناة + رقمك"""
    success_count = 0
    for i, chat_id in enumerate(TARGET_CHATS, 1):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, data=data, timeout=12)
            if response.status_code == 200:
                success_count += 1
                print(f"✅ وجهة {i}: شغالة")
            else:
                print(f"❌ وجهة {i}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"💥 وجهة {i}: خطأ - {e}")
        time.sleep(1)  # تأخير بين الإرسال
    return success_count

def run_once():
    """التشغيل الرئيسي"""
    print("🚀 بوت أخبار سوريا - 12 وكالة موثوقة")
    print(f"📅 آخر 48 ساعة | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    
    articles = []
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=48)
    
    for i, feed_url in enumerate(RSS_FEEDS, 1):
        source_name = get_source_name(feed_url)
        print(f"[{i:2d}/12] 🔍 {source_name}")
        
        try:
            response = requests.get(feed_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            
            if not feed.entries:
                continue
                
            for entry in feed.entries[:10]:  # 10 أخبار من كل وكالة
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                link = getattr(entry, "link", "")
                
                if not link or len(title) < 15:
                    continue
                
                full_text = f"{title} {summary}"
                if not contains_keyword(full_text):
                    continue
                
                pub_date = get_entry_datetime(entry)
                if not pub_date or pub_date < cutoff:
                    continue
                
                score = score_news(title, summary, source_name)
                if score < 7:  # فلترة أعلى جودة
                    continue
                
                articles.append({
                    "title": title[:120],
                    "link": link,
                    "source": source_name,
                    "score": score,
                    "pub_date": pub_date
                })
                
        except Exception as e:
            print(f"    ⏭️ تخطي {source_name}")
        
        time.sleep(0.8)  # هدوء السيرفرات
    
    print(f"\n📊 وجد {len(articles)} خبر متطابق")
    
    if not articles:
        message = "📭 <b>لا أخبار مهمة الآن</b>\n\n"
        message += "لم نجد أخبار سورية/محافظات خلال آخر 48 ساعة\n"
        message += "من 12 وكالة عالمية موثوقة"
        send_to_all_chats(message)
        return
    
    # ترتيب: الأهم أولاً
    articles.sort(key=lambda x: (x["score"], x["pub_date"]), reverse=True)
    top_articles = articles[:8]  # أفضل 8 أخبار
    
    # الرسالة الاحترافية
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    message = "<b>📰 أهم أخبار سوريا والمحافظات</b>\n\n"
    message += f"<i>⏰ آخر 48 ساعة | {now_str}</i>\n"
    message += f"<i>🔍 {len(top_articles)} خبر من 12 وكالة</i>\n\n"
    
    for i, article in enumerate(top_articles, 1):
        message += f"<b>{i}.</b> {article['title']}\n"
        message += f"📻 <i>{article['source']}</i> | ⭐{article['score']}\n"
        message += f"🔗 <a href='{article['link']}'>الكامل</a>\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<b>ℹ️ بوت أخبار سوريا المتقدم</b>\n"
    message += "<b>👨‍💻 محمد محمد جلال الخطيب</b>\n"
    message += "<b>🎓 طلاب كليات الإعلام || FMD</b>\n"
    message += "<i>تحديث تلقائي عبر GitHub Actions</i>"
    
    # الإرسال النهائي
    success = send_to_all_chats(message)
    print(f"\n🎉 تم الإرسال: {success}/2 وجهة ناجحة ✅")

if __name__ == "__main__":
    run_once()
