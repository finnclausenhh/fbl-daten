#!/usr/bin/env python3
"""WOSOINSIDER: Prüflauf API-Football für die Frauen-Bundesliga (nur Test, schreibt keine Ticker-Daten).

Modi:
  --bestand  Liga-ID und Abdeckung der Saison lesen, beendete Spiele laden und auswerten,
             welche Felder (Aufstellung, Teamstatistik, Spielerwerte, xG) wirklich befüllt sind.
  --messen   Spiele von heute holen; liegt ein Anpfiff in den nächsten 90 Minuten, alle 3 Minuten
             abfragen und festhalten, wann die Aufstellung erstmals erscheint.

Schlüssel kommt nur aus der Umgebung (Repo-Geheimnis API_FOOTBALL_KEY), nie aus Dateien.
Gratistarif: 100 Abfragen pro Tag. Der Lauf zählt mit und bricht bei 90 ab.
Ausgabe: apifootball/bericht.json bzw. apifootball/messung-<datum>.json
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASIS = "https://v3.football.api-sports.io"
SAISON = int(os.environ.get("SAISON", "2024"))  # Gratistarif: nur 2022 bis 2024
LIMIT = 90
AUS = Path("apifootball")
abfragen = 0


def api(pfad, **params):
    global abfragen
    if abfragen >= LIMIT:
        raise SystemExit("Abfragelimit für diesen Lauf erreicht")
    url = f"{BASIS}/{pfad}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": os.environ["API_FOOTBALL_KEY"],
                                               "User-Agent": "WOSOINSIDER-Test/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        abfragen += 1
        d = json.loads(r.read().decode("utf-8"))
    if d.get("errors"):
        raise SystemExit(f"API-Fehler bei {pfad}: {d['errors']}")
    return d.get("response", [])


def liga():
    for eintrag in api("leagues", country="Germany"):
        if eintrag["league"]["name"].strip().lower() == "frauen bundesliga":
            saison = next((s for s in eintrag["seasons"] if s["year"] == SAISON), None)
            return eintrag["league"]["id"], saison
    raise SystemExit("Frauen Bundesliga nicht gefunden")


def befuellt(x):
    return x not in (None, "", [], {}, 0)


def werte_spiel(f):
    """Ein Spiel aus fixtures?ids= auswerten."""
    lineups = f.get("lineups", [])
    stats = f.get("statistics", [])
    players = f.get("players", [])
    statfelder = {}
    for team in stats:
        for s in team.get("statistics", []):
            statfelder.setdefault(s["type"], 0)
            statfelder[s["type"]] += befuellt(s["value"])
    spielerfelder, n_spielerinnen = {}, 0
    for team in players:
        for p in team.get("players", []):
            st = (p.get("statistics") or [{}])[0]
            if not (st.get("games") or {}).get("minutes"):
                continue
            n_spielerinnen += 1
            for gruppe, inhalt in st.items():
                if isinstance(inhalt, dict):
                    for k, v in inhalt.items():
                        key = f"{gruppe}.{k}"
                        spielerfelder.setdefault(key, 0)
                        spielerfelder[key] += befuellt(v)
    return {
        "id": f["fixture"]["id"],
        "spiel": f'{f["teams"]["home"]["name"]} - {f["teams"]["away"]["name"]}',
        "anstoss": f["fixture"]["date"],
        "aufstellung_teams": len(lineups),
        "startelf_groessen": [len(l.get("startXI", [])) for l in lineups],
        "bank_groessen": [len(l.get("substitutes", [])) for l in lineups],
        "formationen": [l.get("formation") for l in lineups],
        "ereignisse": len(f.get("events", [])),
        "teamstatistik": statfelder,
        "spielerinnen_mit_minuten": n_spielerinnen,
        "spielerfelder": spielerfelder,
    }


def bestand():
    lid, saison = liga()
    spiele = api("fixtures", league=lid, season=SAISON, status="FT-AET-PEN")
    # Gratistarif kennt kein ids-Parameter: Stichprobe von 8 Spielen über die Saison verteilt,
    # je Spiel 3 Einzelabfragen (Aufstellung, Teamstatistik, Spielerwerte).
    spiele.sort(key=lambda s: s["fixture"]["date"])
    schritt = max(1, len(spiele) // 8)
    details = []
    for s in spiele[::schritt][:8]:
        fid = s["fixture"]["id"]
        details.append(dict(s, lineups=api("fixtures/lineups", fixture=fid),
                            statistics=api("fixtures/statistics", fixture=fid),
                            players=api("fixtures/players", fixture=fid), events=s.get("events", [])))
    auswertung = [werte_spiel(f) for f in details]
    n = len(auswertung) or 1
    quote = lambda key: round(sum(1 for a in auswertung if a[key]) / n * 100)
    alle_stat = sorted({k for a in auswertung for k in a["teamstatistik"]})
    alle_sp = sorted({k for a in auswertung for k in a["spielerfelder"]})
    sp_summe = sum(a["spielerinnen_mit_minuten"] for a in auswertung) or 1
    bericht = {
        "stand": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "liga_id": lid, "saison": SAISON,
        "abdeckung_laut_api": saison and saison.get("coverage"),
        "spiele_beendet_saison": len(spiele), "stichprobe": len(auswertung),
        "quote_spiele_mit_aufstellung": quote("aufstellung_teams"),
        "quote_spiele_mit_teamstatistik": quote("teamstatistik"),
        "quote_spiele_mit_spielerwerten": quote("spielerinnen_mit_minuten"),
        "teamstatistik_befuellt_in_prozent_der_teams": {
            k: round(sum(a["teamstatistik"].get(k, 0) for a in auswertung) / (2 * n) * 100) for k in alle_stat},
        "spielerfelder_befuellt_in_prozent_der_spielerinnen": {
            k: round(sum(a["spielerfelder"].get(k, 0) for a in auswertung) / sp_summe * 100) for k in alle_sp},
        "xg_vorhanden": any("expected" in k.lower() for k in alle_stat),
        "spiele": auswertung,
        "abfragen": abfragen,
    }
    AUS.mkdir(exist_ok=True)
    (AUS / "bericht.json").write_text(json.dumps(bericht, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in bericht.items() if k != "spiele"}, ensure_ascii=False, indent=1))


def messen():
    lid, _ = liga()
    heute = datetime.now(timezone.utc).date().isoformat()
    spiele = api("fixtures", league=lid, season=SAISON, date=heute)
    jetzt = datetime.now(timezone.utc)
    bald = [s for s in spiele if s["fixture"]["status"]["short"] == "NS"
            and timedelta(0) < datetime.fromisoformat(s["fixture"]["date"]) - jetzt <= timedelta(minutes=90)]
    if not bald:
        print("Kein Anpfiff in den nächsten 90 Minuten.")
        return
    ende = max(datetime.fromisoformat(s["fixture"]["date"]) for s in bald) + timedelta(minutes=5)
    ids = "-".join(str(s["fixture"]["id"]) for s in bald)
    erstmals = {}
    while datetime.now(timezone.utc) < ende:
        for f in api("fixtures", ids=ids):
            fid = f["fixture"]["id"]
            if fid not in erstmals and f.get("lineups"):
                anpfiff = datetime.fromisoformat(f["fixture"]["date"])
                erstmals[fid] = {"spiel": f'{f["teams"]["home"]["name"]} - {f["teams"]["away"]["name"]}',
                                 "anstoss": anpfiff.isoformat(),
                                 "aufstellung_gesehen": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                 "minuten_vor_anpfiff": round((anpfiff - datetime.now(timezone.utc)).total_seconds() / 60),
                                 "mit_bank": all(l.get("substitutes") for l in f["lineups"])}
        if len(erstmals) == len(bald):
            break
        time.sleep(180)
    ergebnis = {"datum": heute, "spiele": [s["fixture"]["id"] for s in bald], "erstmals": erstmals,
                "ohne_aufstellung_bis_anpfiff": [s["fixture"]["id"] for s in bald if s["fixture"]["id"] not in erstmals],
                "abfragen": abfragen}
    AUS.mkdir(exist_ok=True)
    (AUS / f"messung-{heute}-{jetzt:%H%M}.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1))
    print(json.dumps(ergebnis, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    try:
        messen() if "--messen" in sys.argv else bestand()
    except SystemExit as e:
        if e.code not in (None, 0):
            AUS.mkdir(exist_ok=True)
            (AUS / "fehler.json").write_text(json.dumps({"stand": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                "modus": "messen" if "--messen" in sys.argv else "bestand", "fehler": str(e.code), "abfragen": abfragen},
                ensure_ascii=False, indent=1))
            print("FEHLER:", e.code)
        raise
