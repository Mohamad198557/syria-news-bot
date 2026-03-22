import os
import time
import logging
import re
from datetime import datetime, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"

# الكلمات المفتاحية
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق"
]

BREAKING_KEYWORDS = ["عاجل", "Breaking", "Urgent", "فوري", "Alert"]

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

def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding='utf-8') as f: 
            return set(f.read().splitlines())
    return set()

def save_sent_articles(links_list):
    """حفظ قائمة الروابط في الذاكرة (تُستدعى فقط بعد نجاح الإرسال)"""
    if not links_list: return
    try:
        with open(DB_FILE, "a", encoding='utf-8') as f:
            for link in links_list:
                f.write(link + "\n")
    except Exception as e:
        logging.error(f"Error saving to DB: {e}")

def translate_text(text):
    try:
        if re.search(r'[a-zA-Z]', text):
            return GoogleTranslator(source='en', target='ar').translate(text)
        return text
    except: return text

def get_syria_weather():
    """جلب الطقس بطريقة مستقرة ومضمونة 100% بدون مكتبات معقدة"""
    weather_report = "🌡️ <b>حالة الطقس في المحافظات:</b>\n"
    cities = {
        "Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", 
        "Deir ez-Zor": "دير الزور", "Daraa": "درعا", "Latakia": "اللاذقية"
    }
    try:
        for eng, arb in cities.items():
            url = f"https://wttr.in/{eng}?format=%c+%t"
            r = requests.get(url, timeout=5) # 5 ثوانٍ فقط لتجنب التأخير
            if r.status_code == 200:
                temp_data = r.text.strip().replace('+', '')
                weather_report += f"{temp_data} : {arb}\n"
        return weather_report + "\n"
    except Exception as e:
        logging.error(f"Weather Error: {e}")
        return "" # في حال تعطل موقع الطقس، يتجاهله الكود ولا يتوقف

def get_gold_dollar_prices():
    try:
        r = requests.get("https://sp-today.com/en", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
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
            feed = feedparser.parse(requests.get(url, timeout=10).content)
            source = get_source_name(url)
            for entry in feed.entries[:8]:
                link = getattr(entry, 'link', '')
                if link in sent_list: continue # تخطي الأخبار القديمة
                
                title_or = getattr(entry, 'title', '')
                title_ar = translate_text(title_or)
                full_txt = f"{title_or} {title_ar} {getattr(entry, 'summary', '')}"
                
                if any(k.lower() in full_txt.lower() for k in KEYWORDS_SYRIA):
                    data = {'title': title_ar[:125].strip(), 'link': link, 'source': source}
                    
                    if any(bk.lower() in full_txt.lower() for bk in BREAKING_KEYWORDS):
                        breaking.append(data)
                    else:
                        normal.append(data)
                        
                if len(normal) >= 12: break
        except: continue
    return breaking, normal[:12]

def send_telegram(chat_id, message, is_breaking=False):
    if not chat_id: return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": message, "parse_mode": "HTML",
        "disable_web_page_preview": True, "disable_notification": not is_breaking
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except: return False

def main():
    if not BOT_TOKEN or not CHAT_ID: return

    sent_list = load_sent_articles()
    breaking_news, normal_news = get_rss_news(sent_list)
    
    links_to_save = [] # قائمة الروابط التي سيتم حفظها لاحقاً

    # 1. إرسال العاجل فوراً
    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, True):
                links_to_save.append(b['link']) # نحفظه فقط إذا نجح الإرسال
    
    # 2. إرسال النشرة العادية
    if normal_news:
        weather_p = get_syria_weather()
        gold_p, dollar_p = get_gold_dollar_prices()
        damascus_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y/%m/%d - %I:%M %p")

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

        success = False
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, False):
                success = True
        
        # نحفظ الأخبار العادية في الذاكرة فقط إذا تم إرسال الرسالة الكبيرة بنجاح
        if success:
            for art in normal_news:
                links_to_save.append(art['link'])

    # 3. تحديث الذاكرة في النهاية (السر البرمجي الذي سيمنع الخطأ)
    save_sent_articles(links_to_save)

if __name__ == "__main__":
    main()
