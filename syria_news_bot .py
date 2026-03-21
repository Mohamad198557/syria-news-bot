import feedparser
import requests
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# 🌍 20 وكالة أنباء
RSS_FEEDS = [
    # عالمي
    "https://feeds.reuters.com/reuters/worldNews",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://rss.cnn.com/rss/edition_world.rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.theguardian.com/world/rss",
    "https://feeds.apnews.com/apf-topnews",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/top-stories/s-9097/rss",
    "https://www.euronews.com/rss?level=theme&name=news",

    # عربي
    "https://www.aljazeera.net/aljazeera/rss",
    "https://www.alarabiya.net/.mrss/en.xml",
    "https://www.skynewsarabia.com/rss",
    "https://arabic.rt.com/rss/",
    "https://www.asharq.com/rss",
    "https://www.alaraby.co.uk/rss.xml",
    "https://www.annahar.com/RSS",
    "https://www.youm7.com/rss/SectionRss?SectionID=65",
    "https://www.masrawy.com/rss/rss",
    "https://www.almodon.com/rss"
]

# 🔥 كلمات البحث الموسعة
KEYWORDS = [
    # عام
    "Syria", "Syrian", "سوريا", "سوري",

    # مدن ومحافظات
    "Damascus", "دمشق",
    "Aleppo", "حلب",
    "Homs", "حمص",
    "Hama", "حماة",
    "Latakia", "اللاذقية",
    "Tartus", "طرطوس",
    "Idlib", "إدلب",
    "Raqqa", "الرقة",
    "Deir ez-Zor", "دير الزور",
    "Daraa", "درعا",
    "Hasakah", "الحسكة",
    "Sweida", "السويداء",

    # شخصيات
    "Ahmed al-Sharaa", "أحمد الشرع",

    # حكومي
    "Syrian president", "الرئيس السوري",
    "Syrian minister", "وزير سوري",
    "Syrian government", "الحكومة السورية",

    # دبلوماسي
    "Syrian ambassador", "سفير سوري",
    "UN Syria", "الأمم المتحدة سوريا",

    # عسكري / سياسي
    "SDF", "قسد",
    "HTS", "هيئة تحرير الشام",
    "FSA", "الجيش الحر",
]

IMPORTANT_WORDS = [
    "attack", "strike", "war", "explosion",
    "agreement", "sanctions", "killed", "arrest",
    "هجوم", "قصف", "حرب", "انفجار",
    "اتفاق", "عقوبات", "مقتل", "اعتقال"
]


def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "disable_web_page_preview": True
    })


def translate(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ar",
            "dt": "t",
            "q": text
        }
        res = requests.get(url, params=params).json()
        return res[0][0][0]
    except:
        return text


def score(title, summary):
    text = (title + summary).lower()
    s = 0

    for w in IMPORTANT_WORDS:
        if w.lower() in text:
            s += 2

    for k in KEYWORDS:
        if k.lower() in text:
            s += 1

    return s


def collect_news():
    collected = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            title = entry.title
            link = entry.link
            summary = getattr(entry, "summary", "")

            if not any(k.lower() in (title + summary).lower() for k in KEYWORDS):
                continue

            s = score(title, summary)

            if s >= 3:
                collected.append({
                    "title": title,
                    "link": link,
                    "score": s
                })

    return collected


def send_top_news(news_list):
    if not news_list:
        return

    news_list = sorted(news_list, key=lambda x: x["score"], reverse=True)[:5]

    message = "🚨 أهم أخبار سوريا الآن\n\n"

    for i, n in enumerate(news_list, 1):
        t = translate(n["title"])
        message += f"{i}. {t}\n🔗 {n['link']}\n\n"

    message += f"""
⏰ {datetime.now().strftime('%H:%M')}

━━━━━━━━━━━━━━
تم التصميم بواسطة محمد محمد جلال الخطيب  
Powered by: FMD || طلاب كليات الإعلام
"""

    send(message)


def main():
    news = collect_news()
    send_top_news(news)
