"""抓新北市公車即時到站資料，只留下學府之森附近的站牌，存成 bus.json。
資料來源：新北市政府資料開放平臺（公車預估到站時間／公車站位資訊／公車路線清單）"""
import json, time, urllib.request, sys, os
from datetime import datetime, timezone, timedelta

BASE = "https://data.ntpc.gov.tw/api/datasets/{}/json?page={}&size={}"
ETA, STOPS, ROUTES = "07f7ccb3-ed00-43c4-966d-08e9dab24e95", "34b402a8-53d9-483d-9406-24a682c2d6dc", "0ee4e6bf-cee6-4ec8-8fe1-71f544015127"
# 要追蹤的站牌（名稱包含這些字就算）
WANT = ["廣福國小", "廣福里", "捷運海山站", "捷運土城站", "土城區公所", "捷運永寧站", "裕民廣場"]
TZ = timezone(timedelta(hours=8))

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tucheng-grandparents-helper"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8-sig"))
        except Exception as e:
            print("retry", i, url, e, file=sys.stderr); time.sleep(3)
    raise RuntimeError("fetch failed " + url)

def all_rows(ds, size=1000):
    rows, page = [], 0
    while True:
        chunk = get(BASE.format(ds, page, size))
        if not chunk: break
        rows += chunk; page += 1
        if len(chunk) < size or page > 400: break
    return rows

def k(row, *names):
    low = {key.lower(): v for key, v in row.items()}
    for n in names:
        if n.lower() in low and low[n.lower()] not in (None, ""): return low[n.lower()]
    return None

def load_cached(path, ds, max_age_h=24):
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_h * 3600:
        return json.load(open(path, encoding="utf-8"))
    rows = all_rows(ds); json.dump(rows, open(path, "w", encoding="utf-8"), ensure_ascii=False); return rows

def main(out):
    os.makedirs(".cache", exist_ok=True)
    stops = load_cached(".cache/stops.json", STOPS)
    routes = load_cached(".cache/routes.json", ROUTES)
    if stops: print("stop keys:", list(stops[0].keys()))
    if routes: print("route keys:", list(routes[0].keys()))
    rinfo = {}
    for r in routes:
        rid = str(k(r, "id", "routeid", "Id"))
        rinfo[rid] = {"name": k(r, "nameZh", "name", "routename") or rid,
                      "dep": k(r, "departureZh", "departure") or "", "dest": k(r, "destinationZh", "destination") or ""}
    want = {}
    for s in stops:
        name = k(s, "nameZh", "name", "stopname") or ""
        if any(w in name for w in WANT):
            sid = str(k(s, "id", "stopid", "Id"))
            want[sid] = {"stop": name, "route": str(k(s, "routeId", "routeid") or ""), "goBack": str(k(s, "goBack", "goback") or "")}
    print("matched stops:", len(want))
    eta = all_rows(ETA)
    if eta: print("eta keys:", list(eta[0].keys()), "rows:", len(eta))
    by = {}
    for e in eta:
        sid = str(k(e, "StopID", "stopid"))
        if sid not in want: continue
        w = want[sid]; rid = str(k(e, "RouteID", "routeid") or w["route"]); r = rinfo.get(rid, {"name": rid, "dep": "", "dest": ""})
        gb = str(k(e, "GoBack", "goback") or w["goBack"])
        toward = r["dest"] if gb == "0" else r["dep"]
        try: sec = int(float(k(e, "EstimateTime", "estimatetime")))
        except (TypeError, ValueError): sec = None
        by.setdefault(w["stop"], []).append({"route": r["name"], "to": toward, "sec": sec})
    for lst in by.values():
        lst.sort(key=lambda x: (x["sec"] is None or x["sec"] < 0, x["sec"] if x["sec"] is not None else 0, x["route"]))
    data = {"updated": datetime.now(TZ).isoformat(timespec="seconds"), "source": "新北市政府資料開放平臺", "stops": by}
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("stops with data:", {s: len(v) for s, v in by.items()})

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bus.json")
