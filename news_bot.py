import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # رقمك الشخصي
CHANNEL_ID = "-1003803988944"  # قناتك مباشرة في الكود

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("❌ BOT_TOKEN أو CHAT_ID مفقود!")

TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
logger.info(f"📤 إرسال لـ {len(TARGET_CHATS)} وجهة")

# 20 وكالة أنباء
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

# الـ 14 محافظة + أحمد الشرع
KEYWORDS = [
    "Syria", "سوريا", "دمشق", "ريف دمشق", "حلب", "حمص", "حماة", "اللاذقية",
    "طرطوس", "إدلب", "ادلب", "الرقة", "دير الزور", "الحسكة", "القامشلي",
    "السويداء", "درعا", "القنيطرة", "تدمر", "أحمد الشرع", "الرئيس السوري",
    "HTS", "هيئة تحرير الشام", "SDF", "قسد", "تركيا", "إسرائيل"
]

def get_source_name(url):
    u = url.lower()
    sources = {
        "aljazeera": "🟢 الجزيرة", "alarabiya": "🟠 العربية",
        "skynewsarabia": "🔵 سكاي", "reuters": "🟡 رويترز",
        "bbc": "🔴 بي بي سي", "cnn": "🟣 CNN",
        "nytimes": "⚫ NYT", "theguardian": "🟠 الغارديان"
    }
    return next((v for k, v in sources.items() if k in u), "📰 وكالة")

def contains_keyword(text):
    return any(k.lower() in text.lower() for k in KEYWORDS)

def score_news(title, summary, source):
    text = (title + " " + summary).lower()
    score = sum(3 for k in KEYWORDS if k.lower() in text)
    if any(s in source.lower() for s in ["رويترز", "bbc", "الجزيرة"]): score += 3
    return score

def get_entry_datetime(entry):
    for field in ["published_parsed", "updated_parsed"]:
        if hasattr(entry, field) and getattr(entry, field):
            dt = getattr(entry, field)
            try: return datetime(*dt[:6])
            except: pass
    return None

def send_to_all_chats(message):
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
            time.sleep(1)
        except Exception as e:
            logger.error(f"💥 {chat_id[:10]}...: {e}")
    return success_count

def run_once():
    logger.info("🚀 بوت أخبار سوريا - إرسال للقناة + الشخصي")
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
                if not link or len(title) < 10 or not contains_keyword(title + " " + summary):
                    continue
                pub_date = get_entry_datetime(entry)
                if not pub_date or pub_date < cutoff:
                    continue
                score = score_news(title, summary, source)
                if score < 6: continue
                articles.append({
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "link": link,
                    "source": source,
                    "score": score
                })
        except Exception as e:
            logger.warning(f"⏭️ {source}: {e}")
        time.sleep(0.5)
    
    logger.info(f"📊 وجد {len(articles)} خبر")
    
    if not articles:
        msg = "📭 <b>لا أخبار مهمة</b>\n\nلم نجد أخبار عن سوريا خلال آخر 48 ساعة"
        send_to_all_chats(msg)
        return
    
    articles.sort(key=lambda x: (x["score"], x["title"]), reverse=True)
    top = articles[:10]
    
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    msg = "<b>📰 أهم أخبار سوريا والمحافظات</b>\n\n"
    msg += f"⏰ آخر 48 ساعة | {now_str}\n"
    msg += f"🔍 20 وكالة | {len(top)} خبر\n\n"
    
    for i, art in enumerate(top, 1):
        msg += f"{i}. <b>{art['title']}</b>\n"
        msg += f"📻 {art['source']} | ⭐{art['score']}\n"
        msg += f"🔗 <a href='{art['link']}'>الكامل</a>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>👨‍💻 تم تصميم البوت بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n\n"
    msg += "<b>🎓 Powered by:</b>\n"
    msg += "<b>طلاب كليات الإعلام || FMD</b>\n"
    
    success = send_to_all_chats(msg)
    logger.info(f"✅ نجح: {success}/2 وجهة")

if __name__ == "__main__":
    run_once()
