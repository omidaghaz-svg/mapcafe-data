#!/usr/bin/env python3
"""استخراج «مکان‌های نقشه» خانوادهٔ غذا (کافه، رستوران، فست‌فود، کباب، طباخی،
آبمیوه و بستنی) از یک فایل PBF اوپن‌استریت‌مپ (ازپیش‌فیلترشده) و ساخت خروجی
گزیپ‌شده برای مصرف سرور Mapto.

این اسکریپت در ریپوی دادهٔ `mapcafe-data` توسط GitHub Actions اجرا می‌شود تا بار
پردازش سنگین از سرور برنامه برداشته شود. سرور فقط فایل گزیپ را دانلود و با دستور
`map:import-cafes` به‌صورت idempotent وارد جدول `map_places` می‌کند.

## چرا یک فایل برای چند نقشه

هر شش نقشهٔ خانوادهٔ غذا از همین یک استخراج تغذیه می‌شوند تا:
- پیمایش PBF (سنگین‌ترین بخش) فقط یک‌بار انجام شود؛
- انتقال به نقشهٔ اختصاصی هر دامنه **فقط با فیلتر `domain`** ممکن باشد و نیازی
  به استخراج مجدد نباشد.

## چند دامنه برای یک مکان (مکان ترکیبی)

یک مکان می‌تواند هم‌زمان عضو چند دامنه باشد؛ مثلاً «کافه‌رستوران»
(`amenity=restaurant` + `cuisine=cafe`) هم روی نقشهٔ کافه و هم روی نقشهٔ رستوران
می‌آید، و «رستوران کبابی» (`amenity=restaurant` + `cuisine=kebab`) روی نقشهٔ
رستوران و نقشهٔ کباب. پس هر مکان فیلد `domains` (فهرست دامنه‌ها) دارد و فیلد
`domain` (تک‌مقداری) فقط دامنهٔ اصلی/نمایشی را برای سازگاری عقب‌رو نگه می‌دارد.

دامنه‌ها و ترتیب تقدم دامنهٔ اصلی: `cafe` > `juice_icecream` > `tabbakh` >
`kebab` > `fastfood` > `restaurant`.

## قاعدهٔ «سازگاری با نقشهٔ فعلی»

دامنه‌های کافه و آبمیوه/بستنی باید **دقیقاً** همان مجموعهٔ پیشین را نگه دارند تا
نقشهٔ فعلی کوچک‌ترین تغییر را ببیند؛ گسترش فقط **افزایشی** است:
- چیزی از نقشهٔ کافه حذف نمی‌شود (شمار کافه بدون تغییر می‌ماند)؛
- نقشهٔ آبمیوه/بستنی فقط مکان‌های «ترکیبی» را اضافه می‌گیرد (نقشهٔ پیشین زیرمجموعهٔ
  نقشهٔ جدید است).
سیگنال کافه در cuisine (`coffee`/`tea`/`cake`/...) به‌تنهایی «عضو‌کننده» نیست؛
فقط مکانی را که از مسیر دیگری (کافه یا آبمیوه) عضو شده، در دامنهٔ کافه هم نگه
می‌دارد. این آینهٔ رفتار پیشین `MapPlaceTags::domain()` است.

## چرا ورودی «ازپیش‌فیلترشده» است

فایل `iran-latest.osm.pbf` حدود ۲۷ میلیون گره دارد. اجرای callbackهای پایتونی روی
همهٔ آن‌ها بیش از ۱۵ دقیقه طول می‌کشد و به سقف زمانی Actions نزدیک می‌شود. بنابراین
ورک‌فلو ابتدا با ابزار C++ اوپن‌استریت‌مپ (سریع، چند ثانیه) سه مرحله را اجرا می‌کند:

    1. osmium tags-filter iran.osm.pbf <filters> -o candidates.osm.pbf
       (پیش‌فرض `tags-filter` گره‌های ارجاع‌شدهٔ wayها و اعضای relationها را هم
        به خروجی می‌افزاید، پس هندسهٔ کامل در دسترس است.)
    2. osmium add-locations-to-ways candidates.osm.pbf -o candidates-loc.osm.pbf
       (مختصات گره‌های هر way را داخل خودِ way تزریق می‌کند.)
    3. python extract-cafes.py candidates-loc.osm.pbf cafes.json.gz

سپس همین اسکریپت روی فایل کوچک (چند صد کیلوبایت) اجرا می‌شود و در کسری از ثانیه
به پایان می‌رسد. اگر همین اسکریپت را مستقیم روی PBF کامل ایران اجرا کنید کار می‌کند
اما بسیار کند خواهد بود؛ برای اجرای محلی از همان سه دستور بالا استفاده کنید.

## قواعد مرجع

`docs/map-places-ownership.md` §۲. مجموعهٔ تگ‌ها باید با
`app/Domains/Cafe/Support/MapPlaceTags.php` هم‌راستا بماند (`matchingDomains()`).
طبقه‌بندی دامنهٔ اصلی نیز باید با `MapPlaceTags::domain()` یکی بماند. همگام‌سازی
سمت سرور (چند‌دامنه‌شدن `map_places.domain`) با انتقال ماژول نقشه به `Core/Map`
انجام می‌شود؛ تا آن زمان سرور ردیف‌های دامنه‌های جدید را نادیده می‌گیرد و
نقشهٔ کافه/آبمیوه بدون تغییر می‌ماند.

## ساختار خروجی (سازگار با MapPlaceImportService)

    {"generated_at": "2026-10-09T00:00:00Z", "places": [
        {"osm_type": "node", "osm_id": 123, "lat": 35.7, "lng": 51.4,
         "domain": "cafe", "tags": {"amenity": "cafe", "name": "..."}}
    ]}

برای `way` و `relation`، مختصات مرکز به‌صورت میانگین مکان اعضا محاسبه می‌شود
(برای relation فقط اعضای غیرِ `inner` تا حفره‌های multipolygon مرکز را جابه‌جا نکنند).

استفاده:
    python extract-cafes.py candidates-loc.osm.pbf cafes.json.gz
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import datetime, timezone

import osmium


DOMAIN_CAFE = "cafe"
DOMAIN_RESTAURANT = "restaurant"
DOMAIN_FASTFOOD = "fastfood"
DOMAIN_KEBAB = "kebab"
DOMAIN_TABBAKH = "tabbakh"
DOMAIN_JUICE_ICECREAM = "juice_icecream"

# ترتیب تقدم دامنهٔ اصلی (اول = بالاتر). فقط برای انتخاب `domain` تک‌مقداری است؛
# عضویت در `domains` از این ترتیب مستقل است.
DOMAIN_PRIORITY = (
    DOMAIN_CAFE,
    DOMAIN_JUICE_ICECREAM,
    DOMAIN_TABBAKH,
    DOMAIN_KEBAB,
    DOMAIN_FASTFOOD,
    DOMAIN_RESTAURANT,
)

# cuisineهایی که «کافه‌بودن» را ثابت می‌کنند.
CAFE_CUISINES = frozenset({"cafe", "coffee_shop"})
# سیگنال‌های «کافه‌بودن» در cuisine (coffee/tea/cake/...). این‌ها **عضو‌کنندهٔ**
# مستقل نیستند؛ فقط مکانی را که از مسیر دیگری عضو شده، در دامنهٔ کافه هم نگه
# می‌دارند (آینهٔ رفتار پیشین `MapPlaceTags::domain()`).
CAFE_SIGNAL_CUISINES = frozenset({
    "cafe", "coffee_shop", "coffee", "tea", "cake", "dessert",
    "pastry", "bakery", "breakfast", "brunch", "chocolate",
})
# cuisineهایی که «آبمیوه/بستنی‌بودن» را ثابت می‌کنند.
JUICE_CUISINES = frozenset({"juice", "smoothie", "ice_cream"})
# مقادیر اصلی که به‌تنهایی دامنهٔ آبمیوه و بستنی را قطعی می‌کنند.
JUICE_AMENITIES = frozenset({"ice_cream", "juice_bar"})
JUICE_SHOPS = frozenset({"ice_cream", "juice"})
# cuisineهای کباب: کباب، کوبیده، و جگرکی (جگر/دل و قلوه). املاهای رایج OSM
# پذیرفته شده‌اند تا پوشش بیشتر شود. تطبیق «شامل‌بودن» است تا مقادیر ترکیبی
# فارسی/چندتکه (`کباب_کاکوری`, `kebab;persian`) هم گرفته شوند.
KEBAB_CUISINE_KEYWORDS = (
    "kebab", "kabab", "kebaab", "koobideh", "kubideh",
    "doner", "döner", "shawarma", "shaorma", "iskender",
    "jigar", "jigaraki", "jegar", "liver", "offal", "del", "dil",
    "کباب", "کوبیده", "جگر", "دلوقلوه", "دونر",
)
# cuisineهای طباخی: دیزی/آبگوشت/کله‌پاچه/سیراب و شیردان، به‌علاوهٔ غذاهای
# سنتیِ قلمروِ طباخی که کاربر خواست: آش، حلیم، شله مشهدی، بریانی، کوفته،
# هریسه، دلمه و عدسی. تگ استاندارد OSM برای این‌ها کم‌کاربرد است؛ هم املاهای
# لاتین و هم فارسی پذیرفته شده‌اند تا پوشش بیشتر شود.
TABBAKH_CUISINE_KEYWORDS = (
    "dizi", "abgoosht", "abgusht",
    "kale_pache", "kalle_pache", "kalepache",
    "kale_pacheh", "kalle_pacheh", "kaleh_pacheh", "kaleh_pache",
    "sirab", "shirdan", "sirab_shirdan", "tabbakh", "tabakh",
    "ash", "halim", "haleem", "harissa", "sholeh", "shole",
    "biryani", "beriyani", "kofta", "koftah", "kofteh", "koofteh", "kufta", "kofte",
    "dolma", "dolmeh", "soup",
    "دیزی", "آبگوشت", "کلهپاچه", "سیراب", "شیردان", "طباخی",
    "آش", "حلیم", "هلیم", "شله", "بریانی", "کوفته", "هریسه", "دلمه",
    "عدسی", "سوپ", "شوربا", "پاچه", "اشکده", "آشکده", "آشی", "آشپزی",
)
# تگ‌های کترینگ (زیرمجموعهٔ رستوران). `craft=caterer` تگ رسمی OSM است و
# `shop=catering`/`amenity=catering` هم در داده دیده می‌شوند.
CATERING_SHOPS = frozenset({"catering"})
CATERING_AMENITIES = frozenset({"catering"})
CATERING_CRAFTS = frozenset({"caterer", "catering"})
# مکان‌هایی که «غذاخوری» شمرده می‌شوند. قواعد نام‌محور فقط روی این‌ها اعمال
# می‌شوند تا مثلاً مدرسه‌ای به نام «دبیرستان کباب» یا فروشگاه کابینت به نام
# «کابینت آشپزخانه مهدی» وارد نقشه نشود.
FOOD_AMENITIES = frozenset({
    "cafe", "restaurant", "fast_food", "food_court",
    "ice_cream", "juice_bar", "catering",
    # `bbq` و `biergarten` در ایران عملاً برای کبابی/باغ‌رستوران به کار می‌روند
    # (شاهد داده: «چلوکبابی سلیمانی» و «کبابی برگ» با `amenity=bbq`).
    "bbq", "biergarten",
})
# فروشگاه‌ها/پیشه‌های غذاخوری که بدون `amenity` هم «غذاخوری» شمرده می‌شوند.
# فهرست بسته است تا `shop=kitchen`/`craft=carpenter` ناخواسته وارد نشوند.
# `deli` هم کسب‌وکار غذای آماده است (شاهد داده: «کبابی باباعلی» با `shop=deli`).
FOOD_SHOPS = frozenset({"coffee", "ice_cream", "juice", "catering", "deli"})
FOOD_CRAFTS = frozenset({"caterer", "catering"})

# کلیدواژه‌های نام (فارسی، بدون فاصله/نیم‌فاصله پس از نرمال‌سازی). OSM در ایران
# برای کبابی/جگرکی/طباخی/کترینگ تقریباً هیچ تگ استانداردی ندارد؛ پس نام مکان
# تنها سیگنال در دسترس است. این کلیدواژه‌ها فقط دامنه‌های restaurant/kebab/tabbakh
# را تحت تأثیر قرار می‌دهند و به دامنهٔ کافه/آبمیوه دست نمی‌زنند.
KEBAB_NAME_KEYWORDS = (
    "کباب",       # کباب، کبابی، کباب‌پز، کباب‌سرا، چلوکباب
    "جگرکی",      # جگرکی
    "جگر",        # جگر، جگرچه
    "دلوقلوه",    # دل و قلوه
    "دونر",       # کباب ترکی
)
TABBAKH_NAME_KEYWORDS = (
    "کلهپاچه",   # کله‌پاچه، کله پاچه
    "کلهپزی",    # کله‌پزی، کله پزی
    "سیراب",      # سیراب (شیردان)
    "شیردان",
    "آبگوشت",     # آبگوشت، آبگوشتی
    "طباخی",
    "طباخ",
    "حلیم",       # حلیم، حلیم‌فروشی، حلیم بادمجان
    "هلیم",       # «آش و هلیم» (املای رایج دیگر)
    "شله",        # شله مشهدی، شله قلمکار
    "بریانی",     # بریانی اصفهانی
    "کوفته",      # کوفته تبریزی
    "هریسه",      # هریسه (حلوا‌شکری سنتی)
    "دلمه",       # دلمه، دلمه‌پزخانه
    "عدسی",       # عدسی‌فروشی
    "شوربا",      # شوربا (آش/خورش سنتی)
)
# کلیدواژه‌های کوتاه/مبهم طباخی که تطبیق **مرزکلمه‌ای** لازم دارند. تطبیق
# زیررشته‌ای «آش» ناخواسته «آشپزخانه» (برند رایج رستوران)، «آشنا»، «آشتی»،
# «آشوری» و «سرآشپز» را می‌گیرد. پس فقط کلمهٔ کامل پذیرفته می‌شود و شکل‌های
# صرفی درست («آشی»، «آشکده»، «آشپزی») صریحاً فهرست شده‌اند.
TABBAKH_NAME_TOKEN_KEYWORDS = (
    "آش",         # آش، آش آبادان، آش و حلیم، آش سرای مادر
    "آشی",        # آشی فردوسی
    "آشکده",      # آشکده خاتون
    "آشپزی",      # آشپزی جنوب
    "آشفروشی",    # آش فروشی (اگر نیم‌فاصله نداشته باشد یک کلمه است)
    "سوپ",        # سوپ؛ از «سوپرمارکت» جدا می‌شود
    "پاچه",       # پاچه‌پزی
    "بریان",      # بریان پلو؛ عمداً بدون قاف تا «بریانک» (محله) گرفته نشود
    "دیزی",       # دیزی‌سرا؛ عمداً مرزکلمه‌ای تا «دیزین» (پیست اسکی) گرفته نشود
)
CATERING_NAME_KEYWORDS = (
    "کترینگ",
    "کیترینگ",
    "catering",
    "تهیهغذا",    # تهیه غذا (کترینگ خانگی)
    "پذیرایی",    # پذیرایی و کترینگ
)
# کلیدواژه‌های نام دامنهٔ **فست‌فود**. بخش بزرگی از ساندویچی/پیتزایی/برگری/
# ساندویچی‌های OSM ایران با `amenity=restaurant` ثبت شده‌اند؛ نتیجه این بود که
# روی نقشهٔ رستوران می‌افتادند و نقشهٔ فست‌فود خالی می‌ماند. این کلیدواژه‌ها
# چنین مکانی را به دامنهٔ فست‌فود می‌برند و (به‌شرط نبودن واژهٔ «رستوران» در نام)
# از نقشهٔ رستوران برمی‌دارند تا نقشهٔ رستوران فقط رستوران واقعی نشان دهد.
# توجه: `normalize_name` فاصله/نیم‌فاصله را برمی‌دارد؛ پس «فست فود» و
# «فست‌فود» هر دو یکسان تطبیق می‌شوند و برند «فستیز» ناخواسته گرفته نمی‌شود.
FASTFOOD_NAME_KEYWORDS = (
    "ساندویچ",    # ساندویچ، ساندویچی، ساندویچ‌فروشی
    "ساندویج",    # املای رایج دیگر (شاهد داده: «ساندویج فروشی قاسمی»)
    "فلافل",
    "شاورما",
    "پیتزا",      # پیتزا، پیتزافروشی، پیتزاچی، پیتزاکاملی
    "برگر",       # برگر، همبرگر، چیزبرگر، برگرلند
    "هاتداگ",     # هات‌داگ و هات داگ
    "فستفود",     # فست فود و فست‌فود
    "دونر",       # دونر، دونرکباب، دونر گاردن
    "döner",
    "sandwich", "falafel", "shawarma", "pizza", "burger", "hotdog", "doner",
)
# «دنر» (بدون واو) املای رایج دیگری است که فقط با تطبیق **مرزکلمه‌ای** سنجیده
# می‌شود تا در واژه‌های دیگر ناخواسته تطبیق نشود (شاهد داده: «دنر ترک»).
FASTFOOD_NAME_TOKEN_KEYWORDS = ("دنر",)
# نام‌هایی که **محصول نانوایی**اند، نه فست‌فود: «نان ساندویچی» یعنی نانِ مخصوص
# ساندویچ (کالای نانوایی)، نه مغازهٔ ساندویچی. این‌ها از دامنهٔ فست‌فود بیرون
# می‌مانند (شاهد داده: «نان ساندویچی» با `amenity=biergarten`).
FASTFOOD_NAME_EXCLUDED = (
    "نانساندویچ",   # نان ساندویچی
    "نانساندویج",   # نان ساندویجی
    "نانپیتزا",     # نان پیتزایی
    "نانبرگر",      # نان برگر
    "نانهمبرگر",    # نان همبرگر
    "نانهاتداگ",    # نان هات‌داگ
)
# نام‌هایی که صریحاً «رستوران» بودن را اعلام می‌کنند. مغازهٔ فست‌فودی که نامش
# «رستوران» هم دارد (مثل «رستوران و فست فود پرک») کسب‌وکار **ترکیبی** است؛
# پس روی هر دو نقشه می‌ماند (قاعدهٔ بند ۱۳).
RESTAURANT_NAME_KEYWORDS = ("رستوران", "restaurant")


def tag_values(tags: dict, key: str) -> list:
    """تگ چندمقداری را به فهرست مقادیر کوچک‌شده می‌شکند (جداکنندهٔ `;`)."""
    raw = str(tags.get(key, "") or "")
    return [part.strip().lower() for part in raw.split(";") if part.strip()]


# اعراب، شدّه، همزهٔ ترکیبی (مثل «هٔ»)، تنوین، کشیده و نویسه‌های کنترلی جهت‌دهی
# که در تطبیق نام بی‌اثرند. بازهٔ \u064b-\u065f همزهٔ بالای «ه» را هم می‌گیرد تا
# «آشکدهٔ» با «آشکده» یکسان دیده شود. نیم‌فاصله اینجا **حذف نمی‌شود** تا در
# تطبیق مرزکلمه‌ای، «دیزی‌سرا» به دو کلمه «دیزی» و «سرا» شکسته شود.
_NAME_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u0640\u200e\u200f]")
# فاصله و نشانه‌های نگارشی که برای تطبیق مقاوم حذف/شکسته می‌شوند.
_NAME_SEPARATORS = re.compile(r"[\s\-_.,،؛;:!?؟()\[\]{}«»\"'\\/|*+#@&+=~^%$]+")
# نیم‌فاصله/فاصلهٔ مجازی که در نام‌های فارسی «مرز کلمه» است.
_NAME_JOINERS = re.compile(r"[\u200c\u200d]+")
# مرز کلمه: فاصله/نشانه‌ها یا نیم‌فاصله.
_NAME_TOKEN_SPLIT = re.compile(r"[\s\-_.,،؛;:!?؟()\[\]{}«»\"'\\/|*+#@&+=~^%$]+|[\u200c\u200d]+")


def _normalize_letters(value: str) -> str:
    """حروف را یکسان می‌کند و اعراب/نیم‌فاصله/جهت‌دهی را برمی‌دارد (بدون حذف فاصله).

    خروجی هنوز فاصله/نشانه دارد؛ برای تطبیق «مرزکلمه‌ای» به همین شکل نیاز است
    (تفکیک «آش» از «آشپزخانه» و «آشتی»).
    """
    text = str(value or "").strip().lower()
    if not text:
        return ""

    # یکسان‌سازی نویسه‌های عربی/فارسی پرکاربرد در نام‌های ایرانی.
    text = (
        text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
        .replace("ة", "ه").replace("ۀ", "ه").replace("أ", "ا")
        .replace("إ", "ا").replace("آ", "ا").replace("ؤ", "و")
    )
    text = _NAME_DIACRITICS.sub("", text)

    return text


def normalize_name(value: str) -> str:
    """نام را برای تطبیق کلیدواژه‌ای نرمال می‌کند (بدون فاصله/نشانه).

    چرا لازم است: نام مکان‌های OSM در ایران با املای متفاوت ثبت می‌شوند
    («کله‌پاچه» با نیم‌فاصله، «کله پاچه» با فاصله، «كله پاچه» با کاف عربی،
    «کله پاچة» با هٔ عربی). پس ابتدا حروف عربی به فارسی یکسان می‌شوند، سپس
    اعراب/نیم‌فاصله/جهت‌دهی حذف می‌شود و در پایان همهٔ فاصله‌ها و نشانه‌ها
    برداشته می‌شود تا «کله پاچه»، «کله‌پاچه» و «کله-پاچه» یکسان دیده شوند.
    """
    return _NAME_JOINERS.sub("", _NAME_SEPARATORS.sub("", _normalize_letters(value)))


def name_tokens(value: str) -> list:
    """نام را به کلمه‌های نرمال‌شده می‌شکند (برای تطبیق مرزکلمه‌ای).

    مثال: «آش و حلیم آنا» به `["آش", "و", "حلیم", "انا"]` می‌شکند. تطبیق مرزکلمه‌ای لازم
    است چون در تطبیق زیررشته‌ای، «آش» ناخواسته با «آشپزخانه» (برند رایج
    رستوران)، «آشنا»، «آشتی» و «سرآشپز» هم می‌خورد.
    """
    return [token for token in _NAME_TOKEN_SPLIT.split(_normalize_letters(value)) if token]


# کلیدهایی که نام مکان ممکن است در آن‌ها باشد. بعضی مکان‌های ایران نام فارسی را
# فقط در `name:fa` دارند و `name` لاتین/بیگانه است (مثل `sina tabakhi`)، پس
# تطبیق نام‌محور باید همهٔ این کلیدها را ببیند.
NAME_KEYS = ("name", "name:fa", "official_name", "alt_name")


def name_values(tags: dict) -> list:
    """همهٔ نام‌های مکان از کلیدهای نام‌دار (بدون تکرار و تهی)."""
    values = []
    for key in NAME_KEYS:
        value = tags.get(key)
        if value:
            values.append(str(value))
    return values


def name_has_keyword(tags: dict, keywords) -> bool:
    """آیا نام مکان یکی از کلیدواژه‌ها را دارد؟ (هر دو طرف نرمال می‌شوند)

    کلیدواژه‌ها هم نرمال می‌شوند تا حروف عربی/فارسی (مثل «آ» در «آبگوشت») و
    فاصله‌ها در نام و کلیدواژه یکسان دیده شوند.
    """
    normalized_keywords = [normalize_name(keyword) for keyword in keywords]
    for value in name_values(tags):
        normalized = normalize_name(value)
        if normalized and any(keyword in normalized for keyword in normalized_keywords):
            return True
    return False


def name_has_token(tags: dict, keywords) -> bool:
    """آیا یکی از کلمه‌های نام **دقیقاً** برابر کلیدواژه‌ای است؟ (تطبیق مرزکلمه‌ای)

    برای کلیدواژه‌های کوتاه/مبهم (مثل «آش» و «سوپ») که تطبیق زیررشته‌ای‌شان
    ناخواسته «آشپزخانه»/«آشنا»/«سوپرمارکت» را می‌گیرد. شکل‌های صرفی رایج
    («آشی»، «آشکده»، «آشپزی») به‌عنوان کلیدواژهٔ مستقل فهرست شده‌اند، نه با
    پیشوندگیری خودکار.
    """
    normalized = {normalize_name(keyword) for keyword in keywords}
    for value in name_values(tags):
        if any(token in normalized for token in name_tokens(value)):
            return True
    return False


def cuisine_has_keyword(tags: dict, keywords) -> bool:
    """آیا cuisine مکان یکی از کلیدواژه‌ها را دارد؟ (هر دو نرمال می‌شوند)

    مقدار cuisine در ایران هم لاتین (`ash`, `halim`) و هم فارسی
    (`حلیم`, `آش_و_حلیم`) و گاه چندتکه با `_` ثبت شده است. نرمال‌سازی `_` را
    برمی‌دارد؛ پس «آش_و_حلیم» شامل «آش» و «حلیم» می‌شود و «کباب_کاکوری» شامل
    «کباب». چون فهرست cuisine فقط نامِ غذا است (نه نام کسب‌وکار)، تطبیق
    زیررشته‌ای اینجا خطای «آشپزخانه» را ندارد.

    کلیدواژه‌های **کوتاه** (کمتر از ۴ نویسه پس از نرمال‌سازی، مثل `ash`، `del`
    و «آش») فقط با تطبیق **کلمهٔ کامل** سنجیده می‌شوند؛ چون نرمال‌سازی «آ» به
    «ا» رشتهٔ «آش» را به «اش» تبدیل می‌کند که با «اشکان»/«باشگاه» هم می‌خورد.
    """
    substring = [
        normalize_name(keyword) for keyword in keywords
        if len(normalize_name(keyword)) >= 4
    ]
    tokens = {
        normalize_name(keyword) for keyword in keywords
        if len(normalize_name(keyword)) < 4
    }
    for value in tag_values(tags, "cuisine"):
        normalized = normalize_name(value)
        if any(keyword in normalized for keyword in substring):
            return True
        if tokens and (set(name_tokens(value)) & tokens):
            return True
    return False


def matching_domains(tags: dict) -> list:
    """دامنه‌های نقشه‌ای که این عنصر عضو آن‌هاست (می‌تواند چندتا باشد).

    عضویت هر دامنه **مستقل** سنجیده می‌شود تا «مکان ترکیبی» روی همهٔ نقشه‌های
    مربوط بیاید (کافه‌رستوران روی نقشهٔ کافه و رستوران). خروجی به ترتیب
    `DOMAIN_PRIORITY` است؛ پس عنصر اول «دامنهٔ اصلی» است.

    باید با `MapPlaceTags::matchingDomains()` سرور هم‌راستا بماند؛ در غیر این
    صورت ردیف‌های اضافی ساخته می‌شود که import آن‌ها را دور می‌ریزد.

    قواعد عضویت (پایهٔ کافه و آبمیوه دقیقاً همان قواعد پیشین `matches()`/`domain()`
    است تا نقشهٔ فعلی تغییر نکند):
    - `cafe`: `amenity=cafe` یا `shop=coffee` یا (`amenity` موجود و cuisine شامل
      `cafe`/`coffee_shop`)؛ به‌علاوهٔ مکان‌هایی که از مسیر آبمیوه عضو شده‌اند و
      سیگنال کافه دارند (`coffee`/`tea`/`cake`/...)؛ آینهٔ تقدم کافه در رفتار
      پیشین که کافه/رستوران چندنوعی را از نقشهٔ بستنی بیرون می‌گذاشت.
    - `juice_icecream`: `amenity∈{ice_cream,juice_bar}` یا
      `shop∈{ice_cream,juice}` یا (`amenity` موجود و cuisine شامل
      `juice`/`smoothie`/`ice_cream`).
    - `tabbakh`: `amenity` موجود و cuisine شامل املاهای طباخی
      (`dizi`/`abgoosht`/`kale_pache`/`sirab`/`shirdan`/`ash`/`halim`/`sholeh`/
      `biryani`/`kofta`/...) **یا** نام غذاخوری شامل کلیدواژه‌های طباخی
      (کله‌پاچه/کله‌پزی/سیراب/شیردان/دیزی/آبگوشت/طباخی/آش/حلیم/شله/بریانی/
      کوفته/هریسه/عدسی/شوربا).
    - `kebab`: `amenity` موجود و cuisine شامل `kebab`/`koobideh`/`jigar`/`liver`
      و هم‌خانواده‌ها **یا** نام غذاخوری شامل کلیدواژه‌های کباب
      (کباب/جگرکی/جگر/دل و قلوه).
    - `fastfood`: `amenity=fast_food` **یا** نام غذاخوری شامل کلیدواژه‌های
      فست‌فود (ساندویچ/ساندویج/فلافل/شاورما/پیتزا/برگر/هات‌داگ/فست فود/دونر).
    - `restaurant`: `amenity=restaurant` **یا** تگ کترینگ
      (`shop=catering`/`amenity=catering`/`craft=caterer`) **یا** نام شامل
      کلیدواژه‌های کترینگ (کترینگ/کیترینگ/تهیه غذا/پذیرایی).

    **تمیزکاری نقشهٔ رستوران (قاعدهٔ مهم):** OSM در ایران بسیاری از
    ساندویچی/پیتزایی/برگری/فلافلی و مغازه‌های «فست فود» را
    `amenity=restaurant` ثبت کرده است. چنین مکانی رستوران نیست و نباید روی
    نقشهٔ رستوران بیاید؛ پس وقتی سیگنال نام فست‌فود وجود دارد، دامنهٔ
    `restaurant` **برداشته** می‌شود. دو استثنا: (۱) مکان **کترینگ** (تگ یا نام
    کترینگ/پذیرایی) زیرمجموعهٔ رستوران است و می‌ماند؛ (۲) مکانی که نامش صریحاً
    واژهٔ «رستوران» را دارد، کسب‌وکار ترکیبی است و روی هر دو نقشه می‌ماند.
    این قاعده به دامنهٔ `cafe`/`juice_icecream`/`kebab`/`tabbakh` دست نمی‌زند.

    **دو نکتهٔ دقتی:** (۱) نام‌ها با تطبیق زیررشته‌ای سنجیده می‌شوند تا شکل‌های
    صرفی («چلوکبابی»، «حلیم‌فروشی»، «آشپزی») گرفته شوند؛ اما کلیدواژه‌های کوتاه
    و مبهم طباخی («آش»، «سوپ»، «پاچه»، «بریان») با تطبیق **مرزکلمه‌ای** سنجیده
    می‌شوند تا «آشپزخانه» (برند رایج رستوران)، «آشتی»، «آشوری»، «سرآشپز» و
    «سوپرمارکت» ناخواسته وارد نشوند. (۲) قواعد نام‌محور فقط روی «غذاخوری»های
    فهرست‌بسته اعمال می‌شوند (`amenity` غذایی، `shop`/`craft` غذایی، `food=*` یا
    `cuisine=*`) تا «کابینت آشپزخانه» و «دبیرستان کباب» وارد نقشه نشوند.
    """
    amenity = str(tags.get("amenity", "") or "")
    shop = str(tags.get("shop", "") or "")
    craft = str(tags.get("craft", "") or "")
    cuisine = tag_values(tags, "cuisine")
    has_amenity = amenity != ""
    # «غذاخوری» بودن با فهرست بسته سنجیده می‌شود: `amenity` غذایی، یا `shop`/
    # `craft` غذایی (مثل `craft=caterer`). `amenity` ناشناخته (مثل school) یا
    # `shop` غیرغذایی (مثل kitchen/cabinet_maker) نام‌محور پذیرفته نمی‌شود؛ وگرنه
    # «کابینت آشپزخانه مهدی» وارد نقشهٔ طباخی می‌شد.
    # `food=*` و `cuisine=*` هم سیگنال غذاخوری‌اند؛ بعضی آشکده‌ها/حلیم‌فروشی‌ها
    # فقط با همین تگ‌ها ثبت شده‌اند و هیچ `amenity`/`shop` ندارند.
    is_food_poi = (
        amenity in FOOD_AMENITIES
        or shop in FOOD_SHOPS
        or craft in FOOD_CRAFTS
        or "food" in tags
        or bool(cuisine)
    )

    # پایهٔ کافه: همان شرط پذیرش پیشین.
    cafe_base = (
        amenity == "cafe"
        or shop == "coffee"
        or (has_amenity and any(value in CAFE_CUISINES for value in cuisine))
    )
    # پایهٔ آبمیوه/بستنی: همان شرط پذیرش پیشین.
    juice_base = (
        amenity in JUICE_AMENITIES
        or shop in JUICE_SHOPS
        or (has_amenity and any(value in JUICE_CUISINES for value in cuisine))
    )

    found = set()

    # تقدم کافه: مکانی که آبمیوه‌ای است ولی سیگنال کافه دارد، در دامنهٔ کافه هم می‌ماند.
    if cafe_base or (juice_base and any(value in CAFE_SIGNAL_CUISINES for value in cuisine)):
        found.add(DOMAIN_CAFE)
    if juice_base:
        found.add(DOMAIN_JUICE_ICECREAM)
    if amenity == "restaurant":
        found.add(DOMAIN_RESTAURANT)
    if amenity == "fast_food":
        found.add(DOMAIN_FASTFOOD)
    # فست‌فود نام‌محور: ساندویچی/پیتزایی/برگری که OSM آن را restaurant ثبت
    # کرده هم فست‌فود است (نقشهٔ رستوران در پایان از این‌ها پاک می‌شود).
    fastfood_by_name = (
        is_food_poi
        and not name_has_keyword(tags, FASTFOOD_NAME_EXCLUDED)
        and (
            name_has_keyword(tags, FASTFOOD_NAME_KEYWORDS)
            or name_has_token(tags, FASTFOOD_NAME_TOKEN_KEYWORDS)
        )
    )
    if fastfood_by_name:
        found.add(DOMAIN_FASTFOOD)
    # کباب: تگ cuisine یا نام مکان (چون OSM برای جگرکی/کبابی تگ استاندارد ندارد).
    if ((has_amenity or is_food_poi) and cuisine_has_keyword(tags, KEBAB_CUISINE_KEYWORDS)) \
            or (is_food_poi and name_has_keyword(tags, KEBAB_NAME_KEYWORDS)):
        found.add(DOMAIN_KEBAB)
    # طباخی: تگ cuisine یا نام مکان (کله‌پاچه/سیراب شیردان/دیزی/آبگوشت/آش/حلیم/
    # شله مشهدی/بریانی/کوفته/هریسه). نام‌های کوتاه (آش/سوپ/پاچه) مرزکلمه‌ای‌اند.
    if ((has_amenity or is_food_poi) and cuisine_has_keyword(tags, TABBAKH_CUISINE_KEYWORDS)) \
            or (is_food_poi and (
                name_has_keyword(tags, TABBAKH_NAME_KEYWORDS)
                or name_has_token(tags, TABBAKH_NAME_TOKEN_KEYWORDS)
            )):
        found.add(DOMAIN_TABBAKH)
    # کترینگ زیرمجموعهٔ رستوران است.
    is_catering = (
        shop in CATERING_SHOPS
        or amenity in CATERING_AMENITIES
        or craft in CATERING_CRAFTS
        or (is_food_poi and name_has_keyword(tags, CATERING_NAME_KEYWORDS))
    )
    if is_catering:
        found.add(DOMAIN_RESTAURANT)

    # تمیزکاری نقشهٔ رستوران: مغازهٔ فست‌فودی که با تگ اشتباه `amenity=restaurant`
    # ثبت شده رستوران نیست. استثنا: کترینگ (زیرمجموعهٔ رستوران) و مکانی که
    # نامش صریحاً «رستوران» دارد (کسب‌وکار ترکیبی، مثل «رستوران و فست فود پرک»).
    if (
        fastfood_by_name
        and DOMAIN_RESTAURANT in found
        and not is_catering
        and not name_has_keyword(tags, RESTAURANT_NAME_KEYWORDS)
    ):
        found.discard(DOMAIN_RESTAURANT)

    return [name for name in DOMAIN_PRIORITY if name in found]


# --- خودآزمون طبقه‌بندی -----------------------------------------------------
# این جدول، قرارداد طبقه‌بندی را قفل می‌کند: اگر کسی قاعده‌ای را اشتباه عوض کند،
# ورک‌فلو پیش از استخراج شکست می‌خورد و نسخهٔ سالم قبلی روی سرور جایگزین نمی‌شود.
# ترتیب دامنه‌ها در هر ردیف باید دقیقاً همان ترتیب `DOMAIN_PRIORITY` باشد.
SELF_TEST_CASES = (
    # کافه و آبمیوه: رفتار باید عیناً مثل نسخهٔ پیشین بماند.
    ({"amenity": "cafe"}, ["cafe"]),
    ({"amenity": "cafe", "cuisine": "ice_cream"}, ["cafe", "juice_icecream"]),
    ({"shop": "coffee"}, ["cafe"]),
    ({"amenity": "ice_cream"}, ["juice_icecream"]),
    ({"shop": "juice"}, ["juice_icecream"]),
    ({"amenity": "fast_food", "cuisine": "juice;ice_cream"}, ["juice_icecream", "fastfood"]),
    ({"amenity": "restaurant", "cuisine": "cake;coffee_shop"}, ["cafe", "restaurant"]),
    # مکان ترکیبی: روی همهٔ نقشه‌های مربوط می‌آید.
    ({"amenity": "restaurant", "cuisine": "cafe"}, ["cafe", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "kebab"}, ["kebab", "restaurant"]),
    ({"amenity": "fast_food", "cuisine": "kebab"}, ["kebab", "fastfood"]),
    # رستوران و فست‌فود تگ‌محور.
    ({"amenity": "restaurant"}, ["restaurant"]),
    ({"amenity": "fast_food"}, ["fastfood"]),
    # کباب نام‌محور: OSM برای کبابی/جگرکی تگ استاندارد ندارد.
    ({"amenity": "restaurant", "name": "چلوکبابی جوان"}, ["kebab", "restaurant"]),
    ({"amenity": "fast_food", "name": "جگرکی حاج رضا"}, ["kebab", "fastfood"]),
    ({"amenity": "restaurant", "name": "کباب پز"}, ["kebab", "restaurant"]),
    ({"amenity": "restaurant", "name": "دل و قلوه فروشی"}, ["kebab", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "doner"}, ["kebab", "restaurant"]),
    # طباخی نام‌محور (کله‌پاچه/سیراب شیردان/دیزی/آبگوشت/طباخی).
    ({"amenity": "restaurant", "name": "کله‌پاچه ساحل"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "کله پزی یاران"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "سیراب شیردان علی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "دیزی سرا"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "دیزی‌سرای سنتی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آبگوشت ولیعصر"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "طباخی کوثر"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "kaleh_pacheh;persian"}, ["tabbakh", "restaurant"]),
    # طباخی گسترش‌یافته: آش، حلیم، شله مشهدی، بریانی، کوفته، هریسه، عدسی، شوربا.
    ({"amenity": "restaurant", "name": "آش آبادان"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آش سرای مادر"}, ["tabbakh", "restaurant"]),
    ({"amenity": "fast_food", "name": "آش و حلیم آنا"}, ["tabbakh", "fastfood"]),
    ({"amenity": "cafe", "name": "کافه آش مهتاب"}, ["cafe", "tabbakh"]),
    ({"amenity": "restaurant", "name": "حلیم و آش رشته سید مهدی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آش و هلیم سحرخیزان"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آشکده خاتون"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آشکدهٔ نازخاتون"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "آشی فردوسی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "food_court", "name": "آشپزی جنوب"}, ["tabbakh"]),
    ({"amenity": "restaurant", "name": "آشپزی و بریانی خراسانی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "شله مشهدی رضوان"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "بریانی اصفهانی نقش جهان"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "کوفته تبریزی آذر"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "هریسه سرای قزوین"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "دلمه پز خانه"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "تهیه غذای دلمه"}, ["tabbakh", "restaurant"]),
    ({"amenity": "fast_food", "name": "عدسی فروشی حاج حسن"}, ["tabbakh", "fastfood"]),
    ({"amenity": "restaurant", "name": "شوربای گیلانی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "سوپ و آش مهر"}, ["tabbakh", "restaurant"]),
    # شکل‌های املایی: الف مقصوره («ى») و نام فارسی در `name:fa`.
    ({"amenity": "restaurant", "name": "کله پزى حاج نادر"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "sina tabakhi", "name:fa": "طباخی سینا"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "Cafe", "official_name": "آش و حلیم آنا"}, ["tabbakh", "restaurant"]),
    # مکان‌هایی که فقط `cuisine`/`food` دارند و هیچ `amenity`/`shop` ندارند.
    ({"name": "آشکده شامار", "cuisine": "ash"}, ["tabbakh"]),
    ({"name": "حلیم و عدسی کرمی", "cuisine": "حلیم;عدسی"}, ["tabbakh"]),
    ({"name": "آش سرای ولیعصر", "food": "yes"}, ["tabbakh"]),
    # طباخی + کباب روی هم (مکان ترکیبی): ترتیب تقدم tabbakh > kebab > restaurant.
    ({"amenity": "restaurant", "name": "کباب و حلیم سادات"}, ["tabbakh", "kebab", "restaurant"]),
    ({"amenity": "restaurant", "name": "کباب بریانی احمدی"}, ["tabbakh", "kebab", "restaurant"]),
    ({"amenity": "restaurant", "name": "کوفته کباب"}, ["tabbakh", "kebab", "restaurant"]),
    ({"amenity": "restaurant", "name": "آش وحلیم و کبابی صفری"}, ["tabbakh", "kebab", "restaurant"]),
    # طباخی تگ‌محور (cuisine لاتین و فارسی چندتکه).
    ({"amenity": "restaurant", "cuisine": "ash"}, ["tabbakh", "restaurant"]),
    ({"amenity": "fast_food", "cuisine": "soup"}, ["tabbakh", "fastfood"]),
    ({"amenity": "restaurant", "cuisine": "halim;ash"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "آش_و_حلیم"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "شله_مشهدی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "سوپ;حلیم;سوسیس_تخم_مرغ"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "بریانی"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "دلمه"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "kebab;persian"}, ["kebab", "restaurant"]),
    ({"amenity": "restaurant", "cuisine": "کباب_کاکوری"}, ["kebab", "restaurant"]),
    # محافظ‌های خطای زیررشته: این‌ها هرگز نباید طباخی بگیرند.
    ({"amenity": "restaurant", "name": "آشپزخانه آفرینش"}, ["restaurant"]),
    ({"amenity": "restaurant", "name": "آشپزباشی"}, ["restaurant"]),
    ({"amenity": "cafe", "name": "آشوب"}, ["cafe"]),
    ({"amenity": "cafe", "name": "کافه سنتی آشیانه دریا"}, ["cafe"]),
    ({"amenity": "cafe", "name": "کافه قهر و آشتی"}, ["cafe"]),
    ({"amenity": "restaurant", "name": "کبابی سرآشپز"}, ["kebab", "restaurant"]),
    ({"shop": "supermarket", "name": "سوپرمارکت رفاه"}, []),
    ({"shop": "kitchen", "name": "کابینت آشپزخانه مهدی"}, []),
    ({"shop": "cabinet_maker", "name": "آشپزخانه وجدانی"}, []),
    ({"amenity": "place_of_worship", "name": "امامزاده حلیمه خاتون"}, []),
    ({"name": "گردنه دیزین", "ele": "2000", "mountain_pass": "yes"}, []),
    ({"amenity": "restaurant", "name": "رستوران سنتی دیزینو"}, ["restaurant"]),
    ({"amenity": "fast_food", "name": "دیزین ترک"}, ["fastfood"]),
    # فست‌فود نام‌محور: OSM در ایران ساندویچی/پیتزایی/برگری را با
    # `amenity=restaurant` ثبت می‌کند؛ چنین مکانی رستوران نیست و باید فقط روی
    # نقشهٔ فست‌فود بیاید (نقشهٔ رستوران تمیز می‌ماند).
    ({"amenity": "restaurant", "name": "ساندویچ بهارستان"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "ساندویج فروشی قاسمی"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "پیتزا فروشی آیلار"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "فست فود شیلا"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "فست‌فود دلستان"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "خانه همبرگر"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "فلافل جلیلی"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "شاورما دمشق"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "Haida Sandwich"}, ["fastfood"]),
    ({"amenity": "restaurant", "name": "دنر ترک"}, ["fastfood"]),
    # «دنر» (بدون واو) باید ترکیب ساندویچی‌وار بماند ولی رستوران نباشد.
    ({"amenity": "restaurant", "name": "دنر پیتزا چلسی"}, ["fastfood"]),
    # فست‌فود نام‌محور روی کافه: کافه می‌ماند و فست‌فود هم اضافه می‌شود.
    ({"amenity": "cafe", "name": "کافه فست فود چت میت"}, ["cafe", "fastfood"]),
    # مکان ترکیبی: نام صریحاً «رستوران» دارد، پس روی هر دو نقشه می‌ماند.
    ({"amenity": "restaurant", "name": "رستوران و فست فود پرک"}, ["fastfood", "restaurant"]),
    ({"amenity": "restaurant", "name": "پیتزا رستوران"}, ["fastfood", "restaurant"]),
    # کترینگ زیرمجموعهٔ رستوران است و با نام فست‌فودی هم از رستوران نمی‌افتد.
    ({"craft": "caterer", "name": "کترینگ فست فود رضوان"}, ["fastfood", "restaurant"]),
    # دامنه‌های دیگر دست‌نخورده‌اند: کباب/طباخی بدون سیگنال فست‌فود.
    ({"amenity": "restaurant", "name": "کباب پز"}, ["kebab", "restaurant"]),
    ({"amenity": "restaurant", "name": "کله‌پاچه ساحل"}, ["tabbakh", "restaurant"]),
    # گاردِ منفی: برند «فستیز» نباید فست‌فود شمرده شود، و «سابق» نباید با
    # هیچ کلیدواژه‌ای تطبیق بخورد.
    ({"amenity": "restaurant", "name": "کافه رستوران فستیز"}, ["restaurant"]),
    ({"amenity": "restaurant", "name": "تالار شاهان (نیلا سابق)"}, ["restaurant"]),
    # «نان ساندویچی» محصول نانوایی است، نه ساندویچی.
    ({"amenity": "biergarten", "name": "نان ساندویچی"}, []),
    # روی هم‌افتادگی طباخی و کباب (طباخی‌های کباب‌دار).
    ({"amenity": "restaurant", "name": "دیزی و کبابی بیشه"}, ["tabbakh", "kebab", "restaurant"]),
    # کترینگ زیرمجموعهٔ رستوران.
    ({"craft": "caterer", "name": "کترینگ ونوس"}, ["restaurant"]),
    ({"shop": "catering", "name": "Tehran Catering"}, ["restaurant"]),
    ({"amenity": "fast_food", "name": "تالار پذیرایی مهر"}, ["fastfood", "restaurant"]),
    ({"amenity": "fast_food", "name": "تهیه غذای الهیه"}, ["fastfood", "restaurant"]),
    # نرمال‌سازی نام: کاف عربی، هٔ عربی و فاصله‌های متفاوت باید یکسان دیده شوند.
    ({"amenity": "restaurant", "name": "كله پاچة سنتي"}, ["tabbakh", "restaurant"]),
    ({"amenity": "restaurant", "name": "كبابي"}, ["kebab", "restaurant"]),
    # مواردی که نباید پذیرفته شوند.
    ({"amenity": "restaurant", "name": "رستوران مروارید"}, ["restaurant"]),
    ({"name": "کبابی"}, []),
    ({"amenity": "school", "name": "دبیرستان کباب"}, []),
)


def run_self_test() -> int:
    """طبقه‌بندی را روی جدول قرارداد می‌سنجد؛ ۰ یعنی موفق."""
    failures = []

    for tags, expected in SELF_TEST_CASES:
        got = matching_domains(tags)
        if got != expected:
            failures.append((tags, expected, got))

    if failures:
        for tags, expected, got in failures:
            print(f"self-test FAIL: {tags} expected={expected} got={got}", file=sys.stderr)
        return 1

    print(f"self-test ok ({len(SELF_TEST_CASES)} cases)")
    return 0


def is_map_place(tags: dict) -> bool:
    """آیا عنصر عضو «مکان‌های نقشه» خانوادهٔ غذا است؟ (برآیند همهٔ دامنه‌ها)."""
    return bool(matching_domains(tags))


def to_dict(tags) -> dict:
    return {tag.k: tag.v for tag in tags}


def centroid(locations: list) -> tuple | None:
    """میانگین lat/lng فهرست مکان‌های معتبر؛ اگر خالی بود `None`."""
    if not locations:
        return None
    lats = [lat for lat, _ in locations]
    lngs = [lng for _, lng in locations]
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


class MapPlaceHandler(osmium.SimpleHandler):
    """گردآورندهٔ مکان‌های نقشه (کافه و آبمیوه/بستنی) از گره، way و relation.

    `way_centroids` مرکز همهٔ wayهای فایل را نگه می‌دارد (نه فقط wayهای تگ‌دار)
    چون wayهای عضوِ یک relation کافه معمولاً خودشان تگ ندارند و فقط نقشِ هندسهٔ
    ساختمان را دارند. ترتیب PBF (گره → way → relation) تضمین می‌کند که هنگام
    رسیدن به relation، مرکز wayها از قبل محاسبه شده باشد.

    `node_locations` مکان همهٔ گره‌های فایل را نگه می‌دارد. علت: در کتابخانهٔ
    pyosmium، `RelationMember` ویژگی `location` **ندارد** (نه با ایندکس مکان و نه
    بدون آن)؛ پس مکان گره‌های عضو relation باید از همین دیکشنری خوانده شود.
    بدون آن، هر relation که عضو گره داشته باشد با `AttributeError` کل استخراج را
    می‌شکست. حجم حافظه متناسب با تعداد گره‌های فایل ورودی است و این اسکریپت فقط
    روی فایل ازپیش‌فیلترشده (چند ده هزار گره) اجرا می‌شود.
    """

    def __init__(self, places: list) -> None:
        super().__init__()
        self.places = places
        self.way_centroids: dict = {}
        self.node_locations: dict = {}

    def node(self, n) -> None:
        if not n.location.valid():
            return
        # مکان همهٔ گره‌ها ذخیره می‌شود (نه فقط گره‌های منطبق) چون گره‌های عضو
        # relation معمولاً خودشان تگ ندارند.
        self.node_locations[n.id] = (n.location.lat, n.location.lon)
        tags = to_dict(n.tags)
        doms = matching_domains(tags)
        if not doms:
            return
        self.places.append(
            {
                "osm_type": "node",
                "osm_id": n.id,
                "lat": round(n.location.lat, 7),
                "lng": round(n.location.lon, 7),
                "domains": doms,
                "domain": doms[0],
                "tags": tags,
            }
        )

    def way(self, w) -> None:
        locations = [
            (node_ref.location.lat, node_ref.location.lon)
            for node_ref in w.nodes
            if node_ref.location.valid()
        ]
        center = centroid(locations)
        if center is None:
            return

        # مرکز همهٔ wayها ذخیره می‌شود تا relationهای عضو بتوانند از آن استفاده کنند.
        self.way_centroids[w.id] = center

        tags = to_dict(w.tags)
        doms = matching_domains(tags)
        if not doms:
            return

        self.places.append(
            {
                "osm_type": "way",
                "osm_id": w.id,
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
                "domains": doms,
                "domain": doms[0],
                "tags": tags,
            }
        )

    def relation(self, r) -> None:
        tags = to_dict(r.tags)
        doms = matching_domains(tags)
        if not doms:
            return

        locations = []
        for member in r.members:
            # حفره‌های multipolygon نباید مرکز را به بیرون بکشند.
            if (member.role or "") == "inner":
                continue
            if member.type == "w":
                center = self.way_centroids.get(member.ref)
                if center is not None:
                    locations.append(center)
            elif member.type == "n":
                location = self.node_locations.get(member.ref)
                if location is not None:
                    locations.append(location)

        center = centroid(locations)
        if center is None:
            return

        self.places.append(
            {
                "osm_type": "relation",
                "osm_id": r.id,
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
                "domains": doms,
                "domain": doms[0],
                "tags": tags,
            }
        )


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return run_self_test()

    if len(sys.argv) != 3:
        print(
            "usage: extract-cafes.py <input.osm.pbf> <output.json.gz>\n"
            "       extract-cafes.py --self-test",
            file=sys.stderr,
        )
        return 2

    source, target = sys.argv[1], sys.argv[2]
    places: list = []

    # بدون locations=True: مختصات wayها توسط `osmium add-locations-to-ways`
    # از قبل داخل خودشان تزریق شده و ساخت ایندکس مکان، کندی بی‌دلیل می‌آورد.
    MapPlaceHandler(places).apply_file(source)
    places.sort(key=lambda item: (item["osm_type"], item["osm_id"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "places": places,
    }

    # محافظ سلامت: خروجی خالی یعنی فیلتر/ورودی خراب است؛ انتشار نباید انجام شود
    # وگرنه نسخهٔ سالم قبلی روی سرور با فایل خالی جایگزین می‌شود.
    if not places:
        print("no cafe-family places found; refusing to write an empty release", file=sys.stderr)
        return 1

    with gzip.open(target, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))

    kinds: dict = {}
    domain_counts: dict = {}
    for item in places:
        kinds[item["osm_type"]] = kinds.get(item["osm_type"], 0) + 1
        for name in item["domains"]:
            domain_counts[name] = domain_counts.get(name, 0) + 1

    ordered_counts = {name: domain_counts[name] for name in DOMAIN_PRIORITY if name in domain_counts}
    print(f"wrote {len(places)} places to {target} ({kinds}, domains={ordered_counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
