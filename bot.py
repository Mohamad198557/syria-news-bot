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

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
DB_FILE = "sent_articles.txt"
CACHE_FILE = "translation_cache.txt"
TIMEOUT = 10

# إنشاء session للاتصالات المتكررة (أسرع بكثير)
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# الكلمات المفتاحية
KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus", "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah", "السويداء", "Suwayda", 
    "درعا", "Daraa", "القنيطرة", "Quneitra", "ريف دمشق"
]

BREAKING_KEYWORDS = ["عاجل", "Breaking", "Urgent", "فوري", "Alert"]

# مصادر الأخبار - مع أولويات
RSS_FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://sana.sy/?feed=rss2",  # المصدر السوري الأساسي
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://trt.global/arabi/rss/",
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories",
    "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://www.syria.tv/feed",
    "https://syriasteps.com/feed/",
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

# مصادر تخزين Cache
translation_cache = {}

def hash_text(text):
    """حساب hash للنص لتخزين الترجمات بكفاءة"""
    return hashlib.md5(text.encode()).hexdigest()

def load_translation_cache():
    """تحميل cache الترجمات"""
    global translation_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding='utf-8') as f:
                for line in f:
                    if "|" in line:
                        key, value = line.strip().split("|", 1)
                        translation_cache[key] = value
        except Exception as e:
            logging.warning(f"Error loading cache: {e}")

def save_translation_to_cache(text, translation):
    """حفظ الترجمة في cache"""
    key = hash_text(text)
    translation_cache[key] = translation
    try:
        with open(CACHE_FILE, "a", encoding='utf-8') as f:
            f.write(f"{key}|{translation}\n")
    except Exception as e:
        logging.warning(f"Error saving to cache: {e}")

def get_hijri_date():
    """جلب التاريخ الهجري بدقة عبر API"""
    try:
        r = session.get("http://api.aladhan.com/v1/gToH", 
                       params={"date": datetime.now().strftime("%d-%m-%Y")}, 
                       timeout=5)
        if r.status_code == 200:
            data = r.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']} هـ"
    except Exception as e:
        logging.warning(f"Hijri date error: {e}")
    return ""

def load_sent_articles():
    """تحميل قائمة المقالات المرسلة"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f: 
                return set(f.read().splitlines())
        except Exception as e:
            logging.error(f"Error loading DB: {e}")
    return set()

def save_sent_articles(links_list):
    """حفظ قائمة المقالات الجديدة"""
    if not links_list: 
        return
    try:
        with open(DB_FILE, "a", encoding='utf-8') as f:
            for link in links_list:
                f.write(link + "\n")
    except Exception as e:
        logging.error(f"Error saving to DB: {e}")

def translate_text(text):
    """ترجمة النص مع استخدام Cache"""
    try:
        if not re.search(r'[a-zA-Z]', text):
            return text
        
        # البحث في Cache
        text_hash = hash_text(text)
        if text_hash in translation_cache:
            return translation_cache[text_hash]
        
        # الترجمة إذا لم توجد في Cache
        translation = GoogleTranslator(source='en', target='ar').translate(text)
        save_translation_to_cache(text, translation)
        return translation
    except Exception as e:
        logging.warning(f"Translation error: {e}")
        return text

@lru_cache(maxsize=128)
def get_source_name(url):
    """استخراج اسم المصدر مع إيموجي مميز (مع caching)"""
    sources = {
        "sana.sy": "🇸🇾 سانا", 
        "syria.tv": "📺 تلفزيون سوريا", 
        "aljazeera": "🟢 الجزيرة", 
        "bbc": "🔴 BBC", 
        "guardian": "🟠 الغارديان", 
        "nytimes": "🇺🇸 نيويورك تايمز", 
        "aa.com.tr": "🇹🇷 الأناضول", 
        "france24": "🇫🇷 فرانس 24", 
        "rt": "🇷🇺 روسيا اليوم",
        "dw.com": "🇩🇪 DW",
        "trt.global": "🇹🇷 TRT"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة أنباء")

def fetch_feed(feed_url, sent_list):
    """جلب أخبار من مصدر واحد (للمعالجة المتزامنة)"""
    breaking, normal = [], []
    try:
        response = session.get(feed_url, timeout=TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        source = get_source_name(feed_url)
        
        for entry in feed.entries[:5]:  # تقليل العدد لتسريع المعالجة
            try:
                link = getattr(entry, 'link', '')
                if not link or link in sent_list:
                    continue
                
                title_or = getattr(entry, 'title', '')
                if not title_or:
                    continue
                
                title_ar = translate_text(title_or)
                summary = getattr(entry, 'summary', '')[:100]  # تقصير الـ summary
                full_txt = f"{title_or} {title_ar} {summary}".lower()
                
                # التحقق من الكلمات المفتاحية
                if any(k.lower() in full_txt for k in KEYWORDS_SYRIA):
                    data = {'title': title_ar[:125].strip(), 'link': link, 'source': source}
                    
                    if any(bk.lower() in full_txt for bk in BREAKING_KEYWORDS):
                        breaking.append(data)
                    else:
                        normal.append(data)
            except Exception as e:
                logging.debug(f"Error parsing entry: {e}")
                continue
    
    except Exception as e:
        logging.warning(f"Error fetching from {feed_url}: {e}")
    
    return breaking, normal

def get_rss_news_parallel(sent_list):
    """جلب الأخبار بشكل متوازي (أسرع بكثير)"""
    breaking_all, normal_all = [], []
    
    # استخدام ThreadPoolExecutor للمعالجة المتزامنة
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_feed, url, sent_list): url for url in RSS_FEEDS}
        
        for future in as_completed(futures):
            try:
                breaking, normal = future.result()
                breaking_all.extend(breaking)
                normal_all.extend(normal)
                
                # التوقف إذا جمعنا عدد كافي من الأخبار
                if len(normal_all) >= 12:
                    break
            except Exception as e:
                logging.error(f"Error in parallel processing: {e}")
    
    return breaking_all, normal_all[:12]

def get_syria_weather():
    """جلب الطقس بشكل متزامن (أسرع)"""
    report = "🌡️ <b>درجات الحرارة المتوقعة:</b>\n"
    cities = {
        "Damascus": "دمشق", 
        "Aleppo": "حلب", 
        "Homs": "حمص", 
        "Latakia": "اللاذقية"
    }
    
    def fetch_weather(city_name):
        try:
            url = f"https://wttr.in/{city_name}?format=%t"
            r = session.get(url, timeout=5)
            if r.status_code == 200:
                temp = r.text.strip().replace('+', '')
                return f"• {cities[city_name]}: <code>{temp}</code>"
        except:
            pass
        return None
    
    weather_lines = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_weather, city): city for city in cities}
        for future in as_completed(futures):
            result = future.result()
            if result:
                weather_lines.append(result)
    
    if weather_lines:
        report += "  ".join(weather_lines[:2]) + "\n"
        if len(weather_lines) > 2:
            report += "  ".join(weather_lines[2:]) + "\n"
        report += "\n"
    
    return report if len(weather_lines) > 0 else ""

def get_gold_dollar_prices():
    """جلب الأسعار بتحسين الخوارزمية"""
    try:
        r = session.get("https://sp-today.com/en", timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        
        # تحسين regex للأسعار
        gold_match = re.search(r'1[,\d]{6,9}', text)
        dollar_match = re.search(r'1[1-2],\d{3}', text)
        
        gold = gold_match.group(0) if gold_match else "1,517,000"
        dollar = dollar_match.group(0) if dollar_match else "11,950"
        
        return gold, dollar
    except Exception as e:
        logging.warning(f"Price fetch error: {e}")
        return "1,517,000", "11,950"

def send_telegram(chat_id, message, is_breaking=False):
    """إرسال الرسالة إلى Telegram"""
    if not chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True, 
        "disable_notification": not is_breaking
    }
    
    try:
        r = session.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"Telegram send error: {e}")
        return False

def main():
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("BOT_TOKEN or CHAT_ID is missing!")
        return
    
    # تحميل cache الترجمات
    load_translation_cache()
    
    # قياس الوقت
    start_time = time.time()
    
    sent_list = load_sent_articles()
    breaking_news, normal_news = get_rss_news_parallel(sent_list)  # معالجة متزامنة
    links_to_save = []

    # 1. إرسال الأخبار العاجلة
    for b in breaking_news:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS: 
            if send_telegram(cid, msg, is_breaking=True):
                if b['link'] not in links_to_save:
                    links_to_save.append(b['link'])
    
    # 2. إرسال النشرة العادية
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

    # حفظ الروابط
    save_sent_articles(links_to_save)
    
    elapsed = time.time() - start_time
    logging.info(f"✅ تم إكمال التشغيل في {elapsed:.2f} ثانية")
    
        # أضف هذا السطر مؤقتاً قبل save_sent_articles في نهاية main
    if not normal_news and not breaking_news:
        logging.info("لم يتم العثور على أخبار جديدة لإرسالها.")
        # يمكنك تفعيل السطر التالي للتأكد من وصول التنبيهات إليك
        # send_telegram(CHAT_ID, "🔍 البوت يعمل بنجاح ولكن لا توجد أخبار جديدة حالياً.")
        

if __name__ == "__main__":
    main()
