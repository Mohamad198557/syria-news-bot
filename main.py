import os
import time
import random
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

# مصادر الأخبار كاملة
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

# حكم يومية منوعة
DAILY_WISDOM = [
    "الخوف من التعب تعب، والإقدام على التعب راحة.",
    "ليس المهم أن تسير سريعاً، المهم أن تسير في الطريق الصحيح.",
    "الكلمة الطيبة ليست سهماً، لكنها تخترق القلب.",
    "النجاح ليس عدم فعل الأخطاء، النجاح هو عدم تكرار نفس الخطأ مرتين.",
    "لا تنتظر الفرصة، بل اصنعها بنفسك.",
    "من أراد النجاح في هذا العالم عليه أن يتغلب على أسس الفقر الثلاثة: النوم، والتراخي، والخوف.",
    "العقل كالمظلة، لا يعمل إلا إذا كان مفتوحاً."
]

def get_hijri_date():
    """جلب التاريخ الهجري بدقة عبر API"""
    try:
        r = requests.get("http://api.aladhan.com/v1/gToH", params={"date": datetime.now().strftime("%d-%m-%Y")}, timeout=5)
        if r.status_code == 200:
            data = r.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']} هـ"
    except: pass
    return ""

def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding='utf-8') as f: 
            return set(f.read().splitlines())
    return set()

def save_sent_articles(links_list):
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
    """جلب الطقس للمحافظات المحددة بتنسيق رشيق وأفقي"""
    report = "🌤️ <b>حالة الطقس المتوقعة:</b>\n"
    cities = {
        "Damascus": "دمشق", 
        "Aleppo": "حلب", 
        "Homs": "حمص", 
        "Latakia": "اللاذقية", 
        "Daraa": "درعا", 
        "Deir ez-Zor": "دير الزور"
    }
    try:
        weather_lines = []
        for eng, arb in cities.items():
            url = f"https://wttr.in/{eng}?format=%c%t"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                temp_info = r.text.strip().replace('+', '')
                weather_lines.append(f"• {arb}: <code>{temp_info}</code>")
        
        # تقسيم المدن إلى سطرين لجعل الرسالة "أرشق"
        if len(weather_lines) >= 6:
            report += "  ".join(weather_lines[:3]) + "\n"
            report += "  ".join(weather_lines[3:]) + "\n\n"
        else:
            report += "  ".join(weather_lines) + "\n\n"
        return report
    except: return ""

def get_gold_dollar_prices():
    try:
        r = requests.get("https://sp-today.com/en", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        gold = re.findall(r'1[,\\d]{6,9}', text)
        dollar = re.findall(r'1[1-2],\\d{3}', text)
        return (gold[0] if gold else "1,517,000"), (dollar[0] if dollar else "11,950")
    except: return "1,517,000", "11,950"

def get_source_name(url):
    """استخراج اسم المصدر مع إيموجي مميز"""
    sources = {"sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", "aljazeera": "🟢 الجزيرة", "bbc": "🔴 BBC", "guardian": "🟠 الغارديان", "nytimes": "🇺🇸 نيويورك تايمز", "aa.com.tr": "🇹🇷 الأناضول", "skynewsarabia": "🔵 سكاي عربية", "france24": "🇫🇷 فرانس 24", "rt": "🇷🇺 روسيا اليوم"}
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة أنباء")

def get_rss_news(sent_list):
    """جلب الأخبار وفصل العاجل عن العادي"""
    breaking, normal = [], []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(requests.get(url, timeout=10).content)
            source = get_source_name(url)
            for entry in feed.entries[:8]:
                link = getattr(entry, 'link', '')
                if link in sent_list: continue
                
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
        except Exception as e: 
            logging.warning(f"Error fetching from {url}: {e}")
            continue
    return breaking, normal[:12]

def send_telegram(chat_id, message, is_breaking=False):
    """إرسال الرسالة مع التحكم في كتم/تفعيل التنبيهات بناءً على نوع الخبر"""
    if not chat_id: return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True, 
        "disable_notification": not is_breaking # التنبيه مفعل فقط للعاجل
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except: return False

def main():
    if not BOT_TOKEN or not CHAT_ID: 
        logging.error("BOT_TOKEN or CHAT_ID is missing!")
        return
    
    sent_list = load_sent_articles()
    breaking_news, normal_news = get_rss_news(sent_list)
    links_to_save = []

    # 1. إرسال الأخبار العاجلة (فصل كل خبر برسالة لضمان التنبيه)
    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, is_breaking=True):
                if b['link'] not in links_to_save:
                    links_to_save.append(b['link'])
    
    # 2. إرسال النشرة العادية الشاملة والمزينة
    if normal_news:
        hijri = get_hijri_date()
        wisdom = random.choice(DAILY_WISDOM)
        weather_p = get_syria_weather()
        gold_p, dollar_p = get_gold_dollar_prices()
        damascus_time = (datetime.utcnow() + timedelta(hours=3))

        msg = f"<b>🇸🇾 موجز الشارع السوري</b>\n"
        msg += f"📅 {damascus_time.strftime('%Y/%m/%d')} | {hijri}\n"
        msg += f"✨ <i>\"{wisdom}\"</i>\n"
        msg += "───━━━━─━━━━───\n\n"
        
        msg += weather_p
        
        msg += f"<b>💰 أسعار الصرف والذهب (دمشق):</b>\n"
        msg += f"💵 الدولار: <code>{dollar_p}</code> ل.س\n"
        msg += f"🪙 الذهب ع21: <code>{gold_p}</code> ل.س\n\n"
        
        msg += "<b>📰 أهم الأنباء المحلية والدولية:</b>\n"
        for i, art in enumerate(normal_news, 1):
            msg += f"{i}️⃣ <b>{art['title']}</b>\n└ {art['source']} | <a href='{art['link']}'>🔗 التفاصيل</a>\n\n"
        
        msg += "───━━━━─━━━━───\n"
        msg += "<b>تطوير : محمد محمد جلال الخطيب - طلاب كليات الإعلام ||FMD</b>"

        success = False
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, is_breaking=False):
                success = True
        
        if success:
            for art in normal_news:
                if art['link'] not in links_to_save:
                    links_to_save.append(art['link'])

    # حفظ الروابط لتجنب التكرار
    save_sent_articles(links_to_save)

if __name__ == "__main__":
    main()
