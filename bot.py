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

# الكلمات المفتاحية والساخنة (كما هي)
KEYWORDS_SYRIA = ["سوريا", "Syria", "سوري", "دمشق", "حلب", "حمص", "حماة", "اللاذقية", "طرطوس", "إدلب", "الرقة", "دير الزور", "الحسكة", "السويداء", "درعا", "القنيطرة", "ريف دمشق"]
BREAKING_KEYWORDS = ["عاجل", "Breaking", "انفجار", "اغتيال", "مقتل", "هجوم", "قصف", "غارة", "اشتباكات", "مرسوم", "إقالة", "زلزال", "سقوط", "استهداف", "طيران", "مسيرة", "مفخخة"]

# المصادر الـ 19 الأساسية
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

# --- دالة قشط قناة تليجرام (جديد) ---
def fetch_telegram_channel(channel_username, sent_list):
    """جلب الأخبار من نسخة الويب لقناة تليجرام"""
    tg_news = []
    try:
        url = f"https://t.me/s/{channel_username}"
        r = session.get(url, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, 'html.parser')
        # تليجرام يضع الرسائل في div كلاس 'tgme_widget_message_wrap'
        messages = soup.find_all('div', class_='tgme_widget_message_wrap')
        
        for msg in messages[::-1][:5]: # نأخذ آخر 5 رسائل
            text_div = msg.find('div', class_='tgme_widget_message_text')
            if not text_div: continue
            
            content = text_div.get_text(strip=True)
            link_tag = msg.find('a', class_='tgme_widget_message_date')
            msg_link = link_tag['href'] if link_tag else f"https://t.me/{channel_username}"
            
            if msg_link in sent_list: continue
            
            # فلترة وتحقق
            if any(k.lower() in content.lower() for k in KEYWORDS_SYRIA):
                # استخراج صورة إن وجدت
                img_div = msg.find('a', class_='tgme_widget_message_photo_wrap')
                img_url = None
                if img_div:
                    style = img_div.get('style', '')
                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                    if match: img_url = match.group(1)
                
                tg_news.append({
                    'title': content[:150] + "...",
                    'link': msg_link,
                    'source': "📺 الإخبارية (TG)",
                    'image': img_url,
                    'is_breaking': any(bk in content for bk in BREAKING_KEYWORDS)
                })
    except Exception as e:
        logging.error(f"Telegram Scraping Error: {e}")
    return tg_news

# --- بقية الدوال المساعدة (نفس الوظائف السابقة مع تحسين الأسعار) ---

def get_gold_dollar_prices():
    gold, dollar = "1,515,000", "14,850"
    try:
        r = session.get("https://sp-today.com/city/damascus", timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        usd_row = soup.find('tr', id='table_row_usd')
        if usd_row:
            tds = usd_row.find_all('td')
            if len(tds) >= 3: dollar = tds[2].get_text(strip=True)
        gold_text = soup.find(string=re.compile("الذهب عيار 21"))
        if gold_text:
            match = re.search(r'(\d{1,3}(,\d{3})+)', gold_text.find_parent().get_text())
            if match: gold = match.group(1)
        return re.sub(r'[^\d,]', '', gold), re.sub(r'[^\d,]', '', dollar)
    except: return gold, dollar

# (دوال الترجمة، الهجري، الطقس، والإرسال تبقى كما هي في الكود السابق لضمان الاستقرار)
# ... [تجنباً للتكرار الطويل، سأركز على دالة main لدمج التليجرام] ...

def main():
    if not BOT_TOKEN or not CHAT_ID: return
    # load_translation_cache(), load_sent_articles() الخ...
    # [هنا يتم جلب أخبار RSS]
    sent_list = load_sent_articles()
    
    # جلب أخبار التليجرام أولاً (لأنها الأسرع والأحدث)
    tg_breaking = []
    tg_normal = []
    logging.info("Checking Telegram Channel...")
    tg_results = fetch_telegram_channel("AlekhbariahSY", sent_list)
    for item in tg_results:
        if item['is_breaking']: tg_breaking.append(item)
        else: tg_normal.append(item)

    # جلب أخبار الـ RSS الموازية
    from_rss_breaking, from_rss_normal = get_rss_news_parallel(sent_list)
    
    # دمج النتائج
    all_breaking = tg_breaking + from_rss_breaking
    all_normal = tg_normal + from_rss_normal
    
    links_to_save = []

    # إرسال العاجل فوراً
    for b in all_breaking:
        msg = f"🚨 <b>خبر عاجل</b>\n\n📰 <b>{b['title']}</b>\n\n{b['source']} | <a href='{b['link']}'>🔗 التفاصيل</a>"
        for cid in TARGET_CHATS:
            success = send_telegram_photo(cid, msg, b['image']) if b.get('image') else False
            if not success: send_telegram(cid, msg, is_breaking=True)
            links_to_save.append(b['link'])

    # إرسال الموجز (يتضمن أخبار التليجرام العادية)
    # ... [نفس منطق النشرة الدورية السابق] ...

if __name__ == "__main__":
    # ملاحظة: تأكد من نسخ كل الدوال المساعدة من الكود السابق (translate, send, weather, etc.)
    # ليعمل الملف بشكل كامل ومستقر.
    main()
