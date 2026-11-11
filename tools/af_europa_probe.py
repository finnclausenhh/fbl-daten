#!/usr/bin/env python3
"""Einmaliger Test (11.11.2026): Führt API-Football den Women's Europa Cup / die Women's CL mit Noten?"""
import json, os, urllib.request
def api(p, **q):
    u = "https://v3.football.api-sports.io/" + p + "?" + "&".join(f"{k}={v}" for k, v in q.items())
    r = urllib.request.Request(u, headers={"x-apisports-key": os.environ.get("API_FOOTBALL_KEY", ""), "User-Agent": "WOSOINSIDER-Probe/1.0"})
    d = json.loads(urllib.request.urlopen(r, timeout=20).read().decode())
    if d.get("errors"): print("ERR", p, q, d["errors"])
    return d.get("response", [])
out = {}
for s in ("Women", "Europa Cup", "UEFA Women"):
    for l in api("leagues", search=s.replace(" ", "%20")):
        out.setdefault("ligen", []).append([l["league"]["id"], l["league"]["name"], l["country"]["name"], [x["year"] for x in l["seasons"]][-2:]])
print(json.dumps(out.get("ligen"), ensure_ascii=False))
for tag in ("2026-11-10", "2026-11-11"):
    for f in api("fixtures", date=tag):
        n = (f["teams"]["home"]["name"] + " " + f["teams"]["away"]["name"]).lower()
        if any(k in n for k in ("wolfsburg", "frankfurt", "bayern", "feyenoord", "psv", "paris")) and ("w" in f["league"]["name"].lower()):
            pl = api("fixtures/players", fixture=f["fixture"]["id"])
            no = sum(1 for t in pl for x in t.get("players", []) for st in x.get("statistics", []) if (st.get("games") or {}).get("rating"))
            li = api("fixtures/lineups", fixture=f["fixture"]["id"])
            r = [tag, f["fixture"]["id"], f["league"]["id"], f["league"]["name"], f["teams"]["home"]["id"], f["teams"]["home"]["name"], f["teams"]["away"]["id"], f["teams"]["away"]["name"], f["fixture"]["status"]["short"], "noten", no, "lineups", len(li)]
            print("FIX", json.dumps(r, ensure_ascii=False))
            out.setdefault("spiele", []).append(r)
os.makedirs("apifootball", exist_ok=True)
json.dump(out, open("apifootball/europa_probe.json", "w"), ensure_ascii=False, indent=1)
