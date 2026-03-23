import os
import time
import random
import logging
import re
import hashlib
import requests
import feedparser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. الإعدادات العامة والسجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"
CACHE_FILE = "translation_cache.txt"
TIMEOUT = 15

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# 2. الكلمات المفتاحية
KEYWORDS_SYRIA = ["سوريا", "Syria", "سوري", "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", "إدلب", "الرقة", "دير الزور", "الحسكة", "السويداء", "درعا", "القنيطرة", "ريف دمشق"]
BREAKING_KEYWORDS = ["عاجل", "Breaking", "انفجار", "اغتيال", "مقتل", "هجوم", "قصف", "غارة", "اشتباكات", "مرسوم", "إقالة", "زلزال", "سقوط", "استهداف", "طيران", "مسيرة", "مفخخة"]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=site:reuters.com+languagedirectory:ar&hl=ar&gl=AE&ceid=AE:ar",
    "https://arabic.rt.com/rss/", "https://www.skynewsarabia.com/rss/middle-east.xml",
    "http://feeds.bbci.co.uk/arabic/rss.xml", "https://www.france24.com/ar/rss",
    "https://arabic.euronews.com/rss?level=vertical&name=news", "https://www.dubaicanvas.ae/feed/",
    "https://www.albayan.ae/rss-feeds-1.2587", "https://www.emaratalyoum.com/rss-feeds-1.2483",
    "https://www.alittihad.ae/rss", "https://www.almayadeen.net/rss",
    "https://www.enabbaladi.net/feed/", "https://alwatan.sy/feed",
    "https://sana.sy/?feed=rss2", "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/", "https://alikhbariah.com/feed/",
    "https://aawsat.com/rss-feed", "https://www.alarabiya.net/.mrss/ar/middle-east.xml"
]

DAILY_WISDOM = ["الخوف من التعب تعب، والإقدام على التعب راحة.", "ليس المهم أن تسير سريعاً، المهم أن تسير في الطريق الصحيح.", "الكلمة الطيبة ليست سهماً، لكنها تخترق القلب.", "لا تنتظر الفرصة، بل اصنعها بنفسك.", "العقل كالمظلة، لا يعمل إلا إذا كان مفتوحاً."]

translation_cache = {}

# 3. الدوال المساعدة (Utility Functions)

def hash_text(text): return hashlib.md5(text.encode()).hexdigest()

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

def load_translation_cache():
    global translation_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    if "|" in line:
                        key, val = line.strip().split("|", 1)
                        translation_cache[key] = val
        except: pass

def translate_text(text):
    try:
        if not re.search(r'[a-zA-Z]', text): return text
        h = hash_text(text)
        if h in translation_cache: return translation_cache[h]
        trans = GoogleTranslator(source='auto', target='ar').translate(text)
        translation_cache[h] = trans
        with open(CACHE_FILE, "a", encoding='utf-8') as f: f.write(f"{h}|{trans}\n")
        return trans
    except: return text

@lru_cache(maxsize=128)
def get_source_name(url):
    srcs = {"reuters": "🇬🇧 رويترز", "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", "enabbaladi": "🍇 عنب بلدي", "alwatan": "📰 الوطن", "rt.com": "🇷🇺 روسيا اليوم", "skynews": "🔵 سكاي نيوز", "bbc": "🔴 BBC", "france24": "🇫🇷 فرانس 24", "almayadeen": "🟠 الميادين", "euronews": "🇪🇺 يورونيوز", "albayan": "🇦🇪 البيان", "alarabiya": "🟩 العربية"}
    return next((v for k, v in srcs.items() if k in url.lower()), "📰 وكالة أنباء")

# 4. دوال جلب البيانات (Data Fetching)

def get_gold_dollar_prices():
    g, d = "1,520,000", "14,900"
    try:
        r = session.get("https://sp-today.com/city/damascus", timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        row = soup.find('tr', id='table_row_usd')
        if row:
            tds = row.find_all('td')
            if len(tds) >= 3: d = tds[2].get_text(strip=True)
        gold_el = soup.find(string=re.compile("الذهب عيار 21"))
        if gold_el:
            m = re.search(r'(\d{1,3}(,\d{3})+)', gold_el.find_parent().get_text())
            if m: g = m.group(1)
        return re.sub(r'[^\d,]', '', g), re.sub(r'[^\d,]', '', d)
    except: return g, d

def get_syria_weather():
    cities = {"Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", "Latakia": "اللاذقية"}
    res = []
    for eng, arb in cities.items():
        try:
            r = session.get(f"https://wttr.in/{eng}?format=%t", timeout=5)
            if r.status_code == 200: res.append(f"• {arb}: <code>{r.text.strip()}</code>")
        except: continue
    return "🌡️ <b>الحرارة:</b> " + "  ".join(res) + "\n\n" if res else ""

def fetch_telegram_channel(user, sent):
    news = []
    try:
        r = session.get(f"https://t.me/s/{user}", timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, 'html.parser')
        msgs = soup.find_all('div', class_='tgme_widget_message_wrap')
        for m in msgs[::-1][:5]:
            txt_div = m.find('div', class_='tgme_widget_message_text')
            if not txt_div: continue
            content = txt_div.get_text(strip=True)
            link = m.find('a', class_='tgme_widget_message_date')['href']
            if link in sent: continue
            if any(k in content for k in KEYWORDS_SYRIA):
                img = None
                img_div = m.find('a', class_='tgme_widget_message_photo_wrap')
                if img_div:
                    style = img_div.get('style', '')
                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                    if match: img = match.group(1)
                news.append({'title': content[:150], 'link': link, 'source': "📺 الإخبارية", 'image': img, 'is_brk': any(bk in content for bk in BREAKING_KEYWORDS)})
    except: pass
    return news

def fetch_feed(url, sent):
    brk, nrm = [], []
    try:
        f = feedparser.parse(session.get(url, timeout=TIMEOUT).content)
        for e in f.entries[:5]:
            link = getattr(e, 'link', '')
            if not link or link in sent: continue
            title = translate_text(getattr(e, 'title', ''))
            if any(k in title for k in KEYWORDS_SYRIA):
                img = None # تبسيطاً للـ RSS
                item = {'title': title, 'link': link, 'source': get_source_name(url), 'image': img}
                if any(bk in title for bk in BREAKING_KEYWORDS): brk.append(item)
                else: nrm.append(item)
    except: pass
    return brk, nrm

# 5. دوال الإرسال (Telegram Sending)

def send_msg(chat, text, img=None, brk=False):
    if img:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": chat, "photo": img, "caption": text[:1024], "parse_mode": "HTML", "disable_notification": not brk}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True, "disable_notification": not brk}
    try: return session.post(url, json=payload, timeout=20).status_code == 200
    except: return False

# 6. الدالة الأساسية (Main)

def main():
    if not BOT_TOKEN or not CHAT_ID: return
    load_translation_cache()
    sent_list = load_sent_articles()
    links_to_save = []

    # جلب الأخبار
    tg_news = fetch_telegram_channel("AlekhbariahSY", sent_list)
    rss_brk, rss_nrm = [], []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(fetch_feed, u, sent_list) for u in RSS_FEEDS]
        for f in as_completed(futures):
            b, n = f.result()
            rss_brk.extend(b); rss_nrm.extend(n)

    # معالجة العاجل
    for b in (tg_news + rss_brk):
        if b.get('is_brk') or any(bk in b['title'] for bk in BREAKING_KEYWORDS):
            m = f"🚨 <b>خبر عاجل</b>\n\n📰 {b['title']}\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
            for c in TARGET_CHATS:
                if send_msg(c, m, img=b.get('image'), brk=True):
                    links_to_save.append(b['link'])

    # معالجة الموجز
    if rss_nrm:
        g, d = get_gold_dollar_prices()
        weather = get_syria_weather()
        t = (datetime.utcnow() + timedelta(hours=3)).strftime('%Y/%m/%d')
        msg = f"<b>🇸🇾 موجز الشارع السوري</b>\n📅 {t}\n──━━━━──\n\n{weather}"
        msg += f"<b>💰 الأسعار:</b>\n💵 دولار: <code>{d}</code> | 🪙 ذهب21: <code>{g}</code>\n\n<b>📰 أهم الأنباء:</b>\n"
        for i, a in enumerate(rss_nrm[:12], 1):
            msg += f"{i}️⃣ {a['title']}\n└ {a['source']} | <a href='{a['link']}'>🔗 التفاصيل</a>\n\n"
        msg += "──━━━━──\n<b>تطوير: محمد محمد جلال الخطيب</b>"
        for c in TARGET_CHATS:
            if send_msg(c, msg):
                for a in rss_nrm[:12]: links_to_save.append(a['link'])

    save_sent_articles(links_to_save)

if __name__ == "__main__":
    main()
