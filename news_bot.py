import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

# إعداد اللوج
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# متغيرات البيئة من GitHub Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("❌ BOT_TOKEN أو CHAT_ID غير موجودين!")
    raise SystemExit("تحقق من Secrets في GitHub")

logger.info(f"🚀 بدء البوت - Chat ID: {CHAT_ID[:10]}...")

# 🔥 20 وكالة أنباء عالمية
RSS_FEEDS = [
    # عربي (10)
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.alarabiya.net/feeds/1410836791105.xml",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.annahar.com/rss/generalnews",
    "https://asharq.com/rss/feed/1/",
    "https://www.france24.com/ar/tag/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1-%D8%B3%D9%88%D8%B1%D9%8A%D8%A7/rss",
    "https://www.dostor.org/rss/feed",
    "https://www.masrawy.com/rss/all/index.xml",
    "https://www.vetogate.com/rss.xml",
    "https://www.elbalad.news/rss",
    # عالمي (10)
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
]

# ✅ كلمات مفتاحية شاملة (سوريا + 14 محافظة + أحمد الشرع)
KEYWORDS = [
    # سوريا عامة
    "Syria", "Syrian", "سوريا", "سوري", "السوريين",
    # الـ 14 محافظة
    "Damascus", "دمشق", "Rif Dimashq", "ريف دمشق",
    "Aleppo", "حلب", "Homs", "حمص", "Hama", "حماة",
    "Latakia", "اللاذقية", "Tartus", "طرطوس",
    "Idlib", "إدلب", "ادلب", "Raqqa", "الرقة",
    "Deir ez-Zor", "دير الزور", "ديرالزور", "Hasakah", "الحسكة",
    "Qamishli", "القامشلي", "As-Suwayda", "السويداء", "Daraa", "درعا",
    "Quneitra", "القنيطرة", "Palmyra", "تدمر",
    # الرئيس الحالي
    "Ahmed al-Sharaa", "أحمد الشرع", "الشرع", "Syrian president", "الرئيس السوري",
    # كيانات
    "HTS", "هيئة تحرير الشام", "SDF", "قسد",
    # دول مجاورة
    "Turkey", "تركيا", "Israel", "إسرائيل", "Lebanon", "لبنان", "Iraq", "العراق"
]

IMPORTANT_WORDS = [
    "attack", "strike", "explosion", "killed", "injured", "war", "arrest",
    "هجوم", "قصف", "انفجار", "مقتل", "إصابة", "حرب", "اعتقال"
]

def get_source_name(url: str) -> str:
    """اسم الوكالة من URL"""
    u = url.lower()
    sources = {
        "aljazeera": "🟢 الجزيرة",
        "alarabiya": "🟠 العربية",
        "skynewsarabia": "🔵 سكاي",
        "reuters": "🟡 رويترز",
        "bbc": "🔴 بي بي سي", 
        "cnn": "🟣 CNN",
        "nytimes": "⚫ NYT",
        "theguardian": "🟠 الغارديان",
        "apnews": "🔷 أسوشيتد",
        "france24": "🔵 فرانس 24"
    }
    for key, name in sources.items():
        if key in u: return name
    return "📰 وكالة"

def contains_keyword(text: str) -> bool:
    """فلترة بالكلمات"""
    return any(k.lower() in text.lower() for k in KEYWORDS)

def score_news(title: str, summary: str, source: str) -> int:
    """حساب درجة الأهمية"""
    text = (title + " " + summary).lower()
    score = 0
    
    # وزن الوكالات الكبرى
    if any(s in source.lower() for s in ["رويترز", "bbc", "cnn", "الجزيرة"]):
        score += 3
    
    # كلمات مهمة
    for w in IMPORTANT_WORDS:
        if w.lower() in text: score += 2
    
    # كلمات سوريا
    for w in KEYWORDS:
        if w.lower() in text: score += 3
        
    return score

def get_entry_datetime(entry):
    """استخراج تاريخ الخبر"""
    for field in ["published_parsed", "updated_parsed"]:
        if hasattr(entry, field) and getattr(entry, field):
            dt = getattr(entry, field)
            try: return datetime(*dt[:6])
            except: pass
    return None

def send_telegram(message: str) -> bool:
    """إرسال لتيليجرام"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        logger.info(f"📤 Telegram: {r.status_code}")
        if r.status_code != 200:
            logger.error(f"❌ Telegram error: {r.text}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"💥 Telegram exception: {e}")
        return False

def run_once():
    """الدالة الرئيسية"""
    logger.info("🔥 جمع أخبار سوريا من 20 وكالة...")
    articles = []
    
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=48)
    
    for i, url in enumerate(RSS_FEEDS, 1):
        source = get_source_name(url)
        logger.info(f"[{i}/20] {source}")
        
        try:
            resp = requests.get(url, timeout=12)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            
            for entry in feed.entries[:12]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                link = getattr(entry, "link", "")
                
                if not link or len(title) < 10:
                    continue
                
                if not contains_keyword(title + " " + summary):
                    continue
                
                pub_date = get_entry_datetime(entry)
                if not pub_date or pub_date < cutoff:
                    continue
                
                score = score_news(title, summary, source)
                if score < 6: continue
                
                articles.append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "score": score,
                    "pub_date": pub_date
                })
                
        except Exception as e:
            logger.warning(f"⏭️ تخطي {source}: {e}")
        
        time.sleep(0.5)
    
    logger.info(f"📊 وجد {len(articles)} مقال")
    
    if not articles:
        msg = "📭 <b>لا أخبار مهمة</b>\n\nلم نجد أخبار سورية خلال آخر 48 ساعة"
        send_telegram(msg)
        return
    
    # ترتيب واختيار أفضل 10
    articles.sort(key=lambda x: (x["score"], x["pub_date"]), reverse=True)
    top = articles[:10]
    
    # الرسالة النهائية
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = "<b>📰 أهم أخبار سوريا والمحافظات</b>\n\n"
    msg += f"⏰ آخر 48 ساعة | {now_str}\n\n"
    
    for i, art in enumerate(top, 1):
        msg += f"{i}. <b>{art['title'][:100]}...</b>\n"
        msg += f"📻 {art['source']} | ⭐{art['score']}\n"
        msg += f"🔗 <a href='{art['link']}'>الخبر</a>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>👨‍💻 المصمم:</b> محمد محمد جلال الخطيب\n"
    msg += "<b>🎓 الدعم:</b> طلاب كليات الإعلام || FMD"
    
    success = send_telegram(msg)
    logger.info(f"✅ انتهى: {'ناجح' if success else 'فشل Telegram'}")

if __name__ == "__main__":
    run_once()
