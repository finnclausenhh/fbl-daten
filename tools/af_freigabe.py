#!/usr/bin/env python3
"""Gibt die nächste datenbasierte Meldung aus apifootball.json frei (Regel Finn 04.11.2026).

Zwischen 7 und 22 Uhr (deutsche Zeit): Kam im Ticker seit 4 Stunden keine neue Meldung
(news.json oder bereits freigegebene Meldung aus apifootball.json), bekommt die erste Meldung
der Warteschlange die aktuelle Uhrzeit und erscheint damit im Ticker. Pro Lauf höchstens eine.

Abwechslung (Finn 04.11.2026): nie zwei gleiche Arten hintereinander (z. B. zweimal Formtief),
und jede Art höchstens einmal pro Tag. Formtief, Formhoch und Aufwind zählen als eine Art (Form).
Passt keine Meldung der Warteschlange, wird lieber nichts freigegeben.

Aufruf: python3 tools/af_freigabe.py [apifootball.json] [news.json]
"""
import json, sys, datetime
from zoneinfo import ZoneInfo

AF = sys.argv[1] if len(sys.argv) > 1 else "apifootball.json"
NEWS = sys.argv[2] if len(sys.argv) > 2 else "news.json"
LUECKE = datetime.timedelta(hours=4)

jetzt = datetime.datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None, second=0, microsecond=0)
if not 7 <= jetzt.hour < 22:
    print("außerhalb 7 bis 22 Uhr"); sys.exit(0)

af = json.load(open(AF, encoding="utf-8"))
zeiten = []
try:
    for m in json.load(open(NEWS, encoding="utf-8")).get("meldungen", []):
        try: zeiten.append(datetime.datetime.fromisoformat(m["zeit"][:16]))
        except Exception: pass
except FileNotFoundError: pass
for n in af.get("news", []):
    if n.get("zeit"):
        z = datetime.datetime.fromisoformat(n["zeit"])
        if z <= jetzt: zeiten.append(z)
letzte = max((z for z in zeiten if z <= jetzt), default=None)
if letzte and jetzt - letzte < LUECKE:
    print(f"letzte Meldung {letzte:%d.%m. %H:%M}, noch keine Lücke"); sys.exit(0)

GRUPPE = {"FORMTIEF": "FORM", "FORMHOCH": "FORM", "AUFWIND": "FORM"}
def art_von(n):
    t = (n.get("tags") or [""])[0]
    return GRUPPE.get(t, t)
erschienen = []
try:
    for m in json.load(open(NEWS, encoding="utf-8")).get("meldungen", []):
        try: erschienen.append((datetime.datetime.fromisoformat(m["zeit"][:16]), art_von(m)))
        except Exception: pass
except FileNotFoundError: pass
for n in af.get("news", []):
    if n.get("zeit") and datetime.datetime.fromisoformat(n["zeit"]) <= jetzt:
        erschienen.append((datetime.datetime.fromisoformat(n["zeit"]), art_von(n)))
erschienen.sort()
zuletzt_art = erschienen[-1][1] if erschienen else None
heute = {a for z, a in erschienen if z.date() == jetzt.date()}
warte = [n for n in af.get("news", []) if not n.get("zeit") and not n.get("halten")]
if not warte:
    print("Warteschlange leer"); sys.exit(0)
passend = [n for n in warte if art_von(n) != zuletzt_art and art_von(n) not in heute]
if not passend:
    print("keine passende Art (Abwechslung), nichts freigegeben"); sys.exit(0)
warte = passend
warte[0]["zeit"] = jetzt.strftime("%Y-%m-%dT%H:%M")
json.dump(af, open(AF, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("freigegeben:", warte[0]["headline"])
