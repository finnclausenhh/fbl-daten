"""PK-Fahrplan vor dem Spieltag (Finn 13.11.2026).

Jeden Freitag vor einem Liga-Spieltag eine News: welche Vereine vor dem Spiel eine Pressekonferenz geben,
wann, wo man sie sieht, und dass bis zur offiziellen Aufstellung noch Last-Minute-Updates kommen können.

Quellen der Angaben:
  - tools/pk_termine.json: bestätigte Termine je Spieltag (von Claude-Läufen oder von Hand eingetragen),
    z. B. {"10": {"FCB": {"wann": "Fr 13.11., 12:00", "wer": "José Barcala", "quelle": "FC Bayern"}}}
  - GEWOHNHEIT unten: was die Vereine bisher regelmäßig machen (Stand 13.11.2026, geprüft an EintrachtTV,
    FC Bayern TV, vfl-wolfsburg.de). Für alle anderen gibt es keine feste Vorab-PK, Personal kommt im Vorbericht.
Regeln:
  - Nur eine Meldung je Spieltag (id pk-mdNN). Läuft nur, wenn der erste Anstoß des nächsten Spieltags
    in den nächsten 4 Tagen liegt (Freitagsspiel am selben Abend zählt mit).
  - Keine erfundenen Uhrzeiten: ohne Eintrag in pk_termine.json steht "Uhrzeit gibt der Verein kurzfristig bekannt".
Aufruf: python3 tools/pk_fahrplan.py --repo . [--jetzt 2026-11-13T09:00] [--neu]
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    BERLIN = timezone(timedelta(hours=1))

WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Gewohnheit: "immer" = vor jedem Pflichtspiel, "top" = vor Topspielen (Gegner unter den ersten 4) und Europapokal
GEWOHNHEIT = {
    "FCB": {"art": "immer", "wer": "Trainer José Barcala", "wo": "FC Bayern TV, Aussagen meist auch auf fcbayern.com",
            "quelle": ("FC Bayern Frauen", "https://fcbayern.com/frauen/de")},
    "WOB": {"art": "top", "wer": "Trainer Stephan Lerch", "wo": "Zusammenfassung auf vfl-wolfsburg.de",
            "quelle": ("VfL Wolfsburg", "https://www.vfl-wolfsburg.de/")},
    "SGE": {"art": "top", "wer": "Trainer Niko Arnautis mit einer Spielerin", "wo": "live auf EintrachtTV",
            "quelle": ("EintrachtTV", "https://tv.eintracht.de/")},
}


def tag_vorher(anstoss):
    d = anstoss.date() - timedelta(days=1)
    return f"{WT[d.weekday()]} {d.day}.{d.month}."


def zeit_txt(anstoss):
    return f"{WT[anstoss.weekday()]} {anstoss.day}.{anstoss.month}., {anstoss:%H:%M} Uhr"


def tabelle_top4(sp):
    """Erste 4 nach Punkten und Tordifferenz aus den beendeten Partien in spielplan.json."""
    t = {}
    for st in sp.get("spieltage", []):
        for p in st.get("partien", []):
            e = p.get("ergebnis")
            if isinstance(e, str):
                e = e.split(":")
            if p.get("status") != "beendet" or not e or len(e) < 2:
                continue
            try:
                a, b = int(e[0]), int(e[1])
            except (TypeError, ValueError):
                continue
            for k, tp, tm in ((p["heim_k"], a, b), (p["gast_k"], b, a)):
                r = t.setdefault(k, [0, 0])
                r[0] += 3 if tp > tm else 1 if tp == tm else 0
                r[1] += tp - tm
    return {k for k, _ in sorted(t.items(), key=lambda x: (-x[1][0], -x[1][1]))[:4]}


def bauen(repo, jetzt, neu=False):
    sp = json.load(open(os.path.join(repo, "spielplan.json"), encoding="utf-8"))
    pfad_news = os.path.join(repo, "news.json")
    news = json.load(open(pfad_news, encoding="utf-8"))
    termine_p = os.path.join(repo, "tools", "pk_termine.json")
    termine = json.load(open(termine_p, encoding="utf-8")) if os.path.exists(termine_p) else {}

    # nächster Spieltag mit noch nicht begonnenen Partien
    st = None
    for s in sp.get("spieltage", []):
        ps = [p for p in s.get("partien", []) if p.get("anstoss")]
        if ps and all(p.get("status") == "geplant" for p in ps):
            st = s
            break
    if not st:
        print("kein offener Spieltag")
        return None
    md = st["nr"]
    partien = sorted(st["partien"], key=lambda p: p["anstoss"])
    erster = datetime.fromisoformat(partien[0]["anstoss"]).replace(tzinfo=BERLIN)
    if not (jetzt <= erster + timedelta(hours=1) and erster - jetzt <= timedelta(days=4)):
        print(f"Spieltag {md} beginnt {erster}, noch nicht dran")
        return None
    mid = f"pk-md{md}"
    alle = news["meldungen"]
    if any(m.get("id") == mid for m in alle) and not neu:
        print("schon da:", mid)
        return None

    top4 = tabelle_top4(sp)
    tm = termine.get(str(md), {})
    zeilen, quellen, mit_pk = [], [], []
    for p in partien:
        an = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=BERLIN)
        for k, gegner in ((p["heim_k"], p["gast_k"]), (p["gast_k"], p["heim_k"])):
            g = GEWOHNHEIT.get(k)
            t = tm.get(k)
            if not t and not (g and (g["art"] == "immer" or gegner in top4)):
                continue
            name = p["heim"] if k == p["heim_k"] else p["gast"]
            gname = p["gast"] if k == p["heim_k"] else p["heim"]
            wann = (t or {}).get("wann")
            wer = (t or {}).get("wer") or (g or {}).get("wer", "Trainerteam")
            wo = (t or {}).get("wo") or (g or {}).get("wo", "")
            if wann:
                zeilen.append(f"{name} (gegen {gname}, {zeit_txt(an)}): Pressekonferenz {wann}, mit {wer}" + (f", {wo}" if wo else "") + ".")
            else:  # nur Gewohnheit, Termin nicht bestätigt
                zeilen.append(f"{name} (gegen {gname}, {zeit_txt(an)}): Vor solchen Spielen gibt es üblicherweise eine Pressekonferenz mit {wer}, meist am Vortag ({tag_vorher(an)}). Einen Termin hat der Verein noch nicht genannt" + (f", danach {wo}" if wo else "") + ".")
            mit_pk.append(name)
            q = (t or {}).get("quelle")
            if q and isinstance(q, dict):
                quellen.append(q)
            elif g:
                quellen.append({"name": g["quelle"][0], "url": g["quelle"][1]})
    ohne = [p for p in partien]
    ohne_namen = []
    for p in ohne:
        for n in (p["heim"], p["gast"]):
            if n not in mit_pk:
                ohne_namen.append(n)

    text = [f"Vor dem {md}. Spieltag geben nur wenige Vereine eine Pressekonferenz. Was dort zum Personal gesagt wird, ist oft die letzte Info vor der offiziellen Aufstellung."]
    text += zeilen if zeilen else ["Diesmal ist bei keinem Verein eine Pressekonferenz vor dem Spiel bekannt."]
    if ohne_namen:
        text.append(f"Keine Pressekonferenz vor dem Spiel bekannt: {', '.join(ohne_namen)}. Dort steht das Personal meist im Vorbericht des Vereins am Vortag oder am Spieltag.")
    text.append("Die offiziellen Aufstellungen kommen etwa eine Stunde vor Anpfiff, wir melden sie automatisch. Bis dahin sind Last-Minute-Änderungen möglich, gerade bei Vereinen, die unter der Woche im Europapokal gespielt haben.")
    kick = ("Aufstellung erst nach den Pressekonferenzen festzurren"
            + (f" ({', '.join(dict.fromkeys(mit_pk))})" if mit_pk else "")
            + ". Bei allen anderen ist die offizielle Aufstellung vor Anpfiff die erste sichere Info.")
    seen, qn = set(), []
    for q in quellen:
        if q["url"] not in seen:
            seen.add(q["url"])
            qn.append(q)
    m = {"id": mid, "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"), "spielerin": "Pressekonferenzen", "verein": "", "nr": "", "pos": f"{md}. Spieltag", "symbol": "pk",
         "tags": ["UPDATE"], "headline": f"Vor dem {md}. Spieltag: Pressekonferenzen und späte Updates",
         "kurz": f"{md}. Spieltag: wer vorher spricht, wann Updates kommen", "text": text, "kickbase": kick,
         "quellen": qn or [{"name": "DFB-Datencenter", "url": "https://datencenter.dfb.de/"}]}
    news["meldungen"] = [x for x in alle if x.get("id") != mid]
    news["meldungen"].insert(0, m)
    news["stand"] = jetzt.strftime("%Y-%m-%dT%H:%M")
    json.dump(news, open(pfad_news, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("neu:", mid)
    return m


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--repo", default=".")
    a.add_argument("--jetzt")
    a.add_argument("--neu", action="store_true")
    o = a.parse_args()
    j = datetime.fromisoformat(o.jetzt).replace(tzinfo=BERLIN) if o.jetzt else datetime.now(BERLIN)
    bauen(o.repo, j, o.neu)
