#!/usr/bin/env python3
"""Noten-Wächter (Finn, 06.11.2026): Noten von API-Football so früh wie möglich in den Ticker.

Bisher holte "API-Football Daten für den Ticker" die Noten nur zu festen Zeiten (Spieltagsabend 21:50, Wochenende 16:50,
täglich 4:40). Dieses Skript prüft nach jedem Abpfiff alle WARTE Sekunden bei API-Football (fixtures/players), ob die
Noten da sind. Sobald ein Spiel Noten für mindestens MIN_NOTEN Spielerinnen hat, startet es den Bau von apifootball.json
(Workflow apifootball-daten.yml) und hält in tracking/noten_zeit.json fest, wann die Noten zuerst da waren
(gemessen ab Abpfiff laut Sportschau-Uhr a2 + 45 Min. bzw. dem Zeitpunkt, an dem wir das Spiel als beendet sahen).

Aufruf: python3 tools/af_noten.py --repo . [--laufzeit 50] [--start]   (--start: Bau-Workflow wirklich auslösen)
"""
import argparse, json, os, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TZ = ZoneInfo("Europe/Berlin")
LIGA, SAISON = 82, 2026
AF_TEAM = {1858: "TSG", 1859: "B04", 1860: "FCB", 1863: "WOB", 1867: "SCF", 1870: "SVW", 1871: "KOE"}
try:
    import live_ergebnis as L  # gleiche Team-Zuordnung wie im Live-Ergebnis
    AF_TEAM = L.AF_TEAM
except Exception:
    pass
WARTE = 120  # 07.11.2026: 180 -> 120 s, genauer messen
MIN_NOTEN = 20


def api(pfad, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(f"https://v3.football.api-sports.io/{pfad}?{q}",
                                 headers={"x-apisports-key": os.environ.get("API_FOOTBALL_KEY", ""), "User-Agent": "WOSOINSIDER-Noten/1.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    if d.get("errors"):
        print("API-Fehler", pfad, d["errors"], flush=True)
    return d.get("response", [])


def offene(repo):
    """Sportschau-Partien von heute und gestern, beendet, ohne Noten in apifootball.json."""
    sp = json.load(open(os.path.join(repo, "spielplan.json"), encoding="utf-8"))
    pa = os.path.join(repo, "apifootball.json")
    af = json.load(open(pa, encoding="utf-8")) if os.path.exists(pa) else {}
    tage = {(datetime.now(TZ) - timedelta(days=d)).strftime("%Y-%m-%d") for d in (0, 1)}
    out = []
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            if p.get("anstoss", "")[:10] in tage and p.get("status") == "beendet" and not ((af.get("spiele") or {}).get(p["id"]) or {}).get("no"):
                out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--laufzeit", type=int, default=50)
    ap.add_argument("--start", action="store_true")
    a = ap.parse_args()
    pz = os.path.join(a.repo, "tracking", "noten_zeit.json")
    log = json.load(open(pz, encoding="utf-8")) if os.path.exists(pz) else {}
    ende = time.time() + a.laufzeit * 60
    gestartet = False
    while True:
        offen = offene(a.repo)
        if not offen:
            print("keine beendeten Spiele ohne Noten", flush=True)
            break
        jetzt = datetime.now(TZ)
        fx = []
        for tag in sorted({p["anstoss"][:10] for p in offen}):
            fx += api("fixtures", league=LIGA, season=SAISON, date=tag)
        neu_fertig = []
        for p in offen:
            f = next((f for f in fx if AF_TEAM.get(f["teams"]["home"]["id"]) == p.get("heim_k") and AF_TEAM.get(f["teams"]["away"]["id"]) == p.get("gast_k")), None)
            e = log.setdefault(p["id"], {"spiel": f"{p.get('heim_k')}-{p.get('gast_k')}", "anstoss": p["anstoss"]})
            u = p.get("uhr") or {}
            if u.get("a2") and "abpfiff_ca" not in e:  # 2. Halbzeit + 45 Min. + 3 Min. Nachspielzeit als Schätzung
                e["abpfiff_ca"] = (datetime.fromisoformat(u["a2"].replace("Z", "+00:00")) + timedelta(minutes=48)).astimezone(TZ).strftime("%Y-%m-%dT%H:%M")
            if not f:
                e["hinweis"] = "Spiel bei API-Football nicht gefunden (Team-Zuordnung fehlt?)"
                continue
            e["fixture"] = f["fixture"]["id"]
            e["af_status"] = f["fixture"]["status"]["short"]
            e.setdefault("erste_pruefung", jetzt.strftime("%Y-%m-%dT%H:%M"))
            if e.get("noten_da"):
                continue
            pl = api("fixtures/players", fixture=f["fixture"]["id"])
            n = sum(1 for t in pl for x in t.get("players", []) for s in x.get("statistics", []) if (s.get("games") or {}).get("rating"))
            e["noten_zuletzt"] = n
            e["letzte_pruefung"] = jetzt.strftime("%Y-%m-%dT%H:%M")
            print(f"{jetzt:%H:%M} {e['spiel']} Status {e['af_status']} Noten {n}", flush=True)
            if n >= MIN_NOTEN:
                e["noten_da"] = jetzt.strftime("%Y-%m-%dT%H:%M")
                if e.get("abpfiff_ca"):
                    e["minuten_nach_abpfiff"] = round((jetzt - datetime.fromisoformat(e["abpfiff_ca"]).replace(tzinfo=TZ)).total_seconds() / 60)
                neu_fertig.append(p["id"])
        os.makedirs(os.path.dirname(pz), exist_ok=True)
        json.dump(log, open(pz, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if not neu_fertig and a.start and not gestartet:  # Noten da, Bau lief noch nicht durch (z. B. abgebrochen): nach 30 Min. erneut
            alt = [log[p["id"]].get("bau_gestartet") for p in offen if log.get(p["id"], {}).get("noten_da")]
            if alt and all(x and x < (jetzt - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M") for x in alt):
                neu_fertig = [p["id"] for p in offen if log.get(p["id"], {}).get("noten_da")]
        if neu_fertig and a.start and not gestartet:
            for i in neu_fertig:
                log[i]["bau_gestartet"] = jetzt.strftime("%Y-%m-%dT%H:%M")
            json.dump(log, open(pz, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            r = subprocess.run(["gh", "workflow", "run", "apifootball-daten.yml", "--ref", "main"])
            print("Bau gestartet" if r.returncode == 0 else "WARN Bau nicht gestartet", flush=True)
            gestartet = r.returncode == 0
        if all(log.get(p["id"], {}).get("noten_da") for p in offen) or time.time() + WARTE > ende:
            break
        time.sleep(WARTE)


if __name__ == "__main__":
    main()
