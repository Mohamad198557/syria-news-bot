import os
import time
import random
import logging
import re
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import requests
import feedparser
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
TIMEOUT = 12  # تقليل وقت الانتظار لزيادة السرعة

# تسريع الاتصالات عبر إبقاء الجلسة مفتوحة
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# 2. الكلمات المفتاحية الموسعة (الأكبر على الإطلاق)
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الرئيس السوري", "الأسد",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق", "الجولان", "Golan", 
    "البادية السورية", "قسد", "الجيش السوري", "SDF"
]

BREAKING_KEYWORDS = [
    "عاجل", "Breaking", "Urgent", "فوري", "Alert", "انفجار", "اغتيال", 
    "مقتل", "هجوم", "قصف", "غارة", "اشتباكات", "مرسوم", "إقالة", 
    "زلزال", "هزة", "سقوط", "استهداف", "طيران", "مسيرة", "مفخخة"
]

# 3. المصادر الشاملة (34 مصدر + قناة تليجرام يتم معالجتها منفصلة)
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=site:reuters.com+languagedirectory:ar&hl=ar&gl=AE&ceid=AE:ar",
    "https://www.aljazeera.com/xml/rss/all.xml", "https://www.alarabiya.net/.mrss/ar.xml",
    "https://arabic.rt.com/rss/", "https://www.france24.com/ar/rss",
    "https://www.aa.com.tr/ar/rss/default.aspx", "https://www.skynewsarabia.com/rss/latest.xml",
    "https://www.skynewsarabia.com/rss/world.xml", "https://www.addustour.com/RSS.aspx",
    "https://www.independentarabia.com/ar/rss.xml", "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/", "https://alikhbariah.com/feed/",
    "https://sana.sy/?feed=rss2", "https://www.enabbaladi.net/archives/category/news/feed",
    "https://all4syria.info/feed", "https://www.zamanalwsl.net/rss.xml",
    "https://arabic.reuters.com/rss", "http://www.bbc.co.uk/arabic/rss.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml", "https://apnews.com/rss",
    "http://rss.cnn.com/rss/edition_world.rss", "https://feeds.washingtonpost.com/rss/world",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://aawsat.com/rss-feed", "https://www.dw.com/ar/rss-eco",
    "https://www.guardian.co.uk/world/rss", "https://www.euronews.com/rss.xml",
    "https://ina.iq/rss/", "https://trt.global/arabi/rss/",
    "https://www.spa.gov.sa/rss", "https://www.wam.ae/ar/rss",
    "https://www.qna.org.qa/rss", "https://www.kuna.net.kw/rss/"
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

# 4. دوال الذاكرة والترجمة والطقس
def hash_text(text): return hashlib.md5(text.encode()).hexdigest()

def load_cache():
    global translation_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    if "|" in line:
                        k, v = line.strip().split("|", 1)
                        translation_cache[k] = v
        except: pass

def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding='utf-8') as f: return set(f.read().splitlines())
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
        h = hash_text(text)
        if h in translation_cache: return translation_cache[h]
        t = GoogleTranslator(source='auto', target='ar').translate(text)
        translation_cache[h] = t
        with open(CACHE_FILE, "a", encoding='utf-8') as f: f.write(f"{h}|{t}\n")
        return t
    except: return text

def get_hijri_date():
    try:
        r = session.get("http://api.aladhan.com/v1/gToH", params={"date": datetime.now().strftime("%d-%m-%Y")}, timeout=5)
        if r.status_code == 200:
            d = r.json()['data']['hijri']
            return f"{d['day']} {d['month']['ar']} {d['year']} هـ"
    except: pass
    return ""

def get_syria_weather():
    report = "🌡️ <b>الطقس اليوم:</b>\n"
    cities = {"Damascus": "دمشق", "Aleppo": "حلب", "Homs": "حمص", "Latakia": "اللاذقية", "Deir ez-Zor": "دير الزور"}
    try:
        lines = []
        for eng, arb in cities.items():
            r = session.get(f"https://wttr.in/{eng}?format=%t", timeout=5)
            if r.status_code == 200: lines.append(f"• {arb}: <code>{r.text.strip().replace('+','')}</code>")
        if lines:
            return report + "  ".join(lines[:3]) + "\n" + "  ".join(lines[3:]) + "\n\n"
    except: pass
    return ""

# 5. دوال استخراج الأخبار (التليجرام والـ RSS)
@lru_cache(maxsize=128)
def get_source_name(url):
    srcs = {
        "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا", "aljazeera": "🟢 الجزيرة", "bbc": "🔴 BBC", 
        "skynewsarabia": "🔵 سكاي عربية", "france24": "🇫🇷 فرانس 24", "rt.com": "🇷🇺 روسيا اليوم", 
        "enabbaladi": "🍇 عنب بلدي", "reuters": "🇬🇧 رويترز", "alarabiya": "🟩 العربية", 
        "aa.com.tr": "🇹🇷 الأناضول", "nytimes": "🇺🇸 نيويورك تايمز", "washingtonpost": "🇺🇸 واشنطن بوست",
        "cnn": "🇺🇸 CNN", "dw.com": "🇩🇪 DW", "aawsat": "🗞️ الشرق الأوسط", "alikhbariah": "📺 الإخبارية"
    }
    return next((name for key, name in srcs.items() if key in url.lower()), "📰 وكالة أنباء")

def get_image_url(entry):
    """استخراج رابط الصورة من الخبر للـ RSS"""
    try:
        if 'media_content' in entry and len(entry.media_content) > 0: return entry.media_content[0].get('url')
        if 'links' in entry:
            for link in entry.links:
                if 'image' in link.get('type', ''): return link.get('href')
        if 'summary' in entry:
            img = BeautifulSoup(entry.summary, 'html.parser').find('img')
            if img: return img.get('src')
    except: pass
    return None

def fetch_telegram_channel(user, sent):
    """قشط سريع لقناة الإخبارية على تليجرام"""
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
            
            if any(k.lower() in content.lower() for k in KEYWORDS_SYRIA):
                img = None
                img_div = m.find('a', class_='tgme_widget_message_photo_wrap')
                if img_div:
                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", img_div.get('style', ''))
                    if match: img = match.group(1)
                news.append({'title': content[:150], 'link': link, 'source': "📺 الإخبارية (TG)", 'image': img, 'is_brk': any(bk in content for bk in BREAKING_KEYWORDS)})
    except: pass
    return news

def fetch_feed(url, sent_list):
    """جلب أخبار الـ RSS مع الترجمة والصور"""
    brk, nrm = [], []
    try:
        f = feedparser.parse(session.get(url, timeout=TIMEOUT).content)
        source = get_source_name(url)
        for e in f.entries[:5]: # نأخذ أول 5 فقط للسرعة
            link = getattr(e, 'link', '')
            if not link or link in sent_list: continue
            
            title = translate_text(getattr(e, 'title', ''))
            full_txt = f"{title} {getattr(e, 'summary', '')}"
            
            if any(k.lower() in full_txt.lower() for k in KEYWORDS_SYRIA):
                item = {'title': title[:130].strip(), 'link': link, 'source': source, 'image': get_image_url(e)}
                if any(bk.lower() in full_txt.lower() for bk in BREAKING_KEYWORDS): brk.append(item)
                else: nrm.append(item)
    except: pass
    return brk, nrm

# 6. دوال الإرسال لتليجرام
def send_telegram_msg(chat_id, text, image=None, is_breaking=False):
    if not chat_id: return False
    if image:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": image, "caption": text[:1024], "parse_mode": "HTML", "disable_notification": not is_breaking}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True, "disable_notification": not is_breaking}
    
    try: return session.post(url, json=payload, timeout=20).status_code == 200
    except: return False

# 7. الدالة الرئيسية (القلب النابض)
def main():
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("البيانات الأساسية للبوت مفقودة!")
        return
    
    load_cache()
    sent_list = load_sent_articles()
    links_to_save = []

    # جلب أخبار التليجرام أولاً (الأسرع)
    tg_news = fetch_telegram_channel("AlekhbariahSY", sent_list)
    
    # جلب أخبار 34 مصدر بشكل متوازٍ وسريع جداً
    rss_brk, rss_nrm = [], []
    with ThreadPoolExecutor(max_workers=15) as ex: # 15 عامل لسرعة فائقة
        futures = [ex.submit(fetch_feed, u, sent_list) for u in RSS_FEEDS]
        for f in as_completed(futures):
            b, n = f.result()
            rss_brk.extend(b); rss_nrm.extend(n)

    # 1. إرسال الأخبار العاجلة (فردية مع صور)
    all_brk = tg_news + rss_brk
    for b in all_brk:
        # تأكيد العاجل من التليجرام أو الـ RSS
        if b.get('is_brk') or any(bk in b['title'] for bk in BREAKING_KEYWORDS):
            msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
            for cid in TARGET_CHATS:
                success = send_telegram_msg(cid, msg, image=b.get('image'), is_breaking=True)
                # Fallback للـ Text لو فشلت الصورة
                if not success and b.get('image'):
                    send_telegram_msg(cid, msg, image=None, is_breaking=True)
            links_to_save.append(b['link'])

    # 2. إرسال النشرة الدورية (بدون أسعار، سريعة وأنيقة)
    # تنقية الأخبار العادية من التليجرام (التي ليست عاجلة)
    normal_tg = [n for n in tg_news if not n.get('is_brk')]
    all_nrm = normal_tg + rss_nrm
    
    if all_nrm:
        dam_time = (datetime.utcnow() + timedelta(hours=3))
        msg = f"<b>🇸🇾 موجز الشارع السوري</b>\n"
        msg += f"📅 {dam_time.strftime('%Y/%m/%d')} | {get_hijri_date()}\n"
        msg += f"✨ <i>\"{random.choice(DAILY_WISDOM)}\"</i>\n"
        msg += "───━━━━─━━━━───\n\n"
        
        weather = get_syria_weather()
        if weather: msg += weather
        
        msg += "<b>📰 أهم الأنباء المحلية والدولية:</b>\n"
        # أخذ أهم 15 خبر فقط لكي لا تتجاوز الرسالة الحد المسموح
        for i, a in enumerate(all_nrm[:15], 1):
            msg += f"{i}️⃣ <b>{a['title']}</b>\n└ {a['source']} | <a href='{a['link']}'>🔗 التفاصيل</a>\n\n"
            
        msg += "───━━━━─━━━━───\n<b>تم التطوير بواسطة: محمد محمد جلال الخطيب\nطلاب كليات الاعلام ||FMD</b>"
        
        sent_ok = False
        for cid in TARGET_CHATS:
            if send_telegram_msg(cid, msg, is_breaking=False): sent_ok = True
            
        if sent_ok:
            for a in all_nrm[:15]: links_to_save.append(a['link'])

    save_sent_articles(links_to_save)
    logging.info("تمت العملية بنجاح وبأقصى سرعة.")

if __name__ == "__main__":
    main()
