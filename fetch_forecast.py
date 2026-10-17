#!/usr/bin/env python3
"""Office Week Planner: fetch 15-minute forecasts for every waypoint in routes.json
and write data.json. Free Open-Meteo API, no key needed.

Usage:  python3 fetch_forecast.py [routes.json] [data.json]
Output schema (data.json):
{
  "generated": "2026-10-18T20:31:00+02:00",
  "source": "Open-Meteo, 15-min (ICON-D2/HARMONIE blend), hourly beyond",
  "stepMinutes": 15,
  "points": { "51.6978,5.3037": { "2026-10-19": { "06:00": [rain_mm, wind_kmh, gust_kmh, temp_c], ... } } }
}
"""
import json, sys, time, urllib.request, urllib.parse, datetime

routes_path = sys.argv[1] if len(sys.argv) > 1 else "routes.json"
out_path = sys.argv[2] if len(sys.argv) > 2 else "data.json"
cfg = json.load(open(routes_path, encoding="utf-8"))

points = {}
for r in cfg["routes"]:
    for w in r["waypoints"]:
        points["%.4f,%.4f" % (w["lat"], w["lon"])] = (w["lat"], w["lon"])

def fetch_all(coords):
    """One request for all points (Open-Meteo accepts comma-separated lists); 3 attempts."""
    q = {
        "latitude": ",".join("%.4f" % la for la, lo in coords),
        "longitude": ",".join("%.4f" % lo for la, lo in coords),
        "minutely_15": "precipitation,temperature_2m,wind_speed_10m,wind_gusts_10m",
        "hourly": "precipitation,temperature_2m,wind_speed_10m,wind_gusts_10m",
        "forecast_days": 8, "timezone": "Europe/Amsterdam", "wind_speed_unit": "kmh",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q)
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "office-planner/1.0 (github.com/analluran-alt/office-planner)"})
            with urllib.request.urlopen(req, timeout=60) as f:
                j = json.load(f)
            return j if isinstance(j, list) else [j]
        except Exception as e:
            last = e
            print("attempt", attempt + 1, "failed:", e, file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise last

def rnd(x, n=1):
    return None if x is None else round(x, n)

data = {"generated": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
        "source": "Open-Meteo, 15-min where available, hourly beyond", "stepMinutes": 15, "points": {}}

keys = list(points.keys())
results = fetch_all([points[k] for k in keys])
if len(results) != len(keys):
    raise SystemExit("Open-Meteo returned %d results for %d points" % (len(results), len(keys)))
for key, j in zip(keys, results):
    days = {}
    # hourly first (coarse), then 15-min overrides where present
    h = j.get("hourly", {})
    for i, t in enumerate(h.get("time", [])):
        d, hm = t.split("T")
        slot = days.setdefault(d, {})
        for q in range(4):  # expand each hour to four 15-min slots
            hh, mm = hm.split(":")
            k = "%s:%02d" % (hh, q * 15)
            slot[k] = [rnd(h["precipitation"][i] / 4.0 if h["precipitation"][i] is not None else None, 2),
                       rnd(h["wind_speed_10m"][i]), rnd(h["wind_gusts_10m"][i]), rnd(h["temperature_2m"][i])]
    m = j.get("minutely_15", {})
    for i, t in enumerate(m.get("time", [])):
        d, hm = t.split("T")
        vals = [m["precipitation"][i], m["wind_speed_10m"][i], m["wind_gusts_10m"][i], m["temperature_2m"][i]]
        if all(v is None for v in vals):
            continue  # beyond the 15-min horizon: keep the hourly value
        days.setdefault(d, {})[hm] = [rnd(vals[0], 2), rnd(vals[1]), rnd(vals[2]), rnd(vals[3])]
    # keep only 05:00–21:45 to stay small
    for d in list(days):
        days[d] = {k: v for k, v in sorted(days[d].items()) if "05:00" <= k <= "21:45"}
    data["points"][key] = days
    print("fetched", key, len(days), "days", file=sys.stderr)

json.dump(data, open(out_path, "w", encoding="utf-8"), separators=(",", ":"))
print("wrote", out_path, file=sys.stderr)
