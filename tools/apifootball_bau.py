#!/usr/bin/env python3
"""Baut apifootball.json für den Ticker aus den API-Football-Rohdaten.

Regeln (Finn, 03.11.2026):
- Minuten, Startelf, Tore, Vorlagen, Status kommen aus unserer Quelle (spielerinnen.json).
  API-Football ergänzt nur: Noten, Teamwerte (xG, Schüsse, Ecken ...), Schlüsselpässe, Paraden, Elfmeter.
- Formkurve nur aus Einsätzen ab 60 Minuten (unsere Minuten).
- Summen immer selbst aus den Einzelspielen (Saison-Endpunkt ist unvollständig).

Aufruf: python3 tools/apifootball_bau.py [--aus test/apifootball.json]
Liest: spielerinnen.json, spielplan.json, apifootball/saison2023..2026/
"""
import json, os, re, sys, unicodedata, datetime, collections
from zoneinfo import ZoneInfo
JETZT_B = lambda: datetime.datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUS = sys.argv[sys.argv.index("--aus") + 1] if "--aus" in sys.argv else os.path.join(ROOT, "apifootball.json")
SAISON = int(os.environ.get("SAISON", "2026"))
P = lambda *a: os.path.join(ROOT, *a)
PA = lambda *a: os.path.join(os.environ.get("AFDIR", os.path.join(ROOT, "apifootball")), *a)
lade = lambda p: json.load(open(p, encoding="utf-8"))

# API-Team-ID -> unser Kürzel (IDs bleiben über die Saisons gleich)
TEAM = {1858: "TSG", 1859: "B04", 1860: "FCB", 1863: "WOB", 1867: "SCF", 1870: "SVW", 1871: "KOE",
        14014: "SGE", 20487: "FCN", 20498: "HSV", 20501: "RBL", 21564: "M05", 24130: "VFB", 24133: "FCU"}

# Starker Fuß aus unseren Stammdaten (claude/fbl-kader-stammdaten.csv, Stand 25.10.2026), Schlüssel Verein + Rückennummer
# r = rechts, l = links, b = beidfüßig. Zusätzlich die abweichenden Nummern aus dem Ligadatenfeed.
FUSS_ROH = """FCB 01b 22r 38r 02r 03r 04r 05l 07r 11r 19l 20l 36l 08b 10r 14l 15r 18r 25r 28r 06r 09r 17r 21b 23r 29r
WOB 01r 21r 22r 40b 02b 04r 16b 20r 23l 24r 39r 05r 06r 08r 10b 14b 15r 17r 07r 09b 13r 18b 19r 28r 38b 41b
SGE 01b 12r 21r 11l 13r 14r 15l 17r 19r 38r 23r 27b 29r 04r 06r 07r 08r 09r 18r 26r 10r 16r 22r 28r 47r
TSG 01r 28r 27r 04l 14l 20r 22b 30r 34r 06r 16r 17r 21l 23r 26r 11b 15b 19r 29r
B04 01r 12r 35r 02r 03r 05r 08l 10r 14l 24r 30l 06r 11b 16r 19r 21l 27r 34r 42b 07r 09r 17r 18r 23r 41r
SCF 01r 21r 33l 02r 03r 05l 18r 19r 20l 32b 34l 35l 04l 06r 07r 08r 09l 10b 15r 16r 30r 13r 31r 14r 17r 22r 23r
RBL 01r 44r 03r 05b 15r 22l 24r 30r 06r 13r 16r 18r 07r 08r 14r 17r 20r 77r
KOE 01r 12l 34r 35r 02r 04r 05r 13r 14r 21b 24l 25r 33r 37r 08r 17r 27r 28l 30r 09r 11b 19r 26r 29r
SVW 01r 16b 30r 39r 02l 03r 04r 05r 15r 19r 21r 27b 32b 33r 06r 07r 14r 23r 28r 08r 09r 10r 11b 13r 20r 26l 31b
FCU 01r 12r 28r 40r 02r 04r 05l 17r 19r 21r 25r 26r 30r 77r 06b 07l 08r 31l 32r 41r 09r 10r 11r 14r 23r 27r 42l
HSV 01r 18r 12r 33l 36r 02r 04r 05l 14r 21l 39b 08r 09r 10r 15r 26l 28r 29r 32l 37r 07r 11r 17r 19b 20r 22b 23r
FCN 01b 25b 31r 33r 02b 04r 05b 12r 14l 16r 17b 18r 21r 22l 03r 06r 07r 09r 10b 11r 19r 28r 15r 20r 23r 24r 29r 99r
VFB 01r 12r 25l 03l 05r 16b 18l 32r 06l 08b 11r 19b 28r 31r 33r 10r 79r 20r 26r
M05 01r 32r 03r 04r 09r 15r 18l 20b 25r 31r 37l 06r 07r 08r 10r 14r 16r 19r 22r 23r 27r"""
FUSS = {}
for z in FUSS_ROH.splitlines():
    k, *w = z.split()
    for t in w: FUSS[(k, str(int(t[:-1])))] = {"r": "rechts", "l": "links", "b": "beidfüßig"}[t[-1]]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s).split()

def zahl(v):
    try: return float(str(v).rstrip("%"))
    except (TypeError, ValueError): return None

# ---------------------------------------------------------------- unsere Daten
SPN = lade(P("spielerinnen.json"))
SPP = lade(P("spielplan.json"))
WIR = SPN["spielerinnen"]
PRO_K = collections.defaultdict(list)
for s in WIR: PRO_K[s["k"]].append(s)

PARTIE = {}   # (md, heimK, gastK) -> partie
for t in SPP["spieltage"]:
    for p in t["partien"]: PARTIE[(p["md"], p["heim_k"], p["gast_k"])] = p

def md_aus(r):
    m = re.search(r"(\d+)$", r or ""); return int(m.group(1)) if m else None

def finde(k, api_name, nr):
    """API-Spielerin einer unserer Spielerinnen im Verein k zuordnen: Nachname, sonst Rückennummer."""
    teile = norm(api_name)
    kand = PRO_K.get(k, [])
    if teile:
        nach = teile[-1]
        treffer = [s for s in kand if nach in norm(s["n"])]
        if len(treffer) == 1: return treffer[0]
        if len(treffer) > 1 and nr is not None:
            t2 = [s for s in treffer if str(s.get("nr")) == str(nr)]
            if t2: return t2[0]
        # "K. Buhl" vs "Bühl": norm entfernt Umlaute schon; zusammengesetzte Namen
        for s in kand:
            ns = norm(s["n"])
            if teile and len(teile[-1]) > 3 and any(x.startswith(teile[-1][:5]) for x in ns): return s
    if nr is not None:
        t3 = [s for s in kand if str(s.get("nr")) == str(nr)]
        if len(t3) == 1: return t3[0]
    return None

# ---------------------------------------------------------------- aktuelle Saison
DET = lade(PA(f"saison{SAISON}", "spiele_details.json"))
APIP = lade(PA(f"saison{SAISON}", "spielerinnen.json"))
APIP_BY = {a["player"]["id"]: a["player"] for a in APIP}

ID = {}                 # API-ID -> unsere ID
PEN = []
GELB_AF = collections.Counter()
ungeklaert = set()
spiele = {}             # unsere Partie-ID -> Teamwerte, Noten
sp = collections.defaultdict(lambda: {"no": [], "kp": 0, "kpmin": 0, "par": 0, "parsp": 0, "elf": [0, 0], "drib": [0, 0]})
teamsp = collections.defaultdict(list)   # K -> Liste je Spiel (für Ecken, xG)
ST = {"Total Shots": "sch", "Shots on Goal": "tor", "Ball Possession": "bes", "Corner Kicks": "eck",
      "Fouls": "fou", "Goalkeeper Saves": "par", "Total passes": "pas", "Passes %": "pq", "expected_goals": "xg"}
WIRBYID = {s["id"]: s for s in WIR}

for g in DET:
    md = md_aus(g["league"]["round"])
    hk, gk = TEAM.get(g["teams"]["home"]["id"]), TEAM.get(g["teams"]["away"]["id"])
    p = PARTIE.get((md, hk, gk))
    if not p or g["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"): continue
    pid = p["id"]
    werte = {}
    for blk in g.get("statistics") or []:
        k = TEAM.get(blk["team"]["id"]); seite = 0 if k == hk else 1
        for e in blk["statistics"]:
            if e["type"] in ST:
                werte.setdefault(ST[e["type"]], [None, None])[seite] = zahl(e["value"])
    noten = {}
    for blk in g.get("players") or []:
        k = TEAM.get(blk["team"]["id"])
        for pl in blk["players"]:
            a = pl["player"]; st = pl["statistics"][0]; gm = st["games"]
            wir = ID.get(a["id"])
            if not wir:
                f = finde(k, (APIP_BY.get(a["id"]) or {}).get("lastname") or a["name"], gm.get("number"))
                if f: ID[a["id"]] = wir = f["id"]
                elif gm.get("minutes"): ungeklaert.add(f"{k} {a['name']} #{gm.get('number')}")
            if not wir or not gm.get("minutes"): continue
            r = zahl(gm.get("rating"))
            if r: noten[wir] = round(r, 1)
            d = sp[wir]
            kp = (st.get("passes") or {}).get("key")
            if kp is not None: d["kp"] += kp; d["kpmin"] += gm["minutes"]
            sv = (st.get("goals") or {}).get("saves")
            if gm.get("position") == "G" and sv is not None: d["par"] += sv; d["parsp"] += 1
            dr = st.get("dribbles") or {}
            if dr.get("attempts"): d["drib"][0] += dr.get("success") or 0; d["drib"][1] += dr["attempts"]
    # Elfmeter aus den Ereignissen
    for ev in g.get("events") or []:
        if ev["type"] == "Card" and ev["detail"] == "Yellow Card":
            wy = ID.get((ev.get("player") or {}).get("id"))
            if not wy:
                fy = finde(TEAM.get(ev["team"]["id"]), (ev.get("player") or {}).get("name"), None); wy = fy and fy["id"]
            if wy: GELB_AF[wy] += 1
        if ev["type"] == "Goal" and ev["detail"] in ("Penalty", "Missed Penalty"):
            wir = ID.get(ev["player"]["id"])
            if not wir:
                f = finde(TEAM.get(ev["team"]["id"]), ev["player"]["name"], None)
                wir = f and f["id"]
            if wir: sp[wir]["elf"][0 if ev["detail"] == "Penalty" else 1] += 1; PEN.append({"md": md, "id": wir, "ok": ev["detail"] == "Penalty", "min": ev["time"]["elapsed"], "pid": pid})
    spiele[pid] = {"md": md, "w": werte, "no": noten}
    for seite, k in ((0, hk), (1, gk)):
        teamsp[k].append({"md": md, "ha": "H" if seite == 0 else "A",
                          "eck": (werte.get("eck") or [None, None])[seite], "eckg": (werte.get("eck") or [None, None])[1 - seite],
                          "fs": (werte.get("fou") or [None, None])[1 - seite], "fsg": (werte.get("fou") or [None, None])[seite],
                          "xg": (werte.get("xg") or [None, None])[seite], "xgg": (werte.get("xg") or [None, None])[1 - seite],
                          "sch": (werte.get("sch") or [None, None])[seite], "schg": (werte.get("sch") or [None, None])[1 - seite],
                          "tor": (werte.get("tor") or [None, None])[seite], "torg": (werte.get("tor") or [None, None])[1 - seite],
                          "t": int(p["ergebnis"][seite]), "g": int(p["ergebnis"][1 - seite])})

# Noten den Ligaspielen zuordnen (unsere Minuten zählen)
for pid, s in spiele.items():
    for wir, note in s["no"].items():
        e = next((x for x in WIRBYID[wir]["spiele"] if x["md"] == s["md"]), None)
        if e and e.get("art") in ("S", "E"): sp[wir]["no"].append([s["md"], note, e.get("min", 0)])

def heute():
    return datetime.date.today()

# ---------------------------------------------------------------- Profilwerte
profil = {}
for s in WIR:
    d = sp.get(s["id"]); a = None
    for aid, wid in ID.items():
        if wid == s["id"]: a = APIP_BY.get(aid); break
    noten = sorted(d["no"]) if d else []
    voll = [n for n in noten if n[2] >= 60]
    alter = (a or {}).get("age")
    geb = ((a or {}).get("birth") or {}).get("date")
    if geb:
        g = datetime.date.fromisoformat(geb); h = heute(); alter = h.year - g.year - ((h.month, h.day) < (g.month, g.day))
    gr = zahl((a or {}).get("height"))
    eintrag = {}
    if noten: eintrag["no"] = noten
    if voll:
        eintrag["avg"] = round(sum(n[1] for n in voll) / len(voll), 2)
        eintrag["best"] = max(n[1] for n in voll)
        if len(voll) >= 3: eintrag["l3"] = round(sum(n[1] for n in voll[-3:]) / 3, 2)
    f = FUSS.get((s["k"], str(s.get("nr") or "")))
    if f: eintrag["fuss"] = f
    if alter: eintrag["alter"] = alter
    if gr and 140 < gr < 200: eintrag["gr"] = int(gr)
    if d:
        if d["kpmin"] >= 90: eintrag["kp90"] = round(d["kp"] / d["kpmin"] * 90, 2); eintrag["kp"] = d["kp"]
        if d["parsp"]: eintrag["par"] = d["par"]; eintrag["parsp"] = d["parsp"]
        if any(d["elf"]): eintrag["elf"] = d["elf"]
        if d["drib"][1] >= 5: eintrag["drib"] = d["drib"]
    if eintrag: profil[s["id"]] = eintrag

# ---------------------------------------------------------------- Formtief / Formhoch (Inside)
stabil = []
def form_liste():
    tief, hoch = [], []
    for s in WIR:
        e = profil.get(s["id"]) or {}
        voll = [n for n in e.get("no", []) if n[2] >= 60]
        starts = sum(1 for x in s["spiele"] if x.get("art") == "S")
        if len(voll) < 5 or starts < 5 or s.get("pos") == "TW": continue
        l3 = sum(n[1] for n in voll[-3:]) / 3
        vor = voll[:-3]; basis = sum(n[1] for n in vor) / len(vor)
        diff = round(l3 - basis, 2)
        letzte = s["spiele"][-3:]
        k = {"id": s["id"], "n": s["n"], "k": s["k"], "pos": s.get("pos"), "l3": round(l3, 2), "vorher": round(basis, 2), "diff": diff,
             "noten": [n[1] for n in voll[-5:]], "min3": [x.get("min", 0) for x in letzte],
             "prog": (s.get("prognose") or {}).get("st")}
        # Stabil (Finn 04.11.): die ganze Saison hoch und zuletzt immer von Anfang an. Wer schon vorher sehr gut war, ist nicht "im Aufwind".
        l5 = s["spiele"][-5:]; avg = sum(n[1] for n in voll) / len(voll); k["avg"] = round(avg, 2)
        stamm = sum(1 for x in l5 if x.get("art") == "S") >= 4 and all(x.get("art") == "S" and (x.get("min") or 0) >= 60 for x in letzte)
        if diff <= -0.6: tief.append(k)
        elif stamm and avg >= 7.2 and l3 >= 7.0 and (abs(diff) < 0.5 or (diff > 0 and basis >= 7.6)): stabil.append(k)
        elif diff >= 0.6: hoch.append(k)
    tief.sort(key=lambda x: x["diff"]); hoch.sort(key=lambda x: -x["diff"]); stabil.sort(key=lambda x: -x["avg"])
    return tief[:10], hoch[:10]

tief, hoch = form_liste()

# ---------------------------------------------------------------- Einordnung: Gegner, Belastung, Ertrag (Finn 03.11.2026)
def _tab():
    t = {k: {"p": 0, "d": 0, "t": 0} for k in SPN["vereine"]}
    for (m, h, g), p in PARTIE.items():
        if p.get("status") != "beendet": continue
        a, b = int(p["ergebnis"][0]), int(p["ergebnis"][1])
        for k, x, y in ((h, a, b), (g, b, a)): t[k]["p"] += 3 if x > y else 1 if x == y else 0; t[k]["d"] += x - y; t[k]["t"] += x
    r = sorted(t, key=lambda k: (-t[k]["p"], -t[k]["d"], -t[k]["t"])); return {k: i + 1 for i, k in enumerate(r)}
RANG0 = _tab()

def einordnung(s):
    letzte = [x for x in s["spiele"] if x.get("art") in ("S", "E")][-3:]
    if not letzte: return {}
    rg = [RANG0.get(x.get("gk")) for x in letzte if x.get("gk")]
    avg = round(sum(rg) / len(rg), 1) if rg else None
    stufe = None if avg is None else "stark" if avg <= 5 else "schwach" if avg >= 10 else "mittel"
    ende = max(x["datum"][:10] for x in letzte)
    start = (datetime.date.fromisoformat(ende) - datetime.timedelta(days=14)).isoformat()
    alle = [x["datum"][:10] for x in s["spiele"] if x.get("art") in ("S", "E")] + [x["datum"][:10] for x in s.get("pokal") or [] if x.get("art") in ("S", "E")]
    last = sum(1 for d in alle if start < d <= ende)
    tv = sum(len(x.get("tore") or []) + (x.get("vorl") or 0) for x in letzte)
    return {"geg": [x.get("gk") for x in letzte], "gr": avg, "gs": stufe, "last": last, "tv": tv}

def programm(k):
    L = [z for z in SPN["vereine"][k].get("kommend") or [] if z.get("wb") == "Liga" and z.get("gk")][:3]
    if not L: return {}
    rg = [RANG0.get(z["gk"]) for z in L if RANG0.get(z["gk"])]
    av = round(sum(rg) / len(rg), 1) if rg else None
    return {"next": [[z["gk"], z["ha"], RANG0.get(z["gk"])] for z in L], "nr": av, "ns": None if av is None else "schwer" if av <= 5.5 else "leicht" if av >= 9.5 else "mittel"}
stabil = stabil[:10]
for k in tief + hoch + stabil: k.update(einordnung(WIRBYID[k["id"]])); k.update(programm(k["k"]))

# Noten und Ertrag passen nicht zusammen
trifft, leer = [], []
for s in WIR:
    e = profil.get(s["id"]) or {}
    voll = [n for n in e.get("no", []) if n[2] >= 60]
    starts = sum(1 for x in s["spiele"] if x.get("art") == "S")
    if len(voll) < 5 or starts < 5 or s.get("pos") == "TW": continue
    l3 = sum(n[1] for n in voll[-3:]) / 3; avg = sum(n[1] for n in voll) / len(voll)
    ein = einordnung(s)
    k = {"id": s["id"], "n": s["n"], "k": s["k"], "pos": s.get("pos"), "l3": round(l3, 2), "vorher": round(avg, 2), "diff": round(l3 - avg, 2), "noten": [n[1] for n in voll[-5:]],
         "min3": [x.get("min", 0) for x in s["spiele"][-3:]], "prog": (s.get("prognose") or {}).get("st"), **ein, **programm(s["k"])}
    if (l3 <= avg - 0.2 and ein.get("tv", 0) >= 2) or (l3 < 6.5 and ein.get("tv", 0) >= 1): trifft.append(k)
    elif (l3 >= avg + 0.2 or l3 >= 7.3) and ein.get("tv", 0) == 0 and s.get("pos") in ("MF", "ST") and sum(1 for x in s["spiele"][-3:] if x.get("art") == "S") >= 2: leer.append(k)
trifft.sort(key=lambda x: -x["tv"]); leer.sort(key=lambda x: -x["l3"])
lauf = []
for s in WIR:
    e = profil.get(s["id"]) or {}
    voll = [n for n in e.get("no", []) if n[2] >= 60]
    if len(voll) < 4 or s.get("pos") == "TW" or (s.get("prognose") or {}).get("st") not in ("sicher", "erwartet"): continue
    if s["id"] in {x["id"] for x in tief + hoch + stabil}: continue   # nur eine Gruppe je Spielerin (Finn 04.11.2026)
    l3 = sum(n[1] for n in voll[-3:]) / 3
    pg = programm(s["k"])
    if l3 >= 7.4 and pg.get("ns") == "leicht":
        lauf.append({"id": s["id"], "n": s["n"], "k": s["k"], "pos": s.get("pos"), "l3": round(l3, 2), "noten": [n[1] for n in voll[-5:]], "min3": [x.get("min", 0) for x in s["spiele"][-3:]], "prog": (s.get("prognose") or {}).get("st"), **einordnung(s), **pg})
lauf.sort(key=lambda x: -x["l3"])

# Team-Form: letzte 3 Ligaspiele gegen die Spiele davor
teamform = []
for k in SPN["vereine"]:
    L = []
    for (m, h, g), p in sorted(PARTIE.items()):
        if p.get("status") != "beendet" or k not in (h, g): continue
        si = 0 if k == h else 1; a = spiele.get(p["id"]) or {}
        no = [n for i, n in (a.get("no") or {}).items() if WIRBYID[i]["k"] == k and next((x.get("min", 0) for x in WIRBYID[i]["spiele"] if x["md"] == m), 0) >= 60]
        xg = (a.get("w") or {}).get("xg") or [None, None]
        t, gg = int(p["ergebnis"][si]), int(p["ergebnis"][1 - si])
        L.append({"md": m, "pkt": 3 if t > gg else 1 if t == gg else 0, "t": t, "g": gg, "no": sum(no) / len(no) if no else None, "xg": xg[si], "xgg": xg[1 - si], "gk": g if si == 0 else h})
    if len(L) < 5: continue
    d3, dv = L[-3:], L[:-3]
    sn = lambda X, f: (lambda w: round(sum(w) / len(w), 2) if w else None)([f(x) for x in X if f(x) is not None])
    tf = {"k": k, "rang": RANG0[k], "p3": sn(d3, lambda x: x["pkt"]), "pv": sn(dv, lambda x: x["pkt"]), "n3": sn(d3, lambda x: x["no"]), "nv": sn(dv, lambda x: x["no"]),
          "t3": sn(d3, lambda x: x["t"]), "g3": sn(d3, lambda x: x["g"]), "xg3": sn(d3, lambda x: x["xg"]), "xgg3": sn(d3, lambda x: x["xgg"]),
          "gr3": round(sum(RANG0[x["gk"]] for x in d3) / 3, 1), "form": "".join("S" if x["pkt"] == 3 else "U" if x["pkt"] == 1 else "N" for x in d3)}
    tf["trend"] = round((tf["n3"] or 0) - (tf["nv"] or 0), 2)
    teamform.append(tf)
teamform.sort(key=lambda x: -x["trend"])

# xG-Check der letzten beiden Spieltage mit xG
xgmds = sorted({s["md"] for s in spiele.values() if (s["w"].get("xg") or [None])[0] is not None})[-2:]
xgcheck = []
for pid, s in spiele.items():
    if s["md"] not in xgmds: continue
    p = next(pp for (m, h, g), pp in PARTIE.items() if pp["id"] == pid)
    xg = s["w"]["xg"]
    for seite, k in ((0, p["heim_k"]), (1, p["gast_k"])):
        t = int(p["ergebnis"][seite])
        if xg[seite] is None: continue
        xgcheck.append({"md": s["md"], "k": k, "gg": p["gast_k"] if seite == 0 else p["heim_k"], "t": t, "xg": xg[seite], "d": round(t - xg[seite], 2)})
xgcheck.sort(key=lambda x: -abs(x["d"]))

# Standards: Ecken je Team, Elfmeter
ecken = {}
for k, L in teamsp.items():
    e = [x["eck"] for x in L if x["eck"] is not None]; eg = [x["eckg"] for x in L if x["eckg"] is not None]
    if e: ecken[k] = {"f": round(sum(e) / len(e), 1), "g": round(sum(eg) / len(eg), 1) if eg else None, "n": len(e)}
# Schüsse pro Spiel (Finn 04.11.2026): abgegeben und zugelassen, aufs Tor, xG. Großchancen liefert API-Football nicht.
schuesse = {}
for k, L in teamsp.items():
    def avg(f, nk=1):
        v = [x[f] for x in L if x.get(f) is not None]; return (round(sum(v) / len(v), nk), len(v)) if v else (None, 0)
    sch, n = avg("sch"); schg, _ = avg("schg"); tor, _ = avg("tor"); torg, _ = avg("torg"); xg, nx = avg("xg", 2); xgg, _ = avg("xgg", 2)
    if n: schuesse[k] = {"f": sch, "g": schg, "tf": tor, "tg": torg, "xf": xg, "xgg": xgg, "n": n, "nx": nx}
# Freistöße pro Spiel: Fouls des Gegners (API-Football zählt Freistöße nicht getrennt)
freist = {}
for k, L in teamsp.items():
    e = [x["fs"] for x in L if x.get("fs") is not None]; eg = [x["fsg"] for x in L if x.get("fsg") is not None]
    if e: freist[k] = {"f": round(sum(e) / len(e), 1), "g": round(sum(eg) / len(eg), 1) if eg else None, "n": len(e)}
elfer = sorted([{"id": i, "n": WIRBYID[i]["n"], "k": WIRBYID[i]["k"], "t": e["elf"][0], "v": e["elf"][1], "fuss": e.get("fuss")}
                for i, e in profil.items() if e.get("elf")], key=lambda x: (-x["t"], x["v"]))

# Bestenlisten (Statistik)
def bl(werte, n=10): return sorted(werte, key=lambda x: -x["w"])[:n]
best = {}
best["note"] = bl([{"id": i, "w": e["avg"], "z": f"{len([n for n in e['no'] if n[2] >= 60])} Spiele"} for i, e in profil.items()
                   if len([n for n in e.get("no", []) if n[2] >= 60]) >= 4])
best["kp90"] = bl([{"id": i, "w": e["kp90"], "z": f"{e['kp']} gesamt"} for i, e in profil.items()
                   if e.get("kp90") and sp[i]["kpmin"] >= 300])
best["par"] = bl([{"id": i, "w": round(e["par"] / e["parsp"], 1), "z": f"{e['par']} in {e['parsp']} Spielen"} for i, e in profil.items()
                  if e.get("parsp", 0) >= 3], 8)
joker = []
for s in WIR:
    t = sum(len(x.get("tore") or []) for x in s["spiele"] if x.get("art") == "E")
    if t: joker.append({"id": s["id"], "w": t, "z": f"{sum(1 for x in s['spiele'] if x.get('art') == 'E')}x eingewechselt"})
best["joker"] = bl(joker, 8)

# ---------------------------------------------------------------- Vorschau "Daten zum Spiel"
ARCH = []
for y in range(2023, SAISON):
    try: ARCH += lade(PA(f"saison{y}", "spiele_details.json"))
    except FileNotFoundError: pass

def tabelle():
    t = {k: {"p": 0, "t": 0, "g": 0, "sp": 0} for k in SPN["vereine"]}
    for (m, h, g), p in PARTIE.items():
        if p.get("status") != "beendet": continue
        a, b = int(p["ergebnis"][0]), int(p["ergebnis"][1])
        for k, x, y in ((h, a, b), (g, b, a)):
            t[k]["t"] += x; t[k]["g"] += y; t[k]["sp"] += 1; t[k]["p"] += 3 if x > y else 1 if x == y else 0
    rang = sorted(t, key=lambda k: (-t[k]["p"], -(t[k]["t"] - t[k]["g"]), -t[k]["t"]))
    return {k: i + 1 for i, k in enumerate(rang)}, t

RANG, TAB = tabelle()

def rolltab(ort):
    t = {k: [0, 0, 0, 0] for k in SPN["vereine"]}
    for (m, h, g), p in PARTIE.items():
        if p.get("status") != "beendet": continue
        a, b = int(p["ergebnis"][0]), int(p["ergebnis"][1])
        k, x, y = (h, a, b) if ort == "H" else (g, b, a)
        t[k][0] += 3 if x > y else 1 if x == y else 0; t[k][1] += x - y; t[k][2] += x; t[k][3] += 1
    r = sorted(t, key=lambda k: (-(t[k][0] / max(1, t[k][3])), -(t[k][1] / max(1, t[k][3])), -t[k][2]))
    return {k: i + 1 for i, k in enumerate(r)}
HEIMTAB, AUSTAB = rolltab("H"), rolltab("A")

def spiele_von(k):
    out = []
    for (m, h, g), p in sorted(PARTIE.items()):
        if p.get("status") != "beendet" or k not in (h, g): continue
        s = 0 if k == h else 1
        out.append({"md": m, "ha": "H" if s == 0 else "A", "t": int(p["ergebnis"][s]), "g": int(p["ergebnis"][1 - s]),
                    "gk": g if s == 0 else h})
    return out

def schnitt(L, f):
    w = [f(x) for x in L if f(x) is not None]
    return round(sum(w) / len(w), 2) if w else None

def duelle(a, b):
    ida = [i for i, k in TEAM.items() if k == a][0]; idb = [i for i, k in TEAM.items() if k == b][0]
    out = []
    for g in ARCH:
        h, w = g["teams"]["home"]["id"], g["teams"]["away"]["id"]
        if {h, w} != {ida, idb} or g["goals"]["home"] is None: continue
        ta = g["goals"]["home"] if h == ida else g["goals"]["away"]; tb = g["goals"]["away"] if h == ida else g["goals"]["home"]
        out.append({"d": g["fixture"]["date"][:10], "h": TEAM[h], "t": [ta, tb]})
    for s in spiele_von(a):
        if s["gk"] == b: out.append({"d": f"{SAISON}-md{s['md']}", "h": a if s["ha"] == "H" else b, "t": [s["t"], s["g"]]})
    return sorted(out, key=lambda x: x["d"])

def form5(L): return "".join("S" if x["t"] > x["g"] else "U" if x["t"] == x["g"] else "N" for x in L[-5:])

def karte(p):
    h, g = p["heim_k"], p["gast_k"]
    H, G = spiele_von(h), spiele_von(g)
    hh = [x for x in H if x["ha"] == "H"]; ga = [x for x in G if x["ha"] == "A"]
    def blk(L, k, ort):
        tl = [x for x in teamsp[k] if x["ha"] == ort]
        return {"sp": len(L), "pkt": schnitt(L, lambda x: 3 if x["t"] > x["g"] else 1 if x["t"] == x["g"] else 0),
                "t": schnitt(L, lambda x: x["t"]), "g": schnitt(L, lambda x: x["g"]),
                "zn": sum(1 for x in L if x["g"] == 0), "eck": schnitt(tl, lambda x: x["eck"]), "xg": schnitt(tl, lambda x: x["xg"])}
    bh, bg = blk(hh, h, "H"), blk(ga, g, "A")
    du = duelle(h, g)
    siege = [sum(1 for x in du if x["t"][0] > x["t"][1]), sum(1 for x in du if x["t"][0] == x["t"][1]), sum(1 for x in du if x["t"][0] < x["t"][1])]
    # Einordnung: Grundregeln aus dem Archiv 2023 bis 2025
    satz = []
    dh = (bh["t"] or 0) - (bh["g"] or 0); dg = (bg["t"] or 0) - (bg["g"] or 0)
    name = lambda k: SPN["vereine"][k]["name"]
    rh, ra = HEIMTAB.get(h), AUSTAB.get(g)
    if bh["sp"] >= 4 and bg["sp"] >= 4 and rh and ra:
        rolle = f"{name(h)} steht auf Platz {rh} der Heimtabelle, {name(g)} auf Platz {ra} der Auswärtstabelle"
        if rh <= 4 and ra <= 4: satz.append(f"{rolle}: Hier treffen zwei der stärksten Teams in ihrer Rolle aufeinander, die Daten sprechen für ein enges Spiel.")
        elif ra - rh >= 5 and dh - dg >= 1.5: satz.append(f"{rolle}. {name(h)} ist zu Hause klar stärker als {name(g)} auswärts. Die Tordifferenz der ersten Heim- bzw. Auswärtsspiele hat in den letzten drei Saisons den Rest der Saison gut vorhergesagt.")
        elif rh - ra >= 5 and dg - dh >= 1.5: satz.append(f"{rolle}. {name(g)} ist auswärts klar stärker als {name(h)} zu Hause. Die Tordifferenz der ersten Heim- bzw. Auswärtsspiele hat in den letzten drei Saisons den Rest der Saison gut vorhergesagt.")
        elif abs(rh - ra) >= 3: satz.append(f"{rolle}. Leichte Vorteile für {name(h) if rh < ra else name(g)}, aber kein klares Gefälle.")
        else: satz.append(f"{rolle}. Die Bilanzen liegen nah beieinander, die Daten sprechen für ein offenes Spiel.")
    # Heimstärke/-schwäche nur als Zufall einordnen (r = -0,04 im Archiv)
    gef = []
    for k, L in ((h, H), (g, G)):
        heim = [x for x in L if x["ha"] == "H"]; aus = [x for x in L if x["ha"] == "A"]
        if len(heim) >= 3 and len(aus) >= 3:
            ph = schnitt(heim, lambda x: 3 if x["t"] > x["g"] else 1 if x["t"] == x["g"] else 0); pa = schnitt(aus, lambda x: 3 if x["t"] > x["g"] else 1 if x["t"] == x["g"] else 0)
            if abs(ph - pa) >= 1.2: gef.append(f"{name(k)} {'zu Hause' if ph > pa else 'auswärts'}")
    if gef:
        satz.append(f"Dass {' und '.join(gef)} deutlich mehr Punkte {'holen' if len(gef) > 1 else 'holt'}, ist nach so wenigen Spielen eher Zufall: Ein Heim-Auswärts-Gefälle nach 4 Spielen hat im Archiv nichts über den Rest der Saison gesagt.")
    # Kantersieg zuletzt: nicht fortschreiben
    for k, L in ((h, H), (g, G)):
        if L and L[-1]["t"] - L[-1]["g"] >= 5:
            satz.append(f"Das {L[-1]['t']}:{L[-1]['g']} von {name(k)} zuletzt lässt sich nicht fortschreiben: Nach Siegen mit 5 Toren Abstand fielen im nächsten Spiel im Schnitt weniger Tore als sonst (2,26 gegenüber 2,59).")
    kb = []
    if bh["zn"] and bh["sp"] and bh["zn"] / bh["sp"] >= .5: kb.append(f"{name(h)} spielt zu Hause oft zu Null ({bh['zn']} von {bh['sp']}), gut für Torhüterin und Abwehr.")
    if bg["zn"] and bg["sp"] and bg["zn"] / bg["sp"] >= .5: kb.append(f"{name(g)} spielt auswärts oft zu Null ({bg['zn']} von {bg['sp']}), gut für Torhüterin und Abwehr.")
    if (bh["t"] or 0) >= 2.5: kb.append(f"{name(h)} trifft zu Hause im Schnitt {f"{bh['t']:g}".replace('.', ',')}-mal, Offensive gefragt.")
    if (bg["t"] or 0) >= 2.5: kb.append(f"{name(g)} trifft auswärts im Schnitt {f"{bg['t']:g}".replace('.', ',')}-mal, Offensive gefragt.")
    if (bh["g"] or 0) >= 2.5: kb.append(f"{name(h)} kassiert zu Hause im Schnitt {f"{bh['g']:g}".replace('.', ',')} Tore.")
    if (bg["g"] or 0) >= 2.5: kb.append(f"{name(g)} kassiert auswärts im Schnitt {f"{bg['g']:g}".replace('.', ',')} Tore.")
    return {"id": p["id"], "md": p["md"], "h": h, "g": g, "rang": [RANG[h], RANG[g]], "rolle": [HEIMTAB.get(h), AUSTAB.get(g)], "form": [form5(H), form5(G)],
            "heim": bh, "gast": bg, "du": du[-6:], "dus": siege, "satz": satz[:3], "kb": kb[:2]}

naechster = SPP.get("aktuell")
vorschau = [karte(p) for (m, h, g), p in sorted(PARTIE.items()) if m == naechster and p.get("status") != "beendet"]

# ---------------------------------------------------------------- Standards aus dem Sportschau-Liveticker (tools/standards_ticker.py)
stdt = {}
try:
    T = lade(P("standards_ticker.json"))["teams"]
    for k, L in T.items():
        def gr(n):
            f = finde(k, n, None); return (profil.get(f["id"]) or {}).get("gr") if f else None
        stdt[k] = {"kopf": [[x["n"], x["std_kopf"], max(x["std_tore"], x.get("std_kopftore", 0)), gr(x["n"])] for x in sorted(L, key=lambda q: (-q["std_kopf"], -max(q["std_tore"], q.get("std_kopftore", 0)))) if x["std_kopf"] or x["std_tore"]][:3],
                   "ecke": [[x["n"], x["ecke_tritt"]] for x in sorted(L, key=lambda x: -x["ecke_tritt"]) if x["ecke_tritt"]][:2],
                   "fs": [[x["n"], x["fs_tritt"]] for x in sorted(L, key=lambda x: -x["fs_tritt"]) if x["fs_tritt"]][:2],
                   # Ecken nach Seite: nur mit mindestens 2 Belegen (Finn 04.11.2026)
                   "seiten": {s: [max(((x["n"], x.get("ecke_" + s, 0)) for x in L), key=lambda q: q[1])[0], max(x.get("ecke_" + s, 0) for x in L)]
                              for s in ("l", "r") if L and max(x.get("ecke_" + s, 0) for x in L) >= 2}}
except FileNotFoundError: pass

# ---------------------------------------------------------------- News-Kandidaten (Testkopie; später in die News-Läufe)
MDL = max((v["md"] for v in spiele.values()), default=0)
jetzt = JETZT_B()
letzt = max((p["anstoss"] for (m, h, g), p in PARTIE.items() if m == MDL and p.get("anstoss")), default=None)
STAND = JETZT_B().strftime("%Y-%m-%dT%H:%M")
VN = lambda k: SPN["vereine"][k]["name"]
QAF = [{"name": "API-Football (Noten, Teamwerte)", "url": "https://www.api-football.com"}, {"name": "Sportschau (Minuten, Tore)", "url": "https://www.sportschau.de/live-und-ergebnisse/fussball/deutschland-bundesliga-frauen/"}]
PSW = {"sicher": "gesetzt", "erwartet": "erwartet in der Startelf", "unsicher": "unsicher", "unwahrscheinlich": "eher nicht in der Startelf", "ausgeschlossen": "fällt aus"}
def dz(x): return f"{x:.1f}".replace(".", ",")
def prog_satz(f):
    if not f.get("next"): return ""
    t = ", ".join(f"{'zu Hause' if h == 'H' else 'auswärts'} gegen {VN(g)} ({r}.)" for g, h, r in f["next"])
    return f"Die nächsten Ligaspiele: {t}. Im Schnitt Tabellenplatz {round(f['nr'])}, {'ein schweres' if f['ns'] == 'schwer' else 'ein leichtes' if f['ns'] == 'leicht' else 'ein gemischtes'} Programm."
def meld(sid, tags, head, kurz, text, kb, typ):
    s = WIRBYID[sid]
    return {"id": f"af-{typ}-{sid}-{MDL}", "pid": sid, "zeit": STAND, "spielerin": s["n"], "verein": s["verein"], "nr": s.get("nr"), "pos": s.get("pos"),
            "tags": tags, "headline": head, "kurz": kurz, "text": text, "kickbase": kb, "quellen": QAF, "af": True}
news = []
# Formtief/Formhoch als Frage mit Einordnung und Formvergleich (Finn 04.11.2026), Logik in tools/af_formnews.py
exec(open(os.path.join(ROOT, "tools", "af_formnews.py"), encoding="utf-8").read())
for liste, tief_ in ((tief, True), (hoch, False)):
    n_ok = 0
    for f in liste:
        if n_ok >= 2: break
        m = formmeldung(f, tief_)
        if m: news.append(m); n_ok += 1
        else: print("keine Einzelmeldung (Team genauso):", f["n"])
for f in [x for x in lauf if x["id"] not in {h["id"] for h in hoch[:2]}][:2]:
    nach = f["n"].split()[-1]; pr = PSW.get(f["prog"] or "", "offen")
    news.append(meld(f["id"], ["AUFWIND", "INSIDER"], f"{nach} in starker Form, die nächsten Gegner stehen unten", f"{nach}: Form gut, Gegner leicht",
        [f"{f['n']} ({VN(f['k'])}) kommt in den letzten drei Spielen ab 60 Minuten auf eine Durchschnittsnote von {dz(f['l3'])} und hat dabei {f.get('tv', 0)} Scorerpunkte gesammelt.", prog_satz(f)],
        f"Minuten der letzten 3 Ligaspiele: {' · '.join(str(m) + chr(39) for m in f['min3'])}. Prognose fürs nächste Spiel: {pr}.", "lauf"))
PENG = {}
for x in PEN:
    if x["md"] == MDL: PENG.setdefault(x["id"], []).append(x)
for sid, L in PENG.items():
    s = WIRBYID[sid]; nach = s["n"].split()[-1]; ok = sum(1 for x in L if x["ok"]); e = {"ok": ok == len(L)}
    news.append(meld(sid, ["ELFMETER", "STANDARD"], f"Bitter: {nach} verschießt Elfmeter" if not ok else f"{nach} verwandelt {'zwei Elfmeter' if ok == 2 else 'Elfmeter'}", (f"{nach} verwandelt {'zwei Elfmeter' if ok == 2 else 'Elfmeter'}" if ok == len(L) else f"{nach} verschießt Elfmeter"),
        [f"{s['n']} ({VN(s['k'])}) trat am {MDL}. Spieltag {'zweimal' if len(L) == 2 else ''} zum Elfmeter an ({', '.join(str(x['min']) + '. Minute' for x in L)}) und verwandelte {ok} von {len(L)}.".replace("  ", " ")],
        "Für Kickbase zählt, wer schießt: Sie ist als Schützin vermerkt." if e["ok"] else "Ob sie Schützin bleibt, ist offen. Wir beobachten den nächsten Elfmeter.", "elfmeter"))
JK = sorted([(s, next((z for z in s["spiele"] if z["md"] == MDL and z.get("art") == "E" and z.get("tore")), None)) for s in WIR], key=lambda q: -len((q[1] or {}).get("tore") or []))
JK = [q for q in JK if q[1]][:3]
for s, x in JK:
    news.append(meld(s["id"], ["JOKER"], f"Joker sticht: {s['n'].split()[-1]} trifft nach Einwechslung", f"{s['n'].split()[-1]} trifft als Joker" + (" doppelt" if len(x["tore"]) == 2 else ""),
        [f"{s['n']} ({VN(s['k'])}) kam am {MDL}. Spieltag von der Bank und traf {({1: 'einmal', 2: 'doppelt', 3: 'dreifach'}).get(len(x['tore']), str(len(x['tore'])) + '-mal')} ({', '.join(t + chr(39) for t in x['tore'])}), nach {x.get('min', 0)} Minuten Einsatzzeit."],
        "Ein Joker-Tor ist noch kein Startelf-Platz. Erst die Aufstellung am nächsten Spieltag zeigt, ob sie beginnt.", "joker"))
# Gelbe Karten: nur melden, wenn Sportschau und API-Football übereinstimmen und die DFB-Sperrenliste passt
def dfb_sperren():
    import urllib.request, html as H
    try:
        req = urllib.request.Request("https://www.dfb.de/ueber-uns/verbandsrecht/sperren", headers={"User-Agent": "Mozilla/5.0"})
        t = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print("DFB-Sperrenliste nicht erreichbar:", e); return None
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    z = [H.unescape(x).strip() for x in re.sub(r"<[^>]+>", "\n", t).split("\n")]
    z = [x for x in z if x]
    try: i = next(j for j, x in enumerate(z) if "Sperren in der Google Pixel Frauen-Bundesliga" in x)
    except StopIteration: return []
    out, j = [], i + 1
    while j < len(z) and not z[j].startswith("Die aktuellen Sperren"):
        if z[j] in ("Spielerin", "Verein", "Urteil", "Grund") or z[j].startswith("Stand"): j += 1; continue
        if j + 3 < len(z): out.append({"n": z[j], "verein": z[j + 1], "urteil": z[j + 2], "grund": z[j + 3]}); j += 4
        else: break
    return out
SPERREN = dfb_sperren()
gesperrt_dfb = lambda s: SPERREN is not None and any(norm(x["n"])[-1:] == norm(s["n"])[-1:] and set(norm(x["n"])) & set(norm(s["n"])) for x in SPERREN)
gelb_pruefen, gelb4, gelb5 = [], [], []
for s in WIR:
    g = sum(1 for z in s["spiele"] if z.get("gelb") and not z.get("gr"))
    ga = GELB_AF.get(s["id"], 0)
    if g >= 4 and g != ga: gelb_pruefen.append({"id": s["id"], "n": s["n"], "sportschau": g, "apifootball": ga})
    if g == 5 and ga == 5 and SPERREN is not None and not gesperrt_dfb(s): gelb_pruefen.append({"id": s["id"], "n": s["n"], "sportschau": g, "apifootball": ga, "hinweis": "5. Gelbe, nicht in der DFB-Sperrenliste"})
    if g == 4 and ga == 4 and SPERREN is not None and not gesperrt_dfb(s): gelb4.append(s)
    letzte_gelb = max((z["md"] for z in s["spiele"] if z.get("gelb") and not z.get("gr")), default=0)
    if g == 5 and ga == 5 and letzte_gelb == MDL and gesperrt_dfb(s): gelb5.append(s)
def naechster_gegner(k):
    z = next((z for z in SPN["vereine"][k].get("kommend") or [] if z.get("wb") == "Liga"), None)
    return f"{'zu Hause gegen' if z['ha'] == 'H' else 'auswärts gegen'} {VN(z['gk'])}" if z and z.get("gk") else "im nächsten Ligaspiel"
QDFB = [{"name": "DFB-Sperrenliste", "url": "https://www.dfb.de/ueber-uns/verbandsrecht/sperren"}]
NMD = SPP.get("aktuell")
anst = sorted(p["anstoss"] for (m, h, g), p in PARTIE.items() if m == NMD and p.get("anstoss") and p.get("status") != "beendet")
if gelb4 and anst:
    # Vorbericht: fester Artikel am Tag vor dem ersten Spiel, 10:15 (liegt das schon zurück: sofort)
    vor = (datetime.datetime.fromisoformat(anst[0]) - datetime.timedelta(days=1)).replace(hour=10, minute=15)
    news.append({"id": f"af-gelb-vor-md{NMD}", "zeit": (vor if vor > jetzt else jetzt).strftime("%Y-%m-%dT%H:%M"), "fix": True,
        "tags": ["GELBSPERRE", "VORBERICHT"], "headline": f"Gelbsperre droht: {len(gelb4)} {'Spielerin steht' if len(gelb4) == 1 else 'Spielerinnen stehen'} vor dem {NMD}. Spieltag bei vier Gelben",
        "kurz": f"Gelbsperre droht: {', '.join(x['n'].split()[-1] for x in gelb4)}",
        "text": ["Mit der fünften Gelben Karte ist eine Spielerin in der Frauen-Bundesliga ein Spiel gesperrt. Vor dem Spieltag stehen bei vier Gelben:"] +
                [f"{x['n']} ({VN(x['k'])}), {naechster_gegner(x['k'])}." for x in gelb4] +
                ["Gezählt nach den Spielberichten der Sportschau und gegengeprüft mit API-Football. Wer bereits gesperrt ist, steht auf der Sperrenliste des DFB und fehlt hier."],
        "kickbase": "Eine Gelbe mehr und sie fehlt im Spiel danach.", "quellen": QAF + QDFB, "af": True})
if gelb5 and letzt:
    # Nachbericht: fester Artikel am Tag nach dem letzten Spiel, 10:15
    nach = (datetime.datetime.fromisoformat(letzt) + datetime.timedelta(days=1)).replace(hour=10, minute=15)
    news.append({"id": f"af-gelb-nach-md{MDL}", "zeit": nach.strftime("%Y-%m-%dT%H:%M"), "fix": True, "tags": ["GELBSPERRE", "SPERRE"],
        "headline": f"Neue Gelbsperren nach dem {MDL}. Spieltag", "kurz": f"Gelbgesperrt: {', '.join(x['n'].split()[-1] for x in gelb5)}",
        "text": ["Diese Spielerinnen haben am Spieltag ihre fünfte Gelbe Karte gesehen und stehen auf der Sperrenliste des DFB:"] +
                [f"{x['n']} ({VN(x['k'])}) fehlt {naechster_gegner(x['k'])}." for x in gelb5],
        "kickbase": "Für den nächsten Spieltag nicht einplanen.", "quellen": QAF + QDFB, "af": True})
if xgcheck:
    x = [r for r in xgcheck if r["md"] == MDL]
    if x:
        r = x[0]
        news.append({"id": f"af-xg-{MDL}", "zeit": STAND, "verein": VN(r["k"]), "tags": ["xG-CHECK", "INSIDER"],
            "headline": f"xG-Check: {VN(r['k'])} {'trifft weit über' if r['d'] > 0 else 'bleibt weit unter'} den Chancen",
            "kurz": f"xG-Check: {VN(r['k'])} {r['t']} Tore bei {dz(r['xg'])} xG", "text": [f"{VN(r['k'])} erzielte gegen {VN(r['gg'])} {r['t']} Tore bei {dz(r['xg'])} erwarteten Toren (xG)."] +
            [f"{VN(z['k'])}: {z['t']} Tore bei {dz(z['xg'])} xG." for z in x[1:4]],
            "kickbase": "Hohe Effizienz gleicht sich meist aus, ungenutzte Chancen sprechen eher für mehr Tore im nächsten Spiel.", "quellen": QAF, "af": True})
def nachname(n): return n.split(" ")[-1]
if stdt:
    # Standard-Check mit Messlatte (Finn 04.11.2026). Liste: alle mit mindestens 3 Kopfbällen nach Standard oder einem
    # Kopfballtor danach. Grafik: die ersten 6 dieser Liste. Größen aus API-Football, sonst aus groessen.json (Name -> cm, Stammdaten soccerdonna/Vereine).
    try: GRS = lade(P("groessen.json"))
    except FileNotFoundError: GRS = {}
    POSW = {"TW": "Tor", "ABW": "Abwehr", "MF": "Mittelfeld", "ST": "Sturm"}
    alle = []
    for k, L in T.items():
        for x in L:
            if not (x["std_kopf"] or x["std_tore"]): continue
            f = finde(k, x["n"], None); pr = (profil.get(f["id"]) or {}) if f else {}
            alle.append({"n": x["n"], "k": k, "kopf": x["std_kopf"], "tore": x.get("std_kopftore", 0), "_k": x["kopf"],
                         "cm": pr.get("gr") or GRS.get(x["n"]), "pos": POSW.get((f or {}).get("pos", ""), "")})
    liste = sorted([x for x in alle if x["kopf"] >= 3 or (x["tore"] and x["kopf"])], key=lambda q: (-q["kopf"], -q["tore"], -q["_k"], -(q["cm"] or 0)))
    torj = [x for x in liste if x["tore"]]
    sp = liste[:6]   # Grafik: die 6 mit den meisten Kopfbällen nach Standard (Gleichstand: Tore, Kopfbälle insgesamt, Größe)
    for x in liste: x.pop("_k", None)
    if sp:
        top = sp[0]; ohne = [x for x in torj]
        titel = (f"{nachname(top['n'])} köpft am häufigsten, die Tore machen andere" if not top["tore"] and torj
                 else f"{nachname(top['n'])} köpft am häufigsten und trifft auch")
        news.append({"id": f"af-standards-md{MDL}", "zeit": None, "verein": VN(top["k"]), "spielerin": top["n"], "tags": ["STANDARD", "INSIDER"], "headline": "Standard-Check: Wer nach Ecken und Freistößen gefährlich wird",
            "kurz": titel,
            "text": ["Wir haben die Liveticker aller Ligaspiele ausgewertet: Wer kommt nach Ecken und Freistößen zum Kopfball, wer trifft so?"] +
                    [f"{x['n']} ({VN(x['k'])}): {x['kopf']} {'Kopfball' if x['kopf'] == 1 else 'Kopfbälle'} nach Standard, {x['tore'] or 'kein'} {'Tor' if x['tore'] <= 1 else 'Tore'}{', ' + str(x['cm']) + ' cm' if x['cm'] else ''}." for x in liste] +
                    ["Gezählt nach den Texten im Sportschau-Liveticker, also nur Szenen, die dort beschrieben sind. Größen: soccerdonna und Vereine."],
            "grafik": {"typ": "messlatte", "titel": titel, "sp": sp, "liste": liste, "liste_titel": "Alle mit mindestens 3 Kopfbällen oder einem Tor nach Standard"},
            "kickbase": (f"{top['n']} kommt nach Ecken und Freistößen am häufigsten zum Kopfball"
                         + (f", {top['tore']} {'davon war ein Tor' if top['tore'] == 1 else 'davon waren Tore'}." if top["tore"] else ".")
                         + " Wer bei Standards vorne steht, sammelt Torchancen, die im Kader oft unterschätzt werden."),
            "quellen": [{"name": "Sportschau-Liveticker", "url": "https://www.sportschau.de/live-und-ergebnisse/fussball/deutschland-bundesliga-frauen/"}], "af": True})
try:
    for w in (lade(P("inside.json")).get("swaps") or []):
        if not w.get("k") or not w.get("neu"): continue
        news.append({"id": "af-swap-" + w["k"] + "-" + "".join(norm((w.get("art") or "") + " " + (w.get("neu") or ""))), "zeit": None, "verein": VN(w["k"]),
            "tags": ["STANDARD"], "headline": f"Standard-Wechsel bei {VN(w['k'])}: {w['neu']} übernimmt {w.get('art') or 'die Standards'}",
            "kurz": f"{w['neu']} übernimmt {w.get('art') or 'Standards'}", "text": [t for t in [w.get("text"), w.get("check")] if t],
            "kickbase": w.get("kb") or "", "quellen": [{"name": "WOSOINSIDER Inside", "url": "https://wosoinsider.de/ticker/#inside"}], "af": True})
except FileNotFoundError: pass
news = [n for n in news if n]
# Von Hand überarbeitete Meldungen (tools/af_text.json: ID -> Felder), z. B. tiefere Analyse mit eigener Grafik
try: OVR = lade(os.path.join(ROOT, "tools", "af_text.json"))
except FileNotFoundError: OVR = {}
for n in news:
    o = OVR.get(n["id"])
    if o: n.update({k: v for k, v in o.items() if not k.startswith("_")})
for n in news: n["text"] = [t for t in n.get("text", []) if t]

# Ereignis-Meldungen nur, solange der Spieltag frisch ist (bis 3 Tage nach dem letzten Spiel)
if letzt and (jetzt - datetime.datetime.fromisoformat(letzt)).days > 3:
    news = [n for n in news if n["tags"][0] not in ("JOKER", "ELFMETER", "xG-CHECK")]
# Warteschlange (Finn 04.11.2026): eine Meldung erscheint erst, wenn tools/af_freigabe.py sie freigibt
# (zwischen 7 und 22 Uhr, wenn im Ticker seit 4 Stunden nichts Neues kam). Feste Artikel (fix) haben ihre eigene Zeit.
alt, alt_n = {}, []
try:
    for n in lade(AUS).get("news", []):
        if n.get("zeit") and datetime.datetime.fromisoformat(n["zeit"]) <= jetzt: alt[n["id"]] = n["zeit"]; alt_n.append(n)
except Exception: pass
# schon erschienene Meldungen bleiben 3 Tage stehen, auch wenn sie nicht mehr neu entstehen
ids = {n["id"] for n in news}
news += [n for n in alt_n if n["id"] not in ids and jetzt - datetime.datetime.fromisoformat(n["zeit"]) <= datetime.timedelta(days=3)]
RANGF = {"JOKER": 0, "ELFMETER": 1, "xG-CHECK": 2, "FORMTIEF": 3, "FORMHOCH": 4, "AUFWIND": 5}
news.sort(key=lambda n: (0 if n.get("fix") else 1, RANGF.get(n["tags"][0], 9)))
for n in news:
    if not n.get("fix"): n["zeit"] = alt.get(n["id"])
# Zurückgehaltene Meldungen (Finn 04.11.2026): halten = true bleibt stehen, af_freigabe.py überspringt sie.
# Der Standard-Check bleibt gesperrt, bis Finn die neue Kopfball-Zählung freigibt (HALTEN in diesem Skript).
HALTEN = set()   # z. B. {"af-standards-"}; Standard-Check freigegeben 04.11.2026 nach neuer Zählung
for n in news:
    if any(n["id"].startswith(h) for h in HALTEN): n["halten"] = True; n["zeit"] = None

# Von Finn ausgeblendete Meldungen (tools/af_ausblenden.json: Liste von IDs oder ID-Anfängen)
try: AUSBL = lade(os.path.join(ROOT, "tools", "af_ausblenden.json"))
except FileNotFoundError: AUSBL = []
news = [n for n in news if not any(n["id"].startswith(x) for x in AUSBL)]

# ---------------------------------------------------------------- schreiben
out = {"stand": JETZT_B().strftime("%Y-%m-%dT%H:%M"), "saison": SAISON, "md": max((s["md"] for s in spiele.values()), default=0),
       "hinweis": "Noten und Teamwerte: API-Football. Minuten, Startelf, Tore, Vorlagen: Sportschau und eigene Auswertung.",
       "sp": profil, "spiele": spiele, "form": {"tief": tief, "hoch": hoch, "stabil": stabil, "trifft": trifft[:6], "leer": leer[:6], "lauf": lauf[:6]}, "team": teamform, "stdt": stdt, "news": news, "gelb_pruefen": gelb_pruefen, "sperren_dfb": SPERREN, "xg": xgcheck[:8], "xgmd": xgmds,
       "ecken": ecken, "freist": freist, "schuesse": schuesse, "elf": elfer, "best": best, "vorschau": vorschau, "ungeklaert": sorted(ungeklaert)}
os.makedirs(os.path.dirname(os.path.abspath(AUS)), exist_ok=True)
json.dump(out, open(AUS, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"{AUS}: {len(profil)} Profile, {len(spiele)} Spiele, zugeordnet {len(ID)}, ungeklärt {len(ungeklaert)}, Vorschau {len(vorschau)}")
