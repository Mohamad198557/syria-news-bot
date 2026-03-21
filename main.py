import os
import time
import logging
import re
from datetime import datetime, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt" # ملف الذاكرة

# الكلمات المفتاحية (كاملة دون اختصار)
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    "أحمد الشرع", "Ahmed al-Sharaa", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "السويداء", "Suwayda", "درعا", "Daraa", "القنيطرة", "Quneitra"
]

# الروابط (تم الترتيب: دولي -> عربي -> سوري محلي في النهاية)
RSS_FEEDS = [
    # 🌍 عالمية ودولية
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://trt.global/arabi/rss/",
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories",
    "https://www.euronews.com/rss.xml",
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
    
    # 🇸🇦 🇦🇪 وكالات عربية رسمية
    "https://www.spa.gov.sa/rss",
    "https://www.wam.ae/ar/rss",
    "https://www.bna.bh/rss/?lang=ar",
    "https://www.petra.gov.jo/rss/JoSiteAr.aspx",
    "https://www.aps.dz/rss",
    "https://www.saba.ye/rss/feed.xml",
    "https://www.qna.org.qa/rss",
    "https://www.kuna.net.kw/rss/",
    "https://www.mapnews.ma/rss/actualite-generale",
    "https://www.ani.mr/rss/",
    "https://www.suna-ed.org/rss/",
    "https://www.omannews.gov.om/rss",
    "https://www.wafa.ps/pages/rss.aspx",
    "https://www.wal.ps/rss/",
    "https://www.tapinfo.tn/rss",
    "https://www.ina.iq/rss/",
    "https://www.mena.org.eg/rss/",
    "https://aawsat.com/rss-feed",
    "https://www.alaraby.co.uk/feed.xml",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://asharq.com/rss/feed/1/",

    # 🇸🇾 المصادر السورية (في النهاية بناءً على طلبك)
    "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/",
    "https://alikhbariah.com/feed/",
    "https://sana.sy/?feed=rss2"
]

def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_sent_article(link):
    with open(DB_FILE, "a") as f:
        f.write(link + "\n")

def get_gold_dollar_prices():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://sp-today.com/en"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        gold = re.findall(r'1[,\\d]{6,9}', text)
        dollar = re.findall(r'1[1-2],\\d{3}', text)
        return (gold[0] if gold else "1,484,000"), (dollar[0] if dollar else "11,950")
    except:
        return "1,484,000", "11,950"

def get_source_name(url):
    sources = {
        "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا",
        "alikhbariah": "📺 الإخبارية السورية", "syriasteps": "🇸🇾 سورياستيبس",
        "aljazeera": "🟢 الجزيرة", "bbc": "🔴 بي بي سي",
        "aa.com.tr": "🇹🇷 الأناضول", "spa.gov.sa": "🇸🇦 واس السعودية",
        "wam.ae": "🇦🇪 وام الإمارات", "skynewsarabia": "🔵 سكاي عربية"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة")

def get_rss_news(sent_list):
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(requests.get(url, timeout=10).content)
            source_name = get_source_name(url)
            for entry in feed.entries[:5]:
                link = getattr(entry, 'link', '')
                title = getattr(entry, 'title', '')
                # فحص التكرار وفحص الكلمات المفتاحية
                if link not in sent_list and any(k.lower() in (title + getattr(entry, 'summary', '')).lower() for k in KEYWORDS_SYRIA):
                    articles.append({'title': title[:120], 'link': link, 'source': source_name})
                    save_sent_article(link) # حفظه فوراً كمرسل
                    if len(articles) >= 10: break # نكتفي بـ 10 أخبار جديدة
        except: continue
        if len(articles) >= 10: break
    return articles

def main():
    sent_list = load_sent_articles()
    gold_price, dollar_price = get_gold_dollar_prices()
    articles = get_rss_news(sent_list)
    
    if not articles:
        print("📭 لا توجد أخبار جديدة حالياً.")
        return

    now_str = (datetime.utcnow() + timedelta(hours=3)).strftime("%I:%M %p")
    msg = f"<b>🇸🇾 أهم أخبار سوريا (تحديث جديد)</b>\n\n"
    msg += f"<b>💰 الأسعار الآن:</b>\n🪙 ذهب: {gold_price} | 💵 دولار: {dollar_price}\n\n"
    
    for i, art in enumerate(articles, 1):
        msg += f"{i}. <b>{art['title']}</b>\n"
        msg += f"{art['source']} | <a href='{art['link']}'>🔗 التفاصيل</a>\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم التطوير بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "🎓 طلاب كليات الإعلام || FMD"

    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chat_id in TARGET_CHATS:
        requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True})

if __name__ == "__main__":
    main()
