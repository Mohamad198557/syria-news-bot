import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")        # رقمك الشخصي
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # القناة (اختياري)

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("❌ BOT_TOKEN أو CHAT_ID مفقود!")

# قائمة الوجهات
TARGET_CHATS = [CHAT_ID]
if CHANNEL_ID:
    TARGET_CHATS.append(CHANNEL_ID)

logger.info(f"📤 إرسال إلى {len(TARGET_CHATS)} وجهة: {TARGET_CHATS}")

# نفس الـ RSS_FEEDS والـ KEYWORDS اللي اشتغلت
RSS_FEEDS = [
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

KEYWORDS = [
    "Syria", "سوريا", "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس",
    "إدلب", "الرقة", "دير الزور", "الحسكة", "القامشلي", "السويداء", "درعا",
    "أحمد الشرع", "الرئيس السوري", "HTS", "قسد", "تركيا", "إسرائيل"
]

def get_source_name(url):
    u = url.lower()
    sources = {
        "aljazeera": "🟢 الجزيرة", "alarabiya": "🟠 العربية",
        "skynewsarabia": "🔵 سكاي", "reuters": "🟡 رويترز",
        "bbc": "🔴 بي بي سي", "cnn": "🟣 CNN",
        "nytimes": "⚫ NYT", "theguardian": "🟠 الغارديان"
    }
    return next((name for key, name in sources.items() if key in u), "📰 وكالة")

def contains_keyword(text):
    return any(k.lower() in text.lower() for k in KEYWORDS)

def score_news(title, summary, source):
    text = (title + " " + summary).lower()
    score = 0
    if any(s in source.lower() for s in ["رويترز", "bbc", "الجزيرة"]): score += 3
    score += sum(3 for k in KEYWORDS if k.lower() in text)
    return score

def get_entry_datetime(entry):
    for field in ["published_parsed", "updated_parsed"]:
        if hasattr(entry, field) and getattr(entry, field):
            dt = getattr(entry, field)
            try: return datetime(*dt[:6])
            except: pass
    return None

def send_telegram_to_all(message):
    """إرسال لكل الوجهات"""
    success_count = 0
    for chat_id in TARGET_CHATS:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            r = requests.post(url, data=data, timeout=15)
            logger.info(f"📤 {chat_id[:10]}...: {r.status_code}")
            if r.status_code == 200:
                success_count += 1
            else:
                logger.error(f"❌ {chat_id[:10]}...: {r.text}")
        except Exception as e:
            logger.error(f"💥 {chat_id[:10]}...: {e}")
        time.sleep(1)  # تأخير بين الإرسال
    return success_count

def run_once():
    logger.info("🚀 جمع أخبار سوريا...")
    articles = []
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=48)
    
    for i, url in enumerate(RSS_FEEDS, 1):
        source = get_source_name(url)
        logger.info(f"[{i}/20] {source}")
        try:
            resp = requests.get(url, timeout=12)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:12]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                link = getattr(entry, "link", "")
                if not link or not contains_keyword(title + " " + summary):
                    continue
                pub_date = get_entry_datetime(entry)
                if not pub_date or pub_date < cutoff:
                    continue
                score = score_news(title, summary, source)
                if score < 6: continue
                articles.append({
                    "title": title[:100],
                    "link": link,
                    "source": source,
                    "score": score
                })
        except Exception as e:
            logger.warning(f"⏭️ {source}: {e}")
        time.sleep(0.5)
    
    if not articles:
        msg = "📭 <b>لا أخبار مهمة</b>\n\nآخر 48 ساعة"
        send_telegram_to_all(msg)
        return
    
    articles.sort(key=lambda x: (x["score"], x["title"]), reverse=True)
    top = articles[:10]
    
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = "<b>📰 أهم أخبار سوريا</b>\n\n"
    msg += f"⏰ آخر 48 ساعة | {now_str}\n\n"
    for i, art in enumerate(top, 1):
        msg += f"{i}. <b>{art['title']}...</b>\n"
        msg += f"📻 {art['source']} | ⭐{art['score']}\n"
        msg += f"🔗 <a href='{art['link']}'>الخبر</a>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>👨‍💻 محمد محمد جلال الخطيب</b>\n"
    msg += "<b>🎓 طلاب كليات الإعلام || FMD</b>"
    
    success = send_telegram_to_all(msg)
    logger.info(f"✅ {success}/{len(TARGET_CHATS)} ناجح")

if __name__ == "__main__":
    run_once()
