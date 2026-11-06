#!/usr/bin/env python3
"""Regressionstest der Live-Leselogik (Finn, 06.11.2026): Fehler vor dem Anpfiff finden statt währenddessen.

Liest den Sportschau-Liveticker jeder beendeten Partie mit live_ergebnis.lesen() und vergleicht mit drei Referenzen:
- spielplan.json (Endstand, Tore mit Vorlage, Wechsel und Karten an den Aufstellungs-Chips, Platzverweise)
- OpenLigaDB ffb1 (unabhängige Quelle: Endstand, Torschützinnen)
- Plausibilität (Tore je Seite = Ergebnis, Wechsel vollständig, Minuten lesbar, Anpfiff/Abpfiff-Uhrzeiten vorhanden)
Außerdem: jede Ereignisart (data-event_action/kind, Tor-Klassen), die unsere Logik nicht kennt, ist ein Fehler.
Neue Arten sind genau die Fälle, die live zum ersten Mal auftauchen würden (Rot, Elfmeter, Eigentor, Verlängerung ...).

Aufruf: python3 tools/parser_test.py --repo . [--cache DIR] [--nur ID,ID] [--out tracking/parser_test.json]
Exit 1 bei Fehlern. Die Seiten werden in --cache abgelegt, damit Folgetests ohne Netz laufen.
"""
import argparse, gzip, json, os, re, sys, unicodedata, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_ergebnis as L  # noqa: E402
import csv  # noqa: E402

SPIELERINNEN = set()

# Ereignisarten, die live_ergebnis.py verarbeitet oder bewusst ignoriert. Alles andere ist neu und muss geprüft werden.
BEKANNT = {("card", "yellow"), ("card", "yellow-red"), ("card", "red"), ("card", "yellowred"), ("card", "second-yellow"),
           ("goal", "head"), ("goal", "left-foot"), ("goal", "right-foot"), ("goal", "direct-free-kick"), ("goal", "penalty"),
           ("goal", "own-goal"), ("goal", "goal"), ("goal", "other"),
           ("match", "game-start"), ("match", "first-half-end"), ("match", "second-half-start"), ("match", "game-end"),
           ("playing", "substitute-in"), ("playing", "substitute-out"), ("special", "additional-time"), ("special", "missed-penalty")}
TOR_KLASSEN = {"goal", "home", "away", "head", "left-foot", "right-foot", "direct-free-kick", "penalty", "own-goal", "goal-other", "other"}
# Fehler der Quelle selbst (nicht unserer Logik), geprüft und bewusst hingenommen. Live fängt sie der Wächter bzw. API-Football ab.
QUELLFEHLER = {"12306064": "Status"}  # MD1 Hoffenheim-Stuttgart: Sportschau-Seite steht nach Abpfiff dauerhaft auf "1. Halbzeit"
OL_TEAMS = {"FC Bayern München Frauen": "FC Bayern", "VfL Wolfsburg Frauen": "VfL Wolfsburg", "Eintracht Frankfurt Frauen": "Eintracht Frankfurt",
            "Bayer 04 Leverkusen Frauen": "Bayer Leverkusen", "1. FC Köln Frauen": "1. FC Köln", "RB Leipzig Frauen": "RB Leipzig",
            "SV Werder Bremen Frauen": "Werder Bremen", "SC Freiburg Frauen": "SC Freiburg", "1. FC Union Berlin Frauen": "Union Berlin",
            "VfB Stuttgart Frauen": "VfB Stuttgart", "TSG 1899 Hoffenheim Frauen": "TSG Hoffenheim", "Hamburger SV Frauen": "Hamburger SV",
            "1. FC Nürnberg Frauen": "1. FC Nürnberg", "1. FSV Mainz 05 Frauen": "Mainz 05", "SGS Essen Frauen": "SGS Essen",
            "SGS Essen": "SGS Essen", "Carl Zeiss Jena Frauen": "Carl Zeiss Jena"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def nn(s):
    """Nachname normalisiert (für Vergleiche über Quellen hinweg)."""
    s = str(s or "").strip()
    return norm(s.split()[-1]) if s else ""


def mi(m):
    z = re.match(r"(\d+)(?:\+(\d+))?$", str(m or ""))
    return (int(z.group(1)), int(z.group(2) or 0)) if z else None


def holen(url, cache, pid):
    f = os.path.join(cache, f"{pid}.html.gz") if cache else None
    if f and os.path.exists(f):
        return gzip.open(f, "rt", encoding="utf-8").read()
    s = L.F.get(url)
    if s and f:
        os.makedirs(cache, exist_ok=True)
        with gzip.open(f, "wt", encoding="utf-8") as g:
            g.write(s)
    return s


def openliga(saison):
    try:
        req = urllib.request.Request(f"https://api.openligadb.de/getmatchdata/ffb1/{saison}", headers={"User-Agent": "WOSOINSIDER-Test/0.2"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # OpenLigaDB ist nur Zusatzreferenz
        print(f"OpenLigaDB nicht erreichbar: {e}")
        return {}
    out = {}
    for m in d:
        h, g = OL_TEAMS.get(m["team1"]["teamName"]), OL_TEAMS.get(m["team2"]["teamName"])
        if h and g and m.get("matchIsFinished"):
            end = next((r for r in m.get("matchResults", []) if r.get("resultTypeID") == 2), None)
            out[(h, g)] = {"erg": [str(end["pointsTeam1"]), str(end["pointsTeam2"])] if end else None,
                           "tore": [{"n": x.get("goalGetterName") or "", "min": x.get("matchMinute"), "et": x.get("isOwnGoal"),
                                     "elf": x.get("isPenalty")} for x in m.get("goals", [])]}
    return out


def pruefen(p, s, ol):
    """Liste von (schwere, text). schwere: fehler | hinweis."""
    f = []
    F = lambda t: f.append(("fehler", t))
    H = lambda t: f.append(("hinweis", t))
    r = L.lesen_text(s) if hasattr(L, "lesen_text") else None
    if r is None:
        return [("fehler", "lesen() liefert nichts (Status oder Ergebnis nicht gefunden)")]
    q = {k: None for k in ("status", "ergebnis", "minute", "tore", "karten", "wechsel")}
    L.anwenden(q, r)
    if q.get("status") != "beendet":
        (H if QUELLFEHLER.get(p["id"]) == "Status" else F)(f"Status nicht als beendet erkannt: Text '{r['text']}'")
    if r["ergebnis"] != p.get("ergebnis"):
        F(f"Ergebnis {r['ergebnis']} statt {p.get('ergebnis')} (spielplan)")
    o = ol.get((p["heim"], p["gast"]))
    if o and o["erg"] and o["erg"] != r["ergebnis"]:
        F(f"Ergebnis {r['ergebnis']} statt {o['erg']} (OpenLigaDB)")
    # Ereignisarten
    arten = set(re.findall(r'data-event_action="([^"]*)" data-event_kind="([^"]*)"', s))
    for a in sorted(arten - BEKANNT):
        F(f"Unbekannte Ereignisart im Liveticker: {a[0]}/{a[1]}")
    m = re.search(r'<div class="module-events">(.*?)</ul>', s, re.S)
    for kl in re.findall(r'<li class="event ([^"]*)"', m.group(1) if m else ""):
        ks = set(kl.split())
        if ks & {"goal"} or any("goal" in k for k in ks):
            for k in sorted(ks - TOR_KLASSEN):
                F(f"Unbekannte Tor-Klasse: {k} ({kl})")
        elif "red" in ks or "yellow-red" in ks:
            pass  # Platzverweise werden unten gegen die Ticker-Karten geprüft
    # Tore
    tore = r["tore"]
    for seite, i in (("heim", 0), ("gast", 1)):
        n = sum(1 for t in tore if t["seite"] == seite)
        if str(n) != r["ergebnis"][i]:
            F(f"{n} Tore {seite} gelesen, Ergebnis sagt {r['ergebnis'][i]} (Eigentor-Seite prüfen)")
    for t in tore:
        if not t["n"]:
            F(f"Tor ohne Namen: {t}")
        if not mi(t["min"]):
            F(f"Tor-Minute unlesbar: {t}")
    ref = p.get("tore") or []
    a = [(t["seite"], nn(t["n"]), t["min"], nn(t.get("vorlage")), t.get("art")) for t in tore]
    # spielplan kennt keinen Freistoß und führt Eigentore als et (bis Cache v6 teils ohne): Art nur vergleichen, wo beide sie kennen
    a = [x[:4] + ((x[4] if x[4] != "Freistoß" else None),) for x in a]
    # spielplan: Eigentor mit et und seite = Team der Schützin; live: art Eigentor und seite = begünstigtes Team (Ticker zaehlt())
    um = {"heim": "gast", "gast": "heim"}
    b = [((um[t["seite"]] if t.get("et") else t["seite"]), nn(t["n"]), t["min"], nn(t.get("vorlage")),
          "Eigentor" if t.get("et") else (t.get("art") or None)) for t in ref]
    if sorted(a, key=str) != sorted(b, key=str):
        nur_a = [x for x in a if x not in b]
        nur_b = [x for x in b if x not in a]
        F(f"Tore weichen vom spielplan ab: live {nur_a} / spielplan {nur_b}")
    if o and o["tore"]:
        ol_n = sorted(nn(x["n"]) for x in o["tore"] if x["n"])
        li_n = sorted(nn(t["n"]) for t in tore)
        if ol_n and ol_n != li_n and len(ol_n) == len(li_n):
            H(f"Torschützinnen anders geschrieben als OpenLigaDB: {li_n} / {ol_n}")
        elif ol_n and len(ol_n) != len(li_n):
            H(f"OpenLigaDB hat {len(ol_n)} benannte Tore, Liveticker {len(li_n)}")
        for x in o["tore"]:
            if x["et"] and not any(t.get("art") == "Eigentor" for t in tore):
                H("OpenLigaDB meldet ein Eigentor, die Sportschau nicht")
            if x["elf"] and not any(t.get("art") == "Elfmeter" for t in tore):
                H("OpenLigaDB meldet einen Elfmeter, die Sportschau nicht")
    # Wechsel gegen Aufstellungs-Chips
    w = r["wechsel"]
    for x in w:
        if not x["ein"] or not x["aus"]:
            F(f"Wechsel unvollständig: {x}")
        if not mi(x["min"]):
            F(f"Wechsel-Minute unlesbar: {x}")
    for seite in ("heim", "gast"):
        au = p.get(seite + "_aufstellung") or {}
        if au.get("typ") != "offiziell":
            continue
        ch_aus = sorted((nn(c.get("voll") or c["n"]), str(c["aus"])) for c in au.get("startelf", []) + au.get("bank", []) if c.get("aus"))
        ch_ein = sorted(nn(c.get("voll") or c["n"]) for c in au.get("bank", []) if c.get("ein"))
        li_aus = sorted((nn(x["aus"]), str(x["min"]).split("+")[0]) for x in w if x["seite"] == seite and x["aus"])
        li_ein = sorted(nn(x["ein"]) for x in w if x["seite"] == seite and x["ein"])
        if ch_aus and [c[0] for c in ch_aus] != [c[0] for c in li_aus]:
            extra = {c[0] for c in li_aus} - {c[0] for c in ch_aus}
            if {c[0] for c in ch_aus} <= {c[0] for c in li_aus} and extra <= set(li_ein):
                H(f"Wechsel {seite}: Eingewechselte wieder ausgewechselt {sorted(extra)} (spielplan ab Cache v6)")
            else:
                F(f"Wechsel {seite}: ausgewechselt live {li_aus} / Aufstellung {ch_aus}")
        if ch_ein and ch_ein != li_ein:
            F(f"Wechsel {seite}: eingewechselt live {li_ein} / Aufstellung {ch_ein}")
        # Karten gegen Chips
        ch_k = sorted(nn(c.get("voll") or c["n"]) for c in au.get("startelf", []) + au.get("bank", []) if c.get("gelb") or c.get("rot") or c.get("gelbrot"))
        alle_k = sorted(set(nn(k["n"]) for k in r["karten"] if k["seite"] == seite))
        li_k = [k for k in alle_k if not SPIELERINNEN or k in SPIELERINNEN]
        for k in sorted(set(alle_k) - set(li_k)):
            H(f"Karte an Trainerbank/Staff: {k}")
        if ch_k and ch_k != li_k:
            F(f"Karten {seite}: live {li_k} / Aufstellung {ch_k}")
    for k in r["karten"]:
        if not mi(k["min"]):
            F(f"Karten-Minute unlesbar: {k}")
    for kl in re.findall(r'<li class="event (card[^"]*)">(?:(?!</li>).)*?person-surname[^"]*">([^<]*)<', m.group(1) if m else "", re.S):
        if not kl[1].strip():
            H(f"Platzverweis ohne Namen im Ereignis-Modul ({kl[0]}), vermutlich Trainerbank")
        elif not any(nn(k["n"]) == nn(kl[1]) and k["art"] in ("rot", "gelbrot") for k in r["karten"]):
            F(f"Platzverweis {kl[1]} ({kl[0]}) im Ereignis-Modul, aber nicht als Rot/Gelb-Rot gelesen")
    pv = sorted(nn(x.get("n") or x.get("spielerin")) for x in p.get("platzverweise") or [] if (x.get("n") or x.get("spielerin")))
    li_pv = sorted(nn(k["n"]) for k in r["karten"] if k["art"] in ("rot", "gelbrot"))
    if pv != li_pv:
        F(f"Platzverweise live {li_pv} / spielplan {pv}")
    # Uhrzeiten für die mitlaufende Minute und Comeback-Zeiten
    for k in ("a1", "a2", "e"):
        if not (r.get("uhr") or {}).get(k):
            H(f"Uhrzeit {k} fehlt im Liveticker")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--cache", default="")
    ap.add_argument("--nur", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    sp = json.load(open(os.path.join(a.repo, "spielplan.json"), encoding="utf-8"))
    SPIELERINNEN.update(nn(r["name"]) for r in csv.DictReader(open(os.path.join(a.repo, "tools/kader.csv"), encoding="utf-8")))
    nur = set(filter(None, a.nur.split(",")))
    ps = [p for p in L.partien(sp) if p.get("status") == "beendet" and p.get("url") and (not nur or p["id"] in nur)]
    saison = sp.get("saison") or (ps[0]["anstoss"][:4] if ps else "2026")
    ol = openliga(str(saison)[:4])
    erg, nf = {}, 0
    for p in ps:
        s = holen(p["url"], a.cache, p["id"])
        name = f"MD{p.get('md')} {p['heim']} {'-'.join(p.get('ergebnis') or [])} {p['gast']}"
        res = pruefen(p, s, ol) if s else [("fehler", "Seite nicht geladen")]
        erg[p["id"]] = {"spiel": name, "befunde": [{"art": x, "text": t} for x, t in res]}
        fe = [t for x, t in res if x == "fehler"]
        nf += bool(fe)
        print(("FEHLER " if fe else "ok     ") + name)
        for x, t in res:
            print(f"   {x}: {t}")
    print(f"\n{len(ps)} Partien geprüft, {nf} mit Fehlern.")
    if a.out:
        os.makedirs(os.path.dirname(os.path.join(a.repo, a.out)) or ".", exist_ok=True)
        json.dump({"partien": len(ps), "mit_fehlern": nf, "ergebnisse": erg}, open(os.path.join(a.repo, a.out), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
