"""Vorberichte der Vereine je Spieltag finden und merken (Finn 13.11.2026).

Finn will in der Freitags-News (tools/pk_fahrplan.py) nicht nur sehen, wer eine Pressekonferenz gibt, sondern auch,
wann welcher Verein seinen Vorbericht bringt, mit Link, und das über die Wochen gelernt.

Ablauf:
  1. Alle 14 Vereinsquellen aus tools/vereinsquellen.json abrufen (gleiche Quellen wie die Claude-Läufe).
  2. Für den nächsten Spieltag je Verein den Artikel suchen, der vor dem Anstoß erschienen ist und nach
     Vorbericht aussieht (Wörter wie Vorbericht, Vorschau, Matchfacts, Zahlen & Fakten oder der Gegner im Titel/Link),
     keine Ergebnisse (Sieg, Niederlage, 2:1 ...).
  3. Treffer nach tools/vorberichte.json schreiben: {"spieltage": {"10": {"SCF": {zeit, titel, url}}},
     "verlauf": {"SCF": [{"md": 10, "tage_vorher": 2, "uhr": "12:00"}]}}. Ein einmal gefundener Vorbericht wird nicht
     überschrieben. Ohne Datum (HSV-Sitemap) gilt der Zeitpunkt, an dem er zuerst gesehen wurde.
  4. Aus dem Verlauf entsteht die Gewohnheit ("meist am Vortag, gegen 17 Uhr"), die pk_fahrplan.py anzeigt.
Aufruf: python3 tools/vorberichte.py --repo . [--jetzt 2026-11-13T09:00]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
# Quelle (Feld "verein" in vereinsquellen.json) -> Kürzel
QUELLE_K = {"FC Bayern München": "FCB", "VfL Wolfsburg": "WOB", "Eintracht Frankfurt": "SGE", "Bayer 04 Leverkusen": "B04",
            "1. FC Köln": "KOE", "RB Leipzig": "RBL", "SV Werder Bremen": "SVW", "SC Freiburg": "SCF",
            "1. FC Union Berlin": "FCU", "VfB Stuttgart": "VFB", "TSG Hoffenheim": "TSG", "Hamburger SV": "HSV",
            "1. FC Nürnberg": "FCN", "1. FSV Mainz 05": "M05"}
# Woran man den Gegner in Titel oder Link erkennt (klein geschrieben, ohne Umlaute zusätzlich)
GEGNER = {"FCB": ["bayern", "fcb", "münchen", "muenchen", "meister"], "WOB": ["wolfsburg", "wölfinnen", "woelfinnen", "vfl", "wob"],
          "SGE": ["frankfurt", "eintracht", "sge"], "B04": ["leverkusen", "bayer", "b04", "werkself"], "KOE": ["köln", "koeln", "fc-frauen", "koe"],
          "RBL": ["leipzig", "rbl", "rb "], "SVW": ["werder", "bremen", "weser", "svw"], "SCF": ["freiburg", "scf", "breisgau"],
          "FCU": ["union", "köpenick", "koepenick", "fcu", "unionerinnen"], "VFB": ["stuttgart", "vfb"], "TSG": ["hoffenheim", "tsg", "sinsheim"],
          "HSV": ["hamburg", "hsv", "volkspark"], "FCN": ["nürnberg", "nuernberg", "fcn", "club"], "M05": ["mainz", "m05", "05-frauen", "nullfünfer"]}
VOR = re.compile(r"vorbericht|vorschau|preview|matchfacts|zahlen\s*&\s*fakten|faktenlage|spielinfo|vor dem spiel|"
                 r"zu gast|gastier|empfang|heimspiel|auswärts|auswaerts|duell|punktejagd|flutlicht|wollen|gegen |vs\.?|an die |nach ", re.I)
ERGEBNIS = re.compile(r"\b\d+\s*:\s*\d+\b|sieg\b|siegen|gewinn|niederlage|verlier|remis|unentschieden|punkt geholt|nachbericht|"
                      r"spielbericht|stimmen zum|ticket|vorverkauf|fanbus|trikot|gewinnspiel|dauerkarte|highlights|zweite mannschaft|u\d\d|juniorinnen|frauen ii|ii\b", re.I)


def gewohnheit(verlauf):
    """Aus [{tage_vorher, uhr}] einen kurzen Satz machen."""
    if not verlauf:
        return None
    tage = Counter(v["tage_vorher"] for v in verlauf if v.get("tage_vorher") is not None).most_common(1)
    if not tage:
        return None
    t = tage[0][0]
    wann = {0: "am Spieltag selbst", 1: "am Vortag", 2: "zwei Tage vorher", 3: "drei Tage vorher"}.get(t, f"{t} Tage vorher")
    uhren = [int(v["uhr"][:2]) for v in verlauf if v.get("uhr") and v.get("tage_vorher") == t]
    if uhren:
        h = sorted(uhren)[len(uhren) // 2]
        wann += f", gegen {h} Uhr" if 6 <= h <= 22 else ""
    return f"meist {wann}" if len(verlauf) > 1 else f"zuletzt {wann}"


def naechster_spieltag(sp, jetzt):
    for s in sp.get("spieltage", []):
        ps = [p for p in s.get("partien", []) if p.get("anstoss")]
        if ps and any(datetime.fromisoformat(p["anstoss"]) > jetzt - timedelta(hours=3) for p in ps) \
                and min(datetime.fromisoformat(p["anstoss"]) for p in ps) - jetzt <= timedelta(days=6):
            return s
    return None


def eintragen(daten, md, k, anstoss, zeit, titel, url, uhr_bekannt=True):
    st = daten.setdefault("spieltage", {}).setdefault(str(md), {})
    if k in st:
        return False
    st[k] = {"zeit": zeit.strftime("%Y-%m-%dT%H:%M"), "titel": titel.strip(), "url": url}
    vl = daten.setdefault("verlauf", {}).setdefault(k, [])
    if not any(v["md"] == md for v in vl):
        vl.append({"md": md, "tage_vorher": (anstoss.date() - zeit.date()).days,
                   "uhr": zeit.strftime("%H:%M") if uhr_bekannt and zeit.strftime("%H:%M") != "00:00" else None})
    return True


def suchen(repo, jetzt):
    import vereinsquellen as vq
    sp = json.load(open(os.path.join(repo, "spielplan.json"), encoding="utf-8"))
    pfad = os.path.join(repo, "tools", "vorberichte.json")
    daten = json.load(open(pfad, encoding="utf-8")) if os.path.exists(pfad) else {}
    s = naechster_spieltag(sp, jetzt)
    if not s:
        print("kein Spieltag in Sicht")
        return daten
    md = s["nr"]
    spiel = {}
    for p in s["partien"]:
        an = datetime.fromisoformat(p["anstoss"])
        spiel[p["heim_k"]] = (an, p["gast_k"])
        spiel[p["gast_k"]] = (an, p["heim_k"])
    bekannt = {v["url"] for st in daten.get("spieltage", {}).values() for v in st.values()}
    try:
        from fbl_fetch import google_aufloesen
    except Exception:  # noqa: BLE001
        google_aufloesen = None
    neu = 0
    for q in json.load(open(os.path.join(HIER, "vereinsquellen.json"), encoding="utf-8")):
        k = QUELLE_K.get(q["verein"])
        if not k or k not in spiel or str(md) in daten.get("spieltage", {}) and k in daten["spieltage"][str(md)]:
            continue
        an, geg = spiel[k]
        try:
            items = vq.pruefe(q, 7)
        except Exception as e:  # noqa: BLE001
            print(k, "Quelle nicht erreichbar:", type(e).__name__)
            continue
        kand = []
        for i in items:
            titel = re.sub(r"\s+-\s+[^-]+$", "", i["titel"]) if q["typ"] == "googlenews" else i["titel"]
            text = (titel + " " + i["url"]).lower()
            if ERGEBNIS.search(titel) or i["url"] in bekannt:
                continue
            treffer_geg = any(w in text for w in GEGNER[geg])
            if not (treffer_geg or re.search(r"vorbericht|vorschau|matchfacts|zahlen\s*&\s*fakten|faktenlage", text)):
                continue
            if not (treffer_geg or VOR.search(titel)):
                continue
            d = i.get("datum")
            if d:
                d = d + timedelta(hours=1) if q["typ"] in ("googlenews", "rss") and d.strftime("%H:%M") != "00:00" else d
                if not (an - timedelta(days=4) <= d < an):
                    continue
            elif not treffer_geg or jetzt >= an:
                continue
            kand.append((d, titel, i["url"], bool(d)))
        if not kand:
            continue
        kand.sort(key=lambda x: x[0] or jetzt)
        d, titel, url, mit_datum = kand[0]
        if "news.google.com" in url and google_aufloesen:
            url = google_aufloesen(url)
        if eintragen(daten, md, k, an, d or jetzt, titel, url, uhr_bekannt=mit_datum):
            neu += 1
            print(f"{k}: {titel} ({(d or jetzt):%d.%m. %H:%M}) {url}")
    daten["stand"] = jetzt.strftime("%Y-%m-%dT%H:%M")
    json.dump(daten, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Spieltag {md}: {neu} neue Vorberichte")
    return daten


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--repo", default=".")
    a.add_argument("--jetzt")
    o = a.parse_args()
    from zoneinfo import ZoneInfo
    suchen(o.repo, datetime.fromisoformat(o.jetzt) if o.jetzt else datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None))
