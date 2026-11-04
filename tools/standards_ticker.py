#!/usr/bin/env python3
"""Wertet die Sportschau-Liveticker nach Standards aus (Finn 04.11.2026).

Je Liga-Spiel werden die Tickertexte gelesen. Gezählt wird pro Spielerin:
- kopf: Ticker-Einträge, in denen sie zum Kopfball kommt (Tor oder Chance)
- std_kopf: davon nach Ecke oder Freistoß
- std_tore: Tore nach Ecke oder Freistoß (Eintrag erwähnt Ecke/Freistoß und ein Tor)
- ecke_tritt: als Schützin einer Ecke genannt ("Ecke von X", "X bringt die Ecke")
Zuordnung über die Nachnamen aus den offiziellen Aufstellungen im spielplan.json.

Aufruf: python3 tools/standards_ticker.py [--aus standards_ticker.json]
Zwischenspeicher: .cache/ticker/<spiel-id>.txt (nicht im Repo)
"""
import json, os, re, sys, html, time, urllib.request, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUS = sys.argv[sys.argv.index("--aus") + 1] if "--aus" in sys.argv else os.path.join(ROOT, "standards_ticker.json")
CACHE = os.path.join(ROOT, ".cache", "ticker"); os.makedirs(CACHE, exist_ok=True)
SP = json.load(open(os.path.join(ROOT, "spielplan.json"), encoding="utf-8"))

def norm(s): return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def text(p):
    f = os.path.join(CACHE, p["id"] + ".txt")
    if os.path.exists(f): return open(f, encoding="utf-8").read().split("\n")
    req = urllib.request.Request(p["url"], headers={"User-Agent": "Mozilla/5.0"})
    t = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    z = [html.unescape(x).strip() for x in re.sub(r"<[^>]+>", "\n", t).split("\n")]
    z = [x for x in z if len(x) > 40]
    open(f, "w", encoding="utf-8").write("\n".join(z)); time.sleep(0.8)
    return z

STD = re.compile(r"\bEcke|Eckball|Freisto[ßs]|Standard", re.I)
KOPF = re.compile(r"Kopf(ball|stoß|ballt)|köpft|nickt|per Kopf", re.I)
TOR = re.compile(r"\bTor\b|Führung|trifft|Treffer|zum \d:\d|erhöht|gleicht aus|Ausgleich|verkürzt|einköpf|ins Netz|ins Tor", re.I)
NICHT_TOR = re.compile(r"knapp (vorbei|neben|über)|verfehlt|Latte|Pfosten|pariert|hält|zupackt|vorbei|daneben|drüber|abgewehrt|klärt", re.I)
TRITT = [re.compile(r"(?:Ecke|Eckball|Freistoß) von (?:\w+ )?(\w[\w-]+)"), re.compile(r"(\w[\w-]+) (?:bringt|schlägt|tritt|zirkelt|bringt) (?:die|den|eine|einen) (?:Ecke|Eckball|Freistoß)"),
         re.compile(r"(?:schlägt|bringt|tritt|zirkelt) (?:\w+ )?(\w[\w-]+) (?:einen|eine|den|die) (?:Ecke|Eckball|Freistoß)"),
         re.compile(r"(\w+)-(?:Ecke|Freistoß)"), re.compile(r"(?:schlägt|bringt) (\w[\w-]+) die Hereingabe")]

zaehl = collections.defaultdict(lambda: {"k": None, "n": None, "kopf": 0, "std_kopf": 0, "std_tore": 0, "ecke_tritt": 0, "fs_tritt": 0})
spiele = 0
for t in SP["spieltage"]:
    for p in t["partien"]:
        if p.get("status") != "beendet" or not p.get("url"): continue
        namen = {}
        for seite, k in (("heim_aufstellung", p["heim_k"]), ("gast_aufstellung", p["gast_k"])):
            a = p.get(seite) or {}
            for s in (a.get("startelf") or []) + (a.get("bank") or []):
                if s.get("n") and s.get("p") != "TW": namen[s["n"]] = (k, s.get("voll") or s["n"])
        if not namen: continue
        try: z = text(p)
        except Exception as e: print("Ticker nicht lesbar:", p["id"], e); continue
        spiele += 1
        such = sorted(namen, key=len, reverse=True)
        # Tore nach Standard: Ticker-Eintrag nennt die Torschützin, ein Tor und Ecke/Freistoß
        for g in p.get("tore") or []:
            if g.get("et") or g.get("art") == "Elfmeter" or g.get("n") not in namen: continue
            n = g["n"]
            for x in [x for x in z if len(x) < 450]:
                if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", x) and TOR.search(x) and STD.search(x) and (g["min"] + ".") in x or (re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", x) and re.search(r"nach (einer|einem) (Ecke|Eckball|Freistoß)|Standardsituation", x) and TOR.search(x)):
                    key = namen[n][0] + "|" + n; d = zaehl[key]; d["k"], d["n"] = namen[n]; d["std_tore"] += 1; break
        for x in z:
            if not (STD.search(x) or KOPF.search(x)): continue
            # Sätze einzeln prüfen, damit Name und Ereignis zusammengehören
            for satz in re.split(r"(?<=[.!?])\s+", x):
                treffer = [n for n in such if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", satz)]
                if not treffer: continue
                std = bool(STD.search(x)); kopf = bool(KOPF.search(satz))
                schuetz = {m.group(1) for r in TRITT for m in [r.search(satz)] if m}
                for n in treffer:
                    key = namen[n][0] + "|" + n; d = zaehl[key]; d["k"], d["n"] = namen[n]
                    if kopf and n not in schuetz: d["kopf"] += 1; d["std_kopf"] += 1 if std else 0
                for r in TRITT:
                    m = r.search(satz)
                    if m and m.group(1) in namen:
                        key = namen[m.group(1)][0] + "|" + m.group(1); d = zaehl[key]; d["k"], d["n"] = namen[m.group(1)]
                        d["ecke_tritt" if re.search(r"Ecke|Eckball", x) and not re.search(r"Freisto", satz) else "fs_tritt"] += 1

teams = collections.defaultdict(list)
for key, d in zaehl.items():
    if d["kopf"] or d["std_tore"] or d["ecke_tritt"] or d["fs_tritt"]: teams[d["k"]].append(d)
for k in teams: teams[k].sort(key=lambda d: (-d["std_tore"], -d["std_kopf"], -d["kopf"]))
json.dump({"spiele": spiele, "teams": teams}, open(AUS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{AUS}: {spiele} Spiele, {sum(len(v) for v in teams.values())} Spielerinnen")
