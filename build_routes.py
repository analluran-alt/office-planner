#!/usr/bin/env python3
"""Office Week Planner: derive scan points along the real road route.

For every route in routes.json that has "auto": true with "from" and "to" coordinates
(and optional "viaPoints": [{lat, lon}, ...]), this asks OSRM (free, no key) for the driving
route, then places a scan point every `scanEveryMin` minutes of the user's own ride time
(`rideMinutes`), proportionally along OSRM's travel time. Points are named by reverse
geocoding (Nominatim). Results are written back into routes.json as `waypoints`, with
`generated` set, so the planner page and fetch_forecast.py can use them unchanged.

Points are rebuilt only when missing, when `from`/`to`/`viaPoints`/`scanEveryMin`/`rideMinutes`
changed (fingerprint), or when `rebuild` is true. Usage: python3 build_routes.py [routes.json]
"""
import json, sys, time, hashlib, urllib.request, urllib.parse, datetime

path = sys.argv[1] if len(sys.argv) > 1 else "routes.json"
cfg = json.load(open(path, encoding="utf-8"))
UA = "office-planner/1.0 (github.com/analluran-alt/office-planner)"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as f:
        return json.load(f)

def osrm_route(points):
    coords = ";".join("%.5f,%.5f" % (p["lon"], p["lat"]) for p in points)
    url = ("https://router.project-osrm.org/route/v1/driving/%s?overview=full&geometries=geojson"
           "&annotations=duration,distance" % coords)
    j = get(url)
    if j.get("code") != "Ok":
        raise RuntimeError("OSRM: %s" % j.get("message", j.get("code")))
    r = j["routes"][0]
    line = r["geometry"]["coordinates"]            # [lon, lat] per vertex
    durs, dists = [], []
    for leg in r["legs"]:
        durs += leg["annotation"]["duration"]      # seconds per segment
        dists += leg["annotation"]["distance"]
    return line, durs, dists, r["duration"], r["distance"]

def reverse_name(lat, lon):
    try:
        j = get("https://nominatim.openstreetmap.org/reverse?lat=%.5f&lon=%.5f&format=json&zoom=10&accept-language=nl" % (lat, lon))
        a = j.get("address", {})
        for k in ("city", "town", "village", "municipality", "suburb", "county"):
            if a.get(k):
                return a[k]
        return j.get("name") or "%.3f,%.3f" % (lat, lon)
    except Exception as e:
        return "%.3f,%.3f" % (lat, lon)

def fingerprint(r):
    key = json.dumps([r.get("from"), r.get("to"), r.get("viaPoints", []), r.get("scanEveryMin", 10), r.get("rideMinutes")], sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()[:12]

changed = False
for r in cfg["routes"]:
    if not r.get("auto") or not r.get("from") or not r.get("to"):
        continue
    fp = fingerprint(r)
    if r.get("waypoints") and r.get("fingerprint") == fp and not r.get("rebuild"):
        print("keep", r["id"], file=sys.stderr)
        continue
    pts = [r["from"]] + r.get("viaPoints", []) + [r["to"]]
    line, durs, dists, total_s, total_m = osrm_route(pts)
    ride = r["rideMinutes"]; every = r.get("scanEveryMin", 10)
    # cumulative OSRM time at each vertex, scaled to the user's ride time
    cum = [0.0]
    for d in durs:
        cum.append(cum[-1] + d)
    scale = (ride * 60.0) / total_s if total_s else 1.0
    targets = list(range(0, ride, every)) + [ride]
    wps = []
    vi = 0
    for tmin in targets:
        t_s = tmin * 60.0 / scale
        while vi < len(cum) - 1 and cum[vi + 1] < t_s:
            vi += 1
        lon, lat = line[min(vi, len(line) - 1)]
        wps.append({"lat": round(lat, 4), "lon": round(lon, 4), "min": tmin})
    # names: start/end from config, the rest reverse geocoded (1 request/s, Nominatim policy)
    for i, w in enumerate(wps):
        if i == 0 and r["from"].get("name"):
            w["name"] = r["from"]["name"]
        elif i == len(wps) - 1 and r["to"].get("name"):
            w["name"] = r["to"]["name"]
        else:
            w["name"] = reverse_name(w["lat"], w["lon"]); time.sleep(1.1)
    r["waypoints"] = wps
    r["fingerprint"] = fp
    r["rebuild"] = False
    r["osrm"] = {"durationMin": round(total_s / 60), "distanceKm": round(total_m / 1000, 1),
                 "generated": datetime.datetime.now().astimezone().isoformat(timespec="minutes")}
    changed = True
    print("built", r["id"], len(wps), "points;", r["osrm"], file=sys.stderr)

if changed:
    json.dump(cfg, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(path, "a", encoding="utf-8").write("\n")
    print("routes.json updated", file=sys.stderr)
else:
    print("routes.json unchanged", file=sys.stderr)
