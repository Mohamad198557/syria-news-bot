import os
import time
import logging
from datetime import datetime, timedelta
import requests
import feedparser

# إعداد اللوج
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# متغيرات البيئة من Secrets في GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("❌ BOT_TOKEN أو CHAT_ID غير موجودين في المتغيرات البيئية.")

# 🔥 20 وكالة أنباء عالمية (10 عربي + 10 أجنبي)
RSS_FEEDS = [
    # وكالات عربية
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.alarabiya.net/feeds/1410836791105.xml",
    "https://www.skynewsarabia.com/rss/world.xml",
    "https://www.annahar.com/rss/generalnews",
    "https://asharq.com/rss/feed/1/",
    "https://www.france24.com/ar/tag/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1-%D8%B3%D9%88%D8%B1%D9%8A%D8%A7/rss",
    "https://www.dostor.org/rss/feed",
    "https://www.masrawy.com/rss/all/index.xml",
    "https://www.vetogate.com/rss.xml",
    "https://www.elbalad.news/rss",
    
    # وكالات عالمية
    "https://feeds.reuters.com/reuters/worldNews",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://www.nytimes.com/svc/collections/v1/publish/www.nytimes.com/section/world/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://www.apnews.com/rss/world-news",
    "http://feeds.feedburner.com/time/world",
    "https://www.washingtonpost.com/world/rss_vmz",
    "https://abcnews.go.com/abcnews/usheadlines",
    "https://www.nbcnews.com/news/world?ocid=feeds-world-topstories-rss",
]

# كلمات مفتاحية شاملة لسوريا + الـ 14 محافظة + أحمد الشرع
KEYWORDS = [
    # سوريا عامة
    "Syria", "Syrian", "سوريا", "سوري", "السوريين",
    
    # الـ 14 محافظة سورية كاملة
    "Damascus", "دمشق",
    "Rif Dimashq", "ريف دمشق", "ريف_دمشق",
    "Aleppo", "حلب", "حالپ",
    "Homs", "حمص",
    "Hama", "حماة",
    "Latakia", "Lattakia", "اللاذقية", "لاذقیه",
    "Tartus", "Tartous", "طرطوس",
    "Idlib", "إدلب", "ادلب", "ادلب",
    "Raqqa", "الرقة", "رقه",
    "Deir ez-Zor", "Deir Ezzor", "دير الزور", "ديرالزور", "ديرالزور",
    "Hasakah", "Al-Hasakah", "الحسكة", "حسكة",
    "Qamishli", "القامشلي", "قامشلي",
    "As-Suwayda", "Suwayda", "السويداء", "سويداء",
    "Daraa", "درعا",
    
    # مدن إضافية مهمة
    "Quneitra", "القنيطرة",
    "Palmyra", "تدمر", "پالمیرا",
    
    # الرئيس السوري الحالي
    "Ahmed al-Sharaa", "أحمد الشرع", "أحمد_الشرع", "الشرع",
    "Syrian president", "الرئيس السوري",
    
    # كيانات ومنظمات
    "HTS", "Hayat Tahrir", "هيئة تحرير الشام",
    "SDF", "قسد", "قوات سوريا الديمقراطية",
    
    # دول الجوار والمنطقة
    "Turkey", "تركيا", "Ankara", "أنقرة",
    "Israel", "إسرائيل", "الجولان", "Golan",
    "Lebanon", "لبنان",
    "Iraq", "العراق",
    "Jordan", "الأردن",
]

# كلمات مهمة للتصنيف
IMPORTANT_WORDS = [
    "attack", "strike", "explosion", "war", "conflict", "ceasefire",
    "killed", "injured", "dead", "arrest", "detained", "sanctions",
    "airstrike", "shelling", "bombing", "raid",
    "هجوم", "قصف", "انفجار", "حرب", "نزاع", "وقف إطلاق نار",
    "مقتل", "إصابة", "مصاب", "اعتقال", "احتجاز", "عقوبات",
    "غارة", "عملية", "اجتياح", "مقاومة", "احتلال",
]

TRANSLATE_URL = "https://libretranslate.de/translate"

def get_source_name(url: str) -> str:
    """استخراج اسم الوكالة من URL"""
    u = url.lower()
    sources = {
        "aljazeera.com": "🟢 الجزيرة",
        "alarabiya.net": "🟠 العربية", 
        "skynewsarabia.com": "🔵 سكاي نيوز",
        "reuters.com": "🟡 رويترز",
        "bbc.co.uk": "🔴 بي بي سي",
        "cnn.com": "🟣 CNN",
        "nytimes.com": "⚫ نيويورك تايمز",
        "theguardian.com": "🟠 الغارديان",
        "apnews.com": "🔷 أسوشيتد برس",
        "france24.com": "🔵 فرانس 24",
        "asharq.com": "🟡 عاشرق الأوسط",
        "annahar.com": "🔴 الأنباء",
    }
    for key, name in sources.items():
        if key in u:
            return name
    return "📰 وكالة أنباء"

def contains_keyword(text: str) -> bool:
    """التحقق من وجود كلمات مفتاحية"""
    t = text.lower()
    return any(k.lower() in t for k in KEYWORDS)

def score_news(title: str, summary: str, source_url: str) -> int:
    """حساب درجة أهمية الخبر"""
    text = (title + " " + summary).lower()
    score = 0
    
    source_name = get_source_name(source_url)
    
    # وزن أعلى للوكالات الكبرى
    top_sources = ["رويترز", "بي بي سي", "CNN", "الجزيرة", "العربية", "سكاي"]
    if any(s in source_name for s in top_sources):
        score += 3
    
    # وزن عالي للمحافظات والرئيس
    syria_keywords = ["أحمد الشرع", "الرئيس السوري"] + [k for k in KEYWORDS if any(m in k for m in ["دمشق", "حلب", "إدلب", "حمص"])]
    for w in syria_keywords:
        if w.lower() in text:
            score += 4
    
    # كلمات مهمة
    for w in IMPORTANT_WORDS:
        if w.lower() in text:
            score += 2
    
    return score

def translate_to_arabic(text: str) -> str:
    """ترجمة العنوان للعربية (مع fallback)"""
    try:
        if len(text) > 500:
            text = text[:500]
        
        data = {
            "q": text,
            "source": "auto", 
            "target": "ar",
            "format": "text"
        }
        r = requests.post(TRANSLATE_URL, json=data, timeout=8)
        if r.status_code == 200:
            return r.json().get("translatedText", text[:100])
        return text[:100]
    except:
        return text[:100] + "..."

def get_entry_datetime(entry) -> datetime | None:
    """استخراج تاريخ الخبر من RSS"""
    for date_field in ["published_parsed", "updated_parsed"]:
        if hasattr(entry, date_field) and getattr(entry, date_field):
            dt_tuple = getattr(entry, date_field)
            try:
                return datetime(*dt_tuple[:6])
            except:
                pass
    return None

def send_telegram(message: str) -> bool:
    """إرسال رسالة لتيليجرام"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=data, timeout=15)
        logger.info(f"✅ Telegram: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"❌ Telegram: {e}")
        return False

def run_once():
    """التشغيل الرئيسي - دفعة واحدة لـ GitHub Actions"""
    logger.info("🚀 بدء بوت أخبار سوريا - 20 وكالة عالمية")
    logger.info(f"📅 البحث عن أخبار آخر 48 ساعة - UTC: {datetime.utcnow()}")
    
    articles = []
    now = datetime.utcnow()
    cutoff_date = now - timedelta(hours=48)  # آخر 48 ساعة
    
    successful_feeds = 0
    
    # فحص 20 مصدر
    for i, feed_url in enumerate(RSS_FEEDS, 1):
        source_display = get_source_name(feed_url)
        logger.info(f"[{i:2d}/20] 🔍 {source_display}")
        
        try:
            # جلب RSS مع timeout قصير
            resp = requests.get(feed_url, timeout=12)
            resp.raise_for_status()
            
            feed = feedparser.parse(resp.text)
            if not feed.entries:
                logger.info(f"     لا مقالات في {source_display}")
                continue
                
            successful_feeds += 1
            
            # فحص آخر 12 مقالة فقط من كل مصدر
            for entry in feed.entries[:12]:
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                link = getattr(entry, "link", "")
                
                if not link or len(title) < 10:
                    continue
                
                full_text = f"{title} {summary}"
                
                # 1️⃣ فلترة بالكلمات المفتاحية
                if not contains_keyword(full_text):
                    continue
                
                # 2️⃣ فلترة بالتاريخ (آخر 48 ساعة فقط)
                pub_date = get_entry_datetime(entry)
                if not pub_date or pub_date < cutoff_date:
                    continue
                
                # 3️⃣ حساب الدرجة
                score = score_news(title, summary, feed_url)
                if score < 6:  # حد أدنى أعلى للجودة
                    continue
                
                articles.append({
                    "title": title,
                    "link": link, 
                    "source": source_display,
                    "score": score,
                    "pub_date": pub_date,
                    "summary": summary[:200]
                })
                
        except requests.exceptions.Timeout:
            logger.warning(f"     ⏰ timeout: {source_display}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"     ❌ خطأ شبكة: {source_display} - {e}")
        except Exception as e:
            logger.error(f"     💥 خطأ غير متوقع: {source_display} - {e}")
        
        # تأخير قصير بين المصادر
        time.sleep(0.8)
    
    logger.info(f"📊 تم فحص {successful_feeds}/20 مصدر | وجد {len(articles)} مقال")
    
    if not articles:
        msg = "📭 <b>لا توجد أخبار مهمة</b>\n\n"
        msg += "لم نجد أخبار سورية مهمة خلال آخر 48 ساعة من 20 وكالة عالمية."
        send_telegram(msg)
        return
    
    # ترتيب: الأعلى درجة → الأحدث
    articles.sort(key=lambda x: (x["score"], x["pub_date"]), reverse=True)
    top_articles = articles[:12]  # أفضل 12 خبر
    
    # بناء الرسالة النهائية
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    message = "<b>🚨 أهم أخبار سوريا والمحافظات</b>\n\n"
    message += f"<i>📊 آخر 48 ساعة | {now_str}</i>\n"
    message += f"<i>🔍 {successful_feeds} وكالة | {len(top_articles)} خبر</i>\n\n"
    
    for i, article in enumerate(top_articles, 1):
        title_ar = translate_to_arabic(article["title"])
        message += f"<b>{i:2d}.</b> {title_ar}\n"
        message += f"📻 {article['source']}  |  ⭐{article['score']}\n"
        message += f"🔗 <a href='{article['link']}'>الكامل</a>\n\n"
    
    # قسم المعلومات والاعتمادات
    message += "━━━━━━━━━━━━━━━━━━━━━\n"
    message += "<b>ℹ️ معلومات البوت</b>\n"
    message += "📱 بوت أخبار سوريا المتقدم\n"
    message += "🌍 20 وكالة أنباء عالمية\n"
    message += "⏰ تحديث تلقائي عبر GitHub Actions\n\n"
    message += "<b>👨‍💻 تم تصميم البوت بواسطة:</b>\n"
    message += "<b>محمد محمد جلال الخطيب</b>\n\n"
    message += "<b>🎓 Powered by:</b>\n"
    message += "<b>طلاب كليات الإعلام || FMD</b>"
    
    # إرسال الرسالة
    success = send_telegram(message)
    if success:
        logger.info("🎉 تم إرسال الملخص بنجاح!")
    else:
        logger.error("💥 فشل إرسال الرسالة النهائية")

if __name__ == "__main__":
    run_once()
