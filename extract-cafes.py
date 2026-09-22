#!/usr/bin/env python3
"""استخراج «مکان‌های نقشه» (خانوادهٔ کافه + خانوادهٔ آبمیوه و بستنی) از یک فایل
PBF اوپن‌استریت‌مپ (ازپیش‌فیلترشده) و ساخت خروجی گزیپ‌شده برای مصرف سرور Mapto.

این اسکریپت در ریپوی دادهٔ `mapcafe-data` توسط GitHub Actions اجرا می‌شود تا بار
پردازش سنگین از سرور برنامه برداشته شود. سرور فقط فایل گزیپ را دانلود و با دستور
`map:import-cafes` به‌صورت idempotent وارد جدول `map_places` می‌کند.

## چرا یک فایل برای چند نقشه

نقشهٔ کافه و نقشهٔ آبمیوه/بستنی از یک استخراج تغذیه می‌شوند تا:
- پیمایش PBF (سنگین‌ترین بخش) فقط یک‌بار انجام شود؛
- انتقال به نقشهٔ اختصاصی هر دامنه **فقط با فیلتر `domain`** ممکن باشد و نیازی
  به استخراج مجدد نباشد.

هر مکان فیلد `domain` می‌گیرد: `cafe` یا `juice_icecream`. سرور همان را در ستون
`map_places.domain` می‌ریزد و API عمومی با پارامتر `domain` فیلتر می‌کند.

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
`app/Domains/Cafe/Support/MapPlaceTags.php` هم‌راستا بماند (`matches()`).
طبقه‌بندی دامنه نیز باید با `MapPlaceTags::domain()` یکی بماند.

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
import sys
from datetime import datetime, timezone

import osmium


DOMAIN_CAFE = "cafe"
DOMAIN_JUICE_ICECREAM = "juice_icecream"

# cuisineهایی که «کافه‌بودن» را ثابت می‌کنند.
CAFE_CUISINES = frozenset({"cafe", "coffee_shop"})
# cuisineهایی که «آبمیوه/بستنی‌بودن» را ثابت می‌کنند.
JUICE_CUISINES = frozenset({"juice", "smoothie", "ice_cream"})
# سیگنال‌های «کافه‌بودن» برای اینکه کافه/رستوران‌های چندنوعی (با coffee/tea/cake)
# به دامنهٔ آبمیوه و بستنی نروند.
CAFE_SIGNAL_CUISINES = frozenset({
    "cafe", "coffee_shop", "coffee", "tea", "cake", "dessert",
    "pastry", "bakery", "breakfast", "brunch", "chocolate",
})
# cuisineهایی که فقط «آبمیوه» را ثابت می‌کنند (برای تفکیک آیکون از بستنی).
JUICE_ONLY_CUISINES = frozenset({"juice", "smoothie"})
# مقادیر اصلی که به‌تنهایی دامنهٔ آبمیوه و بستنی را قطعی می‌کنند.
JUICE_AMENITIES = frozenset({"ice_cream", "juice_bar"})
JUICE_SHOPS = frozenset({"ice_cream", "juice"})


def tag_values(tags: dict, key: str) -> list:
    """تگ چندمقداری را به فهرست مقادیر کوچک‌شده می‌شکند (جداکنندهٔ `;`)."""
    raw = str(tags.get(key, "") or "")
    return [part.strip().lower() for part in raw.split(";") if part.strip()]


def is_map_place(tags: dict) -> bool:
    """آیا عنصر عضو «مکان‌های نقشه» است؟ (خانوادهٔ کافه + خانوادهٔ آبمیوه/بستنی)

    باید دقیقاً با `MapPlaceTags::matches()` سرور هم‌راستا بماند؛ در غیر این صورت
    ردیف‌های اضافی ساخته می‌شود که import آن‌ها را دور می‌ریزد.
    """
    amenity = str(tags.get("amenity", "") or "")
    shop = str(tags.get("shop", "") or "")
    cuisine = tag_values(tags, "cuisine")
    cafe_cuisine = any(value in CAFE_CUISINES for value in cuisine)
    juice_cuisine = any(value in JUICE_CUISINES for value in cuisine)

    if amenity == "cafe":
        return True
    if amenity in ("restaurant", "fast_food") and cafe_cuisine:
        return True
    if amenity == "ice_cream":
        return True
    if shop == "coffee":
        return True
    if shop in JUICE_SHOPS or amenity in JUICE_AMENITIES:
        return True
    # cuisine کافه روی هر amenity دیگری (مثلاً bakery یا pub).
    if cafe_cuisine and amenity != "":
        return True
    # cuisine آبمیوه/بستنی روی هر amenity دیگری.
    return juice_cuisine and amenity != ""


def domain(tags: dict) -> str:
    """دامنهٔ نقشهٔ هر مکان: `cafe` یا `juice_icecream`.

    ترتیب تصمیم قطعی و آینهٔ `MapPlaceTags::domain()` است:
    ۱. اگر «ماهیت کافه» داشته باشد (amenity=cafe، shop=coffee یا
       cuisine=cafe|coffee_shop) → `cafe`.
    ۲. اگر آبمیوه/بستنیِ خالص باشد (amenity=ice_cream|juice_bar یا
       shop=ice_cream|juice) → `juice_icecream`.
    ۳. اگر سیگنال کافه داشته باشد (coffee/tea/cake/...) → `cafe`.
    ۴. اگر cuisine آبمیوه/بستنی داشته باشد → `juice_icecream`.
    ۵. بقیه (پیش‌فرض خانوادهٔ کافه) → `cafe`.

    قاعدهٔ کلیدی: «کافه‌بودن» بر «آبمیوه/بستنی‌بودن» مقدم است؛ پس «کافه آبمیوه
    بستنی» در دامنهٔ کافه می‌ماند و فقط آبمیوه/بستنیِ خالص به دامنهٔ خودش
    می‌رود. علت: فعلاً تمرکز روی نقشهٔ کافه است و نقشهٔ مستقل آبمیوه/بستنی
    نباید کافه‌ها را از نقشهٔ کافه بدزدد.
    """
    amenity = str(tags.get("amenity", "") or "")
    shop = str(tags.get("shop", "") or "")
    cuisine = tag_values(tags, "cuisine")

    if (amenity == "cafe"
            or shop == "coffee"
            or any(value in CAFE_CUISINES for value in cuisine)):
        return DOMAIN_CAFE
    if amenity in JUICE_AMENITIES or shop in JUICE_SHOPS:
        return DOMAIN_JUICE_ICECREAM
    if any(value in CAFE_SIGNAL_CUISINES for value in cuisine):
        return DOMAIN_CAFE
    if any(value in JUICE_CUISINES for value in cuisine):
        return DOMAIN_JUICE_ICECREAM

    return DOMAIN_CAFE


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
    """

    def __init__(self, places: list) -> None:
        super().__init__()
        self.places = places
        self.way_centroids: dict = {}

    def node(self, n) -> None:
        if not n.location.valid():
            return
        tags = to_dict(n.tags)
        if not is_map_place(tags):
            return
        self.places.append(
            {
                "osm_type": "node",
                "osm_id": n.id,
                "lat": round(n.location.lat, 7),
                "lng": round(n.location.lon, 7),
                "domain": domain(tags),
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
        if not is_map_place(tags):
            return

        self.places.append(
            {
                "osm_type": "way",
                "osm_id": w.id,
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
                "domain": domain(tags),
                "tags": tags,
            }
        )

    def relation(self, r) -> None:
        tags = to_dict(r.tags)
        if not is_map_place(tags):
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
            elif member.type == "n" and member.location.valid():
                locations.append((member.location.lat, member.location.lon))

        center = centroid(locations)
        if center is None:
            return

        self.places.append(
            {
                "osm_type": "relation",
                "osm_id": r.id,
                "lat": round(center[0], 7),
                "lng": round(center[1], 7),
                "domain": domain(tags),
                "tags": tags,
            }
        )


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract-cafes.py <input.osm.pbf> <output.json.gz>", file=sys.stderr)
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
    domains: dict = {}
    for item in places:
        kinds[item["osm_type"]] = kinds.get(item["osm_type"], 0) + 1
        domains[item["domain"]] = domains.get(item["domain"], 0) + 1

    print(f"wrote {len(places)} places to {target} ({kinds}, domains={domains})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
