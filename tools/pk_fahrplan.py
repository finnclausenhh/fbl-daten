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
Erweiterung 13.11.2026 (Finn): Die News zeigt auch, wann welcher Verein seinen Vorbericht bringt, mit Link,
sobald er da ist (tools/vorberichte.json, gefüllt von tools/vorberichte.py), sonst die gelernte Gewohnheit.
Die News wird nicht angeheftet und behält ihre erste Zeit, damit der Feed chronologisch bleibt; der Workflow
frischt sie Freitag bis Montag alle 3 Stunden auf (--auffrischen), wenn neue Vorberichte gefunden wurden.
Aufruf: python3 tools/pk_fahrplan.py --repo . [--jetzt 2026-11-13T09:00] [--neu] [--auffrischen]
"""
import argparse
import json
import re
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


def vb_zeit(z):
    if not z:
        return "online"
    d = datetime.fromisoformat(z)
    return f"seit {WT[d.weekday()]} {d.day}.{d.month}." + ("" if z.endswith("T00:00") else f", {d:%H:%M} Uhr")


def bauen(repo, jetzt, neu=False, auffrischen=False):
    sp = json.load(open(os.path.join(repo, "spielplan.json"), encoding="utf-8"))
    pfad_news = os.path.join(repo, "news.json")
    news = json.load(open(pfad_news, encoding="utf-8"))
    termine_p = os.path.join(repo, "tools", "pk_termine.json")
    termine = json.load(open(termine_p, encoding="utf-8")) if os.path.exists(termine_p) else {}

    # nächster Spieltag, der noch nicht ganz gespielt ist (Freitagsspiel läuft schon: Spieltag bleibt derselbe)
    st = None
    for s in sp.get("spieltage", []):
        ps = [p for p in s.get("partien", []) if p.get("anstoss")]
        if ps and any(p.get("status") != "beendet" for p in ps):
            st = s
            break
    if not st:
        print("kein offener Spieltag")
        return None
    md = st["nr"]
    partien = sorted(st["partien"], key=lambda p: p["anstoss"])
    erster = datetime.fromisoformat(partien[0]["anstoss"]).replace(tzinfo=BERLIN)
    letzter = datetime.fromisoformat(partien[-1]["anstoss"]).replace(tzinfo=BERLIN)
    grenze = letzter if auffrischen else erster + timedelta(hours=1)
    if not (jetzt <= grenze and erster - jetzt <= timedelta(days=4)):
        print(f"Spieltag {md} beginnt {erster}, noch nicht dran")
        return None
    mid = f"pk-md{md}"
    alle = news["meldungen"]
    alt = next((m for m in alle if m.get("id") == mid), None)
    if alt and not (neu or auffrischen):
        print("schon da:", mid)
        return None

    vb_p = os.path.join(repo, "tools", "vorberichte.json")
    vb = json.load(open(vb_p, encoding="utf-8")) if os.path.exists(vb_p) else {}
    try:
        from vorberichte import gewohnheit
    except Exception:  # noqa: BLE001
        import sys
        sys.path.insert(0, os.path.join(repo, "tools"))
        from vorberichte import gewohnheit
    vb_md = vb.get("spieltage", {}).get(str(md), {})
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
        text.append(f"Keine Pressekonferenz vor dem Spiel bekannt: {', '.join(ohne_namen)}. Dort steht das Personal meist im Vorbericht des Vereins, siehe unten.")
    # Vorberichte je Partie
    text.append("Wann die Vereine ihre Vorberichte bringen (die Links stehen unten bei den Quellen):")
    vb_quellen, n_da = [], 0
    for p in partien:
        an = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=BERLIN)
        teile = []
        for k, name in ((p["heim_k"], p["heim"]), (p["gast_k"], p["gast"])):
            e = vb_md.get(k)
            if e:
                n_da += 1
                t = e["titel"].strip()
                t = t if re.search(r'[„“"]', t) else f"„{t}“"
                teile.append(f"{name} {vb_zeit(e.get('zeit'))}: {t}")
                vb_quellen.append({"name": f"Vorbericht {name}", "url": e["url"]})
            else:
                g = gewohnheit(vb.get("verlauf", {}).get(k, []))
                if jetzt >= an:
                    teile.append(f"{name} ohne Vorbericht")
                else:
                    teile.append(f"{name} noch nicht da" + (f", {g}" if g else ", noch kein fester Rhythmus bekannt"))
        text.append(f"{p['heim']} gegen {p['gast']} ({zeit_txt(an)}): " + "; ".join(teile) + ".")
    text.append("Die offiziellen Aufstellungen kommen etwa eine Stunde vor Anpfiff, wir melden sie automatisch. Bis dahin sind Last-Minute-Änderungen möglich, gerade bei Vereinen, die unter der Woche im Europapokal gespielt haben.")
    kick = ("Aufstellung erst nach den Pressekonferenzen festzurren"
            + (f" ({', '.join(dict.fromkeys(mit_pk))})" if mit_pk else "")
            + ". Bei allen anderen ist die offizielle Aufstellung vor Anpfiff die erste sichere Info.")
    seen, qn = set(), []
    for q in quellen:
        if q["url"] not in seen:
            seen.add(q["url"])
            qn.append(q)
    qn = vb_quellen + qn
    m = {"id": mid, "zeit": alt["zeit"] if alt else jetzt.strftime("%Y-%m-%dT%H:%M"), "spielerin": "Pressekonferenzen", "verein": "", "nr": "", "pos": f"{md}. Spieltag", "symbol": "pk",
         "tags": ["UPDATE"], "headline": f"Vor dem {md}. Spieltag: Pressekonferenzen, Vorberichte und späte Updates",
         "kurz": f"{md}. Spieltag: wer wann spricht, wer wann berichtet ({n_da} von {2 * len(partien)} Vorberichten da)", "text": text, "kickbase": kick,
         "quellen": qn or [{"name": "DFB-Datencenter", "url": "https://datencenter.dfb.de/"}]}
    if alt and all(alt.get(f) == m.get(f) for f in ("headline", "kurz", "text", "kickbase", "quellen")):
        print("unverändert:", mid)
        return None
    news["meldungen"] = [x for x in alle if x.get("id") != mid] + [m]
    news["meldungen"].sort(key=lambda x: x.get("zeit", ""), reverse=True)  # chronologisch, nicht angeheftet
    news["stand"] = jetzt.strftime("%Y-%m-%dT%H:%M")
    json.dump(news, open(pfad_news, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("neu:", mid)
    return m


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--repo", default=".")
    a.add_argument("--jetzt")
    a.add_argument("--neu", action="store_true")
    a.add_argument("--auffrischen", action="store_true", help="vorhandene News mit neuen Vorberichten aktualisieren, Zeit bleibt")
    o = a.parse_args()
    j = datetime.fromisoformat(o.jetzt).replace(tzinfo=BERLIN) if o.jetzt else datetime.now(BERLIN)
    bauen(o.repo, j, o.neu, o.auffrischen)
