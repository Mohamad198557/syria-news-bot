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
    # الـ 14 محافظة كاملة
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "إدلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "السويداء", "Suwayda", "درعا", "Daraa", "القنيطرة", "Quneitra"
]

# 🔥 20 وكالة أنباء شاملة
RSS_FEEDS = [
    # 🇸🇾 سورية رسمية
    "https://sana.sy/?feed=rss2",
    "https://www.syria.tv/feed",
    "https://alikhbariah.com/feed/",
    "https://syriasteps.com/feed/",
    
    # 🌍 عالمية كبرى
    "https://www.aljazeera.com/xml/rss/all.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    
    # 🇹🇷 تركية موثوقة
    "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://trt.global/arabi/rss/",
    
    # 🇸🇦 عربية
    "https://aawsat.com/rss-feed",
    "https://www.alaraby.co.uk/feed.xml",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.alalam.ir/rss",
    "https://asharq.com/rss/feed/1/",
    
    # 🇪🇺 أوروبية
    "https://www.france24.com/en/rss",
    "https://www.dw.com/en/rss-top-stories",
    "https://www.euronews.com/rss.xml",
    
    # احتياطي
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines"
]

def get_gold_dollar_prices():
    """🔥 استخراج أسعار الذهب والدولار من sp-today"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/10.0'
        }
        url = "https://sp-today.com/en"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        
        # البحث الذكي عن الأسعار
        gold_price = "غير متاح"
        dollar_price = "غير متاح"
        
        # 🔥 ذهب عيار 21 (الأشهر في سوريا)
        gold_match = re.search(r'21\s*[:\-]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if gold_match:
            gold_price = gold_match.group(1).replace(',', '')
        
        # 🔥 سعر الدولار
        dollar_match = re.search(r'(?:\$|دولار|USD)\s*[:\-]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if dollar_match:
            dollar_price = dollar_match.group(1).replace(',', '')
        
        return gold_price, dollar_price
        
    except Exception as e:
        print(f"⚠️ خطأ في الأسعار: {e}")
        return "خطأ", "خطأ"

def contains_syria_keyword(text):
    """فلترة سوريا + 14 محافظة + الرئيس"""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS_SYRIA)

def get_source_name(url):
    """أسماء الوكالات الجميلة"""
    sources = {
        "sana.sy": "🇸🇾 سانا الرسمية",
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
        "dw.com": "🇩🇪 دويتشه فيله"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "📰 وكالة")

def get_rss_news():
    """20 وكالة مع فلترة ذكية"""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("📰 فحص 20 وكالة أنباء...")
    for i, url in enumerate(RSS_FEEDS, 1):
        if i % 4 == 0:
            print(f"   التقدم: {i}/20")
        
        source_name = get_source_name(url)
        print(f"[{i:2d}] {source_name}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/9.0'}
            r = requests.get(url, headers=headers, timeout=12)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            
            for entry in feed.entries[:4]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
                
                full_text = f"{title} {summary}"
                
                if contains_syria_keyword(full_text):
                    pub_date = None
                    for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
                        if hasattr(entry, date_field):
                            try:
                                pub_date = datetime(*getattr(entry, date_field)[:6])
                                break
                            except:
                                pass
                    
                    if pub_date and pub_date > cutoff:
                        articles.append({
                            'title': title[:125],
                            'link': getattr(entry, 'link', ''),
                            'source': source_name,
                            'date': pub_date
                        })
                        print(f"    ✅ خبر سوري ✓")
                        break
                        
        except Exception as e:
            print(f"    ⏭️ خطأ")
        
        time.sleep(0.7)
    
    return sorted(articles, key=lambda x: x['date'], reverse=True)

def send_telegram(chat_id, message):
    """إرسال آمن"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def main():
    print("🎯 بوت أخبار سوريا + الأسعار يعمل...")
    
    # 🔥 الأسعار الجديدة
    gold_price, dollar_price = get_gold_dollar_prices()
    print(f"💰 ذهب: {gold_price} | دولار: {dollar_price}")
    
    # جمع الأخبار
    articles = get_rss_news()
    
    # الرسالة الاحترافية مع الأسعار
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = f"<b>🇸🇾 أهم أخبار سوريا + الأسعار</b>\n\n"
    
    # 🔥 قسم الأسعار في الأعلى
    msg += f"<b>💰 السوق اليوم ({now_str}):</b>\n"
    msg += f"🪙 <b>ذهب عيار 21:</b> {gold_price} ليرة\n"
    msg += f"💵 <b>دولار:</b> {dollar_price} ليرة\n\n"
    
    msg += f"<i>⏰ {now_str} | 20 وكالة أنباء</i>\n"
    msg += f"<i>📍 تغطية 14 محافظة + أحمد الشرع</i>\n\n"
    
    if articles:
        msg += "<b>📰 آخر الأخبار:</b>\n\n"
        for i, article in enumerate(articles[:8], 1):
            msg += f"{i}. <b>{article['title']}</b>\n"
            msg += f"{article['source']}\n"
            msg += f"<a href=\"{article['link']}\">🔗 الكامل</a>\n\n"
    else:
        msg += "<b>📭 لا أخبار سورية الـ 24 ساعة الأخيرة</b>\n\n"
        msg += "🔍 تم فحص 20 وكالة أنباء عالمية وعربية\n"
        msg += "🇸🇾 سانا + تلفزيون سوريا + الإخبارية"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم تطويره بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    # الإرسال
    success_count = 0
    for chat_id in TARGET_CHATS:
        if send_telegram(chat_id, msg):
            success_count += 1
            print(f"📱 نجح: {chat_id}")
    
    print(f"\n🎉 النتيجة: {success_count}/2 وجهة | {len(articles)} خبر")

if __name__ == "__main__":
    main()
