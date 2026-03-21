import os
import time
import logging
import re
from datetime import datetime, timedelta
import requests
import feedparser

logging.basicConfig(level=logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHANNEL_ID = "-1003803988944"
TARGET_CHATS = [CHAT_ID, CHANNEL_ID]

print("🚀 بوت سوريا الشامل - 20 وكالة + 10 X + 14 محافظة")

# 🔥 الكلمات المفتاحية الرئيسية (سوريا + الرئيس + 14 محافظة)
KEYWORDS_SYRIA = [
    # سوريا عام
    "سوريا", "Syria", "سوري", "Syrian", "السوريين",
    # الرئيس أحمد الشرع
    "أحمد الشرع", "Ahmed al-Sharaa", "أحمد الشّرع", "الشرع", "الرئيس السوري",
    # الـ 14 محافظة كاملة ✅
    "دمشق", "Damascus", "ريف دمشق", "Rif Dimashq",
    "حلب", "Aleppo", "حمص", "Homs", "حماة", "Hama",
    "اللاذقية", "Latakia", "طرطوس", "Tartus",
    "إدلب", "Idlib", "ادلب", "الرقة", "Raqqa",
    "دير الزور", "ديرالزور", "Deir ez-Zor", "الحسكة", "Hasakah",
    "القامشلي", "Qamishli", "السويداء", "Suwayda", "درعا", "Daraa",
    "القنيطرة", "Quneitra"
]

# 🔥 20 وكالة أنباء شاملة
RSS_FEEDS = [
    # 🇸🇾 سورية رسمية ⭐
    "https://sana.sy/?feed=rss2",                    # سانا الرسمية
    "https://www.syria.tv/feed",                     # تلفزيون سوريا
    "https://alikhbariah.com/feed/",                 # الإخبارية السورية
    "https://syriasteps.com/feed/",                  # سورياستيبس
    
    # 🌍 عالمية كبرى
    "https://www.aljazeera.com/xml/rss/all.xml",     # الجزيرة
    "http://feeds.bbci.co.uk/news/world/rss.xml",    # بي بي سي
    "https://www.theguardian.com/world/rss",         # الغارديان
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    
    # 🇹🇷 تركية موثوقة
    "https://www.aa.com.tr/ar/rss/default.aspx",     # الأناضول
    "https://trt.global/arabi/rss/",                 # TRT عربي
    
    # 🇸🇦 عربية
    "https://aawsat.com/rss-feed",                   # الشرق الأوسط
    "https://www.alaraby.co.uk/feed.xml",            # العربي الجديد
    "https://www.skynewsarabia.com/rss/world.xml",   # سكاي
    "https://www.alalam.ir/rss",                     # العالم
    "https://asharq.com/rss/feed/1/",                # الشرق
    
    # 🇪🇺 أوروبية
    "https://www.france24.com/en/rss",               # فرانس 24
    "https://www.dw.com/en/rss-top-stories",         # دويتشه فيله
    "https://www.euronews.com/rss.xml",              # يورونيوز
    
    # احتياطي
    "http://feeds.feedburner.com/time/world",
    "https://abcnews.go.com/abcnews/usheadlines",
]

# 🔥 10 حسابات X رسمية سورية
X_ACCOUNTS = [
    {"user": "AH_AlSharaa", "name": "الرئيس أحمد الشرع  "},
    {"user": "syrianmofaex", "name": "الخارجية السورية"},
    {"user": "Sy_Defense", "name": "وزارة الدفاع"},
    {"user": "SyMOEADM", "name": "وزارة الإعلام"},
    {"user": "mocsyr", "name": "وزارة الثقافة"},
    {"user": "SyPresidency", "name": "الرئاسة السورية"},
    {"user": "syrianmoi", "name": "وزارة الداخلية"},
    {"user": "SyrMOfH", "name": "وزارة الصحة"},
    {"user": "SyMOIGov", "name": "الحكومة السورية"}
]

def load_last_tweets():
    """تحميل آخر تغريدات"""
    try:
        if os.path.exists(TWEETS_FILE):
            with open(TWEETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_last_tweets(tweets):
    """حفظ آخر تغريدات"""
    try:
        with open(TWEETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_latest_tweet(username):
    """استخراج آخر تغريدة فعلية"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsBot/8.0'
        }
        url = f"https://x.com/{username}"
        r = requests.get(url, headers=headers, timeout=15)
        
        if 'data-testid="tweetText"' in r.text:
            tweet_match = re.search(r'data-testid="tweetText"[^>]*>(.*?)(?=<div|<a|$)', r.text, re.DOTALL)
            if tweet_match:
                text = re.sub(r'<[^>]+>', '', tweet_match.group(1)).strip()
                if len(text) > 10:
                    return text[:180]
    except:
        pass
    return None

def get_new_tweets():
    """جديد فقط من 10 حسابات"""
    last_tweets = load_last_tweets()
    new_tweets = []
    
    print("🐦 فحص التغريدات الجديدة...")
    
    for account in X_ACCOUNTS:
        latest_tweet = get_latest_tweet(account['user'])
        if latest_tweet:
            last_tweet_id = last_tweets.get(account['user'], "")
            
            # أول مرة أو تغريدة جديدة
            if not last_tweet_id or last_tweet_id != latest_tweet:
                new_tweets.append({
                    'name': account['name'],
                    'username': account['user'],
                    'tweet': latest_tweet
                })
                print(f"  🆕 {account['name']}")
                
                # حفظ كآخر تغريدة
                last_tweets[account['user']] = latest_tweet
            else:
                print(f"  ⏭️ {account['name']} (نفسها)")
        
        time.sleep(2)
    
    # حفظ التحديثات
    save_last_tweets(last_tweets)
    return new_tweets[:6]

def get_rss_news():
    """أخبار سوريا من الوكالات"""
    articles = []
    
    print("📰 فحص الوكالات...")
    for i, url in enumerate(RSS_FEEDS, 1):
        try:
            r = requests.get(url, headers={'User-Agent': 'NewsBot/8.0'}, timeout=10)
            feed = feedparser.parse(r.content)
            
            for entry in feed.entries[:2]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or ''
                
                if any(kw.lower() in f"{title} {summary}".lower() for kw in KEYWORDS_SYRIA):
                    articles.append({
                        'title': title[:130],
                        'link': getattr(entry, 'link', ''),
                        'source': "📰 وكالة"
                    })
                    print(f"  ✅ خبر سوري")
                    break
                    
        except:
            pass
        time.sleep(0.7)
    
    return articles[:4]

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def main():
    print("🚀 البوت الذكي يعمل...")
    
    # جمع الجديد فقط
    new_tweets = get_new_tweets()
    rss_articles = get_rss_news()
    
    # بناء الرسالة
    now_str = datetime.utcnow().strftime("%H:%M UTC")
    msg = f"<b>🇸🇾 تحديث سوريا الجديد</b>

"
    msg += f"<i>⏰ {now_str}</i>

"
    
    # تغريدات جديدة فقط
    if new_tweets:
        msg += "<b>🐦 تغريدات جديدة:</b>

"
        for i, tweet in enumerate(new_tweets, 1):
            msg += f"{i}. <b>{tweet['name']}</b>
"
            msg += f"<code>@{tweet['username']}</code>
"
            msg += f"{tweet['tweet']}

"
    else:
        msg += "<i>🐦 لا تغريدات جديدة</i>

"
    
    # أخبار RSS
    if rss_articles:
        msg += "<b>📰 أخبار سوريا:</b>

"
        for i, article in enumerate(rss_articles, 1):
            msg += f"{i}. <b>{article['title']}</b>
"
            msg += f"{article['source']}
"
            msg += f"<a href='{article['link']}'>🔗 الكامل</a>

"
    
    if not new_tweets and not rss_articles:
        msg += "<i>📭 لا تحديثات جديدة الآن</i>"
    
    msg += "
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"
    msg += "<b>تم تطويره بواسطة:</b>
"
    msg += "<b>محمد محمد جلال الخطيب</b>
"
    msg += "<b>طلاب كليات الإعلام || FMD</b>"
    
    # الإرسال
    success = sum(send_telegram(chat_id, msg) for chat_id in TARGET_CHATS)
    print(f"
🎉 نجح: {success}/2 | {len(new_tweets)} جديد X + {len(rss_articles)} أخبار")

if name == "main":
    main()
