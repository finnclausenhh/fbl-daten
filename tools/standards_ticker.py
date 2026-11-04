#!/usr/bin/env python3
"""Wertet die Sportschau-Liveticker nach Standards aus (Finn 04.11.2026).

Je Liga-Spiel werden die Tickertexte gelesen. Gezählt wird pro Spielerin:
- kopf: Ticker-Einträge, in denen sie zum Kopfball kommt (Tor oder Chance)
- std_kopf: davon nach Ecke oder Freistoß
- std_tore: Tore nach Ecke oder Freistoß (Eintrag erwähnt Ecke/Freistoß und ein Tor)
- std_kopftore: davon per Kopf (Kopfball-Szene nach Standard, die ein Tor beschreibt, Torschützin laut Spielplan)
Abwehrköpfe (Klärungen) zählen nicht. Je Ticker-Eintrag zählt eine Spielerin höchstens einmal (Stand 04.11.2026).
- ecke_tritt: als Schützin einer Ecke genannt ("Ecke von X", "X bringt die Ecke")
Zuordnung über die Nachnamen aus den offiziellen Aufstellungen im spielplan.json.

Aufruf: python3 tools/standards_ticker.py [--aus standards_ticker.json]
Zwischenspeicher: .cache/ticker/<spiel-id>.txt (nicht im Repo)
"""
import json, os, re, sys, html, time, urllib.request, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = "--debug" in sys.argv
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
    # Hervorhebungen und Links im Fließtext nicht als Zeilenumbruch werten, sonst landet der Name in einer eigenen (zu kurzen) Zeile
    t = re.sub(r"</?(?:a|strong|b|em|i)(?:\s[^>]*)?>", "", t)
    z = [html.unescape(x).strip() for x in re.sub(r"<[^>]+>", "\n", t).split("\n")]
    z = [x for x in z if len(x) > 40]
    open(f, "w", encoding="utf-8").write("\n".join(z)); time.sleep(0.8)
    return z

STD = re.compile(r"\bEcke|Eckball|Freisto[ßs]|Standard", re.I)
KOPF = re.compile(r"Kopf(ball|stoß|ballt)|köpft|köpfte|köpfen|köpfelt|geköpft|nickt|per Kopf|mit dem Kopf|mit der Stirn", re.I)
TOR = re.compile(r"\bTor\b|Führung|trifft|Treffer|zum \d:\d|erhöht|gleicht aus|Ausgleich|verkürzt|einköpf|ins Netz|ins Tor|Winkel|versenkt|netzt|köpft (?:\w+ ){0,3}ein\b|nickt (?:\w+ ){0,3}ein\b|Entscheidung|Tooor|\d:\d", re.I)
NICHT_TOR = re.compile(r"knapp (vorbei|neben|über)|verfehlt|Latte|Pfosten|pariert|hält|zupackt|vorbei|daneben|drüber|abgewehrt|klärt", re.I)
TRITT = [re.compile(r"(?:Ecke|Eckball|Freistoß) von (?:\w+ )?(\w[\w-]+)"), re.compile(r"(\w[\w-]+) (?:bringt|schlägt|tritt|zirkelt|flankt|chippt|bringt) (?:die|den|eine|einen) (?:Ecke|Eckball|Freistoß)"),
         re.compile(r"(?:schlägt|bringt|tritt|zirkelt) (?:\w+ )?(\w[\w-]+) (?:einen|eine|den|die) (?:Ecke|Eckball|Freistoß)"),
         re.compile(r"(\w+)-(?:Ecke|Freistoß)"), re.compile(r"(?:schlägt|bringt) (\w[\w-]+) die Hereingabe")]

# Abwehrköpfe zählen nicht (Klärung nach gegnerischer Ecke)
ABWEHR = re.compile(r"weggeköpft|wegköpf|klärt|klären|befrei|aus dem (Sechzehner|Strafraum|Fünfer)|aus der Gefahrenzone|zur Ecke köpft|ins Aus köpft", re.I)
STANDARDWORT = r"(?:Ecke|Eckball|Freistoß|Standard|Hereingabe|Flanke)"
def ist_schuetzin(n, satz):
    q = re.escape(n)
    return bool(re.search(STANDARDWORT + r"\w* (?:von|durch) (?:[\wÄÖÜäöüß-]+ ){0,1}" + q + r"(?![\w-])", satz)
                or re.search(r"(?<![\w-])" + q + r"s? " + STANDARDWORT, satz)
                or re.search(r"(?<![\w-])" + q + r"-" + STANDARDWORT, satz)
                or re.search(r"(?<![\w-])" + q + r" (?:bringt|schlägt|tritt|zirkelt|flankt|chippt|hebt|bedient|serviert|legt)\b", satz)
                or re.search(r"\b(?:bringt|schlägt|tritt|zirkelt|flankt|chippt|hebt|serviert) (?:[\wÄÖÜäöüß]+ ){0,1}" + q + r"(?![\w-])", satz))

SEITE = re.compile(r"von (?:der )?(links|rechts|linken|rechten)\b", re.I)
zaehl = collections.defaultdict(lambda: {"k": None, "n": None, "kopf": 0, "std_kopf": 0, "std_tore": 0, "ecke_tritt": 0, "fs_tritt": 0, "std_kopftore": 0, "ecke_l": 0, "ecke_r": 0})
spiele = 0
OHNE = []   # Kopfbälle nach Standard ohne erkannte Spielerin (zum Nachschärfen der Regeln)
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
        offen = collections.Counter(g["n"] for g in (p.get("tore") or []) if not g.get("et") and g.get("art") != "Elfmeter")
        # Tore nach Standard: Ticker-Eintrag nennt die Torschützin, ein Tor und Ecke/Freistoß
        for g in p.get("tore") or []:
            if g.get("et") or g.get("art") == "Elfmeter" or g.get("n") not in namen: continue
            n = g["n"]
            for x in [x for x in z if len(x) < 450]:
                if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", x) and TOR.search(x) and STD.search(x) and (g["min"] + ".") in x or (re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", x) and re.search(r"nach (einer|einem) (Ecke|Eckball|Freistoß)|Standardsituation", x) and TOR.search(x)):
                    key = namen[n][0] + "|" + n; d = zaehl[key]; d["k"], d["n"] = namen[n]; d["std_tore"] += 1; break
        for x in z:
            if not (STD.search(x) or KOPF.search(x)): continue
            # Zusammenfassungen und Kopfzeilen (Torliste, Fazit) zählen nicht, sonst doppelt
            if re.match(r"\s*(\d+\.\s*(\+\d+\s*)?)?(\d\d:\d\d\s*)?(Halbzeit)?[Ff]azit|\s*Zur Pause|\s*Nach \d+ Minuten", x) or "Element anwählen" in x: continue
            saetze = re.split(r"(?<=[.!?])\s+", x)
            std = bool(STD.search(x))
            koepfe = set()      # je Ticker-Eintrag zählt eine Spielerin höchstens einmal
            zuletzt = None      # zuletzt genannte Spielerin, die nicht Schützin ist (für "Der Kopfball der Berlinerin ...")
            # Torszene: "Tooor für ..., 3:2 durch Eileen Campbell" -> der Kopfball gehört der Torschützin
            tm = re.search(r"Tooor für .*?durch ([^.!?]+?)(?=\s+[A-ZÄÖÜ][a-zäöü]+[ ,!]|[.!?]|$)", x)
            torsch = next((n for n in such if tm and re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", tm.group(1))), None)
            for satz in saetze:
                treffer = [n for n in such if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", satz)]
                # Teilnamen nicht doppelt (z. B. "J. Wrede" und "Wrede")
                treffer = [n for n in treffer if not any(n != m and n in m for m in treffer)]
                schuetz = {m.group(1) for r in TRITT for m in [r.search(satz)] if m} | {n for n in treffer if ist_schuetzin(n, satz)}
                # Gegenspielerin in der Szene ("entwischt dann Vallotto", "gegen Hegering") köpft nicht
                schuetz |= {n for n in treffer if re.search(r"(?:entwischt|enteilt|gegen|vor|an|hinter) (?:dann |der |ihrer )?(?:[\wÄÖÜäöüß-]+ ){0,1}" + re.escape(n) + r"(?![\w-])", satz)}
                pos = {n: max(m.start() for m in re.finditer(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", satz)) for n in treffer}
                km = KOPF.search(satz)
                if km and not ABWEHR.search(satz):
                    if torsch and TOR.search(x) and not NICHT_TOR.search(satz): koepfe.add(torsch)
                    else:
                        # ein Kopfball = eine Spielerin: die Genannte, die dem Wort Kopfball am nächsten steht (nicht die Schützin)
                        wer = sorted([n for n in treffer if n not in schuetz], key=lambda n: abs(pos[n] - km.start()))
                        if wer: koepfe.add(wer[0])
                        elif zuletzt: koepfe.add(zuletzt)
                        elif std: OHNE.append({"spiel": p["id"], "satz": satz[:220]})
                spaeter = [n for n in sorted(treffer, key=lambda n: pos[n]) if n not in schuetz]
                if spaeter: zuletzt = spaeter[-1]
                for r in TRITT:
                    m = r.search(satz)
                    if m and m.group(1) in namen:
                        key = namen[m.group(1)][0] + "|" + m.group(1); d = zaehl[key]; d["k"], d["n"] = namen[m.group(1)]
                        d["ecke_tritt" if re.search(r"Ecke|Eckball", x) and not re.search(r"Freisto", satz) else "fs_tritt"] += 1
            torszene = bool(TOR.search(x)) and not NICHT_TOR.search(x)
            for n in koepfe:
                key = namen[n][0] + "|" + n; d = zaehl[key]; d["k"], d["n"] = namen[n]
                d["kopf"] += 1; d["std_kopf"] += 1 if std else 0
                # Kopfballtor nach Standard: Szene beschreibt ein Tor und sie hat in diesem Spiel getroffen (höchstens so oft wie Tore)
                if std and torszene and offen.get(n, 0) > 0:
                    offen[n] -= 1; d["std_kopftore"] += 1
                if DEBUG and std: print("KOPF", p["id"], namen[n][1], "|", x[:220].replace("\n", " "))
            # Ecken nach Seite (Finn 04.11.2026): wer schlägt Ecken von links, wer von rechts
            if re.search(r"Ecke|Eckball", x) and not re.search(r"Freisto", x):
                seite_x = SEITE.search(x) if len(re.findall(r"Ecke|Eckball", x)) == 1 else None
                getreten = set()
                for satz in saetze:
                    if not re.search(r"Ecke|Eckball|(?:flankt|bringt|schlägt|tritt) (?:den Ball|das Leder|die Kugel|den Standard)", satz): continue
                    for n in such:
                        if n in getreten or not re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", satz): continue
                        if ist_schuetzin(n, satz) or any(m.group(1) == n for r in TRITT for m in [r.search(satz)] if m):
                            sm = SEITE.search(satz) or seite_x
                            if sm:
                                getreten.add(n); key = namen[n][0] + "|" + n; d = zaehl[key]; d["k"], d["n"] = namen[n]
                                d["ecke_l" if sm.group(1).lower().startswith("link") else "ecke_r"] += 1
                                if DEBUG: print("SEITE", p["id"], namen[n][1], sm.group(1), "|", satz[:140])

teams = collections.defaultdict(list)
for key, d in zaehl.items():
    if d["kopf"] or d["std_tore"] or d["ecke_tritt"] or d["fs_tritt"] or d.get("ecke_l") or d.get("ecke_r"): teams[d["k"]].append(d)
for k in teams: teams[k].sort(key=lambda d: (-d["std_tore"], -d["std_kopf"], -d["kopf"]))
json.dump({"spiele": spiele, "teams": teams, "ohne_zuordnung": OHNE[-60:]}, open(AUS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"{AUS}: {spiele} Spiele, {sum(len(v) for v in teams.values())} Spielerinnen")
