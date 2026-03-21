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
SEEN_ARTICLES = set()

print("بوت اخبار سوريا - 20 وكالة + اسعار الذهب والدولار - كل 30 دقيقة اخبار جديدة!")

KEYWORDS_SYRIA = [
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    "احمد الشرع", "Ahmed al-Sharaa", "الشرع", "الرئيس السوري",
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "ادلب", "Idlib", "الرقة", "Raqqa",
    "دير الزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "السويداء", "Suwayda", "درعا", "Daraa", "القنيطرة", "Quneitra"
]

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
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/11.0'}
        url = "https://sp-today.com/en"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        
        gold_price = "1484000"
        dollar_price = "11950"
        
        gold_matches = re.findall(r'1[d,]{6,9}', text)
        dollar_matches = re.findall(r'1[1-2],[d]{3}', text)
        
        if gold_matches:
            gold_price = gold_matches[0].replace(',', '')
            print(f"ذهب من الموقع: {gold_price}")
        if dollar_matches:
            dollar_price = dollar_matches[0].replace(',', '')
            print(f"دولار من الموقع: {dollar_price}")
        
        print(f"نهائي: ذهب {gold_price} | دولار {dollar_price}")
        return gold_price, dollar_price
    except Exception as e:
        print(f"اسعار افتراضية: {e}")
        return "1484000", "11950"

def contains_syria_keyword(text):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS_SYRIA)

def get_source_name(url):
    sources = {
        "sana": "سانا الرسمية",
        "syria.tv": "تلفزيون سوريا",
        "alikhbariah": "الاخبارية السورية",
        "syriasteps": "سورياستيبس",
        "aljazeera": "الجزيرة نت",
        "bbc": "بي بي سي",
        "guardian": "الغارديان",
        "aa.com.tr": "الأناضول",
        "skynewsarabia": "سكاي عربية",
        "aawsat": "الشرق الأوسط",
        "france24": "فرانس 24",
        "dw.com": "دويتشه فيله",
        "wam.ae": "وام الإمارات",
        "bna.bh": "بنا البحرين",
        "petra.gov.jo": "بترا الأردن",
        "aps.dz": "واج الجزائر",
        "saba.ye": "سبأ اليمن",
        "spa.gov.sa": "واس السعودية"
    }
    return next((name for key, name in sources.items() if key in url.lower()), "وكالة")

def get_rss_news():
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("فحص 20 وكالة أنباء (أخبار جديدة فقط)...")
    for i, url in enumerate(RSS_FEEDS, 1):
        if i % 4 == 0:
            print(f"   التقدم: {i}/{len(RSS_FEEDS)}")
        
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
                        article_id = f"{title[:50]}{pub_date}"
                        if article_id not in SEEN_ARTICLES:
                            articles.append({
                                'title': title[:125],
                                'link': getattr(entry, 'link', ''),
                                'source': source_name,
                                'date': pub_date
                            })
                            SEEN_ARTICLES.add(article_id)
                            print(f"    خبر سوري جديد")
                            break
        except Exception as e:
            print(f"    خطأ: {str(e)[:50]}")
        
        time.sleep(0.7)
    
    return sorted(articles, key=lambda x: x['date'], reverse=True)

def send_telegram(chat_id, message):
    if not BOT_TOKEN:
        print("BOT_TOKEN غير موجود!")
        return False
        
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
    except Exception as e:
        print(f"خطأ إرسال: {e}")
        return False

def main():
    print("بوت أخبار سوريا + الأسعار يعمل...")
    
    gold_price, dollar_price = get_gold_dollar_prices()
    print(f"ذهب: {gold_price} | دولار: {dollar_price}")
    
    articles = get_rss_news()
    
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = "<b>اهم أخبار سوريا من أبرز وكالات الأنباء</b>

"
    
    msg += f"<b>السوق اليوم ({now_str}):</b>
"
    msg += f"<b>ذهب عيار 21:</b> {gold_price} ليرة
"
    msg += f"<b>دولار:</b> {dollar_price} ليرة

"
    
    msg += f"<i>{now_str} | 20 وكالة أنباء</i>
"
    
    if articles:
        msg += "<b>آخر الأخبار:</b>

"
        for i, article in enumerate(articles[:8], 1):
            msg += f"{i}. <b>{article['title']}</b>
"
            msg += f"{article['source']}
"
            msg += f"<a href="{article['link']}">الكامل</a>

"
    else:
        msg += "<b>لا أخبار سورية جديدة الـ 24 ساعة الأخيرة</b>

"
        msg += "تم فحص 20 وكالة أنباء عالمية وعربية
"
        msg += "سانا + تلفزيون سوريا + الإخبارية"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"
    msg += "<b>تم تطويره بواسطة:</b>
"
    msg += "<b>محمد محمد جلال الخطيب</b>
"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    success_count = 0
    for chat_id in TARGET_CHATS:
        if send_telegram(chat_id, msg):
            success_count += 1
            print(f"نجح: {chat_id}")
        else:
            print(f"فشل: {chat_id}")
    
    print(f"النتيجة: {success_count}/2 وجهة | {len(articles)} خبر جديد | إجمالي محفوظ: {len(SEEN_ARTICLES)}")

if __name__ == "__main__":
    print("بدء تشغيل تلقائي كل 30 دقيقة - أخبار جديدة فقط!")
    while True:
        try:
            main()
            if len(SEEN_ARTICLES) > 1000:
                SEEN_ARTICLES.clear()
                print("تم تنظيف قاعدة الأخبار (1000+)")
            print("انتظار 30 دقيقة (1800 ثانية)...")
            time.sleep(1800)
        except KeyboardInterrupt:
            print("تم إيقاف البوت بـ Ctrl+C")
            break
        except Exception as e:
            print(f"خطأ غير متوقع: {e}")
            print("إعادة المحاولة خلال دقيقة...")
            time.sleep(60)
