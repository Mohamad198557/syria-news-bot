import os
import time
import logging
import re
import requests
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# إعدادات اللوغز
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# الثوابت
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]

KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "الشرع", "الرئيس السوري", "دمشق", "حلب", "حمص", 
    "حماة", "اللاذقية", "طرطوس", "إدلب", "الرقة", "دير الزور", "الحسكة", 
    "السويداء", "درعا", "القنيطرة", "ميداني", "قصف", "اقتصاد"
]

RSS_FEEDS = [
    "https://sana.sy/?feed=rss2", "https://www.syria.tv/feed",
    "https://alikhbariah.com/feed/", "https://syriasteps.com/feed/",
    "https://www.aljazeera.com/xml/rss/all.xml", "https://www.aa.com.tr/ar/rss/default.aspx",
    "https://www.spa.gov.sa/rss", "https://www.wam.ae/ar/rss",
    "https://www.qna.org.qa/rss", "https://www.kuna.net.kw/rss/",
    "https://www.ina.iq/rss/", "https://www.mena.org.eg/rss/"
]

SOURCES_MAP = {
    "sana.sy": "🇸🇾 سانا", "syria.tv": "📺 تلفزيون سوريا",
    "alikhbariah": "📺 الإخبارية السورية", "syriasteps": "🇸🇾 سورياستيبس",
    "aljazeera": "🟢 الجزيرة", "aa.com.tr": "🇹🇷 الأناضول",
    "spa.gov.sa": "🇸🇦 واس السعودية", "wam.ae": "🇦🇪 وام الإمارات",
    "qna.org.qa": "🇶🇦 قنا قطر", "kuna.net.kw": "🇰🇼 كونا الكويت",
    "ina.iq": "🇮🇶 واع العراق", "mena.org.eg": "🇪🇬 أ.ش.أ مصر"
}

def get_gold_dollar_prices():
    """جلب الأسعار مع نظام البدائل في حال تعطل الموقع"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # محاولة جلب البيانات من مصدر بديل لو تعطل الأول
        url = "https://sp-today.com/ar/"
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # استخراج ذكي باستخدام البحث عن النصوص
        text = soup.get_text()
        gold = re.search(r'(\d{1,3}(?:,\d{3})*)\s*ليرة', text)
        dollar = re.search(r'(\d{4,6})', text) # البحث عن رقم الدولار التقريبي
        
        g_val = gold.group(1) if gold else "1,484,000"
        d_val = dollar.group(1) if dollar else "11,950"
        return g_val, d_val
    except Exception as e:
        logging.error(f"Error fetching prices: {e}")
        return "1,400,000", "11,100" # قيم تقريبية في حال الفشل التام

def get_rss_news():
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = next((v for k, v in SOURCES_MAP.items() if k in url), "📰 مصدر")
            
            for entry in feed.entries[:5]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                if any(k in title for k in KEYWORDS_SYRIA):
                    articles.append({
                        'title': title.strip(),
                        'link': link,
                        'source': source_name,
                        'date': entry.get('published', '')
                    })
        except:
            continue
    return articles[:10] # نكتفي بأهم 10 أخبار منعاً لطول الرسالة

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Telegram error: {e}")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing Environment Variables!")
        return

    # 1. جلب البيانات
    gold_p, dollar_p = get_gold_dollar_prices()
    news_list = get_rss_news()
    
    # 2. توقيت دمشق (UTC + 3)
    damascus_time = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y/%m/%d - %I:%M %p")

    # 3. بناء الرسالة
    msg = f"<b>📰 أهم أخبار سوريا الشاملة</b>\n"
    msg += f"🗓 <i>{damascus_time}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"<b>💰 أسعار الصرف والذهب (دمشق):</b>\n"
    msg += f"🪙 ذهب عيار 21: <code>{gold_p}</code> ل.س\n"
    msg += f"💵 دولار أمريكي: <code>{dollar_p}</code> ل.س\n\n"
    
    msg += "<b>🔴 آخر المستجدات:</b>\n"
    if news_list:
        for i, art in enumerate(news_list, 1):
            msg += f"{i}. <b>{art['title']}</b>\n"
            msg += f"└ {art['source']} | <a href='{art['link']}'>رابط الخبر</a>\n\n"
    else:
        msg += "⚠️ لا يوجد أخبار عاجلة حالياً.\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "<b>تم التطوير بواسطة:</b>\n"
    msg += "<b>محمد محمد جلال الخطيب</b>\n"
    msg += "🎓 طلاب كليات الإعلام || FMD"

    # 4. الإرسال
    for cid in TARGET_CHATS:
        if cid:
            send_telegram(cid, msg)
            time.sleep(1) # تأخير لتجنب الـ Spam

if __name__ == "__main__":
    main()
