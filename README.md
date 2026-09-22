# mapcafe-data

دادهٔ عمومی مپ‌کافه. دو دستهٔ داده در این ریپو منتشر می‌شود:

- **تایل‌های روزانهٔ جاده‌های ایران (MBTiles)** — ریلیزهای `nightly`، `tiles`
  و `latest` با ورک‌فلوهای `build-zoom-*.yml`. (Daily Iran roads MBTiles for
  MapCafe.)
- **مکان‌های نقشه از OpenStreetMap** — ریلیز `places` با دارایی
  `cafes.json.gz`. (همین سند، پایین.)

---

# مکان‌های نقشه (OpenStreetMap)

ریپوی `mapcafe-data` هیچ کدی از برنامه ندارد؛ فقط اسکریپت و ورک‌فلوی زیر را
نگه می‌دارد و هفته‌ای یک بار مکان‌های «خانوادهٔ کافه» را از OpenStreetMap
استخراج و در قالب یک Release منتشر می‌کند. سرور Mapto فقط همان فایل گزیپ را
دانلود و در جدول `map_places` وارد می‌کند (بدون هیچ بار پردازش سنگین روی سرور).

ساختار مرتبط در این ریپو:

    omidaghaz-svg/mapcafe-data        (عمومی)
    ├── .github/workflows/extract-cafes.yml
    ├── extract-cafes.py
    └── README.md

---

## چرا این معماری

- **Stateless و API-first:** سرور هیچ‌وقت PBF پردازش نمی‌کند؛ فقط دانلود + upsert.
- **جابه‌جایی سرور با تغییر env:** فقط `MAPCAFE_PLACES_*` عوض می‌شود.
- **منبع داده:** `https://download.geofabrik.de/asia/iran-latest.osm.pbf` (حجم ~۲۲۹ مگابایت).
- **مجوز:** ODbL — نسبت‌دهی «© OpenStreetMap contributors» الزامی است و در نقشه نمایش داده می‌شود.

اگر همین اسکریپت را مستقیم روی PBF کامل ایران اجرا کنیم، پیمایش ۲۷ میلیون گره بیش از
۱۵ دقیقه طول می‌کشد و به سقف زمانی GitHub Actions نزدیک می‌شود. پس ورک‌فلو اول با
ابزار C++ اوپن‌استریت‌مپ (چند ثانیه) داده را کوچک می‌کند و بعد پایتون را فقط روی
فایل کوچک اجرا می‌کند.

---

## خط لولهٔ استخراج

```
iran-latest.osm.pbf  (۲۲۹MB، ۲۷M گره)
        │  osmium tags-filter  ← فیلتر سریع C++
        ▼
candidates.osm.pbf   (~۲۹٬۵۰۰ گره / ۲٬۰۹۰ way / ۱۰۷ relation)
        │  osmium add-locations-to-ways  ← تزریق مختصات گره‌ها داخل wayها
        ▼
candidates-loc.osm.pbf
        │  python extract-cafes.py
        ▼
cafes.json.gz        (~۲۸۰KB ≈ ۶٬۰۱۵ مکان: ۴٬۹۷۹ کافه + ۱٬۰۳۶ آبمیوه و بستنی)
        │  gh release upload places cafes.json.gz --clobber
        ▼
Release «places» در ریپوی mapcafe-data
        │  php artisan map:import-cafes   (روی سرور)
        ▼
جدول map_places (ستون domain = cafe | juice_icecream)
```

**یک استخراج، دو نقشه:** فایل خروجی هم مکان‌های کافه و هم مکان‌های آبمیوه و
بستنی را با هم دارد و هر مکان فیلد `domain` می‌گیرد. نقشهٔ کافه و نقشهٔ
آبمیوه/بستنی هر دو از همین یک فایل تغذیه می‌شوند؛ تفکیک فقط با فیلتر `domain`
انجام می‌شود و نیازی به استخراج یا جدول دوم نیست.

### نکات فنی مهم

- `-R` در `tags-filter` یعنی **حذف اشیای ارجاع‌شده** (Omit-Referenced)، نه «آوردن ارجاع‌ها».
  رفتار پیش‌فرض `tags-filter` خودش گره‌های ارجاع‌شدهٔ wayها و اعضای relationها را
  به خروجی اضافه می‌کند؛ پس نیازی به `-R` نیست و هندسهٔ کامل در دسترس است.
- الگوی فیلتر باید هم `*cafe*` و هم `*coffee*` داشته باشد: `cuisine=cafe` و
  `cuisine=coffee_shop` دو مقدار متفاوت‌اند و زیررشتهٔ یکی در دیگری نیست.
- الگوهای `*juice*`/`*smoothie*`/`*ice_cream*` برای دامنهٔ آبمیوه و بستنی
  لازم‌اند؛ بیشترِ آبمیوه‌فروشی‌های ایران `amenity=fast_food` با `cuisine=juice`
  برچسب خورده‌اند و بدون این الگوها از دست می‌رفتند.
- `extract-cafes.py` بدون `locations=True` اجرا می‌شود؛ چون مختصات wayها از قبل با
  `add-locations-to-ways` داخل خودشان تزریق شده و ساختن ایندکس مکان کندی بی‌دلیل است.
- اگر خروجی `cafes.json.gz` صفر مکان باشد، اسکریپت با کد خطا خارج می‌شود تا نسخهٔ
  سالم قبلی روی سرور با فایل خالی جایگزین نشود.

---

## راه‌اندازی گام‌به‌گام (یک‌بار)

۱. ریپوی عمومی `mapcafe-data` را بساز (اگر وجود ندارد).

۲. این سه فایل را داخلش قرار بده:

    .github/workflows/extract-cafes.yml
    extract-cafes.py
    README.md

۳. در تنظیمات ریپو → Actions → General → Workflow permissions، گزینهٔ
   **Read and write permissions** را فعال کن (ورک‌فلو برای ساخت Release به آن نیاز دارد).

۴. از تب Actions ورک‌فلو **Extract Cafe Places (OSM)** را یک‌بار دستی اجرا کن
   (`Run workflow`). اولین اجرا PBF را دانلود می‌کند و حدود ۱۰ تا ۱۵ دقیقه طول می‌کشد.

۵. بعد از موفقیت، در تب Releases باید ریلیز **places** با دارایی `cafes.json.gz` دیده شود.

از این پس هر دوشنبه ساعت ۳ بامداد UTC خودکار اجرا می‌شود.

---

## اجرای محلی (برای تست تغییرات)

در محیطی که `osmium-tool` نصب است:

```bash
# دانلود داده ایران
curl -fsSL -o iran-latest.osm.pbf \
  https://download.geofabrik.de/asia/iran-latest.osm.pbf

# مرحله ۱: فیلتر سریع
osmium tags-filter iran-latest.osm.pbf \
  'n/amenity=cafe,restaurant,fast_food,ice_cream,juice_bar' \
  'w/amenity=cafe,restaurant,fast_food,ice_cream,juice_bar' \
  'r/amenity=cafe,restaurant,fast_food,ice_cream,juice_bar' \
  'n/shop=coffee' 'w/shop=coffee' 'r/shop=coffee' \
  'n/shop=ice_cream,juice' 'w/shop=ice_cream,juice' 'r/shop=ice_cream,juice' \
  'n/cuisine=*cafe*' 'w/cuisine=*cafe*' 'r/cuisine=*cafe*' \
  'n/cuisine=*coffee*' 'w/cuisine=*coffee*' 'r/cuisine=*coffee*' \
  'n/cuisine=*juice*' 'w/cuisine=*juice*' 'r/cuisine=*juice*' \
  'n/cuisine=*smoothie*' 'w/cuisine=*smoothie*' 'r/cuisine=*smoothie*' \
  'n/cuisine=*ice_cream*' 'w/cuisine=*ice_cream*' 'r/cuisine=*ice_cream*' \
  -o candidates.osm.pbf --overwrite

# مرحله ۲: تزریق مختصات
osmium add-locations-to-ways candidates.osm.pbf \
  -o candidates-loc.osm.pbf --overwrite

# مرحله ۳: استخراج
pip install --break-system-packages osmium==4.3.1
python extract-cafes.py candidates-loc.osm.pbf cafes.json.gz
```

کل خط لوله روی ماشین معمولی زیر یک دقیقه طول می‌کشد.

---

## مصرف روی سرور Mapto

سرور با دستور زیر فایل ریلیز را دانلود و به‌صورت idempotent وارد می‌کند:

```bash
php artisan map:import-cafes
```

پیکربندی مرتبط در `.env` سرور:

```
MAPCAFE_GITHUB_USER=omidaghaz-svg
MAPCAFE_GITHUB_REPO=mapcafe-data
MAPCAFE_PLACES_TAG=places
MAPCAFE_PLACES_FILE=cafes.json.gz
MAPCAFE_PLACES_TIMEOUT=120
# دامنهٔ پیش‌فرض API: cafe | cafe,juice_icecream | all
MAPCAFE_PLACES_DOMAINS=cafe
```

گزینه‌های اختیاری دستور:

```
--source=/path/to/cafes.json.gz   منبع محلی به‌جای دانلود از ریلیز
--bbox=s,w,n,e                    محدود کردن به یک کادر جغرافیایی
--batch=500                       اندازهٔ دستهٔ upsert
--limit=1000                      فقط N رکورد اول (پایلوت)
--prune                           حذف رکوردهای OSM که دیگر در منبع نیستند
--dry-run                         فقط گزارش، بدون نوشتن در دیتابیس
```

کلید یکتا `(osm_type, osm_id)` است؛ اجرای مکرر رکورد تکراری نمی‌سازد و فیلدهای
`verified_fields` (اطلاعاتی که صاحب تأییدشده وارد کرده) هرگز بازنویسی نمی‌شوند.

---

## مجموعهٔ تگ‌های پذیرفته‌شده

مرجع واحد: `app/Domains/Cafe/Support/MapPlaceTags.php` (متد `matches()` برای
پذیرش و `domain()` برای تفکیک نقشه). توابع `is_map_place()` و `domain()` در
`extract-cafes.py` باید همیشه با آن هم‌راستا بمانند:

| شرط | پذیرش | دامنه | آیکون |
| --- | --- | --- | --- |
| `amenity=cafe` | بله | `cafe` | `coffee` |
| `amenity=restaurant` + `cuisine=cafe`/`coffee_shop` | بله | `cafe` | `utensils` |
| `amenity=fast_food` + `cuisine=cafe`/`coffee_shop` | بله | `cafe` | `burger` |
| `shop=coffee` | بله | `cafe` | `cart` |
| `cuisine=cafe`/`coffee_shop` روی هر amenity دیگر | بله | `cafe` | `coffee` |
| `amenity=ice_cream` | بله | `juice_icecream` | `ice-cream` |
| `shop=ice_cream` | بله | `juice_icecream` | `ice-cream` |
| `shop=juice` یا `amenity=juice_bar` | بله | `juice_icecream` | `juice` |
| `cuisine=juice`/`smoothie`/`ice_cream` روی amenity دیگر | بله | `juice_icecream` | `juice`/`ice-cream`/`juice-icecream` |

**ترتیب تصمیم دامنه (مهم):** ۱) ماهیت کافه (`amenity=cafe`، `shop=coffee` یا
`cuisine=cafe|coffee_shop`) → `cafe`؛ ۲) آبمیوه/بستنیِ خالص با تگ اصلی
(`amenity=ice_cream|juice_bar`، `shop=ice_cream|juice`) → `juice_icecream`؛
۳) سیگنال کافه در cuisine (`coffee`/`tea`/`cake`/`dessert`/`pastry`/`bakery`/
`breakfast`/`brunch`/`chocolate`) → `cafe`؛ ۴) cuisine آبمیوه/بستنی → 
`juice_icecream`؛ ۵) پیش‌فرض → `cafe`.

**قاعدهٔ کلیدی:** «کافه‌بودن» بر «آبمیوه/بستنی‌بودن» مقدم است؛ پس «کافه آبمیوه
بستنی» (مثل `amenity=cafe` + `cuisine=ice_cream` یا `shop=ice_cream` +
`cuisine=cafe`) در دامنهٔ `cafe` می‌ماند و روی نقشهٔ کافه با آیکون کافه می‌آید.
فقط آبمیوه/بستنیِ خالص به دامنهٔ `juice_icecream` می‌رود. آیکون دامنهٔ آبمیوه و
بستنی: اگر هم آبمیوه و هم بستنی باشد `juice-icecream`، اگر فقط بستنی
`ice-cream` و اگر فقط آبمیوه `juice`.

تگ چندمقداری با `;` شکسته می‌شود (مثلاً `cuisine=cake;coffee_shop`) و همهٔ مقادیر
بررسی می‌شوند. دادهٔ OSM فقط **نام و موقعیت** می‌دهد؛ ستاره، امتیاز، آیکون اختصاصی
و منطق بازاریابی Mapto از دادهٔ OSM گرفته نمی‌شود.

---

## قواعد هماهنگی

- این ریپو فقط **داده و ورک‌فلوی استخراج** را نگه می‌دارد؛ کد برنامه در ریپوی
  جداگانهٔ `mapto-app` زندگی می‌کند.
- هر تغییر در `MapPlaceTags::matches()`/`domain()` باید هم‌زمان در
  `is_map_place()`/`domain()` پایتون و در الگوهای `tags-filter` ورک‌فلو آینه شود.
- پس از هر تغییر طبقه‌بندی، تطابق PHP و پایتون را روی کل خروجی بسنج
  (شمارش اختلاف باید صفر شود) تا مکان اشتباه‌دامنه ساخته نشود.
- مستند قواعد مالکیت و امتیاز: `docs/map-places-ownership.md`.
