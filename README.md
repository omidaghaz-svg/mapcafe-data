# mapcafe-data — دادهٔ مکان‌های نقشه (OpenStreetMap)

این پوشه **فایل‌های تحویلی** برای ریپوی جداگانهٔ داده است:

    omidaghaz-svg/mapcafe-data        (عمومی)
    ├── .github/workflows/extract-cafes.yml
    ├── extract-cafes.py
    └── README.md

ریپوی `mapcafe-data` هیچ کدی از برنامه ندارد؛ فقط دو فایل بالا را نگه می‌دارد و
هفته‌ای یک بار «مکان‌های نقشه» خانوادهٔ غذا (کافه، رستوران، فست‌فود، کباب،
طباخی، آبمیوه و بستنی) را از OpenStreetMap استخراج و در قالب یک Release منتشر
می‌کند. سرور Mapto فقط همان فایل گزیپ را دانلود و در جدول `map_places` وارد
می‌کند (بدون هیچ بار پردازش سنگین روی سرور).

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
candidates.osm.pbf   (~۵۰٬۳۳۱ گره / ۳٬۳۴۳ way / ۱۶۲ relation)
        │  osmium add-locations-to-ways  ← تزریق مختصات گره‌ها داخل wayها
        ▼
candidates-loc.osm.pbf
        │  python extract-cafes.py --self-test   ← قفل‌کردن قواعد طبقه‌بندی
        │  python extract-cafes.py
        ▼
cafes.json.gz        (~۸۴۰KB ≈ ۱۸٬۹۲۴ مکان، هر مکان با فهرست `domains`)
        │  gh release upload places cafes.json.gz --clobber
        ▼
Release «places» در ریپوی mapcafe-data
        │  php artisan map:import-cafes   (روی سرور)
        ▼
جدول map_places (ستون domain = دامنهٔ اصلی؛ ستون domains = فهرست دامنه‌ها)
```

**یک استخراج، شش نقشه:** فایل خروجی مکان‌های همهٔ دامنه‌های خانوادهٔ غذا را با هم
دارد و هر مکان فیلد `domains` (فهرست) و `domain` (دامنهٔ اصلی) می‌گیرد. هر
نقشه از همین یک فایل تغذیه می‌شود؛ تفکیک فقط با فیلتر دامنه انجام می‌شود و
نیازی به استخراج یا جدول دوم نیست.

**مکان ترکیبی:** اگر یک مکان هم‌زمان نشانهٔ چند دامنه را داشته باشد، در همهٔ آن
نقشه‌ها می‌آید. مثلاً کافه‌رستوران (`amenity=restaurant` + `cuisine=cafe`) هم
روی نقشهٔ کافه و هم رستوران، و رستوران کبابی (`cuisine=kebab`) هم روی نقشهٔ
رستوران و هم کباب. دامنهٔ اصلی (برای آیکون/نوعِ پیش‌فرض) با ترتیب تقدم
`cafe` > `juice_icecream` > `tabbakh` > `kebab` > `fastfood` > `restaurant`
انتخاب می‌شود.

**آمار واقعی (اجرای کامل روی PBF ایران، ۱ مهر ۱۴۰۵):** کل خروجی ۱۸٬۹۲۴ مکان
(۱۷٬۰۹۷ گره + ۱٬۷۲۴ way + ۱۰۳ relation). شمار مکان‌های هر نقشه (مکان ترکیبی در
هر نقشه جداگانه شمرده می‌شود):

| نقشه | شمار مکان | گره | way | relation | نام‌دار |
| --- | --- | --- | --- | --- | --- |
| رستوران | ۹٬۳۰۵ | ۷٬۹۹۸ | ۱٬۲۵۰ | ۵۷ | ۸٬۶۲۸ |
| کافه | ۴٬۹۸۶ | ۴٬۶۸۵ | ۲۸۹ | ۱۲ | ۴٬۵۴۶ |
| فست‌فود | ۳٬۸۶۲ | ۳٬۶۶۱ | ۱۷۴ | ۲۷ | ۳٬۴۹۰ |
| آبمیوه و بستنی | ۱٬۲۶۵ | ۱٬۱۸۸ | ۶۹ | ۸ | ۱٬۱۶۰ |
| کباب | ۱٬۷۲۳ | ۱٬۵۵۱ | ۱۶۰ | ۱۲ | ۱٬۶۸۹ |
| طباخی | ۵۵۲ | ۵۲۱ | ۲۸ | ۳ | ۵۴۹ |

از این میان ۱۶٬۳۷۴ مکان تک‌دامنه و ۲٬۵۵۰ مکان ترکیبی‌اند. پرتکرارترین ترکیب‌ها:
`kebab+restaurant` (۱٬۲۵۰)، `tabbakh+restaurant` (۴۰۰)، `kebab+fastfood` (۲۴۲)،
`cafe+juice_icecream` (۱۶۱)، `cafe+restaurant` (۱۰۲)، `juice_icecream+fastfood`
(۸۱)، `tabbakh+fastfood` (۵۸)، `tabbakh+kebab+restaurant` (۵۵).

**چهار نکتهٔ مهم آماری:** اول، دامنهٔ کافه **دقیقاً** همان ۴٬۹۸۶ مکان پیشین است
(صفر تغییر در نقشهٔ کافه) و نقشهٔ آبمیوه/بستنی فقط ۲۲۸ مکان ترکیبی به آن اضافه
کرده (نقشهٔ پیشین زیرمجموعهٔ نقشهٔ جدید است). دوم، بیشتر مکان‌های کباب و
تقریباً همهٔ طباخی‌ها فقط از **نام** شناخته شده‌اند، چون OSM برای
کبابی/جگرکی/کله‌پاچه/آشکده تگ استانداردی ندارد. سوم، ۲۴ مکان طباخی و ۲۹ مکان
کباب هیچ `amenity` غذایی ندارند و فقط با `cuisine`/`food`/نام شناسایی شده‌اند.
چهارم، دامنهٔ رستوران تقریباً دو برابر کافه بذر دارد و کترینگ‌ها
(`craft=caterer`) زیرمجموعهٔ آن‌اند.

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
- **نکتهٔ مهم pyosmium:** `RelationMember` هیچ ویژگی `location` ندارد (نه با
  `locations=True` و نه بدون آن). پس اسکریپت مکان گره‌ها را در دیکشنری
  `node_locations` نگه می‌دارد و مرکز relationهایی که عضو گره دارند از همان
  خوانده می‌شود. بدون این کار، اولین relation دارای عضو گره با `AttributeError`
  کل اجرا را می‌شکست (این اشکال در نسخهٔ پیشین وجود داشت و رفع شد).
- **خودآزمون پیش از استخراج:** `python extract-cafes.py --self-test` جدول
  قراردادِ ۸۸ موردی طبقه‌بندی را می‌سنجد و با هر اختلاف، کد خطا برمی‌گرداند.
  ورک‌فلو این را پیش از استخراج اجرا می‌کند تا تغییر اشتباه قاعده‌ها هرگز به
  ریلیز نرسد.
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
  'n/cuisine=*kebab*' 'w/cuisine=*kebab*' 'r/cuisine=*kebab*' \
  'n/cuisine=*dizi*' 'w/cuisine=*dizi*' 'r/cuisine=*dizi*' \
  'n/cuisine=*abgoosht*' 'w/cuisine=*abgoosht*' 'r/cuisine=*abgoosht*' \
  'n/cuisine=*kale_pache*' 'w/cuisine=*kale_pache*' 'r/cuisine=*kale_pache*' \
  'n/cuisine=*sirab*' 'w/cuisine=*sirab*' 'r/cuisine=*sirab*' \
  'n/cuisine=*shirdan*' 'w/cuisine=*shirdan*' 'r/cuisine=*shirdan*' \
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
پذیرش و `domain()` برای دامنهٔ اصلی؛ پس از انتقال ماژول نقشه به `Core/Map`، متد
`matchingDomains()` جای `domain()` را می‌گیرد). توابع `matching_domains()` و
`is_map_place()` در `extract-cafes.py` باید همیشه با آن هم‌راستا بمانند.

**عضویت هر دامنه مستقل سنجیده می‌شود**؛ یک مکان می‌تواند در چند دامنه باشد.
«سیگنال کافه» یعنی `coffee`/`tea`/`cake`/`dessert`/`pastry`/`bakery`/`breakfast`/
`brunch`/`chocolate`؛ این سیگنال‌ها **عضو‌کنندهٔ مستقل نیستند** و فقط مکانی را که
از مسیر دیگری عضو شده، در دامنهٔ کافه هم نگه می‌دارند (آینهٔ تقدم کافه در رفتار
پیشین، تا نقشهٔ کافه دقیقاً ثابت بماند):

| دامنه | شرط عضویت | آیکون پیش‌فرض |
| --- | --- | --- |
| `cafe` | `amenity=cafe` یا `shop=coffee` یا (`amenity` موجود و `cuisine` شامل `cafe`/`coffee_shop`) یا (عضو دامنهٔ آبمیوه/بستنی و `cuisine` شامل سیگنال کافه) | `coffee` |
| `juice_icecream` | `amenity∈{ice_cream,juice_bar}` یا `shop∈{ice_cream,juice}` یا (`amenity` موجود و `cuisine` شامل `juice`/`smoothie`/`ice_cream`) | `ice-cream`/`juice`/`juice-icecream` |
| `tabbakh` | (`amenity` موجود و `cuisine` شامل `dizi`/`abgoosht`/`kale_pache`/`sirab`/`shirdan`/`ash`/`halim`/`sholeh`/`biryani`/`kofta`/`harissa`/`dolma`/`soup`/...) **یا** (نام غذاخوری شامل کلیدواژهٔ طباخی) | `utensils` |
| `kebab` | (`amenity` موجود و `cuisine` شامل `kebab`/`koobideh`/`jigar`/`liver`/`doner`/...) **یا** (نام غذاخوری شامل کلیدواژهٔ کباب) | `utensils` |
| `fastfood` | `amenity=fast_food` | `burger` |
| `restaurant` | `amenity=restaurant` **یا** تگ کترینگ (`shop=catering`/`amenity=catering`/`craft=caterer`) **یا** (نام غذاخوری شامل کلیدواژهٔ کترینگ) | `utensils` |

**طبقه‌بندی نام‌محور (بخش مهم دقت):** OSM در ایران برای کبابی/جگرکی/کله‌پاچه
تقریباً هیچ تگ استانداردی ندارد؛ پس نام مکان تنها سیگنال در دسترس است. نام‌ها
پیش از تطبیق نرمال می‌شوند (تبدیل کاف/ی/هٔ عربی به فارسی، حذف اعراب و نیم‌فاصله و
یکسان‌سازی فاصله‌ها) تا «کله‌پاچه»، «کله پاچه» و «كله پاچة» یکسان دیده شوند.
کلیدواژه‌ها:

- کباب (زیررشته‌ای): `کباب`، `جگرکی`، `جگر`، `دلوقلوه`، `دونر`.
- طباخی (زیررشته‌ای): `کلهپاچه`، `کلهپزی`، `سیراب`، `شیردان`، `آبگوشت`،
  `طباخی`، `طباخ`، `حلیم`، `هلیم`، `شله`، `بریانی`، `کوفته`، `هریسه`،
  `دلمه`، `عدسی`، `شوربا`.
- طباخی (مرزکلمه‌ای): `آش`، `آشی`، `آشکده`، `آشپزی`، `آشفروشی`، `سوپ`،
  `پاچه`، `بریان`، `دیزی`.
- کترینگ: `کترینگ`، `کیترینگ`، `catering`، `تهیهغذا`، `پذیرایی`.

**چرا دو نوع تطبیق؟** تطبیق زیررشته‌ای شکل‌های صرفی را می‌گیرد («چلوکبابی»،
«حلیم‌فروشی»)، اما برای کلیدواژهٔ کوتاه «آش» خطرناک است؛ چون نرمال‌سازی «آ» به
«ا» رشتهٔ «آش» را به «اش» تبدیل می‌کند و ناخواسته «آشپزخانه» (برند رایج
رستوران)، «آشنا»، «آشتی»، «آشوری»، «سرآشپز» و «آشیانه» را می‌گیرد. پس این
کلیدواژه‌ها **مرزکلمه‌ای** سنجیده می‌شوند و شکل‌های صرفی درست
(`آشی`/`آشکده`/`آشپزی`) صریحاً فهرست شده‌اند. به‌همین‌ترتیب «سوپ» از
«سوپرمارکت»، «دیزی» از «دیزین» (پیست اسکی) و «بریان» از «بریانک» جدا می‌شود.

**نکات دقتِ دیگر:**

- نام از همهٔ کلیدهای نام‌دار خوانده می‌شود (`name`، `name:fa`،
  `official_name`، `alt_name`)؛ بعضی مکان‌ها نام فارسی را فقط در `name:fa`
  دارند و `name` لاتین است (نمونه: «طباخی سینا»).
- نیم‌فاصله **مرز کلمه** است: «دیزی‌سرا» به «دیزی» و «سرا» می‌شکند تا تطبیق
  مرزکلمه‌ای کار کند.
- نویسهٔ `ى` (الف مقصوره) هم مثل `ي` به `ی` تبدیل می‌شود («كله پزى»).

قواعد نام‌محور **فقط روی مکان‌های غذاخوری** اعمال می‌شوند تا مثلاً مدرسه‌ای به
نام «دبیرستان کباب» وارد نقشه نشود. «غذاخوری» بودن با فهرست بسته سنجیده می‌شود:
`amenity∈{cafe, restaurant, fast_food, food_court, ice_cream, juice_bar, catering,
bbq, biergarten}` یا `shop∈{coffee, ice_cream, juice, catering, deli}` یا
`craft∈{caterer, catering}` یا وجود تگ `food`/`cuisine`. سه تگ `bbq`،
`biergarten` و `deli` بر پایهٔ شاهد دادهٔ ایران اضافه شده‌اند (کبابی‌هایی که با
`amenity=bbq` یا `shop=deli` ثبت شده‌اند). این قواعد به دامنهٔ
`cafe`/`juice_icecream` **دست نمی‌زنند** و آن دو نقشه عیناً مثل پیشین می‌مانند.

شرط «`amenity` موجود» برای مسیرهای سیگنال cafe/juice در `cuisine`، همان قاعدهٔ
پیشین پروژه است و دست‌نخورده مانده. برای طباخی/کباب، مسیر cuisine روی هر مکان
شناخته‌شدهٔ غذاخوری کار می‌کند و مسیر **نام‌محور** کافی است مکان در فهرست بستهٔ
غذاخوری‌ها باشد (`shop`/`craft` غذایی یا `food=*`/`cuisine=*`)؛ چون بعضی
آشکده/حلیم‌فروشی‌ها هیچ `amenity` استانداردی ندارند.

**دامنهٔ اصلی** با ترتیب تقدم `cafe` > `juice_icecream` > `tabbakh` > `kebab` >
`fastfood` > `restaurant` انتخاب می‌شود و فقط برای آیکون/نوعِ پیش‌فرض و سازگاری
عقب‌رو است؛ حضور مکان روی هر نقشه به عضویت آن در `domains` بستگی دارد، نه به
دامنهٔ اصلی.

چند مثال (سمت چپ تگ‌های OSM و سمت راست فهرست `domains`):

- `amenity=restaurant` + `cuisine=cafe`: فهرست `["cafe","restaurant"]` (کافه‌رستوران روی هر دو نقشه).
- `amenity=restaurant` + `cuisine=kebab`: فهرست `["kebab","restaurant"]`.
- `amenity=cafe` + `cuisine=ice_cream`: فهرست `["cafe","juice_icecream"]`.
- `amenity=fast_food` + `cuisine=juice`: فهرست `["juice_icecream","fastfood"]`.

تگ چندمقداری با `;` شکسته می‌شود (مثلاً `cuisine=cake;coffee_shop`) و همهٔ مقادیر
بررسی می‌شوند. دادهٔ OSM فقط **نام و موقعیت** می‌دهد؛ ستاره، امتیاز، آیکون اختصاصی
و منطق بازاریابی Mapto از دادهٔ OSM گرفته نمی‌شود.

---

## قواعد هماهنگی

- این پوشه فقط **مرجع تحویلی** است؛ خودِ ریپو `mapcafe-data` جدا زندگی می‌کند.
- هر تغییر در طبقه‌بندی (`MapPlaceTags` و `extract-cafes.py`) باید هم‌زمان در
  الگوهای `tags-filter` ورک‌فلو آینه شود.
- پس از هر تغییر طبقه‌بندی، تطابق PHP و پایتون را روی کل خروجی بسنج
  (شمارش اختلاف باید صفر شود) تا مکان اشتباه‌دامنه ساخته نشود.
- **همگام‌سازی مرحله‌ای:** افزودن دامنه‌های جدید (`restaurant`/`fastfood`/
  `kebab`/`tabbakh`) و چند‌دامنه‌ای‌شدن سمت سرور، همراه با انتقال ماژول نقشه به
  `Core/Map` انجام می‌شود. تا آن زمان سرور ردیف‌های دامنه‌های جدید را نادیده
  می‌گیرد و نقشهٔ کافه/آبمیوه بدون تغییر می‌ماند؛ پس تغییر این پوشه بی‌خطر است.
- مستند قواعد مالکیت و امتیاز: `docs/map-places-ownership.md`.
