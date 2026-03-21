import os
import requests
import feedparser
from datetime import datetime
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("❌ BOT_TOKEN أو CHAT_ID غير موجودين في المتغيرات البيئية.")

# 20 وكالة أنباء (10 عربي + 10 أجنبي)
RSS_FEEDS = [
    # عربي
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
    
    # أجنبي
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

# كلمات مفتاحية لسوريا والمنطقة
KEYWORDS = [
    "Syria", "Syrian", "سوريا", "سوري", "السوريين",
    "Damascus", "دمشق", "Aleppo", "حلب", "Idlib", "إدلب", "ادلب",
    "Homs", "حمص", "Daraa", "درعا", "HTS", "هيئة تحرير الشام",
    "SDF", "قسد", "Syrian president", "الرئيس السوري", "بشار الأسد",
    "Turkey", "تركيا", "Israel", "إسرائيل", "Lebanon", "لبنان"
]

IMPORTANT_WORDS = [
    "attack", "strike", "explosion", "war", "conflict",
    "killed", "injured", "dead", "arrest", "sanctions",
    "هجوم", "قصف", "انفجار", "حرب", "نزاع", "مقتل", "إصابة"
]

TRANSLATE_URL = "https://libretranslate.de/translate"

def get_source_name(url: str) -> str:
    u = url.lower()
    sources = {
        "aljazeera": "🟢 الجزيرة",
        "alarabiya": "🟠 العربية", 
        "skynewsarabia": "🔵 سكاي نيوز",
        "reuters": "🟡 رويترز",
        "bbc": "🔴 بي بي سي",
        "cnn": "🟣 CNN",
        "nytimes": "⚫ نيويورك تايمز",
        "theguardian": "🟠 الغارديان",
        "apnews": "🔷 أسوشيتد برس"
    }
    for key, name in sources.items():
        if key in u:
            return name
    return "📰 وكالة أنباء"

def contains_keyword(text: str) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in KEYWORDS)

def score_news(title: str, summary: str, source: str) -> int:
    text = (title + " " + summary).lower()
    score = 0
    
    # وزن المصادر الكبرى
    top_sources = ["رويترز", "bbc", "cnn", "الجزيرة", "العربية"]
    if any(s in source for s in top_sources):
        score += 2
    
    # كلمات مهمة
    for w in IMPORTANT_WORDS:
        if w.lower() in text:
            score += 2
    
    # كلمات سوريا
    for w in KEYWORDS:
        if w.lower() in text:
            score += 3
    
    return score

def translate_to_arabic(text: str) -> str:
    try:
        data = {"q": text[:300], "source": "auto", "target": "ar", "format": "text"}
        r = requests.post(TRANSLATE_URL, json=data, timeout=10)
        if r.status_code == 200:
            return r.json().get("translatedText", text[:100])
    except:
        pass
    return text[:100] + "..."

def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, data=data, timeout=20)
        logger.info(f"Telegram: {r.status_code}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def run_once():
    logger.info("🚀 بدء جمع الأخبار من 20 وكالة...")
    articles = []
    
    for i, feed_url in enumerate(RSS_FEEDS):
        try:
            logger.info(f"فحص {i+1}: {get_source_name(feed_url)}")
            source_name = get_source_name(feed_url)
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:10]:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                link = getattr(entry, "link", "")
                
                if not link or not contains_keyword(title + " " + summary):
                    continue
                
                score = score_news(title, summary, source_name)
                if score >= 5:
                    articles.append({
                        "title": title,
                        "summary": summary[:200],
                        "link": link,
                        "source": source_name,
                        "score": score
                    })
        except Exception as e:
            logger.error(f"خطأ في {feed_url}: {e}")
    
    if not articles:
        send_telegram("📭 لا توجد أخبار مهمة عن سوريا الآن.")
        return
    
    # ترتيب وأفضل 8 أخبار
    articles.sort(key=lambda x: x["score"], reverse=True)
    top_articles = articles[:8]
    
    # بناء الرسالة (محددة في سطر واحد لكل جزء)
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = f"<b>📰 أهم أخبار سوريا والمنطقة</b>\n\n⏱ تحديث: {today}\n\n"
    
    for i, art in enumerate(top_articles, 1):
        title_ar = translate_to_arabic(art["title"])
        msg += f"{i}. <b>{title_ar}</b>\n"
        msg += f"📻 {art['source']} | ⭐{art['score']}\n"
        msg += f"🔗 <a href='{art['link']}'>الرابط</a>\n\n"
    
    # قسم الاعتمادات
    msg += "────────────────────\n"
    msg += "<b>ℹ️ عن البوت:</b>\n"
    msg += "تم تصميم هذا البوت بواسطة:\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n\n"
    msg += "<b>Powered by:</b>\n"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    send_telegram(msg)
    logger.info(f"✅ تم إرسال {len(top_articles)} خبر")

if __name__ == "__main__":
    run_once()
