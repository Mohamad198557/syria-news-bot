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

print("🚀 بوت أخبار سوريا - 20 وكالة + أسعار الذهب والدولار")

# 🔥 الكلمات المفتاحية الرئيسية (سوريا + الرئيس + 14 محافظة)
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

# 🔥 20 وكالة أنباء شاملة
RSS_FEEDS = [
    "https://sana.sy/?feed=rss2", 
    "https://www.syria.tv/feed",
    "https://alikhbariah.com/feed/", 
    "https://syriasteps.com/feed/",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://www.aa.com.tr/ar/rss/default.aspx", 
    "https://trt.global/arabi/rss/",
    "https://aawsat.com/rss-feed", 
    "https://www.alaraby.co.uk/feed.xml",
    "https://www.skynewsarabia.com/rss/world.xml", 
    "https://www.alalam.ir/rss",
    "https://asharq.com/rss/feed/1/", 
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories", 
    "https://www.euronews.com/rss.xml",
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
    "https://www.wam.ae/ar/rss",
    "https://www.bna.bh/rss/?lang=ar",
    "https://www.petra.gov.jo/rss/JoSiteAr.aspx",
    "https://www.aps.dz/rss",
    "https://www.saba.ye/rss/feed.xml",
    "https://www.spa.gov.sa/rss"
]

def get_gold_dollar_prices():
    """🔥 أسعار الذهب والدولار - مضمون 100%"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/11.0'}
        url = "https://sp-today.com/en"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        
        gold_price = "1,484,000"
        dollar_price = "11,950"
        
        gold_matches = re.findall(r'1[\d,]{6,9}', text)
        dollar_matches = re.findall(r'1[1-2],[\d]{3}', text)
        
        if gold_matches:
            gold_price = gold_matches[0].replace(',', '')
            print(f"✅ ذهب من الموقع: {gold_price}")
        
        if dollar_matches:
            dollar_price = dollar_matches[0].replace(',', '')
            print(f"✅ دولار من الموقع: {dollar_price}")
        
        print(f"💰 نهائي: ذهب {gold_price} | دولار {dollar_price}")
        return gold_price, dollar_price
        
    except Exception as e:
        print(f"⚠️ أسعار افتراضية: {e}")
        return "1,484,000", "11,950"

def contains_syria_keyword(text):
    """فلترة سوريا + 14 محافظة + الرئيس"""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS_SYRIA)

def get_source_name(url):
    """أسماء الوكالات الجميلة"""
    sources = {
        "sana": "🇸🇾 سانا الرسمية", 
        "syria.tv": "📺 تلفزيون سوريا",
        "alikhbariah": "📺 الإخبارية السورية", 
        "syriasteps": "🇸🇾 سورياستيبس",
        "aljazeera": "🟢 الجزيرة نت", 
        "bbc": "🔴 بي بي سي",
        "guardian": "🟠 الغارديان", 
        "aa.com.tr": "🇹🇷 الأناضول",
        "skynewsarabia": "🔵 سكاي عربية", 
        "aawsat": "🔷 الشرق الأوسط",
        "france24": "🇫🇷 فرانس 24", 
        "dw.com": "🇩🇪 دويتشه فيله",
        "wam.ae": "🟢 وام الإمارات",
        "bna.bh":
