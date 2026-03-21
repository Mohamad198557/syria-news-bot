import os
import requests
import feedparser
from datetime import datetime
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(name)

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
    "Damascus", "دمشق",
    "Aleppo", "حلب",
    "Idlib", "إدلب", "ادلب",
    "Homs", "حمص",
    "Daraa", "درعا",
    "HTS", "Hayat Tahrir", "هيئة تحرير الشام",
    "SDF", "قسد", "قوات سوريا الديمقراطية",
    "Syrian president", "الرئيس السوري", "بشار الأسد",
    "Turkey", "تركيا", "Ankara", "أنقرة",
    "Israel", "إسرائيل", "الجولان", "Golan",
    "Lebanon", "لبنان", "Iraq", "العراق", "Jordan", "الأردن",
]

IMPORTANT_WORDS = [
    "attack", "strike", "explosion", "war", "conflict",
    "killed", "injured", "dead", "arrest", "sanctions",
    "هجوم", "قصف", "انفجار", "حرب", "نزاع",
    "مقتل", "إصابة", "اعتقال", "غارة", "عملية",
]

TRANSLATE_URL = "https://libretranslate.de/translate"

def get_source_name(url: str) -> str:
    u = url.lower()
    if "aljazeera" in u: return "الجزيرة"
    if "alarabiya" in u: return "العربية"
    if "skynewsarabia" in u: return "سكاي نيوز عربية"
    if "reuters" in u: return "رويترز"
    if "bbc" in u: return "بي بي سي"
    if "cnn" in u: return "سي إن إن"
    if "nytimes" in u: return "نيويورك تايمز"
    if "theguardian" in u: return "الغارديان"
    if "apnews" in u or "ap.org" in u: return "أسوشيتد برس"
    if "france24" in u: return "فرانس 24"
    return "وكالة أنباء"

def contains_keyword(text: str) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in KEYWORDS)

def score_news(title: str, summary: str, source: str) -> int:
    text = (title + " " + summary).lower()
    score = 0

    # وزن المصدر
    for key in ["reuters", "bbc", "cnn", "aljazeera", "alarabiya"]:
        if key in source.lower():
            score += 2

    # الكلمات المهمة
    for w in IMPORTANT_WORDS:
        if w.lower() in text:
            score += 2

    # الكلمات المفتاحية لسوريا
    for w in KEYWORDS:
        if w.lower() in text:
            score += 3

    return score

def translate_to_arabic(text: str) -> str:
    try:
        data = {
            "q": text[:300],
            "source": "auto",
            "target": "ar",
            "format": "text",
        }
        r = requests.post(TRANSLATE_URL, json=data, timeout=10)
        if r.status_code == 200:
            return r.json().get("translatedText", text)
        return text
    except Exception as e:
        logger.warning(f"ترجمة فشلت: {e}")

        return text
def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, data=data, timeout=20)
    if r.status_code != 200:
        logger.error(f"Telegram error: {r.status_code} - {r.text}")

def run_once():
    logger.info("بدء جمع الأخبار...")
    articles = []

    for feed_url in RSS_FEEDS:
        try:
            source_name = get_source_name(feed_url)
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:  # آخر 15 خبر من كل مصدر
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "")

                text = title + " " + summary
                if not contains_keyword(text):
                    continue

                s = score_news(title, summary, feed_url)
                if s < 5:
                    continue

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source_name,
                    "score": s,
                })
        except Exception as e:
            logger.error(f"خطأ في قراءة {feed_url}: {e}")

    if not articles:
        logger.info("لا توجد أخبار مطابقة اليوم.")
        send_telegram("📭 لا توجد أخبار مهمة عن سوريا في الوقت الحالي.")
        return

    # ترتيب واختيار أهم 10
    articles.sort(key=lambda x: x["score"], reverse=True)
    top = articles[:10]

    # بناء الرسالة
    today = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = f"📰 <b>أهم أخبار سوريا والمنطقة الآن</b>

"
    msg += f"⏱ <i>تحديث تلقائي عبر GitHub Actions</i>
"
    msg += f"📅 <i>{today}</i>

"

    for i, art in enumerate(top, 1):
        t_ar = translate_to_arabic(art["title"])
        msg += f"<b>{i}.</b> {t_ar}
"
        msg += f"📻 <i>{art['source']}</i>
"
        msg += f"🔗 <a href="{art['link']}">رابط الخبر</a>

"

    # إضافة قسم "عن البوت"
    msg += (
        "——————————————
"
        "ℹ️ <b>عن البوت</b>
"
        "تم تصميم هذا البوت بواسطة: <b>محمد محمد جلال الخطيب</b>
"
        "Powered by: <b>طلاب كليات الإعلام || FMD</b>
"
    )

    send_telegram(msg)
    logger.info("تم إرسال الملخص بنجاح.")

if name == "main":
    run_once()
