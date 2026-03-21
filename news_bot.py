import os
import time
import re
import requests
import feedparser
from bs4 import BeautifulSoup
import json
import hashlib
from datetime import datetime, timedelta

# متغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]
SEEN_NEWS_FILE = "seen_news.json"

print("🚀 بوت أخبار سوريا - 25 وكالة + كامل الكلمات المفتاحية")

# 🔥 الكلمات المفتاحية الأصلية الكاملة (سوريا + الرئيس + 14 محافظة)
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

# 🔥 25 وكالة أنباء شاملة - الأصلية كاملة
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

def load_seen_news():
    """تحميل الأخبار المشاهدة سابقاً"""
    try:
        if os.path.exists(SEEN_NEWS_FILE):
            with open(SEEN_NEWS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_seen_news(seen_hashes):
    """حفظ الأخبار المشاهدة"""
    try:
        with open(SEEN_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen_hashes), f, ensure_ascii=False)
    except:
        pass

def get_news_hash(title, link):
    """إنشاء hash فريد للخبر"""
    content = title.lower() + link
    return hashlib.md5(content.encode()).hexdigest()

def get_gold_dollar_prices():
    """🔥 أسعار الذهب والدولار - الأصلية"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/1.0'}
        url = "https://sp-today.com/en"
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()
        
        gold_pattern = r'1[,d]{6,9}'
        dollar_pattern = r'1[1-2],[0-9]{3}'
        
        gold_matches = re.findall(gold_pattern, text)
        dollar_matches = re.findall(dollar_pattern, text)
        
        gold_price = gold_matches[0] if gold_matches else "1,484,000"
        dollar_price = dollar_matches[0] if dollar_matches else "11,950"
        
        print("💰 الأسعار: ذهب " + gold_price + " | دولار " + dollar_price)
        return gold_price, dollar_price
    except:
        print("⚠️ أسعار افتراضية")
        return "1,484,000", "11,950"

def contains_syria_keyword(text):
    """فلترة الكلمات المفتاحية الأصلية الكاملة"""
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS_SYRIA)

def get_source_name(url):
    """أسماء الوكالات الأصلية الجميلة"""
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
        "dw.com": "🇩🇪 دويتشه فيله",
        "wam.ae": "🟢 وام الإمارات",
        "bna.bh": "🟣 بنا البحرين",
        "petra.gov.jo": "🟡 بترا الأردن",
        "aps.dz": "🔵 واج الجزائر",
        "saba.ye": "🔴 سبأ اليمن",
        "spa.gov.sa": "⚫ واس السعودية"
    }
    url_lower = url.lower()
    for key, name in sources.items():
        if key in url_lower:
            return name
    return "📰 وكالة أنباء"

def get_new_rss_news(seen_hashes):
    """25 وكالة مع فلترة الأخبار الجديدة فقط"""
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    
    print("📰 فحص 25 وكالة أنباء...")
    
    for i, url in enumerate(RSS_FEEDS, 1):
        if i % 5 == 0:
            print("   التقدم: " + str(i) + "/" + str(len(RSS_FEEDS)))
        
        source_name = get_source_name(url)
        print("[" + str(i) + "] " + source_name)
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/2.0'}
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            
            feed = feedparser.parse(r.content)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                continue
            
            for entry in feed.entries[:3]:
                title = entry.title if hasattr(entry, 'title') else ""
                summary = (entry.summary if hasattr(entry, 'summary') 
                          else entry.description if hasattr(entry, 'description') 
                          else "")
                link = entry.link if hasattr(entry, 'link') else ""
                
                full_text = title + " " + summary
                
                if contains_syria_keyword(full_text):
                    news_hash = get_news_hash(title, link)
                    
                    if news_hash in seen_hashes:
                        continue
                    
                    pub_date = None
                    for date_field in ['published_parsed', 'updated_parsed']:
                        if hasattr(entry, date_field) and getattr(entry, date_field):
                            try:
                                pub_date = datetime(*getattr(entry, date_field)[:6])
                                break
                            except:
                                pass
                    
                    if pub_date is None or pub_date > cutoff:
                        articles.append({
                            'title': title[:120] + "..." if len(title) > 120 else title,
                            'link': link,
                            'source': source_name,
                            'date': pub_date or datetime.utcnow()
                        })
                        seen_hashes.add(news_hash)
                        print("    ✅ خبر سوري جديد!")
                        break
                        
        except Exception as e:
            print("    ❌ خطأ: " + str(e)[:50])
        
        time.sleep(1)
    
    return articles

def send_telegram(chat_id, message):
    """إرسال آمن لتيليجرام"""
    if not BOT_TOKEN or not chat_id:
        return False
    
    try:
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': 'true'
        }
        r = requests.post(url, data=data, timeout=20)
        return r.status_code == 200
    except:
        return False

def run_once():
    """تشغيل دورة واحدة كاملة"""
    print("
" + "="*60)
    print("⏰ [" + datetime.now().strftime('%H:%M:%S') + "] بدء دورة جديدة")
    
    # تحميل الأخبار السابقة
    seen_hashes = load_seen_news()
    print("📊 الأخبار المحفوظة: " + str(len(seen_hashes)))
    
    # الأسعار
    gold_price, dollar_price = get_gold_dollar_prices()
    
    # الأخبار السورية الجديدة
    new_articles = get_new_rss_news(seen_hashes)
    
    # إرسال إذا وُجدت أخبار
    if new_articles:
        now_str = datetime.utcnow().strftime("%H:%M UTC")
        
        message = "<b>🇸🇾 أهم أخبار سوريا من 25 وكالة أنباء</b>

"
        message += "<b>💰 السوق اليوم (" + now_str + "):</b>
"
        message += "🪙 <b>ذهب عيار 21:</b> " + gold_price + " ليرة
"
        message += "💵 <b>دولار:</b> " + dollar_price + " ليرة

"
        message += "<i>⏰ آخر تحديث: " + now_str + " | 25 وكالة</i>

"
        message += "<b>📰 الأخبار الجديدة:</b>
"
        message += "━━━━━━━━━━━━━━━━━━━━━
"
        
        for i, article in enumerate(new_articles[:8], 1):
            message += str(i) + ". <b>" + article['title'] + "</b>
"
            message += article['source'] + "
"
            message += "<a href='" + article['link'] + "'>🔗 قراءة الكامل</a>

"
        
        message += "━━━━━━━━━━━━━━━━━━━━━
"
        message += "<b>تم تطويره بواسطة:</b>
"
        message += "<b>محمد محمد جلال الخطيب</b>
"
        message += "<b>طلاب كليات الإعلام || FMD</b>"
        
        # الإرسال لكل قناة
        success_count = 0
        for chat_id in TARGET_CHATS:
            if chat_id and send_telegram(chat_id, message):
                success_count += 1
                print("📱 نجح: " + chat_id)
        
        print("🎉 تم إرسال " + str(len(new_articles)) + 
              " خبر جديد إلى " + str(success_count) + " قناة")
        
        # حفظ الأخبار الجديدة
        save_seen_news(seen_hashes)
        
    else:
        print("ℹ️ لا توجد أخبار سورية جديدة في آخر 24 ساعة")

def main():
    """الحلقة الرئيسية - كل 30 دقيقة"""
    print("
🚀 البوت جاهز! يعمل كل 30 دقيقة تلقائياً")
    print("💡 Ctrl+C للإيقاف النظيف")
    print("=" * 60)
    
    try:
        while True:
            run_once()
            print("
💤 انتظار 30 دقيقة...")
            time.sleep(1800)  # 30 دقيقة = 1800 ثانية
    except KeyboardInterrupt:
        print("
⏹️ تم إيقاف البوت بنجاح بواسطة المستخدم")
    except Exception as e:
        print("❌ خطأ غير متوقع: " + str(e))
        print("🔄 إعادة المحاولة خلال 5 دقائق...")
        time.sleep(300)

if __name__ == "__main__":
    main()
