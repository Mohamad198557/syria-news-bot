import os
import time
import logging
import re
import asyncio
import python_weather
from datetime import datetime, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# إعداد السجلات لمتابعة الأداء
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# الثوابت الرئيسية
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"

# الكلمات المفتاحية شاملة
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق"
]

BREAKING_KEYWORDS = ["عاجل", "Breaking", "Urgent", "فوري", "Alert"]

# ترتيب المصادر: دولي -> عربي -> سوري في النهاية
RSS_FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://trt.global/arabi/rss/",
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories",
    "https://www.euronews.com/rss.xml",
    "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://www.spa.gov.sa/rss",
    "https://www.wam.ae/ar/rss",
    "https://www.qna.org.qa/rss",
    "https://www.kuna.net.kw/rss/",
    "https://ina.iq/rss/",
    "https://aawsat.com/rss-feed",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/",
    "https://alikhbariah.com/feed/",
    "https://sana.sy/?feed=rss2"
]

def translate_text(text):
    """ترجمة العناوين الأجنبية للعربية"""
    try:
        if re.search(r'[a-zA-Z]', text):
            return GoogleTranslator(source='en', target='ar').translate(text)
        return text
    except: return text

async def get_syria_weather():
    """جلب الطقس للمحافظات المطلوبة"""
    weather_report = "🌡️ <b>حالة الطقس في المحافظات:</b>\n"
    # المحافظات المحدثة بناءً على طلبك
    cities = {
        "Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", 
        "Deir ez-Zor": "دير الزور", "Daraa": "درعا", "Latakia": "اللاذقية"
    }
    try:
        async with python_weather.Client(unit=python_weather.METRIC, locale=python_weather.Locale.ARABIC) as client:
            for eng, arb in cities.items():
                w = await client.get(eng)
                desc = w.kind.value
                emoji = "☀️" if "مشمس" in desc else "☁️" if "غائم" in desc else "🌧️" if "مطر" in desc else "🌡️"
                weather_report += f"{emoji} {arb}: {w.temperature}°م\n"
        return weather_report + "\n"
    except: return ""

def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding='utf-8') as f: return set(f.read().splitlines())
    return set()

def save_sent_article(link):
    with open(DB_FILE, "a", encoding='utf-8') as f: f.write(link + "\n")

def get_gold_dollar_prices():
    try:
        r = requests.get("https://sp-today.com/en", headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        gold = re.findall(r'1[,\\d]{6,9}', text)
        dollar = re.findall(r'1[1-2],\\d{3}', text)
        return (gold[0] if gold else "1,484,000"), (dollar[0] if dollar else "11,950")
    except: return "1,484,000", "11,950"

def get_source_name(url):
    sources = {
        "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", "aljazeera": "🟢 الجزيرة",
        "bbc": "🔴 BBC", "guardian": "🟠 الغارديان", "nytimes": "🇺🇸 نيويورك تايمز",
        "aa.com.tr": "🇹🇷 الأناضول", "skynewsarabia": "🔵 سكاي عربية"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة")

def get_rss_news(sent_list):
    breaking, normal = [], []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(requests.get(url, timeout=12).content)
            source = get_source_name(url)
            for entry in feed.entries[:8]:
                link = getattr(entry, 'link', '')
                if link in sent_list: continue
                
                title_or = getattr(entry, 'title', '')
                title_ar = translate_text(title_or)
                full_txt = f"{title_or} {title_ar} {getattr(entry, 'summary', '')}"
                
                if any(k.lower() in full_txt.lower() for k in KEYWORDS_SYRIA):
                    data = {'title': title_ar[:125].strip(), 'link': link, 'source': source}
                    save_sent_article(link)
                    if any(bk.lower() in full_txt.lower() for bk in BREAKING_KEYWORDS):
                        breaking.append(data)
                    else:
                        normal.append(data)
                if len(normal) >= 12: break
        except: continue
    return breaking, normal[:12]

def send_telegram(chat_id, message, is_breaking=False):
    if not chat_id: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": message, "parse_mode": "HTML",
        "disable_web_page_preview": True, "disable_notification": not is_breaking
    }
    requests.post(url, json=payload, timeout=15)

async def main_async():
    sent_list = load_sent_articles()
    breaking_news, normal_news = get_rss_news(sent_list)
    
    # إرسال العاجل فوراً
    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS: send_telegram(cid, msg, True)
    
    if not normal_news and not breaking_news: return

    weather_p = await get_syria_weather()
    gold_p, dollar_p = get_gold_dollar_prices()
    damascus_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y/%m/%d - %I:%M %p")

    # بناء النشرة
    msg = f"<b>🇸🇾 نشرة أخبار سوريا الشاملة</b>\n🗓 <i>{damascus_time}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    msg += weather_p
    msg += f"<b>💰 الأسعار (دمشق):</b>\n🪙 ذهب عيار 21: <code>{gold_p}</code>\n💵 دولار: <code>{dollar_p}</code>\n\n"
    msg += "<b>🔴 آخر المستجدات:</b>\n"
    
    for i, art in enumerate(normal_news, 1):
        msg += f"{i}. <b>{art['title']}</b>\n└ {art['source']} | <a href='{art['link']}'>🔗 الكامل</a>\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم التطوير بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "🎓 طلاب كليات الإعلام || FMD"
    for cid in TARGET_CHATS: send_telegram(cid, msg, False)

def main():
    if BOT_TOKEN and CHAT_ID: asyncio.run(main_async())

if __name__ == "__main__":
    main()
    
    

    
    
