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

out, lines = {}, {}
for src, url in SRC.items():
    routes = {str(lk(r, "Id")): r for r in get(url.format("GetRoute"))}
    allstops = get(url.format("GetStop"))
    hit = [s for s in allstops if (lk(s, "nameZh") or "") in WANT and str(lk(s, "routeId")) in routes]
    keys = {(str(lk(s, "routeId")), str(lk(s, "goBack"))) for s in hit}
    # 這幾條公車沿路的所有站（照順序），給網頁算「坐幾站、在哪下車」
    seqs = {}
    for s in allstops:
        k = (str(lk(s, "routeId")), str(lk(s, "goBack")))
        if k in keys:
            try: la, lo = round(float(lk(s, "latitude")), 5), round(float(lk(s, "longitude")), 5)
            except (TypeError, ValueError): la = lo = None
            seqs.setdefault(k, []).append((int(lk(s, "seqNo") or 0), lk(s, "nameZh"), la, lo))
    for (rid, gb), lst in seqs.items():
        lst.sort()
        lines[f"{src}|{rid}|{gb}"] = [[n, la, lo] for _, n, la, lo in lst]
    for s in hit:
        rid, gb = str(lk(s, "routeId")), str(lk(s, "goBack"))
        r = routes[rid]
        to = lk(r, "destinationZh") if gb == "0" else lk(r, "departureZh")
        out.setdefault(lk(s, "nameZh"), []).append({"sid": str(lk(s, "Id")), "rid": rid, "src": src, "gb": gb,
            "seq": int(lk(s, "seqNo") or 0), "route": lk(r, "nameZh"), "to": to or ""})
    print(src, "stops matched:", len(hit), "lines:", len(keys))
for v in out.values(): v.sort(key=lambda x: (x["route"], x["to"]))
json.dump({"built": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"), "stops": out, "lines": lines},
          open(sys.argv[1] if len(sys.argv) > 1 else "stops.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print({k: [x["route"] + "→" + x["to"] for x in v] for k, v in out.items()})
