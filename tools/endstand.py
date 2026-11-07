#!/usr/bin/env python3
"""Endstand-Meldung direkt mit dem Abpfiff (Finn, 06.11.2026). Ohne Claude, aus den Live-Daten in spielplan.json.

Bisher kam der Spielbericht erst mit dem stündlichen Spieltage-Lauf (22 bis 29 Minuten nach Abpfiff). Jetzt gibt es
sofort eine kurze Meldung je Partie: Ergebnis, Tore mit Minute und Vorlage, Platzverweise, Gelbe Karten. Der
ausführliche Bericht folgt wie bisher.
Id endstand-<heim>-<TTMM>, steht auch in tools/aufstellungen_live.json (Schutz vor dem Spiegel).
Als Modul: anwenden(news, live, spielplan) -> Liste neuer oder geänderter Ids.
"""
import re
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")


def partien(sp):
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            yield p


def nk(n):
    n = unicodedata.normalize("NFKD", str(n or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", n.split()[-1]) if n.split() else ""


SPIELERINNEN = set()  # Nachnamen aus kader.csv: Karten für andere Namen gehen an Trainerinnen und Staff (Arnautis, Parser-Test 06.11.)


def wer(c):
    return c["n"] if not SPIELERINNEN or nk(c["n"]) in SPIELERINNEN else f"{c['n']} (Trainerbank)"


def _art(n):
    t = n.replace(".", " ").split()
    return "m" if any(x in t for x in ("FC", "SC", "VfL", "VfB", "SV")) else "f" if "TSG" in t else ""


def bei(n):
    return {"m": "beim ", "f": "bei der "}.get(_art(n), "bei ") + n


def gegen(n):
    return {"m": "gegen den ", "f": "gegen die "}.get(_art(n), "gegen ") + n


def meldung(p, jetzt):
    h, g = p["heim"], p["gast"]
    a, b = (int(x) for x in p["ergebnis"])
    if a > b:
        satz = f"{h} gewinnt {gegen(g)} mit {a}:{b}."
    elif a < b:
        satz = f"{g} gewinnt {bei(h)} mit {b}:{a}."
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
    for v in p.get("verschossen") or []:
        text.append(f"Elfmeter verschossen: {v['n']} ({v['min']}.).")
    rot = [f"{wer(c)} ({'Gelb-Rot' if c['art'] == 'gelbrot' else 'Rot'}, {c['min']}.)" for c in k if c.get("art") in ("rot", "gelbrot")]
    if rot:
        text.append("Platzverweis: " + ", ".join(rot) + "." + (" Eine Sperre für das nächste Spiel ist wahrscheinlich."
                                                             if any(nk(c["n"]) in SPIELERINNEN or not SPIELERINNEN for c in k if c.get("art") in ("rot", "gelbrot")) else ""))
    gelb = [wer(c) for c in k if c.get("art") == "gelb"]
    if gelb:
        text.append("Gelb: " + ", ".join(gelb) + ".")
    text.append("Noten und der ausführliche Bericht folgen.")
    tt = p["anstoss"][8:10] + p["anstoss"][5:7]
    return {"id": f"endstand-{(p.get('heim_k') or '').lower()}-{tt}", "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"),
            "spielerin": f"{h} gegen {g}", "verein": h, "nr": "", "pos": "Spielansetzung", "tags": ["SPIELBERICHT"],
            "headline": f"Endstand: {h} {a}:{b} {g}", "kurz": f"Endstand {p.get('heim_k')} {a}:{b} {p.get('gast_k')}",
            "text": text, "kickbase": "",
            "quellen": [{"name": "Sportschau", "url": p.get("url", "")}], "quelle_live": True, "partie_id": p["id"]}


def anwenden(news, live, sp, jetzt=None, kader=None):
    jetzt = jetzt or datetime.now(TZ)
    if kader:
        SPIELERINNEN.update(nk(r["name"]) for r in kader if r.get("name"))
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


# ---------------------------------------------------------------------------------------------------------------
# Spielbericht mit Noten (Finn 07.11.2026): Sobald apifootball.json Noten für eine Partie hat, wird die Endstand-Meldung
# zur richtigen News: Schlagzeile mit der besten Note, Statistik (Schüsse, Ballbesitz, xG), beste Noten je Team,
# schwächste Startelf-Note. Neue Zeit = Zeitpunkt der Noten, damit sie im Feed nach oben rückt. Nur einmal je Partie.
# Noten zählen erst ab 46 Minuten (wie überall im Ticker). Aufruf nach dem Bau von apifootball.json:
#   python3 tools/endstand.py --noten --repo .

def _de(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def _min(v):
    try:
        return int(re.sub(r"\D.*", "", str(v)) or 0) + (int(str(v).split("+")[1]) if "+" in str(v) else 0)
    except (ValueError, IndexError):
        return 0


def minuten(p):
    """Nachname (normalisiert) -> (Minuten, Seite) aus der offiziellen Aufstellung samt Live-Wechseln."""
    out = {}
    ende = 90
    for seite in ("heim", "gast"):
        a = p.get(f"{seite}_aufstellung") or {}
        if a.get("typ") != "offiziell":
            continue
        w = [x for x in (p.get("wechsel") or []) if x.get("seite") == seite]
        aus = {nk(x["aus"]): _min(x["min"]) for x in w if x.get("aus")}
        ein = {nk(x["ein"]): _min(x["min"]) for x in w if x.get("ein")}
        for s in a.get("startelf") or []:
            m = _min(s["aus"]) if s.get("aus") else aus.get(nk(s["n"]), ende)
            out[nk(s["n"])] = (m, seite, "S")
        for s in a.get("bank") or []:
            e = _min(s["ein_min"]) if s.get("ein") and s.get("ein_min") else ein.get(nk(s["n"]))
            if e is not None:
                out[nk(s["n"])] = (max(ende - e, 0), seite, "E")
    return out


# Finn 07.11.2026: Die Note ist keine Meldung. Schlagzeile und Feed-Titel erzählen das Spiel (Ergebnis, wer traf),
# Noten stehen im Text, in der Kickbase-Zeile und in der Aufstellung.
KURZN = {"FCB": "FC Bayern", "WOB": "Wolfsburg", "SGE": "Frankfurt", "SVW": "Werder", "B04": "Leverkusen", "KOE": "Köln", "RBL": "Leipzig",
         "FCU": "Union", "SCF": "Freiburg", "TSG": "Hoffenheim", "FCN": "Nürnberg", "HSV": "HSV", "VFB": "Stuttgart", "M05": "Mainz"}
ZAHL = {2: "doppelt", 3: "dreifach", 4: "vierfach"}
WORT = {2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs"}


def torsatz(p, seite=None):
    """'Kramer und Loonen treffen', 'Pápai trifft doppelt', 'vier verschiedene Torschützinnen'."""
    c = {}
    for t in p.get("tore") or []:
        if t.get("et") or t.get("art") == "Eigentor":
            continue
        if seite and t.get("seite") != seite:
            continue
        c[t["n"]] = c.get(t["n"], 0) + 1
    if not c:
        return ""
    if len(c) == 1:
        n, z = next(iter(c.items()))
        return f"{n} trifft" + (f" {ZAHL.get(z, str(z) + '-mal')}" if z > 1 else "")
    if len(c) >= 4:
        return f"{WORT.get(len(c), len(c))} verschiedene Torschützinnen"
    l = sorted(c, key=lambda n: -c[n])
    if c[l[0]] > 1 and all(c[n] == 1 for n in l[1:]):
        rest = l[1:]
        return f"{l[0]} trifft {ZAHL.get(c[l[0]], str(c[l[0]]) + '-mal')}, dazu " + (rest[0] if len(rest) == 1 else ", ".join(rest[:-1]) + " und " + rest[-1])
    namen = [n + (f" ({c[n]})" if c[n] > 1 else "") for n in l]
    return ", ".join(namen[:-1]) + " und " + namen[-1] + " treffen"


def titel(p):
    h, g, hk, gk = p["heim"], p["gast"], p.get("heim_k"), p.get("gast_k")
    a, b = (int(x) for x in p["ergebnis"])
    kh, kg = KURZN.get(hk, h), KURZN.get(gk, g)
    den = lambda k, n: ("den " + n) if k == "HSV" else n
    if a == b:
        kopf, kurz, ts = f"{h} und {g} {a}:{b}", f"{kh} und {kg} {a}:{b}" if a else f"{kh} und {kg} torlos", torsatz(p)
    elif a > b:
        kopf, kurz, ts = f"{h} gewinnt {a}:{b} {gegen(g)}", f"{kh} schlägt {den(gk, kg)} {a}:{b}", torsatz(p, "heim")
    else:
        kopf, kurz, ts = f"{g} gewinnt {b}:{a} {bei(h)}", f"{kg} siegt {b}:{a} in {kh}" if hk != "HSV" else f"{kg} siegt {b}:{a} beim HSV", torsatz(p, "gast")
    if ts.endswith("Torschützinnen"):
        return f"{kopf} mit {ts.replace('verschiedene', 'verschiedenen')}", kurz
    return (f"{kopf}, {ts}" if ts else kopf), kurz


def bericht(p, af_spiel, spl, jetzt):
    h, g, hk, gk = p["heim"], p["gast"], p.get("heim_k"), p.get("gast_k")
    a, b = (int(x) for x in p["ergebnis"])
    mins = minuten(p)
    noten = {"heim": [], "gast": []}
    for sid, n in (af_spiel.get("no") or {}).items():
        s = spl.get(sid)
        if not s:
            continue
        m = mins.get(nk(s["n"]))
        if not m or m[0] < 46:
            continue
        noten[m[1]].append((n, s["n"].split()[-1] if s["n"].split() else s["n"], m[2]))
    for l in noten.values():
        l.sort(key=lambda x: -x[0])
    alle = sorted(noten["heim"] + noten["gast"], key=lambda x: -x[0])
    if len(alle) < 10:
        return None
    best = alle[0]
    headline, kurz = titel(p)
    # Text
    alt = meldung(p, jetzt)["text"]
    text = [t for t in alt if not t.startswith("Noten und")]
    w = af_spiel.get("w") or {}
    st = []
    if w.get("sch"):
        st.append(f"Torschüsse {int(w['sch'][0])}:{int(w['sch'][1])}" + (f" (aufs Tor {int(w['tor'][0])}:{int(w['tor'][1])})" if w.get("tor") else ""))
    if w.get("bes"):
        st.append(f"Ballbesitz {int(w['bes'][0])}:{int(w['bes'][1])} %")
    if w.get("xg"):
        st.append(f"Expected Goals {_de(w['xg'][0], 2)}:{_de(w['xg'][1], 2)}")
    if w.get("eck"):
        st.append(f"Ecken {int(w['eck'][0])}:{int(w['eck'][1])}")
    text.append(f"Beste Note im Spiel: {best[1]} ({_de(best[0])}).")
    if st:
        text.append("Statistik (" + h + " zuerst): " + ", ".join(st) + ".")
    for seite, name in (("heim", h), ("gast", g)):
        l = noten[seite]
        if l:
            text.append(f"Beste Noten {name}: " + ", ".join(f"{x[1]} {_de(x[0])}" for x in l[:3]) + ".")
    schwach = [x for x in alle if x[2] == "S"]
    if schwach and schwach[-1][0] < 6.0:
        text.append(f"Schwächste Note in der Startelf: {schwach[-1][1]} ({_de(schwach[-1][0])}).")
    # Kickbase: wer ragte heraus, wer enttäuschte (keine Kauf- oder Verkaufsempfehlung)
    top = [x for x in alle if x[0] >= 7.5][:3]
    kb = ""
    if top:
        kb = ("Herausragend: " + ", ".join(f"{x[1]} ({_de(x[0])})" for x in top) + ". ")
    for seite, name in (("heim", h), ("gast", g)):
        l = noten[seite]
        if l and l[0][0] < 6.8:
            kb += f"Bei {name} kam niemand über {_de(l[0][0])}. "
    tt = p["anstoss"][8:10] + p["anstoss"][5:7]
    return {"id": f"endstand-{(hk or '').lower()}-{tt}", "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"),
            "spielerin": f"{h} gegen {g}", "verein": h, "nr": "", "pos": "Spielansetzung", "tags": ["SPIELBERICHT"],
            "headline": headline, "kurz": kurz,
            "text": text, "kickbase": kb.strip(),
            "quellen": [{"name": "Sportschau", "url": p.get("url", "")}, {"name": "API-Football (Noten, Statistik)", "url": "https://www.api-football.com"}],
            "quelle_live": True, "partie_id": p["id"], "noten": True}


def doppelt(x, p):
    """Ein Spielbericht je Partie (Finn 07.11.2026): Bericht des Laufs zur selben Ligapartie (Tag SPIELBERICHT, ohne partie_id,
    kein Pokal, Verein Heim oder Gast, geschrieben zwischen Anpfiff und 8 Stunden danach) fällt weg, der Bericht mit Noten bleibt."""
    if x.get("partie_id") or "SPIELBERICHT" not in (x.get("tags") or []) or "POKAL" in (x.get("tags") or []) or "EUROPAPOKAL" in (x.get("tags") or []):
        return False
    if x.get("verein") not in (p["heim"], p["gast"]):
        return False
    z, a = x.get("zeit", ""), p.get("anstoss", "")[:16]
    try:
        ende = (datetime.fromisoformat(a) + timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        return False
    return a <= z <= ende


def mit_noten(news, live, sp, af, spl, jetzt=None):
    jetzt = jetzt or datetime.now(TZ)
    weg = set(live.get("entfernt", []))
    grenze = (jetzt - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
    out = []
    for p in partien(sp):
        asp = (af.get("spiele") or {}).get(p["id"])
        if p.get("status") != "beendet" or not asp or not asp.get("no") or p.get("anstoss", "") < grenze or len(p.get("ergebnis") or []) != 2:
            continue
        tt = p["anstoss"][8:10] + p["anstoss"][5:7]
        mid = f"endstand-{(p.get('heim_k') or '').lower()}-{tt}"
        alt = next((x for x in news["meldungen"] if x["id"] == mid), None)
        if mid in weg or not alt or alt.get("noten"):  # nur aus einer Live-Endstand-Meldung, genau einmal
            continue
        m = bericht(p, asp, spl, jetzt)
        if not m:
            continue
        news["meldungen"] = [m] + [x for x in news["meldungen"] if x["id"] != mid and not doppelt(x, p)]
        live["meldungen"] = [m] + [x for x in live.get("meldungen", []) if x["id"] != mid]
        out.append(mid)
        print(f"Spielbericht mit Noten: {m['headline']}")
    return out


if __name__ == "__main__":
    import argparse, json, os
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--noten", action="store_true")
    ap.add_argument("--trocken", action="store_true")
    x = ap.parse_args()
    lade = lambda f, d=None: json.load(open(os.path.join(x.repo, f), encoding="utf-8")) if os.path.exists(os.path.join(x.repo, f)) else d
    news, sp, af = lade("news.json"), lade("spielplan.json"), lade("apifootball.json", {})
    live = lade("tools/aufstellungen_live.json", {"meldungen": []})
    spl = {s["id"]: s for s in (lade("spielerinnen.json", {}) or {}).get("spielerinnen", [])}
    ids = mit_noten(news, live, sp, af, spl) if x.noten else []
    if ids and not x.trocken:
        json.dump(news, open(os.path.join(x.repo, "news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(live, open(os.path.join(x.repo, "tools/aufstellungen_live.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(ids)
