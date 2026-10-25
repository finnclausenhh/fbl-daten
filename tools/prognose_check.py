#!/usr/bin/env python3
"""WOSOINSIDER: Trefferquote der möglichen Aufstellungen.

Vergleicht die letzte Prognose vor Anpfiff mit der tatsächlichen Startelf und rechnet je Stufe
(sicher, erwartet, unsicher, unwahrscheinlich, ausgeschlossen) aus, wie oft die Spielerin wirklich begonnen hat.

Zwei Modi:

  live      Liest die Git-Historie von spielplan.json im Repo fbl-daten. Für jede beendete Partie wird die
            letzte Version vor Anpfiff mit "typ": "prognose" gesucht und mit der offiziellen Startelf verglichen.
            Braucht keine Netzabfrage, läuft auch als GitHub Action.
              python3 prognose_check.py live --repo . --out tracking/trefferquote.json

  backtest  Rechnet vergangene Spieltage mit den Regeln aus engine/spielplan_bau.py nach (nur Einsatzdaten
            und Platzverweise, ohne Verletzungsmeldungen und ohne redaktionelle Anpassungen). Liest Sportschau.
              python3 prognose_check.py backtest --engine engine/spielplan_bau.py --kader engine/kader.csv \
                  --von 4 --bis 8 --cache bt_cache.json --out tracking/backtest.json

Die letzte Ausgabezeile ist immer eine JSON-Zusammenfassung.
"""
import argparse, json, re, subprocess, sys, unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
STUFEN = ["sicher", "erwartet", "unsicher", "unwahrscheinlich", "ausgeschlossen"]
SCHWELLEN = [1.0, 0.95, 0.9, 0.85, 0.8, 0.7, 0.55, 0.3]
TRANS = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "ß": "ss", "ð": "d", "ł": "l", "đ": "d"})


def key(name):
    """Vergleichsschlüssel: Nachname ohne Akzente (wie in der Engine üblich)."""
    s = (name or "").lower().translate(TRANS)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s)


def quote_aus(chip):
    m = re.search(r"Einsatzwert (\d+) %", chip.get("warum", ""))
    return int(m.group(1)) / 100 if m else None


# ------------------------------------------------------------------ Auswertung einer Partie
def vergleiche(prog, offiziell_startelf, offiziell_bank=()):
    """prog: Aufstellungsobjekt typ prognose. offiziell_startelf/-bank: Listen von Chips mit "n" und "voll".
    Gibt eine Zeile je eingestufter Spielerin zurück, mit "kader": startelf | bank | nicht im Kader."""
    echt, bank = set(), set()
    for c in offiziell_startelf:
        echt.add(key(c.get("voll") or c["n"]))
        echt.add(key(c["n"]))
    for c in offiziell_bank:
        bank.add(key(c.get("voll") or c["n"]))
        bank.add(key(c["n"]))
    zeilen = []
    gesehen = set()
    for feld in ("startelf", "bank", "ausgeschlossen"):
        for c in prog.get(feld, []):
            k_voll, k_n = key(c.get("voll") or c["n"]), key(c["n"])
            if k_voll in gesehen:
                continue
            gesehen.add(k_voll)
            st = c.get("st")
            if not st:
                continue
            zeilen.append({"n": c["n"], "voll": c.get("voll", c["n"]), "stufe": st, "in_prognose_elf": feld == "startelf",
                           "quote": quote_aus(c), "redaktion": "Einschätzung WOSOINSIDER" in c.get("warum", ""),
                           "begonnen": (k_voll in echt) or (k_n in echt),
                           "kader": "startelf" if (k_voll in echt or k_n in echt) else "bank" if (k_voll in bank or k_n in bank) else "nicht im Kader"})
    elf = [z for z in zeilen if z["in_prognose_elf"]]
    return {"zeilen": zeilen, "elf_treffer": sum(z["begonnen"] for z in elf), "elf_n": len(elf)}


def zusammenfassen(partien):
    """partien: Liste von {"md", "verein", "gegner", "anstoss", "vergleich": vergleiche(...)}"""
    je_stufe = {s: {"n": 0, "begonnen": 0} for s in STUFEN}
    alle = []
    for p in partien:
        for z in p["vergleich"]["zeilen"]:
            je_stufe[z["stufe"]]["n"] += 1
            je_stufe[z["stufe"]]["begonnen"] += z["begonnen"]
            alle.append(z)
    for s, d in je_stufe.items():
        d["quote"] = round(d["begonnen"] / d["n"], 3) if d["n"] else None

    # Kalibrierung nach Einsatzwert (nur Spielerinnen ohne Ausschluss, damit Verletzte das Bild nicht verzerren)
    schwellen = []
    for t in SCHWELLEN:
        g = [z for z in alle if z["quote"] is not None and z["quote"] >= t and z["stufe"] != "ausgeschlossen"]
        if g:
            schwellen.append({"ab_einsatzwert": t, "n": len(g), "begonnen": sum(z["begonnen"] for z in g),
                              "quote": round(sum(z["begonnen"] for z in g) / len(g), 3)})

    elf_n = sum(p["vergleich"]["elf_n"] for p in partien)
    elf_t = sum(p["vergleich"]["elf_treffer"] for p in partien)
    verteilung = {}
    for p in partien:
        t = p["vergleich"]["elf_treffer"]
        verteilung[str(t)] = verteilung.get(str(t), 0) + 1
    daneben = [{"md": p["md"], "verein": p["verein"], "n": z["n"], "stufe": z["stufe"], "kader": z["kader"]}
               for p in partien for z in p["vergleich"]["zeilen"] if z["stufe"] == "sicher" and not z["begonnen"]]
    grund = {"bank": sum(d["kader"] == "bank" for d in daneben), "nicht im Kader": sum(d["kader"] == "nicht im Kader" for d in daneben)}
    return {"teams": len(partien), "elf_treffer_schnitt": round(elf_t / len(partien), 2) if partien else None,
            "elf_quote": round(elf_t / elf_n, 3) if elf_n else None, "elf_verteilung": dict(sorted(verteilung.items(), key=lambda x: -int(x[0]))),
            "je_stufe": je_stufe, "kalibrierung": schwellen, "sicher_daneben_grund": grund, "sicher_aber_nicht_begonnen": daneben}


# ------------------------------------------------------------------ live: aus der Git-Historie
def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def live(a):
    jetzt = json.load(open(Path(a.repo) / "spielplan.json", encoding="utf-8"))
    commits = [l.split(" ", 1) for l in git(a.repo, "log", "--format=%H %cI", "--", "spielplan.json").splitlines() if l.strip()]
    commits = [(h, datetime.fromisoformat(t)) for h, t in commits]  # neueste zuerst
    versionen = {}

    def version(h):
        if h not in versionen:
            try:
                versionen[h] = json.loads(git(a.repo, "show", f"{h}:spielplan.json"))
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                versionen[h] = None
        return versionen[h]

    def partien(sp):
        for t in sp.get("spieltage", []):
            for p in t.get("partien", []) + t.get("nachholspiele", []):
                yield p

    ergebnisse, fehlend = [], []
    beginn = commits[-1][1] if commits else None  # Tracking zählt erst ab der ältesten gespiegelten Version
    gesehen = set()
    for p in partien(jetzt):
        if p.get("status") != "beendet" or p.get("id") in gesehen:
            continue
        gesehen.add(p.get("id"))
        anstoss = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=BERLIN)
        if beginn is None or anstoss <= beginn:
            continue
        for seite, gegner in (("heim", "gast"), ("gast", "heim")):
            off = p.get(f"{seite}_aufstellung") or {}
            if off.get("typ") != "offiziell":
                continue
            prog, prog_zeit = None, None
            for h, t in commits:  # neueste zuerst: erste passende Version vor Anpfiff
                if t >= anstoss:
                    continue
                v = version(h)
                if not v:
                    continue
                alt = next((x for x in partien(v) if x.get("id") == p["id"]), None)
                kand = (alt or {}).get(f"{seite}_aufstellung") or {}
                if kand.get("typ") == "prognose" and not kand.get("datenluecke"):
                    prog, prog_zeit = kand, t
                    break
            if not prog:
                fehlend.append({"md": p["md"], "verein": p[seite]})
                continue
            ergebnisse.append({"md": p["md"], "verein": p[seite], "gegner": p[gegner], "anstoss": p["anstoss"],
                               "prognose_stand": prog_zeit.isoformat(), "vergleich": vergleiche(prog, off["startelf"], off.get("bank", []))})
    out = {"modus": "live", "stand": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M"),
           "hinweis": "Letzte veröffentlichte Prognose vor Anpfiff gegen offizielle Startelf. Quelle: Git-Historie von spielplan.json.",
           "gesamt": zusammenfassen(ergebnisse),
           "je_spieltag": {str(md): zusammenfassen([e for e in ergebnisse if e["md"] == md])
                           for md in sorted({e["md"] for e in ergebnisse})},
           "ohne_prognose": fehlend}
    schreibe(a.out, out)
    print(json.dumps({"teams_ausgewertet": len(ergebnisse), "ohne_prognose": len(fehlend),
                      "sicher": out["gesamt"]["je_stufe"]["sicher"], "elf_schnitt": out["gesamt"]["elf_treffer_schnitt"]}, ensure_ascii=False))


# ------------------------------------------------------------------ backtest: Regeln nachrechnen
def backtest(a):
    import importlib.util
    spec = importlib.util.spec_from_file_location("spielplan_bau", a.engine)
    sb = importlib.util.module_from_spec(spec)
    sys.argv = [sys.argv[0]]
    spec.loader.exec_module(sb)
    kader = sb.Kader(a.kader)
    try:
        cache = json.load(open(a.cache, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    start = sb.lies_spieltag("spiele-und-ergebnisse")
    pfade = start["pfade"]
    spiele = []
    for md in sorted(pfade):
        if md > a.bis:
            break
        c = cache.get(f"md{md}")
        if not c:
            st = sb.lies_spieltag(pfade[md]) if md != start["md"] else start
            c = [s for s in st["spiele"]]
            cache[f"md{md}"] = c
        spiele += [{**s, "md": md} for s in c]
    beendet = [s for s in spiele if s["status"] == "beendet"]
    for s in beendet:
        if s["ma"] not in cache:
            auf = sb.lies_aufstellung(s["ma"])
            if auf:
                cache[s["ma"]] = auf
    json.dump(cache, open(a.cache, "w", encoding="utf-8"), ensure_ascii=False)

    hist = {v: [] for v in sb.VEREINE}
    for s in sorted(beendet, key=lambda s: s["anstoss_utc"], reverse=True):
        auf = cache.get(s["ma"])
        if not auf:
            continue
        for v, seite in ((s["heim"], "home"), (s["gast"], "away")):
            rot = {p["n"] for p in auf[seite]["start"] + auf[seite]["bank"] if p.get("rot")}
            hist[v].append({"ma": s["ma"], "t": sb.berlin(s["anstoss_utc"]), "md": s["md"],
                            "start": auf[seite]["start"], "bank": auf[seite]["bank"], "rot": rot})

    ergebnisse = []
    for s in beendet:
        if not (a.von <= s["md"] <= a.bis) or s["ma"] not in cache:
            continue
        anstoss = sb.berlin(s["anstoss_utc"])
        auf = cache[s["ma"]]
        for v, gegner, seite in ((s["heim"], s["gast"], "home"), (s["gast"], s["heim"], "away")):
            h = [x for x in hist[v] if x["t"] < anstoss]
            if len(h) < 3:
                continue
            sperre = set()
            if h and h[0]["rot"]:
                for n in h[0]["rot"]:
                    r = kader.finde(v, nachname=n)
                    sperre.add((v, r["name"] if r else n))
            prog = sb.prognose(v, gegner, s, s["md"], h, kader, {}, [], sperre, {})
            off = sb.offiziell(v, seite, auf, kader)
            ergebnisse.append({"md": s["md"], "verein": sb.VEREINE[v][0], "gegner": sb.VEREINE[gegner][0],
                               "anstoss": anstoss.strftime("%Y-%m-%dT%H:%M"), "vergleich": vergleiche(prog, off["startelf"], off["bank"])})
    out = {"modus": "backtest", "stand": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M"),
           "hinweis": "Nachgerechnet mit den Regeln aus spielplan_bau.py: nur Einsätze der letzten fünf Ligaspiele und "
                      "Platzverweise. Ohne Verletzungs- und Sperrmeldungen aus news.json und ohne redaktionelle Anpassungen, "
                      "deshalb eher eine Untergrenze für die echte Trefferquote.",
           "spieltage": [a.von, a.bis], "gesamt": zusammenfassen(ergebnisse),
           "je_spieltag": {str(md): zusammenfassen([e for e in ergebnisse if e["md"] == md])
                           for md in sorted({e["md"] for e in ergebnisse})},
           "partien": [{k: v for k, v in e.items() if k != "vergleich"} | {"elf_treffer": e["vergleich"]["elf_treffer"]} for e in ergebnisse]}
    schreibe(a.out, out)
    g = out["gesamt"]
    print(json.dumps({"teams_ausgewertet": len(ergebnisse), "elf_schnitt": g["elf_treffer_schnitt"],
                      "sicher": g["je_stufe"]["sicher"], "erwartet": g["je_stufe"]["erwartet"]}, ensure_ascii=False))


def schreibe(pfad, obj):
    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    json.dump(obj, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="modus", required=True)
    l = sub.add_parser("live")
    l.add_argument("--repo", default=".")
    l.add_argument("--out", default="tracking/trefferquote.json")
    b = sub.add_parser("backtest")
    b.add_argument("--engine", required=True)
    b.add_argument("--kader", required=True)
    b.add_argument("--von", type=int, default=4)
    b.add_argument("--bis", type=int, default=8)
    b.add_argument("--cache", default="bt_cache.json")
    b.add_argument("--out", default="tracking/backtest.json")
    a = ap.parse_args()
    (live if a.modus == "live" else backtest)(a)


if __name__ == "__main__":
    main()
