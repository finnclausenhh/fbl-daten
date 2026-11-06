#!/usr/bin/env python3
"""Endstand-Meldung direkt mit dem Abpfiff (Finn, 06.11.2026). Ohne Claude, aus den Live-Daten in spielplan.json.

Bisher kam der Spielbericht erst mit dem stündlichen Spieltage-Lauf (22 bis 29 Minuten nach Abpfiff). Jetzt gibt es
sofort eine kurze Meldung je Partie: Ergebnis, Tore mit Minute und Vorlage, Platzverweise, Gelbe Karten. Der
ausführliche Bericht folgt wie bisher.
Id endstand-<heim>-<TTMM>, steht auch in tools/aufstellungen_live.json (Schutz vor dem Spiegel).
Als Modul: anwenden(news, live, spielplan) -> Liste neuer oder geänderter Ids.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")


def partien(sp):
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            yield p


def meldung(p, jetzt):
    h, g = p["heim"], p["gast"]
    a, b = (int(x) for x in p["ergebnis"])
    if a > b:
        satz = f"{h} gewinnt gegen {g} mit {a}:{b}."
    elif a < b:
        satz = f"{g} gewinnt bei {h} mit {b}:{a}."
    else:
        satz = f"{h} und {g} trennen sich {a}:{b}."
    text = [satz]
    stand, tore = [0, 0], []
    for t in sorted(p.get("tore") or [], key=lambda t: int(re.sub(r"\D.*", "", str(t.get("min", "0"))) or 0)):
        stand[0 if t["seite"] == "heim" else 1] += 1
        zus = "Elfmeter" if t.get("art") == "Elfmeter" else "direkter Freistoß" if t.get("art") == "Freistoß" else "Eigentor" if t.get("art") == "Eigentor" else \
            (f"Vorlage {t['vorlage']}" if t.get("vorlage") else "")
        tore.append(f"{stand[0]}:{stand[1]} {t['n']} ({t['min']}.{', ' + zus if zus else ''})")
    if tore:
        text.append("Tore: " + ", ".join(tore) + ".")
    k = p.get("karten") or []
    rot = [f"{c['n']} ({'Gelb-Rot' if c['art'] == 'gelbrot' else 'Rot'}, {c['min']}.)" for c in k if c.get("art") in ("rot", "gelbrot")]
    if rot:
        text.append("Platzverweis: " + ", ".join(rot) + ". Eine Sperre für das nächste Spiel ist wahrscheinlich.")
    gelb = [c["n"] for c in k if c.get("art") == "gelb"]
    if gelb:
        text.append("Gelb: " + ", ".join(gelb) + ".")
    text.append("Noten und der ausführliche Bericht folgen.")
    tt = p["anstoss"][8:10] + p["anstoss"][5:7]
    return {"id": f"endstand-{(p.get('heim_k') or '').lower()}-{tt}", "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"),
            "spielerin": f"{h} gegen {g}", "verein": h, "nr": "", "pos": "Spielansetzung", "tags": ["SPIELBERICHT"],
            "headline": f"Endstand: {h} {a}:{b} {g}", "kurz": f"Endstand {p.get('heim_k')} {a}:{b} {p.get('gast_k')}",
            "text": text, "kickbase": "",
            "quellen": [{"name": "Sportschau", "url": p.get("url", "")}], "quelle_live": True, "partie_id": p["id"]}


def anwenden(news, live, sp, jetzt=None):
    jetzt = jetzt or datetime.now(TZ)
    weg = set(live.get("entfernt", []))
    grenze = (jetzt - timedelta(minutes=150)).strftime("%Y-%m-%dT%H:%M")  # nur direkt nach dem Spiel (Live-Fenster)
    out = []
    for p in partien(sp):
        if p.get("status") != "beendet" or len(p.get("ergebnis") or []) != 2 or p.get("anstoss", "") < grenze:
            continue
        m = meldung(p, jetzt)
        if m["id"] in weg:
            continue
        alt = next((x for x in news["meldungen"] if x["id"] == m["id"]), None)
        if alt is not None:
            continue  # einmal mit den Live-Daten geschrieben, danach nicht mehr anfassen (der Spieltage-Lauf ersetzt Tore ohne Karten)
        news["meldungen"] = [m] + news["meldungen"]
        live["meldungen"] = [m] + [x for x in live.get("meldungen", []) if x["id"] != m["id"]]
        out.append(m["id"])
        print(f"Endstand: {m['headline']}")
    return out
