#!/usr/bin/env python3
"""Moment-Analysen für Einzelspielerinnen (Finn 26.11.2026).

Analyse-Artikel im Stil LIGAINSIDER "Wie weit ist Gadou schon?", wenn es einen Anlass gibt:
Nominierung, Nachnominierung, erste Berufung, Rückkehr ins Nationalteam, starker Spieltag.

Regeln (Finn 26.11.2026, Projektdoc claude/wosoinsider-moment-analyse.md):
- Je Artikel genau zwei Grafiken, die für die Analyse Sinn ergeben. Eine zeigt immer, wo sie im
  Vergleich zu ihrer Position steht. Bei Verteidigerinnen klassische Abwehrwerte, nicht Tore.
- Position prüfen: nur Spiele auf der Vergleichsposition zählen (API-Football games.position je Spiel).
- Immer positiv. Ausnahme: höchstens einmal in 30 Tagen ein kritischer Blick auf eine Stammspielerin, die extrem abfällt:
  Mainz/Nürnberg ab 4 Werten bis Perzentil 15, alle anderen Vereine erst ab 5 Werten bis Perzentil 10 (Finn 26.11. 21:02).
- Headline klein, höchstens zweizeilig (Ticker setzt bei grafik.typ "analyse" 24 px).
- Grund für HEUTE: Anlass aus tools/moment_anlaesse.json (redaktionell, vom Tageslauf eingetragen)
  oder Datenanlass (Note ab 7,8 am letzten Spieltag plus mindestens drei Stärken ab Perzentil 85).

Grafiken (news.json, grafik.typ "analyse", abschnitte[].g):
- perzentil: Perzentil-Karte nach Gruppen
- streu:     Streudiagramm zweier Werte mit Median-Linien und beschrifteten Spielerinnen
- verlauf:   Minuten je Spieltag (Startelf, Joker, Bank, nicht im Kader), z. B. nach Verletzung
- strahl:    Strahl je Wert mit allen Spielerinnen der Position, Rang

Aufruf: python3 tools/moment_analyse.py --repo . --roh <spiele_details.json> [--trocken] [--nur PID] [--auto]
"""
import json, os, sys, re, argparse, datetime, statistics, unicodedata, collections
from zoneinfo import ZoneInfo

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=".")
ap.add_argument("--roh", default="/tmp/aft/apifootball/saison2026/spiele_details.json")
ap.add_argument("--trocken", action="store_true", help="nichts schreiben, Artikel ausgeben")
ap.add_argument("--nur", default=None, help="nur diese Spielerin (pid), Anlass muss in moment_anlaesse.json stehen oder --auto")
ap.add_argument("--auto", action="store_true", help="Datenanlass suchen (wöchentlich)")
ap.add_argument("--jetzt", default=None)
A = ap.parse_args()
R = lambda *p: os.path.join(A.repo, *p)
lade = lambda p, d=None: json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d

JETZT = datetime.datetime.fromisoformat(A.jetzt) if A.jetzt else datetime.datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None, second=0, microsecond=0)
SPN = lade(R("spielerinnen.json"))
SP = SPN["spielerinnen"]; BYID = {p["id"]: p for p in SP}
VN = lambda k: SPN["vereine"][k]["name"] if k in SPN.get("vereine", {}) else k
PLAN = lade(R("spielplan.json"), {})
AF = lade(R("apifootball.json"), {})
NEWS = lade(R("news.json"), {"meldungen": []})
ANL_P = R("tools", "moment_anlaesse.json")
ANL = lade(ANL_P, {"anlaesse": []})
ROH = lade(A.roh, [])
if not ROH: print("keine Rohdaten", A.roh); sys.exit(0)

MIN_MIN = 450          # Vergleichsgruppe und eigene Minuten
MIN_MIN_KLEIN = 300    # bei Rückkehr (wenig Spielzeit, mit Hinweis)
PRO_TAG = 1            # höchstens eine Moment-Analyse pro Tag
AUTO_PRO_WOCHE = 2     # Datenanlässe pro Woche
KRITISCH_VEREINE = {"FCN", "M05"}   # dort reicht "deutlich": mindestens 4 Werte bis Perzentil 15
# Finn 26.11. 21:02: bei allen anderen Vereinen auch, wenn es extrem schlecht ist: mindestens 5 Werte bis Perzentil 10
KRITISCH_EXTREM = (5, 10)
KRITISCH_ABSTAND = datetime.timedelta(days=30)
SPERRE_TAGE = 45       # dieselbe Spielerin frühestens nach 45 Tagen wieder (außer neuer redaktioneller Anlass)

def norm(s):
    if "Ã" in s:
        try: s = s.encode("latin1").decode("utf8")
        except Exception: pass
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", " ").replace("-", " ").strip()
def schl(n):
    t = norm(n).split()
    return (t[-1], t[0][0]) if t else ("", "")

# ---------------------------------------------------------------- Positionsgruppen
def gruppe(label):
    l = label or ""
    if l.startswith("Innenverteid"): return "IV"
    if l in ("Rechtsverteidigerin", "Linksverteidigerin") or l.startswith("Schiene"): return "AV"
    if l.startswith("Sechserin"): return "DM"
    if l.startswith("Flügel"): return "FL"
    if l.startswith("Mittelstürm") or l.startswith("Sturm"): return "ST"
    if l == "Tor": return "TW"
    return "ZM"
GNAME = {"IV": ("Innenverteidigerin", "Innenverteidigerinnen"), "AV": ("Außenverteidigerin", "Außenverteidigerinnen"),
         "DM": ("Sechserin", "Sechserinnen"), "ZM": ("zentrale Mittelfeldspielerin", "zentralen Mittelfeldspielerinnen"),
         "FL": ("Flügelspielerin", "Flügelspielerinnen"), "ST": ("Stürmerin", "Stürmerinnen"), "TW": ("Torhüterin", "Torhüterinnen")}
# API-Football games.position je Spiel, die zur Gruppe passt (None = unbekannt, zählt mit)
APIPOS = {"IV": {"D"}, "AV": {"D"}, "DM": {"M"}, "ZM": {"M"}, "FL": {"M", "F"}, "ST": {"F"}, "TW": {"G"}}

# Kennzahlen: key -> (Label, Gruppe in der Karte, höher besser, Format)
SAIS = (lambda x: f"{x}/{(x + 1) % 100:02d}" if isinstance(x, int) else str(x or "2026/27"))(AF.get("saison"))
def p90(a, k): return a[k] * 90 / a["min"] if a["min"] else 0
def quote(a, z, n): return 100 * a[z] / a[n] if a[n] else 0
KZ = {
    "pass": ("Pässe", "SPIELAUFBAU", 1, lambda a: p90(a, "pass")),
    "pass_ok": ("Angekommene Pässe", "SPIELAUFBAU", 1, lambda a: p90(a, "pass_ok")),
    "pq": ("Passquote %", "SPIELAUFBAU", 1, lambda a: quote(a, "pass_ok", "pass")),
    "kp": ("Schlüsselpässe", "SPIELAUFBAU", 1, lambda a: p90(a, "kp")),
    "bg": ("Ballgewinne", "ABWEHR", 1, lambda a: p90(a, "tkl") + p90(a, "int")),
    "tkl": ("Tacklings", "ABWEHR", 1, lambda a: p90(a, "tkl")),
    "int": ("Interceptions", "ABWEHR", 1, lambda a: p90(a, "int")),
    "zkw": ("Zweikämpfe gewonnen", "ABWEHR", 1, lambda a: p90(a, "duel_w")),
    "zq": ("Zweikampfquote %", "ABWEHR", 1, lambda a: quote(a, "duel_w", "duel")),
    "shot": ("Torschüsse", "OFFENSIVE", 1, lambda a: p90(a, "shot")),
    "tb": ("Torbeteiligungen", "OFFENSIVE", 1, lambda a: (a["tore"] + a["vorl"]) * 90 / a["min_o"] if a["min_o"] else 0),
    "drib": ("Dribblings erfolgreich", "OFFENSIVE", 1, lambda a: p90(a, "drib")),
    "foul": ("Fouls", "DISZIPLIN", 0, lambda a: p90(a, "foul")),
    "gelb": ("Gelbe Karten", "DISZIPLIN", 0, lambda a: p90(a, "gelb")),
    "note": ("Note Ø", "GESAMT", 1, lambda a: a["rs"] / a["rn"] if a["rn"] else 0),
}
KARTE = {
    "IV": [("SPIELAUFBAU", ["pass", "pass_ok", "pq", "kp"]), ("ABWEHR", ["bg", "tkl", "int", "zkw", "zq"]), ("DISZIPLIN", ["foul", "gelb"]), ("SONSTIGES", ["shot", "note"])],
    "AV": [("OFFENSIVE", ["tb", "kp", "shot"]), ("SPIELAUFBAU", ["pass", "pq"]), ("ABWEHR", ["bg", "zkw", "zq"]), ("SONSTIGES", ["foul", "note"])],
    "DM": [("SPIELAUFBAU", ["pass", "pq", "kp"]), ("ABWEHR", ["bg", "tkl", "int", "zq"]), ("OFFENSIVE", ["tb", "shot"]), ("SONSTIGES", ["foul", "note"])],
    "ZM": [("OFFENSIVE", ["tb", "kp", "shot", "drib"]), ("SPIELAUFBAU", ["pass", "pq"]), ("ABWEHR", ["bg", "zq"]), ("SONSTIGES", ["note"])],
    "FL": [("OFFENSIVE", ["tb", "kp", "shot", "drib"]), ("SPIELAUFBAU", ["pq"]), ("ABWEHR", ["bg", "zq"]), ("SONSTIGES", ["note"])],
    "ST": [("OFFENSIVE", ["tb", "shot", "kp", "drib"]), ("SPIELAUFBAU", ["pq"]), ("ABWEHR", ["bg", "zq"]), ("SONSTIGES", ["note"])],
}
# Streudiagramm je Gruppe: (x, y, Titel, Ecke oben rechts)
STREU = {
    "IV": ("bg", "zq", "STÄRKEN IN DER ABWEHR", "VIEL UND SICHER", "Klassisch verteidigen: Wo steht sie?"),
    "AV": ("bg", "kp", "HINTEN UND VORNE", "BEIDES STARK", "Hinten und vorne: Wo steht sie?"),
    "DM": ("bg", "pass", "ABRÄUMEN UND VERTEILEN", "BEIDES STARK", "Abräumen und verteilen: Wo steht sie?"),
    "ZM": ("kp", "shot", "VORBEREITEN UND ABSCHLIESSEN", "BEIDES STARK", "Vorbereiten und abschließen: Wo steht sie?"),
    "FL": ("kp", "shot", "VORBEREITEN UND ABSCHLIESSEN", "BEIDES STARK", "Vorbereiten und abschließen: Wo steht sie?"),
    "ST": ("shot", "tb", "GEFAHR VOR DEM TOR", "BEIDES STARK", "Gefahr vor dem Tor: Wo steht sie?"),
}
STRAHL = {
    "IV": ["note", "zq", "bg", "kp", "pq", "foul"], "AV": ["note", "tb", "kp", "zq", "pq", "bg"],
    "DM": ["note", "pass", "pq", "bg", "zq", "kp"], "ZM": ["note", "tb", "kp", "shot", "pq", "bg"],
    "FL": ["note", "tb", "kp", "shot", "drib", "bg"], "ST": ["note", "tb", "shot", "kp", "drib", "zq"],
}

# ---------------------------------------------------------------- Rohdaten je Spielerin (nur passende Position)
keys = collections.defaultdict(list)
for p in SP: keys[schl(p["n"])].append(p)
def finde(name, team):
    c = keys.get(schl(name), [])
    if len(c) == 1: return c[0]["id"]
    t = norm(team)
    for p in c:
        if norm(VN(p["k"])).split()[-1] in t: return p["id"]
    return None
def iv(x):
    try: return int(x or 0)
    except Exception: return 0
AG = collections.defaultdict(collections.Counter)   # nur Spiele auf der Vergleichsposition
POSSP = collections.defaultdict(list)               # (md, api-pos, minuten) je Spielerin
for f in ROH:
    rd = f.get("league", {}).get("round", "")
    md = iv(re.sub(r"\D", "", rd.split("-")[-1]) or 0)
    for t in f.get("players", []):
        for pl in t.get("players", []):
            pid = finde(pl["player"]["name"], t["team"]["name"])
            if not pid: continue
            st = pl["statistics"][0]; m = st["games"]["minutes"] or 0
            if m <= 0: continue
            pos = st["games"]["position"]; POSSP[pid].append((md, pos, m))
            s = BYID[pid]; g = gruppe(s["slots"][0][2]) if s.get("slots") else None
            if not g or (pos is not None and pos not in APIPOS[g]): continue
            a = AG[pid]; a["min"] += m; a["sp"] += 1
            a["pass"] += iv(st["passes"]["total"]); a["pass_ok"] += iv(st["passes"]["accuracy"]); a["kp"] += iv(st["passes"]["key"])
            a["tkl"] += iv(st["tackles"]["total"]); a["int"] += iv(st["tackles"]["interceptions"])
            a["duel"] += iv(st["duels"]["total"]); a["duel_w"] += iv(st["duels"]["won"]); a["drib"] += iv(st["dribbles"]["success"])
            a["foul"] += iv(st["fouls"]["committed"]); a["gelb"] += iv(st["cards"]["yellow"]); a["shot"] += iv(st["shots"]["total"])
            r = st["games"]["rating"]
            if r and m >= 46: a["rs"] += float(r); a["rn"] += 1
# Tore und Vorlagen aus unseren Spielberichten (alle Spiele), Minuten dazu
for pid, a in AG.items():
    sp = BYID[pid]["spiele"]
    a["tore"] = sum(len(g.get("tore", [])) for g in sp); a["vorl"] = sum(iv(g.get("vorl")) for g in sp); a["min_o"] = sum(iv(g.get("min")) for g in sp)

def s_k(pid): return BYID[pid]["k"]
def grp(pid): s = BYID[pid]; return gruppe(s["slots"][0][2]) if s.get("slots") else None
def vergleich(g, mn): return [pid for pid, a in AG.items() if grp(pid) == g and a["min"] >= mn]
def werte(pids, k): return {p: KZ[k][3](AG[p]) for p in pids}
def perz(pid, pids, k):
    w = werte(pids, k); v = w[pid]; hb = KZ[k][2]; vs = [x for q, x in w.items() if q != pid]
    unter = sum(1 for x in vs if (x < v if hb else x > v)); gleich = sum(1 for x in vs if x == v)
    rang = 1 + sum(1 for x in vs if (x > v if hb else x < v))
    return round(100 * (unter + 0.5 * gleich) / max(len(vs), 1)), rang, v
def nach(n): return n.split()[-1]
def dz(x, n=1): return f"{x:.{n}f}".replace(".", ",")
def fw(k, v):
    return f"{v:.0f} %" if k in ("pq", "zq") else dz(v, 1) if k in ("pass", "pass_ok", "note") else dz(v, 2)

# ---------------------------------------------------------------- Grafiken (Daten für den Ticker)
def g_perzentil(pid, pids):
    g = grp(pid); blocks = []
    for t, ks in KARTE[g]:
        rows = []
        for k in ks:
            p, rg, v = perz(pid, pids, k)
            rows.append({"k": k, "l": KZ[k][0], "w": fw(k, v), "p": p, "hb": KZ[k][2]})
        blocks.append({"t": t, "z": rows})
    a = AG[pid]
    return {"typ": "perzentil", "n": BYID[pid]["n"], "k": BYID[pid]["k"], "pos": g, "min": a["min"], "vgl": len(pids),
            "hinweis": f"nur Spiele als {GNAME[g][0]}" if any(pos is not None and pos not in APIPOS[g] for _, pos, _ in POSSP[pid]) else "", "bl": blocks}
def g_streu(pid, pids):
    g = grp(pid); kx, ky, titel, ecke = STREU[g][:4]
    wx, wy = werte(pids, kx), werte(pids, ky)
    # beschriften: sie selbst plus die zwei Besten je Achse (ohne Doppelte), höchstens 5
    beste = sorted(pids, key=lambda p: -(wx[p] / (max(wx.values()) or 1) + wy[p] / (max(wy.values()) or 1)))
    sx_ = (max(wx.values()) - min(wx.values())) or 1; sy_ = (max(wy.values()) - min(wy.values())) or 1
    lab = [pid]
    for p in beste:   # höchstens 3 weitere, die sich im Diagramm nicht überdecken
        if p != pid and len(lab) < 4 and all(abs(wx[p] - wx[q]) / sx_ > .3 or abs(wy[p] - wy[q]) / sy_ > .12 for q in lab): lab.append(p)
    pts = [{"n": BYID[p]["n"], "k": BYID[p]["k"], "x": round(wx[p], 2), "y": round(wy[p], 1 if ky in ("pq", "zq", "pass") else 2), "l": 1 if p in lab else 0, "ich": 1 if p == pid else 0} for p in pids]
    return {"typ": "streu", "titel": titel, "ecke": ecke, "x": KZ[kx][0].replace(" %", "") + (" in %" if kx in ("pq", "zq") else " pro 90 Min."), "y": KZ[ky][0].replace(" %", "") + (" in %" if ky in ("pq", "zq") else " pro 90 Min."),
            "chips": ["FBL " + SAIS, g if g != "ZM" else "ZM", "pro 90 Min.", f"{len(pids)} Spielerinnen"],
            "lab": [BYID[p]["n"] for p in lab], "mx": round(statistics.median(wx.values()), 2), "my": round(statistics.median(wy.values()), 2), "p": pts}
def g_verlauf(pid, ausfall=None):
    sp = BYID[pid]["spiele"]
    return {"typ": "verlauf", "titel": "DER WEG ZURÜCK", "s": [{"md": g["md"], "gk": g.get("gk"), "min": iv(g.get("min")), "art": g.get("art")} for g in sp], "ausfall": ausfall}
def g_strahl(pid, pids):
    g = grp(pid); zeilen = []
    for k in STRAHL[g]:
        w = werte(pids, k); p, rg, v = perz(pid, pids, k)
        zeilen.append({"k": k, "l": KZ[k][0], "w": fw(k, v), "rang": rg, "von": len(pids), "alle": [round(x, 2) for q, x in w.items() if q != pid], "ich": round(v, 2), "hb": KZ[k][2]})
    return {"typ": "strahl", "titel": f"WO STEHT SIE UNTER DEN {GNAME[g][1].upper()}?", "n": BYID[pid]["n"], "k": BYID[pid]["k"], "z": zeilen,
            "chips": ["FBL " + SAIS, f"ab {MIN_MIN_KLEIN if AG[pid]['min'] < MIN_MIN else MIN_MIN} Min.", f"{len(pids)} Spielerinnen", "pro 90 Min."],
            "hinweis": f"Wenig Spielzeit: erst {AG[pid]['min']} Minuten, die Werte schwanken noch stärker." if AG[pid]["min"] < MIN_MIN else ""}

# ---------------------------------------------------------------- Text
def startelf(pid):
    sp = BYID[pid]["spiele"]; return sum(1 for g in sp if g.get("art") == "S"), len(sp)
def naechstes(k):
    best = None
    for t in PLAN.get("spieltage", []):
        for p in t.get("partien", []):
            if k in (p.get("heim_k"), p.get("gast_k")) and p.get("status") != "beendet" and p.get("anstoss"):
                d = datetime.datetime.fromisoformat(p["anstoss"])
                if d > JETZT and (not best or d < best[0]): best = (d, p)
    if not best: return ""
    d, p = best; heim = p["heim_k"] == k; geg = p["gast"] if heim else p["heim"]
    return f"Das nächste Ligaspiel ist am {d:%d.%m.} {'zu Hause gegen ' + ('den ' if geg.startswith('1. FC') else '') + geg if heim else 'in ' + {'FC Bayern':'München','1. FC Köln':'Köln','Hamburger SV':'Hamburg','TSG Hoffenheim':'Hoffenheim','Werder Bremen':'Bremen','VfL Wolfsburg':'Wolfsburg','RB Leipzig':'Leipzig','Eintracht Frankfurt':'Frankfurt','Bayer Leverkusen':'Leverkusen','SC Freiburg':'Freiburg','VfB Stuttgart':'Stuttgart','Union Berlin':'Berlin','1. FC Nürnberg':'Nürnberg','Mainz 05':'Mainz'}.get(geg, geg)}."
PROGW = {"sicher": "gesetzt", "erwartet": "erwartet in der Startelf", "unsicher": "unsicher", "unwahrscheinlich": "eher nicht in der Startelf", "ausgeschlossen": "fällt aus"}
def standards(pid):
    s = BYID[pid].get("standards") or {}; tr = [x for x, k in (("Ecken", "ecken"), ("Freistöße", "freistoesse")) if s.get(k)]
    t = (["Elfmeterschützin"] if s.get("elfmeter") else [])
    if tr: t.append(("" if t else "") + "tritt " + liste(tr))
    return t
STARK = {"pass": "viel Ballbesitz im Aufbau", "pass_ok": "vielen angekommenen Pässen", "pq": "sauberem Passspiel", "kp": "Ideen im Spielaufbau", "bg": "vielen Ballgewinnen",
         "tkl": "starken Tacklings", "int": "abgefangenen Bällen", "zkw": "vielen gewonnenen Zweikämpfen", "zq": "sicheren Zweikämpfen", "shot": "vielen Abschlüssen",
         "tb": "vielen Torbeteiligungen", "drib": "starken Dribblings", "foul": "fairem Zweikampfverhalten", "gelb": "wenigen Karten", "note": "konstant guten Noten"}
SATZ = {"foul": "wenige Fouls", "gelb": "wenige Gelbe Karten", "note": "Note", "pq": "Passquote", "zq": "Zweikampfquote"}
LUFT = {"pass": "beim Passvolumen", "pass_ok": "bei den angekommenen Pässen", "pq": "bei der Passquote", "kp": "bei den Schlüsselpässen", "bg": "bei den Ballgewinnen",
        "tkl": "bei den Tacklings", "int": "bei den abgefangenen Bällen", "zkw": "bei der Zahl gewonnener Zweikämpfe", "zq": "bei der Zweikampfquote", "shot": "bei den Abschlüssen",
        "tb": "bei den Torbeteiligungen", "drib": "bei den Dribblings", "foul": "bei den Fouls", "gelb": "bei den Karten", "note": "bei der Note"}
def ordne(ks): return sorted(ks, key=lambda k: (KZ[k][1] in ("DISZIPLIN", "GESAMT"), 0))
def liste(t): return ", ".join(t[:-1]) + (" und " + t[-1] if len(t) > 1 else t[0])
def bei_satz(pid, pids, ks):
    t = []
    for k in ks:
        p, rg, v = perz(pid, pids, k); t.append(f"{LUFT[k]} ({fw(k, v)}{' pro 90' if k not in ('pq', 'zq', 'note') else ''}, Rang {rg} von {len(pids)})")
    return liste(t)
def stark_satz(pid, pids, ks):
    teile = []
    for k in ks:
        p, rg, v = perz(pid, pids, k)
        teile.append(f"{SATZ.get(k, KZ[k][0])} ({fw(k, v)} pro 90, Perzentil {p})" if k not in ("pq", "zq", "note") else f"{SATZ.get(k, KZ[k][0])} ({fw(k, v)}, Perzentil {p})")
    return liste(teile)

def artikel(pid, anl, modus="positiv"):
    s = BYID[pid]; g = grp(pid); a = AG.get(pid)
    if not g or g == "TW" or not a: return None, "keine Feldspielerin oder keine Daten"
    klein = a["min"] < MIN_MIN or (anl or {}).get("art") == "rueckkehr"
    if a["min"] < MIN_MIN_KLEIN: return None, f"zu wenig Minuten ({a['min']})"
    pids = vergleich(g, MIN_MIN_KLEIN if klein else MIN_MIN)
    if pid not in pids: pids.append(pid)
    if len(pids) < 8: return None, f"Vergleichsgruppe zu klein ({len(pids)})"
    alle = [k for _, ks in KARTE[g] for k in ks] if not klein else STRAHL[g]
    pz = {k: perz(pid, pids, k) for k in alle}
    top = ordne(sorted([k for k in alle if pz[k][0] >= 75], key=lambda k: -pz[k][0]))
    tief = sorted([k for k in alle if pz[k][0] <= 30], key=lambda k: pz[k][0])
    if modus == "positiv" and len(top) < (2 if anl else 3): return None, f"keine klare positive Datenstory (Stärken: {len(top)})"
    if modus == "kritisch":
        if s_k(pid) in KRITISCH_VEREINE:
            if len([k for k in alle if pz[k][0] <= 15]) < 4: return None, "fällt nicht deutlich ab"
        elif len([k for k in alle if pz[k][0] <= KRITISCH_EXTREM[1]]) < KRITISCH_EXTREM[0]: return None, "fällt nicht extrem ab"
    n = s["n"]; nn = nach(n); st, ges = startelf(pid); gn = GNAME[g][0]
    # Positions-Check
    fremd = [(md, pos) for md, pos, m in POSSP[pid] if pos is not None and pos not in APIPOS[g]]
    pos_satz = ""
    if fremd:
        spm = {g_["md"]: g_ for g_ in s["spiele"]}
        PW = {"D": "in der Abwehr", "M": "im Mittelfeld", "F": "im Sturm", "G": "im Tor"}
        wo = PW.get(fremd[0][1], "auf einer anderen Position")
        geg = [spm[md]["gegner"] for md, _ in fremd if md in spm]
        tf = sum(len(spm[md].get("tore", [])) for md, _ in fremd if md in spm)
        pos_satz = (f"Wichtig für die Einordnung: {gn} war sie in {a['sp']} von {len(POSSP[pid])} Spielen. " + (f"Gegen {liste(geg)} spielte sie {wo}" if geg else f"In den übrigen spielte sie {wo}")
                    + (f", dort fielen {tf} ihrer Tore. " if tf > 1 else ", dort fiel eines ihrer Tore. " if tf == 1 else ". ")
                    + f"Für den Vergleich zählen deshalb nur ihre {a['min']} Minuten als {gn}.")
    intro = (anl or {}).get("text") or ""
    if modus == "kritisch" and not intro: intro = f"{n} ist bei {VN(s['k'])} gesetzt. Zeit für einen ehrlichen Blick: Wie schlägt sie sich im Vergleich mit den anderen {GNAME[g][1]}?"
    tore, vorl = a["tore"], a["vorl"]
    tv = [x for x in [f"{tore} {'Tor' if tore == 1 else 'Toren'}" if tore else "", f"{vorl} {'Vorlage' if vorl == 1 else 'Vorlagen'}" if vorl else ""] if x]
    fakt = f"{nn if intro else n} stand in {st} von {ges} Ligaspielen in der Startelf" + (f", mit {liste(tv)}" if tv else "") + "."
    vgl = f"Verglichen wird sie mit {len(pids) - 1} {GNAME[g][1]} mit mindestens {MIN_MIN_KLEIN if klein else MIN_MIN} Minuten. Ein Perzentil von 90 heißt: 90 Prozent der Vergleichsspielerinnen liegen darunter."
    text = [t for t in [intro + (" " if intro else "") + fakt, pos_satz, vgl] if t]
    ab = []
    if klein:
        ausfall = (anl or {}).get("ausfall")
        ab.append({"h": "Wie viel spielt sie schon?", "g": g_verlauf(pid, ausfall), "text": [(anl or {}).get("verlauf_text") or verlauf_satz(pid)]})
        best = [k for k in STRAHL[g] if pz[k][1] == 1]
        h = "Wenn sie spielt, gehört sie zu den Besten ihrer Position" if best or len(top) >= 2 else f"So steht sie unter den {GNAME[g][1]}"
        t2 = f"Unter {len(pids)} {GNAME[g][1]} ist sie stark bei {stark_satz(pid, pids, top[:3])}." if top else ""
        if tief: t2 += f" Luft nach oben hat sie {LUFT[tief[0]]}."
        t2 += f" Die Werte stehen auf nur {a['min']} Minuten." if a["min"] < MIN_MIN else ""
        ab.append({"h": h, "g": g_strahl(pid, pids), "text": [t2.strip()]})
    else:
        t1 = f"Ihre Stärken: {stark_satz(pid, pids, top[:3])}." if modus == "positiv" else f"Die Werte im Vergleich: {stark_satz(pid, pids, (top or alle)[:2])}."
        if tief and modus == "positiv": t1 += f" Luft nach oben hat sie {LUFT[tief[0]]}."
        if modus == "kritisch": t1 = f"Deutlich unter dem Schnitt liegt sie {bei_satz(pid, pids, tief[:3])}." + (f" Stark ist sie dagegen {bei_satz(pid, pids, top[:2])}." if top else "")
        ab.append({"h": titel_karte(top, g) if modus == "positiv" else "Die Werte im Vergleich", "g": g_perzentil(pid, pids), "text": [t1]})
        sx = g_streu(pid, pids); kx, ky = STREU[g][0], STREU[g][1]
        vx, vy = KZ[kx][3](a), KZ[ky][3](a)
        lage = ("über" if vx >= sx["mx"] else "unter") + " dem Median " + LUFT[kx] + ", " + ("über" if vy >= sx["my"] else "unter") + " dem Median " + LUFT[ky]
        andere = [n_ for n_ in sx["lab"][1:] if (lambda q: q["x"] >= sx["mx"] and q["y"] >= sx["my"])(next(q for q in sx["p"] if q["n"] == n_))][:2]
        if len(andere) == 2: vv = f"{andere[0]} und {andere[1]} (beide {VN(BYID_N[andere[0]])})" if BYID_N[andere[0]] == BYID_N[andere[1]] else f"{andere[0]} ({VN(BYID_N[andere[0]])}) und {andere[1]} ({VN(BYID_N[andere[1]])})"
        t2 = f"Im Streudiagramm liegt {nn} {lage}." + (f" Oben rechts stehen {vv}." if len(andere) == 2 else "")
        ab.append({"h": STREU[g][4], "g": sx, "text": [t2]})
    # Kickbase
    pr = s.get("prognose") or {}
    sd = standards(pid)
    kb = [f"{st} von {ges} Ligaspielen in der Startelf." + ((" Sie ist " + " und ".join(sd) + ".").replace("ist tritt", "tritt") if sd else "")]
    if pr.get("st"): kb.append(f"Für den {pr.get('md')}. Spieltag: {PROGW.get(pr['st'], pr['st'])}.")
    if (anl or {}).get("kickbase"): kb.append(anl["kickbase"])
    nx = naechstes(s["k"]);
    if nx: kb.append(nx)
    # Fazit
    if modus == "kritisch":
        fazit = f"{nn} spielt regelmäßig, die Bundesliga ist für sie aber noch ein großer Schritt. Für Kickbase heißt das: Einsätze ja, viele Punkte eher nicht."
    else:
        fazit = f"{nn} ist eine {gn} mit {liste([STARK[k] for k in top[:3]])}." + (f" Zulegen kann sie noch {LUFT[tief[0]]}." if tief else "")
    head = (anl or {}).get("headline") or headline(pid, top, g, anl, modus)
    q = [{"name": "API-Football (Werte pro 90)", "url": "https://www.api-football.com"}, {"name": "Sportschau (Minuten, Tore)", "url": "https://www.sportschau.de/live-und-ergebnisse/fussball/deutschland-bundesliga-frauen/"}] + ((anl or {}).get("quellen") or [])
    return {"id": f"moment-{pid}-{JETZT:%Y%m%d}", "pid": pid, "zeit": JETZT.strftime("%Y-%m-%dT%H:%M"), "spielerin": n, "verein": VN(s["k"]), "nr": s.get("nr"), "pos": s.get("pos"),
            "tags": ["INSIDER"] + ((anl or {}).get("tags") or []), "headline": head, "kurz": (anl or {}).get("kurz") or head, "text": text,
            "grafik": {"typ": "analyse", "modus": modus, "abschnitte": ab, "fazit": [fazit],
                       "daten": f"Datenbasis: API-Football (Werte pro 90, nur Spiele als {gn}), Tore und Minuten aus Spielberichten. Stand {AF.get('md') or ''}. Spieltag."},
            "kickbase": " ".join(kb), "quellen": q, "moment": {"art": (anl or {}).get("art") or "daten", "modus": modus}}, None
BYID_N = {p["n"]: p["k"] for p in SP}
def titel_karte(top, g):
    t = [KZ[k][1] for k in top if KZ[k][1] not in ("DISZIPLIN", "GESAMT")]
    return {"OFFENSIVE": "Gefahr nach vorn", "ABWEHR": "Stark gegen den Ball", "SPIELAUFBAU": "Im Aufbau mit Ideen"}.get(t[0] if t else "", "Sauber und zuverlässig")
def headline(pid, top, g, anl, modus):
    nn = nach(BYID[pid]["n"])
    if modus == "kritisch": return f"{nn}: Wie groß ist der Schritt in die Bundesliga?"
    if anl and anl.get("art") in ("nominierung", "nachnominierung", "erstmals"): return f"{nn} beim DFB: Was sie so stark macht"
    if anl and anl.get("art") == "rueckkehr": return f"{nn} ist zurück: Wie weit ist sie?"
    return f"{nn} im Daten-Check: Was sie so stark macht"
def verlauf_satz(pid):
    sp = BYID[pid]["spiele"][-4:]
    w = {"S": "Startelf", "E": "eingewechselt", "B": "Bank", "X": "nicht im Kader"}
    return "Die letzten Spieltage: " + ", ".join(f"{g['md']}. {w.get(g.get('art'), '')}" + (f" ({iv(g.get('min'))} Min.)" if iv(g.get("min")) else "") for g in sp) + "."

# ---------------------------------------------------------------- Auswahl: was erscheint heute?
meld = NEWS.get("meldungen", [])
momente = [m for m in meld if str(m.get("id", "")).startswith("moment-")]
def zeit(m):
    try: return datetime.datetime.fromisoformat(m["zeit"][:16])
    except Exception: return datetime.datetime.min
heute = [m for m in momente if zeit(m).date() == JETZT.date()]
if len(heute) >= PRO_TAG and not A.nur: print("heute schon eine Moment-Analyse"); sys.exit(0)
gesperrt = {m["pid"] for m in momente if JETZT - zeit(m) < datetime.timedelta(days=SPERRE_TAGE)}

kandidaten = []
for an in ANL.get("anlaesse", []):
    if an.get("erledigt") or (A.nur and an.get("pid") != A.nur): continue
    if an.get("bis") and JETZT.date().isoformat() > an["bis"]: continue
    kandidaten.append((an, an.get("modus", "positiv")))
if A.auto and not A.nur:
    woche = [m for m in momente if m.get("moment", {}).get("art") == "daten" and JETZT - zeit(m) < datetime.timedelta(days=7)]
    if len(woche) < AUTO_PRO_WOCHE:
        md = AF.get("md"); spn = AF.get("sp", {})
        for pid, x in spn.items():
            no = [n for n in x.get("no", []) if n[0] == md]
            if no and no[0][1] >= 7.8 and pid not in gesperrt and pid in AG and grp(pid) not in (None, "TW"):
                kandidaten.append(({"pid": pid, "art": "daten", "text": f"Am {md}. Spieltag holte {BYID[pid]['n']} die Note {dz(no[0][1])}. Zeit für den Blick auf ihre ganze Saison."}, "positiv"))
        # kritisch: höchstens alle 30 Tage, nur Mainz/Nürnberg, nur Stammspielerinnen
        letzt_k = max((zeit(m) for m in momente if m.get("moment", {}).get("modus") == "kritisch"), default=datetime.datetime.min)
        if JETZT - letzt_k > KRITISCH_ABSTAND:
            for pid in AG:
                s = BYID[pid]; st, ges = startelf(pid)
                if pid not in gesperrt and ges and st / ges >= .6 and grp(pid) not in (None, "TW"):
                    kandidaten.append(({"pid": pid, "art": "daten", "text": ""}, "kritisch"))

ergebnis = None
for an, modus in kandidaten:
    pid = an["pid"]
    if an.get("art") == "daten" and pid in gesperrt: continue
    art, grund = artikel(pid, an, modus)
    if art: ergebnis = (an, art); break
    print("übersprungen", BYID.get(pid, {}).get("n", pid), modus, grund)
    if an.get("art") != "daten": an["erledigt"] = f"übersprungen {JETZT:%d.%m.}: {grund}"
if not ergebnis:
    print("keine Moment-Analyse heute")
    if not A.trocken: json.dump(ANL, open(ANL_P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(0)
an, art = ergebnis
if A.trocken:
    print(json.dumps(art, ensure_ascii=False, indent=1)); sys.exit(0)
if an.get("art") != "daten": an["erledigt"] = art["id"]
NEWS["meldungen"].insert(0, art)
json.dump(NEWS, open(R("news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(ANL, open(ANL_P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("erschienen:", art["headline"])
