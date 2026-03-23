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

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# المتغيرات البيئية
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"
CACHE_FILE = "translation_cache.txt"
TIMEOUT = 15

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق"
]

BREAKING_KEYWORDS = [
    "عاجل", "Breaking", "Urgent", "فوري", "Alert",
    "انفجار", "اغتيال", "مقتل", "هجوم", "قصف", "غارة", 
    "اشتباكات", "مرسوم", "إقالة", "زلزال", "هزة أرضية",
    "سقوط", "استهداف", "طيران", "مسيرة", "مفخخة"
]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=site:reuters.com+languagedirectory:ar&hl=ar&gl=AE&ceid=AE:ar",
    "https://arabic.rt.com/rss/",
    "https://www.skynewsarabia.com/rss/middle-east.xml",
    "http://feeds.bbci.co.uk/arabic/rss.xml",
    "https://www.france24.com/ar/rss",
    "https://arabic.euronews.com/rss?level=vertical&name=news",
    "https://www.dubaicanvas.ae/feed/",
    "https://www.albayan.ae/rss-feeds-1.2587",
    "https://www.emaratalyoum.com/rss-feeds-1.2483",
    "https://www.alittihad.ae/rss",
    "https://www.enabbaladi.net/feed/",
    "https://alwatan.sy/feed",
    "https://sana.sy/?feed=rss2",
    "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/",
    "https://alikhbariah.com/feed/",
    "https://aawsat.com/rss-feed",
    "https://www.alarabiya.net/.mrss/ar/middle-east.xml"
]

DAILY_WISDOM = [
    "الخوف من التعب تعب، والإقدام على التعب راحة.",
    "ليس المهم أن تسير سريعاً، المهم أن تسير في الطريق الصحيح.",
    "الكلمة الطيبة ليست سهماً، لكنها تخترق القلب.",
    "النجاح ليس عدم فعل الأخطاء، النجاح هو عدم تكرار نفس الخطأ مرتين.",
    "لا تنتظر الفرصة، بل اصنعها بنفسك.",
    "العقل كالمظلة، لا يعمل إلا إذا كان مفتوحاً."
]

translation_cache = {}

def hash_text(text): return hashlib.md5(text.encode()).hexdigest()

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
            with open(DB_FILE, "r", encoding='utf-8') as f: return set(f.read().splitlines())
        except: pass
    return set()

def save_sent_articles(links_list):
    if not links_list: return
    try:
        with open(DB_FILE, "a", encoding='utf-8') as f:
            for link in links_list: f.write(link + "\n")
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
        "reuters.com": "🇬🇧 رويترز", "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", 
        "enabbaladi": "🍇 عنب بلدي", "alwatan.sy": "📰 الوطن", "syriasteps": "🇸🇾 سيريا ستيبس", 
        "arabic.rt.com": "🇷🇺 روسيا اليوم", "skynewsarabia": "🔵 سكاي نيوز", "bbci.co.uk": "🔴 BBC", 
        "france24.com": "🇫🇷 فرانس 24", "aawsat": "🗞️ الشرق الأوسط", 
        "alarabiya": "🟩 العربية", "euronews": "🇪🇺 يورونيوز", "albayan": "🇦🇪 البيان", 
        "emaratalyoum": "🇦🇪 الإمارات اليوم", "alittihad": "🇦🇪 الاتحاد"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة أنباء")

def get_image_url(entry):
    try:
        if 'media_content' in entry and len(entry.media_content) > 0:
            return entry.media_content[0].get('url')
        if 'links' in entry:
            for link in entry.links:
                if 'image' in link.get('type', ''): return link.get('href')
        if 'summary' in entry:
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img = soup.find('img')
            if img: return img.get('src')
    except: pass
    return None

def fetch_feed(feed_url, sent_list):
    breaking, normal = [], []
    try:
        response = session.get(feed_url, timeout=TIMEOUT)
        feed = feedparser.parse(response.content)
        source = get_source_name(feed_url)
        for entry in feed.entries[:8]:
            try:
                link = getattr(entry, 'link', '')
                if not link or link in sent_list: continue
                title_ar = translate_text(getattr(entry, 'title', ''))
                summary = getattr(entry, 'summary', '')[:100]
                full_txt = f"{title_ar} {summary}".lower()
                if any(k.lower() in full_txt for k in KEYWORDS_SYRIA):
                    img_url = get_image_url(entry)
                    data = {'title': title_ar[:125].strip(), 'link': link, 'source': source, 'image': img_url}
                    if any(bk.lower() in full_txt for bk in BREAKING_KEYWORDS): breaking.append(data)
                    else: normal.append(data)
            except: continue
    except: pass
    return breaking, normal

def get_rss_news_parallel(sent_list):
    breaking_all, normal_all = [], []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_feed, url, sent_list): url for url in RSS_FEEDS}
        for future in as_completed(futures):
            try:
                b, n = future.result()
                breaking_all.extend(b)
                normal_all.extend(n)
            except: pass
    return breaking_all, normal_all[:15]

def get_syria_weather():
    report = "🌡️ <b>درجات الحرارة المتوقعة:</b>\n"
    cities = {"Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", "Latakia": "اللاذقية", "Daraa": "درعا", "Deir ez-Zor": "دير الزور"}
    weather_results = {}
    def fetch_weather(c_eng):
        try:
            r = session.get(f"https://wttr.in/{c_eng}?format=%t", timeout=5)
            if r.status_code == 200: return c_eng, f"• {cities[c_eng]}: <code>{r.text.strip().replace('+', '')}</code>"
        except: pass
        return c_eng, None
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(fetch_weather, c) for c in cities.keys()]
        for f in as_completed(futures):
            ce, res = f.result()
            if res: weather_results[ce] = res
    ordered = [weather_results[c] for c in cities.keys() if c in weather_results]
    if ordered:
        report += "  ".join(ordered[:3]) + "\n" + "  ".join(ordered[3:]) + "\n\n"
        return report
    return ""

def get_gold_dollar_prices():
    """ استخراج الأسعار من موقع 'الليرة اليوم' بدقة """
    gold, dollar = "1,435,000", "12,000" # قيم افتراضية
    try:
        r = session.get("https://sp-today.com/city/damascus", timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # جلب سعر الدولار (نبحث عن السطر الذي يحتوي USD)
        usd_row = soup.find('tr', id='table_row_usd') or soup.find('td', string=re.compile('USD'))
        if usd_row:
            prices = usd_row.find_parent('tr').find_all('td')
            if len(prices) >= 3:
                dollar = prices[2].get_text(strip=True) # مبيع الدولار يكون عادة في العمود الثالث

        # جلب سعر الذهب عيار 21
        gold_section = soup.find(string=re.compile("الذهب عيار 21"))
        if gold_section:
            # نبحث عن أول رقم كبير (6 خانات فما فوق) في النص المجاور
            p_text = gold_section.find_parent().get_text()
            match = re.search(r'(\d{1,3}(,\d{3})+)', p_text)
            if match: gold = match.group(1)
            
        return re.sub(r'[^\d,]', '', gold), re.sub(r'[^\d,]', '', dollar)
    except: return gold, dollar

def send_telegram(chat_id, message, is_breaking=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True, "disable_notification": not is_breaking}
    try: return session.post(url, json=payload, timeout=15).status_code == 200
    except: return False

def send_telegram_photo(chat_id, message, image_url, is_breaking=True):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": image_url, "caption": message[:1024], "parse_mode": "HTML", "disable_notification": not is_breaking}
    try: return session.post(url, json=payload, timeout=20).status_code == 200
    except: return False

def main():
    if not BOT_TOKEN or not CHAT_ID: return
    load_translation_cache()
    sent_list = load_sent_articles()
    breaking_news, normal_news = get_rss_news_parallel(sent_list)
    links_to_save = []

    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS:
            success = send_telegram_photo(cid, msg, b['image']) if b.get('image') else False
            if not success: success = send_telegram(cid, msg, is_breaking=True)
            if success and b['link'] not in links_to_save: links_to_save.append(b['link'])
    
    if normal_news:
        hijri, weather_p, (gold_p, dollar_p) = get_hijri_date(), get_syria_weather(), get_gold_dollar_prices()
        damascus_time = datetime.utcnow() + timedelta(hours=3)
        msg = f"<b>🇸🇾 موجز الشارع السوري</b>\n📅 {damascus_time.strftime('%Y/%m/%d')} | {hijri}\n✨ <i>\"{random.choice(DAILY_WISDOM)}\"</i>\n───━━━━─━━━━───\n\n"
        if weather_p: msg += weather_p
        msg += f"<b>💰 أسعار الصرف والذهب (دمشق):</b>\n💵 الدولار: <code>{dollar_p}</code> ل.س\n🪙 الذهب ع21: <code>{gold_p}</code> ل.س\n\n<b>📰 أهم الأنباء:</b>\n"
        for i, art in enumerate(normal_news, 1):
            msg += f"{i}️⃣ <b>{art['title']}</b>\n└ {art['source']} | <a href='{art['link']}'>🔗 التفاصيل</a>\n\n"
        msg += "───━━━━─━━━━───\n<b>تطوير : محمد محمد جلال الخطيب - طلاب كليات الإعلام ||FMD</b>"
        for cid in TARGET_CHATS:
            if send_telegram(cid, msg) and not links_to_save:
                for art in normal_news: links_to_save.append(art['link'])

    save_sent_articles(links_to_save)

if __name__ == "__main__": main()
