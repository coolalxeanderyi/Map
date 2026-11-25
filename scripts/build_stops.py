"""產生 stops.json：廣福國小、廣福里這兩個站牌有哪些公車、往哪裡。
即時到站時間由網頁自己去抓（新北市、台北市公車動態資訊中心的公開檔案）。"""
import gzip, json, sys, urllib.request
from datetime import datetime, timezone, timedelta

WANT = ["廣福國小", "廣福里"]
SRC = {"ntpc": "https://tcgbusfs.blob.core.windows.net/ntpcbus/{}.gz",
       "tpe": "https://tcgbusfs.blob.core.windows.net/blobbus/{}.gz"}

def get(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "tucheng-helper"}), timeout=60).read()
    try: raw = gzip.decompress(raw)
    except OSError: pass
    return json.loads(raw.decode("utf-8-sig"))["BusInfo"]

def lk(d, *names):
    low = {k.lower(): v for k, v in d.items()}
    for n in names:
        v = low.get(n.lower())
        if v not in (None, ""): return v
    return None

out = {}
for src, url in SRC.items():
    routes = {str(lk(r, "Id")): r for r in get(url.format("GetRoute"))}
    n = 0
    for s in get(url.format("GetStop")):
        name = lk(s, "nameZh") or ""
        if name not in WANT: continue
        r = routes.get(str(lk(s, "routeId")))
        if not r: continue
        gb = str(lk(s, "goBack"))
        to = lk(r, "destinationZh") if gb == "0" else lk(r, "departureZh")
        out.setdefault(name, []).append({"sid": str(lk(s, "Id")), "rid": str(lk(s, "routeId")), "src": src,
                                         "route": lk(r, "nameZh"), "to": to or ""})
        n += 1
    print(src, "stops matched:", n)
for v in out.values(): v.sort(key=lambda x: (x["route"], x["to"]))
json.dump({"built": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"), "stops": out},
          open(sys.argv[1] if len(sys.argv) > 1 else "stops.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print({k: [x["route"] + "→" + x["to"] for x in v] for k, v in out.items()})
