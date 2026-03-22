import os
import time
import random
import logging
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib
import requests
import feedparser
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# إعداد السجلات (Logs)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"
CACHE_FILE = "translation_cache.txt"
TIMEOUT = 12

# إنشاء session للاتصالات المتكررة (أداء أفضل)
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# الكلمات المفتاحية للفلترة (سوريا)
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق"
]

BREAKING_KEYWORDS = ["عاجل", "Breaking", "Urgent", "فوري", "Alert"]

# مصادر الأخبار المختارة بعناية (الأكثر غزارة واستقراراً)
RSS_FEEDS = [
    "https://arabic.rt.com/rss/",  # روسيا اليوم
    "https://www.skynewsarabia.com/rss/middle-east.xml",  # سكاي نيوز
    "http://feeds.bbci.co.uk/arabic/rss.xml",  # BBC عربي
    "https://www.france24.com/ar/rss",  # فرانس 24 عربي
    "https://arabic.euronews.com/rss?level=vertical&name=news",  # يورونيوز عربي
    "https://www.dubaicanvas.ae/feed/", # دبي (أخبار عامة/منوعة)
    "https://www.albayan.ae/rss-feeds-1.2587", # البيان الإماراتية (دبي)
    "https://www.emaratalyoum.com/rss-feeds-1.2483", # الإمارات اليوم (دبي)
    "https://www.alittihad.ae/rss", # الاتحاد (أبوظبي)
    "https://www.enabbaladi.net/feed/",  # عنب بلدي
    "https://alwatan.sy/feed",  # جريدة الوطن السورية
    "https://sana.sy/?feed=rss2",  # سانا
    "https://www.syria.tv/feed",  # تلفزيون سوريا
    "https://syriasteps.com/feed/",  # سيريا ستيبس
    "https://alikhbariah.com/feed/",  # الإخبارية
    "https://aawsat.com/rss-feed",  # الشرق الأوسط
    "https://www.alarabiya.net/.mrss/ar/middle-east.xml" # العربية
]

DAILY_WISDOM = [
    "الخوف من التعب تعب، والإقدام على التعب راحة.",
    "ليس المهم أن تسير سريعاً، المهم أن تسير في الطريق الصحيح.",
    "الكلمة الطيبة ليست سهماً، لكنها تخترق القلب.",
    "النجاح ليس عدم فعل الأخطاء، النجاح هو عدم تكرار نفس الخطأ مرتين.",
    "لا تنتظر الفرصة، بل اصنعها بنفسك.",
    "من أراد النجاح في هذا العالم عليه أن يتغلب على أسس الفقر الثلاثة: النوم، والتراخي، والخوف.",
    "العقل كالمظلة، لا يعمل إلا إذا كان مفتوحاً."
]

translation_cache = {}

def hash_text(text):
    return hashlib.md5(text.encode()).hexdigest()

def load_translation_cache():
    global translation_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    if "|" in line:
                        key, value = line.strip().split("|", 1)
                        translation_cache[key] = value
        except: pass

def save_translation_to_cache(text, translation):
    key = hash_text(text)
    translation_cache[key] = translation
    try:
        with open(CACHE_FILE, "a", encoding='utf-8') as f:
            f.write(f"{key}|{translation}\n")
    except: pass

def get_hijri_date():
    try:
        r = session.get("http://api.aladhan.com/v1/gToH", params={"date": datetime.now().strftime("%d-%m-%Y")}, timeout=5)
        if r.status_code == 200:
            data = r.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']} هـ"
    except: pass
    return ""

def load_sent_articles():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f: 
                return set(f.read().splitlines())
        except: pass
    return set()

def save_sent_articles(links_list):
    if not links_list: return
    try:
        with open(DB_FILE, "a", encoding='utf-8') as f:
            for link in links_list:
                f.write(link + "\n")
    except: pass

def translate_text(text):
    try:
        if not re.search(r'[a-zA-Z]', text): return text
        text_hash = hash_text(text)
        if text_hash in translation_cache: return translation_cache[text_hash]
        translation = GoogleTranslator(source='auto', target='ar').translate(text)
        save_translation_to_cache(text, translation)
        return translation
    except: return text

@lru_cache(maxsize=128)
def get_source_name(url):
    sources = {
        "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", "enabbaladi": "🍇 عنب بلدي",
        "alwatan.sy": "📰 الوطن السورية", "syriasteps": "🇸🇾 سيريا ستيبس", "arabic.rt.com": "🇷🇺 روسيا اليوم",
        "skynewsarabia": "🔵 سكاي نيوز", "bbci.co.uk": "🔴 BBC عربي", "france24.com": "🇫🇷 فرانس 24",
         "aawsat": "🗞️ الشرق الأوسط", "alarabiya": "🟩 العربية",
        "euronews": "🇪🇺 يورونيوز", "albayan": "🇦🇪 البيان (دبي)", "emaratalyoum": "🇦🇪 الإمارات اليوم",
        "alittihad": "🇦🇪 الاتحاد (أبوظبي)"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة أنباء")

def fetch_feed(feed_url, sent_list):
    breaking, normal = [], []
    try:
        response = session.get(feed_url, timeout=TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        source = get_source_name(feed_url)
        
        for entry in feed.entries[:8]:
            try:
                link = getattr(entry, 'link', '')
                if not link or link in sent_list: continue
                
                title_or = getattr(entry, 'title', '')
                if not title_or: continue
                
                title_ar = translate_text(title_or)
                summary = getattr(entry, 'summary', '')[:100]
                full_txt = f"{title_or} {title_ar} {summary}".lower()
                
                if any(k.lower() in full_txt for k in KEYWORDS_SYRIA):
                    data = {'title': title_ar[:125].strip(), 'link': link, 'source': source}
                    if any(bk.lower() in full_txt for bk in BREAKING_KEYWORDS):
                        breaking.append(data)
                    else:
                        normal.append(data)
            except: continue
    except: pass
    return breaking, normal

def get_rss_news_parallel(sent_list):
    breaking_all, normal_all = [], []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_feed, url, sent_list): url for url in RSS_FEEDS}
        for future in as_completed(futures):
            try:
                breaking, normal = future.result()
                breaking_all.extend(breaking)
                normal_all.extend(normal)
                if len(normal_all) >= 15: break # رفعنا سقف الأخبار قليلاً
            except: pass
    return breaking_all, normal_all[:15]

def get_syria_weather():
    report = "🌡️ <b>درجات الحرارة المتوقعة:</b>\n"
    cities = {"Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", "Latakia": "اللاذقية", "Daraa": "درعا", "Deir ez-Zor": "دير الزور"}
    weather_results = {}

    def fetch_weather(city_eng):
        try:
            url = f"https://wttr.in/{city_eng}?format=%t"
            r = session.get(url, timeout=5)
            if r.status_code == 200:
                temp = r.text.strip().replace('+', '')
                return city_eng, f"• {cities[city_eng]}: <code>{temp}</code>"
        except: pass
        return city_eng, None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_weather, city) for city in cities.keys()]
        for future in as_completed(futures):
            city_eng, result = future.result()
            if result: weather_results[city_eng] = result

    ordered_lines = [weather_results[c] for c in cities.keys() if c in weather_results]
    
    if ordered_lines:
        if len(ordered_lines) >= 6:
            report += "  ".join(ordered_lines[:3]) + "\n"
            report += "  ".join(ordered_lines[3:]) + "\n\n"
        else:
            report += "  ".join(ordered_lines) + "\n\n"
        return report
    return ""

def get_gold_dollar_prices():
    try:
        r = session.get("https://sp-today.com/en", timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        gold_match = re.search(r'1[,\d]{6,9}', text)
        dollar_match = re.search(r'1[1-2],\d{3}', text)
        gold = gold_match.group(0) if gold_match else "1,517,000"
        dollar = dollar_match.group(0) if dollar_match else "11,950"
        return gold, dollar
    except: return "1,517,000", "11,950"

def send_telegram(chat_id, message, is_breaking=False):
    if not chat_id: return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True, "disable_notification": not is_breaking}
    try:
        r = session.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except: return False

def main():
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("البيانات الأساسية ناقصة!")
        return
    
    load_translation_cache()
    sent_list = load_sent_articles()
    
    logging.info("بدء جلب الأخبار...")
    breaking_news, normal_news = get_rss_news_parallel(sent_list)
    links_to_save = []

    # 1. الأخبار العاجلة
    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, is_breaking=True):
                if b['link'] not in links_to_save: links_to_save.append(b['link'])
    
    # 2. النشرة الدورية
    if normal_news:
        hijri = get_hijri_date()
        wisdom = random.choice(DAILY_WISDOM)
        weather_p = get_syria_weather()
        gold_p, dollar_p = get_gold_dollar_prices()
        damascus_time = datetime.utcnow() + timedelta(hours=3)

        msg = f"<b>🇸🇾 موجز الشارع السوري</b>\n"
        msg += f"📅 {damascus_time.strftime('%Y/%m/%d')} | {hijri}\n"
        msg += f"✨ <i>\"{wisdom}\"</i>\n"
        msg += "───━━━━─━━━━───\n\n"
        
        if weather_p: msg += weather_p
        
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
            if send_telegram(cid, msg, is_breaking=False): success = True
        
        if success:
            for art in normal_news:
                if art['link'] not in links_to_save: links_to_save.append(art['link'])

    save_sent_articles(links_to_save)
    logging.info("تم إنهاء النشرة بنجاح.")

if __name__ == "__main__":
    main()
