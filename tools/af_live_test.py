#!/usr/bin/env python3
"""Direkter Test API-Football gegen Sportschau während laufender Spiele (06.11.2026).
Fragt alle 30 s beide Quellen ab (höchstens --minuten), hält je Spiel fest, wann welcher Spielstand zuerst auftauchte,
und vergleicht die Minute. Ergebnis: live_test.json im Repo. Schreibt nichts in den Ticker."""
import argparse, json, os, sys, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_ergebnis as L

ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="."); ap.add_argument("--minuten", type=int, default=20)
a = ap.parse_args()
sp = json.load(open(os.path.join(a.repo, "spielplan.json"), encoding="utf-8"))
heute = datetime.now(L.TZ).strftime("%Y-%m-%d")
spiele = [p for p in L.partien(sp) if p.get("anstoss", "").startswith(heute) and p.get("url")]
out = {"start": datetime.now(L.TZ).strftime("%H:%M:%S"), "schluessel": bool(os.environ.get("API_FOOTBALL_KEY")), "spiele": {}, "proben": []}
# Tagesübersicht: Status und Ergebnis laut API-Football für heute (zeigt, ob die Liga live gepflegt wird)
try:
    import urllib.request
    req = urllib.request.Request(f"https://v3.football.api-sports.io/fixtures?league={L.AF_LIGA}&season=2026&date={heute}",
                                 headers={"x-apisports-key": os.environ.get("API_FOOTBALL_KEY", ""), "User-Agent": "WOSOINSIDER-Live/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    print("TAG errors", d.get("errors"), "anzahl", d.get("results"))
    for f in d.get("response", []):
        print("TAG", f["teams"]["home"]["name"], f["goals"], f["fixture"]["status"], len(f.get("events") or []), "events")
    req = urllib.request.Request("https://v3.football.api-sports.io/fixtures?live=all", headers=req.headers)
    d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    print("LIVEALL errors", d.get("errors"), "anzahl", d.get("results"), sorted({f["league"]["id"] for f in d.get("response", [])})[:60])
except Exception as e:
    print("TAG Fehler", e)
ende = time.time() + a.minuten * 60
while time.time() < ende:
    t = datetime.now(L.TZ).strftime("%H:%M:%S")
    af = L.af_live()
    alle_aus = True
    for p in spiele:
        r = L.lesen(p["url"]); x = af.get((p["heim_k"], p["gast_k"]))
        s = out["spiele"].setdefault(p["id"], {"spiel": f"{p['heim_k']}-{p['gast_k']}", "stand_zuerst": {}})
        if r:
            s["stand_zuerst"].setdefault(":".join(r["ergebnis"]), {}).setdefault("sportschau", t)
            if not any(w in r["text"].lower() for w in ("ende", "beendet", "abpfiff")):
                alle_aus = False
        if x:
            s["stand_zuerst"].setdefault(":".join(x["erg"]), {}).setdefault("apifootball", t)
            alle_aus = False
        out["proben"].append({"zeit": t, "spiel": s["spiel"], "ss": r and {"text": r["text"], "erg": r["ergebnis"], "min": r["minute"]},
                              "af": x and {"status": x["kurz"], "erg": x["erg"], "min": L.af_minute(x), "tore": [f"{o['min']} {o['n']}" for o in x["tore"]]}})
    print(t, json.dumps(out["proben"][-len(spiele):], ensure_ascii=False), flush=True)
    if alle_aus and len(out["proben"]) > 2 * len(spiele):
        break
    time.sleep(30)
open(os.path.join(a.repo, "live_test.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
