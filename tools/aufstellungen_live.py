#!/usr/bin/env python3
"""Offizielle Aufstellungen so schnell wie möglich (Finn, 01.11.2026). Läuft als GitHub Action, ohne Claude.

Prüft Liga, DFB-Pokal und Champions League bei der Sportschau. Für jedes Spiel mit Bundesliga-Verein, dessen Anpfiff
in höchstens VORLAUF Minuten ist (oder bis 15 Minuten danach), fragt es die Aufstellung ab, bis sie da ist (jede Minute,
höchstens LAUFZEIT Minuten pro Aufruf). Gefundene Aufstellungen kommen als Meldungen (gleiches Format und gleiche Ids wie
engine/aufstellung_bau.py im Artifact) vorne in news.json und zusätzlich in tools/aufstellungen_live.json.
Selbstheilung: Fehlen Meldungen aus aufstellungen_live.json in news.json (etwa weil ein Spiegel news.json überschrieben
hat), werden sie wieder eingefügt (nur Spiele von heute und gestern).

Aufruf: python3 tools/aufstellungen_live.py --repo .   (Exit 0; Ausgabe "geaendert=1", wenn news.json geschrieben wurde)
"""
import argparse, csv, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbl_fetch as F  # noqa: E402
import aufstellung_bau as AB  # noqa: E402
import dfb_quelle as D  # noqa: E402
import comeback as CB  # noqa: E402
import punkt_update as PU  # noqa: E402
import endstand as ES  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
BASIS = "https://www.sportschau.de/live-und-ergebnisse/fussball/"
WETTBEWERBE = [("deutschland-bundesliga-frauen", None), ("deutschland-dfb-pokal-frauen", "DFB-Pokal"),
               ("uefa-champions-league-frauen", "Champions League")]
VORLAUF = 80
LAUFZEIT = 13
PRE = {"DFB-Pokal": "pokal-", "Champions League": "cl-", "Europa Cup": "ec-"}  # Id-Teil je Wettbewerb (Liga ohne)
EC_NACHLAUF = 150  # Europa Cup: DFB-Datencenter zeigt die Aufstellung teils erst nach Anpfiff (Frankfurt/PSV 11.11.2026), so lange weiter prüfen
EUROPA_URL = {}  # ma -> DFB-Spielseite (Europa Cup kommt nur vom DFB-Datencenter, nicht von der Sportschau)


def spiele_heute(jetzt):
    """[(wettbewerb, basis, ma, anstoss)] für Spiele mit Bundesliga-Verein im Zeitfenster."""
    out = []
    for pfad, wb in WETTBEWERBE:
        basis = BASIS + pfad + "/"
        try:
            s = F.get(basis + "spiele-und-ergebnisse")
        except Exception as e:
            print(f"WARN {pfad}: {e}", file=sys.stderr)
            continue
        for li in re.finditer(r'data-match_id="(\d+)" data-datetime="([0-9T:\-]+)Z"', s):
            mid, dt = li.group(1), li.group(2)
            m = re.search(pfad + r"/(ma" + mid + r"/[a-z0-9\-_]+)/", s[li.start():li.start() + 20000])
            if not m:
                continue
            ma = m.group(1)
            heim, gast = ma.split("/")[1].split("_")
            if heim not in AB.SLUG and gast not in AB.SLUG:
                continue
            an = datetime.fromisoformat(dt).replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ)
            if an - timedelta(minutes=VORLAUF) <= jetzt <= an + timedelta(minutes=15):
                out.append((wb, basis, ma, an))
            elif an.date() == jetzt.date() and an > jetzt:
                SPAETER.append(an)
    for e in D.europa_spiele():  # Europa Cup (Finn 11.11.2026): DFB-Datencenter, nur Bundesliga-Vereine
        h, g = e["heim_slug"], e["gast_slug"]
        h = next((k for k in AB.SLUG if D.KENN.get(k, k) in h), h)
        g = next((k for k in AB.SLUG if D.KENN.get(k, k) in g), g)
        ma = f"dfb{e['id']}/{h}_{g}"
        EUROPA_URL[ma] = e["url"]
        an = datetime.fromisoformat(e["anstoss"]).replace(tzinfo=TZ)
        if an - timedelta(minutes=VORLAUF) <= jetzt <= an + timedelta(minutes=EC_NACHLAUF):
            out.append(("Europa Cup", None, ma, an))
        elif an.date() == jetzt.date() and an > jetzt:
            SPAETER.append(an)
    return out


SPAETER = []  # Anstoßzeiten späterer Spiele heute (für die Kette der Action)


def letzte_liga(spielplan, verein, vor):
    """Startelf und Bank des letzten Ligaspiels (offizielle Aufstellung aus spielplan.json)."""
    best = None
    for t in spielplan.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            if p.get("status") != "beendet" or p.get("anstoss", "") >= vor:
                continue
            for seite in ("heim", "gast"):
                a = p.get(f"{seite}_aufstellung") or {}
                if p.get(seite) == verein and a.get("typ") == "offiziell" and (not best or p["anstoss"] > best[0]):
                    best = (p["anstoss"], {"start": [x["n"] for x in a.get("startelf", [])], "bank": [x["n"] for x in a.get("bank", [])]})
    return best[1] if best else None


_TR = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "ß": "ss", "đ": "d", "Đ": "D", "ł": "l", "Ł": "L", "ð": "d", "þ": "th"})


def nk(name):
    """Nachname vergleichbar machen (Østenstad = Östenstad, Pápai = Papai)."""
    return F.norm(str(name).translate(_TR)).split()[-1] if str(name).strip() else ""


KADER = []

# Namen, unter denen das DFB-Datencenter Spielerinnen abweichend führt (Zweitnamen). Ergänzbar in tools/namen_alias.json
ALIAS = {("VfL Wolfsburg", "Nielsen"): "Fløe", ("TSG Hoffenheim", "Jimenez"): "Laia Martret", ("TSG Hoffenheim", "Jiménez"): "Laia Martret"}
try:
    for _v, _m in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "namen_alias.json"), encoding="utf-8")).items():
        for _a, _z in _m.items():
            ALIAS[(_v, _a)] = _z
except (OSError, ValueError):
    pass


def vereinheitliche(namen, verein, alt):
    """Namen aus Sportschau/DFB auf die Schreibweise des letzten Ligaspiels bringen (Finn 02.11.2026: Prasnikar = Prašnikar,
    Velde = van de Velde, Nielsen = Fløe). Sonst würden dieselben Spielerinnen gleichzeitig als NEU und RAUS geführt."""
    ref = {}
    for n in (alt or {}).get("start", []) + (alt or {}).get("bank", []):
        ref.setdefault(nk(n), n)
    out = []
    for n in namen:
        n = ALIAS.get((verein, n), ALIAS.get((verein, nk(n)), n))
        out.append(ref.get(nk(n), n))
    return out


def ergaenze_dfb(auf, h, g, wb):
    """DFB-Datencenter als zweite Quelle: Startelf, wenn die Sportschau keine hat, und Bank, wenn sie fehlt."""
    if wb == "Champions League":
        return auf
    if auf and auf["bank_heim"] and auf["bank_gast"]:
        return auf
    try:
        d = D.aufstellung(h, g, wb)
    except Exception as e:
        print(f"WARN DFB: {e}", file=sys.stderr)
        d = None
    if not d:
        return auf
    if not auf:
        if len(d["startelf_heim"]) < 11 or len(d["startelf_gast"]) < 11:
            return None
        return {"heim": h, "gast": g, "beendet": False, "startelf_heim": d["startelf_heim"], "startelf_gast": d["startelf_gast"],
                "bank_heim": d["bank_heim"], "bank_gast": d["bank_gast"], "dfb_url": d["url"], "nur_dfb": True}
    for sd in ("heim", "gast"):
        if not auf[f"bank_{sd}"] and d[f"bank_{sd}"]:
            auf[f"bank_{sd}"] = d[f"bank_{sd}"]
            auf["dfb_url"] = d["url"]
    return auf


def europa_auf(ma, h, g):
    """Europa Cup: Aufstellung aus dem DFB-Datencenter (liefert die Bank schon vor Anpfiff). None, solange nichts veröffentlicht ist."""
    d = D.aufstellung_url(EUROPA_URL.get(ma))
    if not d or len(d["startelf_heim"]) < 11 or len(d["startelf_gast"]) < 11:
        return None
    for sl, nm in ((h, d.get("heim_name")), (g, d.get("gast_name"))):  # Gegnername wie im DFB-Datencenter (nicht "Psv Vrouwen ...")
        if nm and sl not in AB.SLUG:
            AB.SLUG[sl] = nm
    return {"heim": h, "gast": g, "beendet": False, "startelf_heim": d["startelf_heim"], "startelf_gast": d["startelf_gast"],
            "bank_heim": d["bank_heim"], "bank_gast": d["bank_gast"], "dfb_url": d["url"], "nur_dfb": True,
            "formation_heim": d.get("formation_heim", ""), "formation_gast": d.get("formation_gast", "")}


def europa_berichte(a, pn, pl, news, live, spielplan, kader, jetzt=None):
    """Spielbericht (Endstand) für Europa-Cup-Spiele mit Bundesliga-Verein, Finn 11.11.2026 (Wolfsburg bei Feyenoord 0:3 blieb ohne
    Bericht, weil der Europa Cup nicht bei der Sportschau steht). Quelle DFB-Datencenter: Ergebnis, Tore mit Minute, Karten.
    Frühestens 105 Minuten nach Anpfiff, nur Spiele der letzten 3 Tage. Id endstand-ec-<verein>-<TTMM>. Gibt die Anstoßzeiten
    laufender, noch nicht berichteter Spiele zurück (die Action bleibt dann in der Kette)."""
    jetzt = jetzt or datetime.now(TZ)
    spiele = D.europa_spiele()
    ids = {m["id"] for m in news["meldungen"]} | set(live.get("entfernt", []))
    laufend, neu = [], []
    for e in spiele:
        club = next((k for k in AB.SLUG if D.KENN.get(k, k) in e["heim_slug"] or D.KENN.get(k, k) in e["gast_slug"]), None)
        if club not in AB.SLUG or AB.SLUG[club] not in AB.KURZ:
            continue
        verein = AB.SLUG[club]
        an = datetime.fromisoformat(e["anstoss"]).replace(tzinfo=TZ)
        tt = an.strftime("%d%m")
        mid = f"endstand-ec-{AB.KURZ[verein]}-{tt}"
        if mid in ids or jetzt < an or jetzt - an > timedelta(days=3):
            continue
        if jetzt < an + timedelta(minutes=105):
            laufend.append(an)
            continue
        v = D.spielverlauf(e["url"])
        if not v or not v["ergebnis"]:
            continue
        heim_ist = D.KENN.get(club, club) in e["heim_slug"]
        fix = lambda l: [dict(x, n=ALIAS.get((verein, x["n"]), x["n"]) if (x["seite"] == "heim") == heim_ist else x["n"]) for x in l]
        k = AB.KURZ[verein]
        gk = e["gast_slug"][:3] if heim_ist else e["heim_slug"][:3]
        p = {"id": "dfb" + e["id"], "heim": e["heim"], "gast": e["gast"], "ergebnis": v["ergebnis"], "tore": fix(v["tore"]),
             "karten": fix(v["karten"]), "anstoss": e["anstoss"], "heim_k": k if heim_ist else gk, "gast_k": gk if heim_ist else k,
             "url": e["url"]}
        p["heim_k"], p["gast_k"] = p["heim_k"].upper(), p["gast_k"].upper()
        m = ES.meldung(p, jetzt)
        m["id"], m["verein"] = mid, verein
        # Schlagzeile wie bei den Ligaberichten (erzählt das Spiel), Kurzform mit ausgeschriebenen Namen statt Kürzeln
        m["headline"], _ = ES.titel(p)
        a_, b_ = int(v["ergebnis"][0]), int(v["ergebnis"][1])
        wir_n = ES.KURZN.get(AB.KURZ[verein].upper(), verein)
        sie_n = (e["gast"] if heim_ist else e["heim"]).split()[0]
        wir, sie = (a_, b_) if heim_ist else (b_, a_)
        m["kurz"] = (f"{wir_n} schlägt {sie_n} {wir}:{sie}" if wir > sie else f"{sie_n} schlägt {wir_n} {sie}:{wir}" if sie > wir
                     else f"{wir_n} und {sie_n} {wir}:{sie}")
        m["tags"] = ["SPIELBERICHT", "EUROPAPOKAL"]
        m["quellen"] = [{"name": "DFB-Datencenter", "url": e["url"]}]
        m["wettbewerb"] = "Europa Cup"
        # Keine Noten im Europa Cup: API-Football führt das Turnier (Liga 1191), aber ohne Spielerinnen-Noten (geprüft 11.11.2026)
        m["text"] = [t for t in m["text"] if not t.startswith("Noten und der ausführliche Bericht")]
        m["text"].append("Für den Europa Cup gibt es keine Noten, unsere Datenquelle bewertet nur Ligaspiele. Für Kickbase zählt das Spiel nicht.")
        # Hin- und Rückspiel: Gesamtergebnis (gleiche beiden Mannschaften, anderes Spiel)
        hin = next((x for x in spiele if x["id"] != e["id"] and {x["heim_slug"], x["gast_slug"]} == {e["heim_slug"], e["gast_slug"]}
                    and x["ergebnis"] and x["anstoss"] < e["anstoss"]), None)
        if hin and hin["ergebnis"]:
            h_ = int(v["ergebnis"][0]) + int(hin["ergebnis"][1 if hin["heim_slug"] == e["gast_slug"] else 0])
            g_ = int(v["ergebnis"][1]) + int(hin["ergebnis"][0 if hin["heim_slug"] == e["gast_slug"] else 1])
            wir, sie = (h_, g_) if heim_ist else (g_, h_)
            gegner_n = e["gast"] if heim_ist else e["heim"]
            urteil = (f"{verein} kommt weiter" if wir > sie else f"{gegner_n} kommt weiter" if wir < sie else "Es steht insgesamt unentschieden")
            m["text"].insert(1, f"Europa Cup, {v.get('runde') or 'Rückspiel'}: Das Hinspiel endete {hin['heim']} {hin['ergebnis'][0]}:{hin['ergebnis'][1]} {hin['gast']}, "
                                f"insgesamt steht es {wir}:{sie} für {verein}. {urteil}." if wir != sie else
                                f"Europa Cup, {v.get('runde') or 'Rückspiel'}: Das Hinspiel endete {hin['heim']} {hin['ergebnis'][0]}:{hin['ergebnis'][1]} {hin['gast']}, "
                                f"insgesamt steht es {wir}:{sie}.")
        neu.append(m)
        ids.add(mid)
    if neu:
        news["meldungen"] = neu + news["meldungen"]
        live["meldungen"] = neu + [x for x in live.get("meldungen", []) if x["id"] not in {y["id"] for y in neu}]
        print(f"Europa-Cup-Bericht: {[m['headline'] for m in neu]}")
        speichern(a, pn, pl, news, live, "Aufstellungen live: " + ", ".join(m["id"] for m in neu))
    return laufend


def ableiten(verein, start, bank, zeit, gegner, wb, news, spielplan, quelle):
    """Fehlt ohne bekannten Grund (Finn 01.11.2026): stand im letzten Ligaspiel im Kader, jetzt weder Startelf noch Bank.
    Nur Stammspielerinnen (Finn 03.11.2026): zuletzt in der Startelf oder in mindestens der Hälfte der letzten Ligaspiele, sonst übergangen.
    Spielerinnen mit bekanntem Status (verletzt, gesperrt, fraglich) laut news.json sind ausgenommen."""
    alt = letzte_liga(spielplan, verein, zeit) or {"start": [], "bank": []}
    jetzt_k = {nk(x) for x in start + bank}
    bekannt = {nk(k) for k in AB.infos(verein, [], news)}
    out = []
    for n in alt["start"] + alt["bank"]:
        k = nk(n)
        if k in jetzt_k or k in bekannt:
            continue
        kv = AB.KADER_VEREIN.get(verein, verein)
        voll = next((r["name"] for r in KADER if r["verein"] == kv and nk(r["name"]) == k), n)
        bis = (datetime.fromisoformat(zeit[:16]) + timedelta(days=10)).strftime("%Y-%m-%d")
        x = {"verein": verein, "n": n, "spielerin": voll, "war": "Startelf" if n in alt["start"] else "Bank", "zeit": zeit,
             "gegner": gegner, "wettbewerb": wb or "Liga", "quelle": quelle, "delta": -1, "bis": bis}
        if not relevant(spielplan, x)[0]:
            continue  # Ergänzungsspielerin: keine Meldung und kein Abzug in der Prognose (Finn 03.11.2026)
        out.append({"verein": verein, "n": n, "spielerin": voll, "war": "Startelf" if n in alt["start"] else "Bank", "zeit": zeit,
                    "gegner": gegner, "wettbewerb": wb or "Liga", "quelle": quelle, "delta": -1, "bis": bis,
                    "grund": f"stand am {zeit[8:10]}.{zeit[5:7]}. gegen {gegner} nicht im Spieltagskader, obwohl im letzten Ligaspiel "
                             f"{'in der Startelf' if n in alt['start'] else 'auf der Bank'}; Grund nicht bekannt"})
    return out




def platzhalter(pid_, wb, basis, ma, an, h, g, jetzt, spielplan):
    """Karte "Aufstellung folgt" ab 80 Minuten vor Anpfiff; wird durch die offiziellen Aufstellungen ersetzt."""
    name = lambda s: AB.SLUG.get(s) or s.replace("-", " ").title().replace("Fc ", "FC ").replace("Sgs ", "SGS ").replace("Vfl ", "VfL ")
    verein = AB.SLUG.get(h) or AB.SLUG.get(g)
    partie = None
    for t in spielplan.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            if ma.split("/")[0] in p.get("url", ""):
                partie = p.get("id")
    wtext = {"DFB-Pokal": "im DFB-Pokal", "Champions League": "in der Champions League", "Europa Cup": "im Europa Cup"}.get(wb, "in der Liga")
    qurl, qname = (basis + ma + "/aufstellung", "Sportschau") if basis else (EUROPA_URL.get(ma, ""), "DFB-Datencenter")
    return {"id": pid_, "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"), "spielerin": "Spielansetzung", "verein": verein, "nr": "",
            "pos": "Spielansetzung", "tags": ["AUFSTELLUNG"] + (["POKAL"] if wb == "DFB-Pokal" else ["EUROPAPOKAL"] if wb else []),
            "headline": f"Aufstellung {name(h)} gegen {name(g)} folgt", "kurz": f"Aufstellung folgt, Anpfiff {an.strftime('%H:%M')}",
            "text": [f"Anpfiff {wtext} ist um {an.strftime('%H:%M')} Uhr. " + ("Die offizielle Aufstellung kommt meist rund 60 Minuten "
                     "vorher" if an - jetzt > timedelta(minutes=60) else "Die offizielle Aufstellung sollte in Kürze kommen")
                     + ", wir ergänzen sie hier automatisch, sobald sie veröffentlicht ist.",
                     "Bis dahin steht unsere Prognose im Spielplan bei der Partie." if partie else
                     "Für Pokal- und Europapokalspiele gibt es keine Prognose, die Aufstellung kommt hier automatisch."],
            "kickbase": "", "quellen": [{"name": qname, "url": qurl}],
            "platzhalter": True, "anstoss": an.strftime("%Y-%m-%dT%H:%M"), **({"wettbewerb": wb} if wb else {}), **({"partie_id": partie} if partie else {})}


def baue(wb, basis, ma, an, a, kader, news, spielplan, zeit):
    url = basis + ma + "/aufstellung" if basis else a.get("dfb_url", "")
    gr = AB.grafik(url) if basis else {}  # auch bei nur_dfb versuchen, die Sportschau-Grafik kann später kommen (Europa Cup: keine Sportschau)
    tt = an.strftime("%d%m")
    out = []
    for slug, gs, st, bk, sd in ((a["heim"], a["gast"], "startelf_heim", "bank_heim", "home"),
                                 (a["gast"], a["heim"], "startelf_gast", "bank_gast", "away")):
        if slug not in AB.SLUG or AB.SLUG[slug] not in AB.KURZ:
            continue
        verein = AB.SLUG[slug]
        if gs not in AB.SLUG:
            AB.SLUG[gs] = gs.replace("-", " ").title().replace("Fc ", "FC ").replace("Sgs ", "SGS ").replace("Vfl ", "VfL ")
        alt = letzte_liga(spielplan, verein, an.strftime("%Y-%m-%dT%H:%M"))
        a[st], a[bk] = vereinheitliche(a[st], verein, alt), vereinheitliche(a[bk], verein, alt)
        vgl = F.vergleich(alt, a[st], a[bk])
        t = AB.team(slug, gs, a[st], a[bk], vgl, kader, news, gr.get(sd), AB.lernen(spielplan, verein),
                    a.get("formation_" + ("heim" if sd == "home" else "gast")) or None)
        if wb:
            t["wettbewerb"] = wb
        # RAUS nur für die letzte Startelf; wer zuletzt auf der Bank saß, ist kein Startelf-Wechsel (Finn 07.11.2026)
        alt_s = {nk(x) for x in (alt or {}).get("start", [])}
        for f in t.get("fehlt", []):
            if f.get("f") == "raus":
                f["war"] = "Startelf" if nk(f["n"]) in alt_s else "Bank"
        if True:
            if not a[bk]:
                # Bank noch nicht veröffentlicht (Pokal vor Anpfiff, auch Liga, wenn Sportschau und DFB nur die Startelf haben,
                # Freiburg/Nürnberg 07.11.2026): niemand als "fehlt" führen, nur im Text nennen; die Bank wird nachgetragen
                t["bank"] = []
                t["fehlt"] = []
                t["bank_offen"] = True
                t["nicht_startelf"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader))
                                       for n in (vgl or {}).get("nicht_mehr_in_startelf", [])]
        pre = PRE.get(wb, "")
        text = []
        if t.get("bank_offen"):
            raus = (vgl or {}).get("nicht_mehr_in_startelf", [])
            text = [("Nicht mehr in der Startelf gegenüber dem letzten Ligaspiel: " + ", ".join(raus) + ". " if raus else "")
                    + "Die Bank folgt, sobald sie veröffentlicht ist."]
        out.append({"id": f"aufstellung-{pre}{AB.KURZ[verein]}-{tt}", "zeit": zeit, "spielerin": "Spielansetzung", "verein": verein,
                    "nr": "", "pos": "Spielansetzung", "tags": ["POKAL" if wb == "DFB-Pokal" else "EUROPAPOKAL" if wb else "TOP"],
                    "headline": f"Offizielle Aufstellung: {verein} gegen {t['gegner']}", "text": text, "kickbase": "",
                    "quellen": ([] if a.get("nur_dfb") else [{"name": "Sportschau", "url": url}])
                               + ([{"name": "DFB-Datencenter", "url": a["dfb_url"]}] if a.get("dfb_url") else []),
                    "aufstellung": t, "quelle_live": True})
        if a[bk]:
            abl = ableiten(verein, a[st], a[bk], an.strftime("%Y-%m-%dT%H:%M"), AB.SLUG.get(gs, gs), wb, news, spielplan,
                           a.get("dfb_url") or url)
            if abl:
                out[-1]["text"] = out[-1]["text"] + ["Nicht im Spieltagskader, obwohl im letzten Ligaspiel dabei: "
                    + ", ".join(x["n"] for x in abl) + ". Einen Grund nennt bisher keine Quelle."]
                out[-1]["ableitungen"] = abl
    return out


def ohne_doppel(news):
    """Jede id nur einmal (Finn 06.11.2026: Bühl-/Proost-Meldung und Aufstellungen standen doppelt,
    weil Live-Lauf und Heilen-Lauf gleichzeitig gepusht haben). Die erste, also neueste Fassung bleibt."""
    gesehen = set()
    news["meldungen"] = [m for m in news["meldungen"] if not (m["id"] in gesehen or gesehen.add(m["id"]))]


def std_zusammen(news, live):
    """Finn 08.11.2026 (Martret doppelt): Gibt es zu einer Standardschützin am selben Tag schon die fehlt-Meldung ihres Vereins,
    wandert die STANDARD-Meldung (meist vom Lauf) in diese Meldung: Tag STANDARD, Standards-Sätze, Kickbase-Satz, Foto.
    Die STANDARD-Meldung kommt nach "entfernt", damit Spiegel und Heilen sie nicht zurückholen. zusammen=True schützt vor Überschreiben."""
    L = news["meldungen"]
    weg = []
    for s in L:
        if "STANDARD" not in (s.get("tags") or []) or s["id"].startswith("fehlt-") or not s.get("spielerin"):
            continue
        tag, nach_ = (s.get("zeit") or "")[:10], s["spielerin"].split()[-1]
        f = next((m for m in L if m["id"].startswith("fehlt-") and m.get("verein") == s.get("verein") and (m.get("zeit") or "")[:10] == tag
                  and (m.get("spielerin") == s["spielerin"] or nach_ in m.get("headline", ""))), None)
        if not f:
            continue
        if "STANDARD" not in f.get("tags", []):
            f["tags"] = ["STANDARD"] + f.get("tags", [])
        f["text"] = f["text"] + [t for t in (s.get("text") or [])[1:] if t not in f["text"]]
        kb = re.split(r"(?<=[.!?])\s+", s.get("kickbase") or "")[0]   # nur der erste Satz, der Rest wiederholt meist den Status
        if kb and kb not in f.get("kickbase", ""):
            f["kickbase"] = (kb + " " + f.get("kickbase", "")).strip()
        if not f.get("foto") and s.get("foto"):
            f["foto"], f["foto_credit"] = s["foto"], s.get("foto_credit")
        if ": " in s.get("headline", "") and ": " not in f["headline"]:
            f["headline"] = f["headline"] + ": " + s["headline"].split(": ", 1)[1]
        f["zusammen"] = True
        weg.append(s["id"])
        live["meldungen"] = [f if y["id"] == f["id"] else y for y in live.get("meldungen", [])]
    if weg:
        news["meldungen"] = [m for m in L if m["id"] not in weg]
        live["meldungen"] = [m for m in live.get("meldungen", []) if m["id"] not in weg]
        live["entfernt"] = list(dict.fromkeys(live.get("entfernt", []) + weg))
        print(f"Standards in fehlt-Meldung zusammengeführt: {weg}")
    return weg


def speichern(a, pn, pl, news, live, nachricht, extra=()):
    std_zusammen(news, live)
    ohne_doppel(news)
    news["stand"] = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
    json.dump(news, open(pn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(live, open(pl, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not a.push:
        return
    g = ["git", "-C", a.repo]
    st = {"letzter_lauf": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"), "lauf": "Aufstellungen live", "news_neu": 1, "spielplan_geaendert": False}
    json.dump(st, open(os.path.join(a.repo, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(g + ["add", "news.json", "tools/aufstellungen_live.json", "status.json", *extra], check=True)
    if subprocess.run(g + ["diff", "--cached", "--quiet", "--", "news.json", "tools/aufstellungen_live.json"]).returncode == 0:
        subprocess.run(g + ["reset", "-q"], check=False)
        return
    subprocess.run(g + ["-c", "user.name=WOSOINSIDER", "-c", "user.email=finnclausenhh@users.noreply.github.com",
                        "commit", "-qm", nachricht], check=True)
    for _ in range(4):
        if subprocess.run(g + ["push", "-q", "origin", "HEAD:main"]).returncode == 0:
            print("gepusht")
            return
        # Konflikt: neu holen, eigene Meldungen erneut einfügen (news.json kann vom Spiegel überschrieben worden sein)
        subprocess.run(g + ["fetch", "-q", "origin", "main"], check=True)
        subprocess.run(g + ["reset", "-q", "--hard", "origin/main"], check=True)
        n2 = json.load(open(pn, encoding="utf-8"))
        ids = {m["id"] for m in n2["meldungen"]}
        weg = set(live.get("entfernt", []))
        lv = {m["id"]: m for m in live["meldungen"]}
        n2["meldungen"] = [m for m in live["meldungen"] if m["id"] not in ids] + [lv.get(m["id"], m) for m in n2["meldungen"] if m["id"] not in weg]
        news.clear(); news.update(n2)
        ohne_doppel(news)
        news["stand"] = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
        json.dump(news, open(pn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(live, open(pl, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        subprocess.run(g + ["add", "news.json", "tools/aufstellungen_live.json"], check=True)
        if subprocess.run(g + ["diff", "--cached", "--quiet"]).returncode == 0:
            print("nichts mehr zu pushen (schon aktuell)")
            return
        subprocess.run(g + ["-c", "user.name=WOSOINSIDER", "-c", "user.email=finnclausenhh@users.noreply.github.com",
                            "commit", "-qm", nachricht], check=True)
        time.sleep(3)
    print("WARN push fehlgeschlagen", file=sys.stderr)
    sys.exit(1)


def einsatz(spielplan, verein, nach, vor, n=5):
    """Startelf-Einsätze in den letzten n Ligaspielen mit offizieller Aufstellung vor einem Zeitpunkt: (starts, spiele, zuletzt_start)."""
    sp = []
    for t in spielplan.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            if p.get("status") != "beendet" or p.get("anstoss", "") >= vor:
                continue
            for seite in ("heim", "gast"):
                au = p.get(f"{seite}_aufstellung") or {}
                if p.get(seite) == verein and au.get("typ") == "offiziell":
                    sp.append((p["anstoss"], {nk(x["n"]) for x in au.get("startelf", [])}))
    sp = sorted(sp)[-n:]
    k = nk(nach)
    starts = sum(1 for _, s in sp if k in s)
    return starts, len(sp), bool(sp) and k in sp[-1][1]


def relevant(spielplan, x):
    """Aufmacher nur für Stammspielerinnen (Finn 01.11.2026): zuletzt in der Startelf oder in mindestens der Hälfte der letzten Ligaspiele."""
    st, n, zul = einsatz(spielplan, x["verein"], x["n"], x["zeit"])
    return zul or (n >= 2 and st / n >= 0.5), st, n


def fehlt_meldung_gruppe(gruppe, spielplan):
    bew = []
    for x in gruppe:
        rel, st, n = relevant(spielplan, x)
        bew.append((rel, st, n, x))
    rel = sorted([b for b in bew if b[0]], key=lambda b: -b[1])
    rest = sorted([b for b in bew if not b[0]], key=lambda b: -b[1])
    if not rel:
        return None  # nur Ergänzungsspielerinnen (z. B. nur Bank): keine eigene Meldung (Finn 01.11.2026)
    rel, rest = rel + rest, []  # Ergänzungsspielerinnen kommen in dieselbe Meldung und in die Überschrift
    x0 = rel[0][3]
    nach = lambda x: x["spielerin"].split()[-1]
    g = x0["gegner"]
    if len(rel) == 1:
        head = f"{nach(x0)} nicht im Kader gegen {g}"
    elif len(rel) == 2:
        head = f"{nach(x0)} und {nach(rel[1][3])} nicht im Kader gegen {g}"
    elif len(rel) == 3:
        head = f"Trio um {nach(x0)} fehlt gegen {g}"
    else:
        head = f"{len(rel)} Spielerinnen um {nach(x0)} fehlen gegen {g}"
    tt = x0["zeit"][8:10] + x0["zeit"][5:7]
    k = AB.KURZ[x0["verein"]].lower()
    kv = AB.KADER_VEREIN.get(x0["verein"], x0["verein"])
    r = next((r for r in KADER if r["verein"] == kv and r["name"] == x0["spielerin"]), {})
    pokal = x0["wettbewerb"] == "DFB-Pokal"
    wo = "im DFB-Pokal" if pokal else {"Champions League": "in der Champions League", "Europa Cup": "im Europa Cup"}.get(x0["wettbewerb"], "in der Liga")
    quelle = "DFB-Datencenter" if "dfb.de" in x0["quelle"] else "Sportschau"
    def satz(b):
        rel_, st, n, x = b
        war = "stand sie in der Startelf" if x["war"] == "Startelf" else "saß sie auf der Bank"
        return f"Im letzten Ligaspiel {war}, in den letzten {n} Ligaspielen begann sie {st}-mal."
    if len(rel) == 1:
        text = [f"{x0['spielerin']} steht {wo} gegen {g} weder in der Startelf noch auf der Bank. " + satz(rel[0])]
    else:
        text = [f"{wo[0].upper() + wo[1:]} gegen {g} stehen weder in der Startelf noch auf der Bank: "
                + ", ".join(f"{b[3]['spielerin']} ({b[1]} von {b[2]} Ligaspielen in der Startelf)" for b in rel) + "."]
    if rest:
        text.append("Außerdem nicht im Kader: " + ", ".join(
            f"{b[3]['spielerin']} ({b[1]} von {b[2]} Ligaspielen in der Startelf)" for b in rest) + ".")
    text.append("Einen Grund nennt bisher weder der Verein noch eine andere Quelle. Möglich sind Verletzung, Krankheit oder Schonung, "
                "das lässt sich aus der Aufstellung allein nicht ablesen.")
    m = {"id": f"fehlt-{re.sub(r'[^a-z0-9]+', '-', nk(nach(x0)))}-{k}-{tt}", "pid": r.get("id", ""), "zeit": x0["zeit"],
         "spielerin": x0["spielerin"], "verein": x0["verein"], "nr": "", "pos": r.get("position", ""),
         "tags": ["AUFSTELLUNG"] + (["POKAL"] if pokal else []), "status": "fraglich", "headline": head, "text": text,
         "kickbase": ("Ein Ausfall auch am nächsten Ligaspieltag ist möglich. Bis eine Quelle den Grund nennt, führen wir sie als fraglich"
                      if len(rel) == 1 else "Ein Ausfall auch am nächsten Ligaspieltag ist möglich. Bis eine Quelle den Grund nennt, führen wir sie alle als fraglich")
                     + " und stufen sie in der Prognose herunter.",
         "quellen": [{"name": quelle, "url": x0["quelle"]}], "quelle_live": True}
    if len(head) > 46:
        m["kurz"] = f"{nach(x0)} nicht im Kader" if len(rel) == 1 else head.split(" gegen ")[0]
    return m


def weiterhin(m, news, spielplan):
    """Bekannte Ausfälle als Schlusssatz der fehlt-Meldung (Finn 06.11.2026, Bühl bei Proost): Stammspielerinnen, die im letzten
    Ligaspiel dabei waren und schon mit Status (verletzt, gesperrt, fraglich) gemeldet sind. Keine eigene Meldung, nur dieser Satz."""
    tt = m["id"].rsplit("-", 1)[-1]
    auf = next((y.get("aufstellung") for y in news["meldungen"]
                if y["id"] == f"aufstellung-{AB.KURZ[m['verein']].lower()}-{tt}" and y.get("aufstellung")), None)
    if not auf:
        return None
    namen = []
    for f in auf.get("fehlt", []):
        if f.get("f") != "raus" or not f.get("i"):
            continue
        x = {"verein": m["verein"], "n": f["n"], "zeit": m["zeit"]}
        if not relevant(spielplan, x)[0]:
            continue
        grund = None
        for y in sorted(news["meldungen"], key=lambda y: y["zeit"], reverse=True):
            if y.get("verein") == m["verein"] and nk(y.get("spielerin", "")).endswith(nk(f["n"])) and " wegen " in y.get("headline", ""):
                grund = y["headline"].split(" wegen ", 1)[1].strip(" .")
                break
        grund = grund or {"verletzt": "verletzt", "gesperrt": "gesperrt", "fraglich": "angeschlagen oder geschont"}.get(f["i"], f["i"])
        namen.append(f"{f['n']} ({grund})")
    if not namen:
        return None
    if len(namen) == 1:
        return f"Wie angekündigt fehlt außerdem {namen[0]}."
    return f"Wie angekündigt fehlen außerdem {', '.join(namen[:-1])} und {namen[-1]}."


def fehlt_meldungen(a, pn, pl, news, live, spielplan):
    """Eine Meldung je Verein und Spiel, Aufmacher nur mit Stammspielerin; Ergänzungsspielerinnen stehen im Text."""
    ids = {m["id"] for m in news["meldungen"]} | set(live.get("entfernt", []))
    gruppen = {}
    for x in live.get("ableitungen", []):
        if x.get("spielerin") and x["verein"] in AB.KURZ:
            gruppen.setdefault((x["verein"], x["zeit"][:10], x["gegner"]), []).append(x)
    neu, ersetzt = [], []
    for gr in gruppen.values():
        m = fehlt_meldung_gruppe(gr, spielplan)
        if not m:
            continue
        w = weiterhin(m, news, spielplan)
        if w:
            m["text"].append(w)
        # Zeit = Veröffentlichung der Aufstellung, nicht der Anstoß (Finn 07.11.2026, Fudalla stand um 14:00 statt 12:50)
        tt = m["id"].rsplit("-", 1)[-1]
        au = next((y for y in news["meldungen"] if y.get("verein") == m["verein"] and y["id"].startswith("aufstellung-")
                   and y["id"].endswith("-" + tt) and not y.get("platzhalter") and y.get("aufstellung")), None)
        if au and au["zeit"] < m["zeit"]:
            m["zeit"] = au["zeit"]
        alt = next((y for y in news["meldungen"] if y["id"] == m["id"]), None)
        if alt is None and m["id"] not in ids:
            neu.append(m); ids.add(m["id"])
        elif alt is not None and alt.get("quelle_live") and not alt.get("zusammen") and (alt["headline"] != m["headline"] or alt["text"] != m["text"] or alt["zeit"] != m["zeit"]) \
                and alt["zeit"][:10] >= (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d"):
            # nur frische Meldungen nachziehen: ältere stehen nicht mehr in aufstellungen_live.json, der Spiegel setzt sie
            # zurück, das gab stündlich ein Hin und Her (06.11.2026: fehlt-reimann/bender/altenburg vom 01.11.)
            ersetzt.append(m)
    for m in ersetzt:
        news["meldungen"] = [m if y["id"] == m["id"] else y for y in news["meldungen"]]
        live["meldungen"] = [m if y["id"] == m["id"] else y for y in live["meldungen"]]
    if neu or ersetzt:
        news["meldungen"] = neu + news["meldungen"]
        live["meldungen"] = neu + live["meldungen"]
        print(f"fehlt-Meldungen: {[m['headline'] for m in neu + ersetzt]}")
        speichern(a, pn, pl, news, live, "Aufstellungen live: nicht im Kader " + ", ".join(m["id"] for m in neu + ersetzt))


def punkt(a, pn, pl, news, live, spielplan):
    """Auf den Punkt aktualisieren (tools/punkt_update.py): Updates, Wackelkandidaten, Uhrzeit im Titel."""
    try:
        if PU.anwenden(news, live, spielplan, a.repo):
            speichern(a, pn, pl, news, live, "Aufstellungen live: Auf den Punkt aktualisiert", extra=["tools/punkt_stand.json"])
    except Exception as e:
        print(f"WARN punkt: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--laufzeit", type=int, default=LAUFZEIT)
    ap.add_argument("--push", action="store_true", help="nach jedem Fund sofort committen und pushen")
    a = ap.parse_args()
    pn, pl, ps = (os.path.join(a.repo, x) for x in ("news.json", "tools/aufstellungen_live.json", "spielplan.json"))
    news = json.load(open(pn, encoding="utf-8"))
    live = json.load(open(pl, encoding="utf-8")) if os.path.exists(pl) else {"meldungen": []}
    spielplan = json.load(open(ps, encoding="utf-8"))
    kader = list(csv.DictReader(open(os.path.join(a.repo, "tools/kader.csv"), encoding="utf-8")))
    KADER[:] = kader
    F.setze_kader_slugs(F.lade_kader(os.path.join(a.repo, "tools/kader.csv")))
    geaendert = False

    # Selbstheilung
    jetzt = datetime.now(TZ)
    grenze = (jetzt - timedelta(days=1)).strftime("%Y-%m-%d")
    live["meldungen"] = [m for m in live["meldungen"] if m["zeit"][:10] >= grenze
                         or (m.get("typ") == "punkt" and (m.get("lebt_bis") or m.get("pin_bis", "")) >= jetzt.strftime("%Y-%m-%dT%H:%M"))]  # Auf den Punkt lebt bis zum letzten Anpfiff
    entfernt = set(live.setdefault("entfernt", []))
    vorher = len(news["meldungen"])
    news["meldungen"] = [m for m in news["meldungen"] if m["id"] not in entfernt]
    if len(news["meldungen"]) != vorher:
        print("Platzhalter entfernt (wieder aufgetaucht)")
        speichern(a, pn, pl, news, live, "Aufstellungen live: alte Platzhalter entfernt")
    ids = {m["id"] for m in news["meldungen"]}
    fehlend = [m for m in live["meldungen"] if m["id"] not in ids]
    lv = {m["id"]: m for m in live["meldungen"]}
    anders = [i for i, m in enumerate(news["meldungen"]) if m["id"] in lv and m != lv[m["id"]]]
    for i in anders:  # Live-Fassung gewinnt (etwa nachgetragene Bank)
        news["meldungen"][i] = lv[news["meldungen"][i]["id"]]
    if anders and not fehlend:
        print(f"Live-Fassung wiederhergestellt: {len(anders)}")
        speichern(a, pn, pl, news, live, "Aufstellungen live: Live-Fassung wiederhergestellt")
    if fehlend:
        news["meldungen"] = fehlend + news["meldungen"]
        geaendert = True
        print(f"wieder eingefügt: {[m['id'] for m in fehlend]}")
        speichern(a, pn, pl, news, live, "Aufstellungen live: wieder eingefügt")

    if std_zusammen(news, live):
        speichern(a, pn, pl, news, live, "Aufstellungen live: Standards in fehlt-Meldung zusammengeführt")
    bank_nachtragen(a, pn, pl, news, live, spielplan, kader, grenze)
    fehlt_meldungen(a, pn, pl, news, live, spielplan)
    weiter_main(a, pn, pl, news, live, spielplan, kader, geaendert)


def bank_nachtragen(a, pn, pl, news, live, spielplan, kader, grenze):
    """Bank nachtragen (Meldungen mit bank_offen von heute und gestern): Pokal nach Abpfiff, Liga sobald Sportschau oder DFB sie zeigen."""
    for m in news["meldungen"]:
        au = m.get("aufstellung") or {}
        if not au.get("bank_offen") or m["zeit"][:10] < grenze:
            continue
        slug = next((k for k, v in AB.SLUG.items() if v == m["verein"]), None)
        if au.get("wettbewerb") == "Europa Cup":
            url = next((q["url"] for q in m["quellen"] if "dfb.de" in q["url"]), "")
            d = D.aufstellung_url(url)
            if not d or not (d["bank_heim"] or d["bank_gast"]):
                continue
            quelle_name = "DFB-Datencenter"
            heim_ist = D.KENN.get(slug, slug) in D.slugify(d["heim_name"])
            auf = {"heim": slug if heim_ist else "gegner", "gast": "gegner" if heim_ist else slug, "beendet": False,
                   "startelf_heim": d["startelf_heim"], "startelf_gast": d["startelf_gast"],
                   "bank_heim": d["bank_heim"], "bank_gast": d["bank_gast"]}
        else:
            url = next((q["url"] for q in m["quellen"] if "sportschau" in q["url"]), m["quellen"][0]["url"])
            mm = re.search(r"(https://[^ ]+/)(ma\d+/([a-z0-9\-]+)_([a-z0-9\-]+))/aufstellung", url)
            if not mm:
                continue
            try:
                auf = F.lies_aufstellung(mm.group(2), mm.group(1))
            except Exception:
                auf = None
            quelle_name = "Sportschau"
            if not auf or not (auf["bank_heim"] or auf["bank_gast"]):
                d = None
                try:
                    d = D.aufstellung(mm.group(3), mm.group(4), au.get("wettbewerb"))
                except Exception:
                    pass
                if d and (d["bank_heim"] or d["bank_gast"]):
                    auf = {"heim": mm.group(3), "gast": mm.group(4), "beendet": False, "startelf_heim": d["startelf_heim"],
                           "startelf_gast": d["startelf_gast"], "bank_heim": d["bank_heim"], "bank_gast": d["bank_gast"]}
                    quelle_name = "DFB-Datencenter"
                    if not any(q["url"] == d["url"] for q in m["quellen"]):
                        m["quellen"].append({"name": "DFB-Datencenter", "url": d["url"]})
                else:
                    continue
        slug = next((k for k, v in AB.SLUG.items() if v == m["verein"]), None)
        seite = "heim" if slug == auf["heim"] else "gast"
        verein = m["verein"]
        alt_l = letzte_liga(spielplan, verein, m["zeit"]) or {"start": [], "bank": []}
        auf[f"startelf_{seite}"] = vereinheitliche(auf[f"startelf_{seite}"], verein, alt_l)
        bank = auf[f"bank_{seite}"] = vereinheitliche(auf[f"bank_{seite}"], verein, alt_l)
        im = {nk(x) for x in auf[f"startelf_{seite}"] + bank}
        alt_s = {nk(x) for x in alt_l["start"]}
        au["bank"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader), **({"f": "raus"} if nk(n) in alt_s else {}))
                      for n in bank]
        inf = {nk(k): v for k, v in AB.infos(verein, [], news["meldungen"]).items()}
        au["fehlt"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader), f="raus",
                            war="Startelf" if n in alt_l["start"] else "Bank", **({"i": inf[nk(n)]} if nk(n) in inf else {}))
                       for n in alt_l["start"] + alt_l["bank"] if nk(n) not in im]
        au.pop("bank_offen")
        au.pop("nicht_startelf", None)
        m["text"] = [x.replace(" Die Bank zeigt die Sportschau im Pokal erst nach Abpfiff.", "") for x in m["text"] if "erst nach Abpfiff" not in x or "Nicht mehr in der Startelf" in x]
        m["text"] = [y for y in (x.replace(" Die Bank folgt, sobald sie veröffentlicht ist.", "").replace("Die Bank folgt, sobald sie veröffentlicht ist.", "").strip()
                                 for x in m["text"]) if y]
        abl = ableiten(verein, auf[f"startelf_{seite}"], bank, m["zeit"], au.get("gegner", ""), au.get("wettbewerb"), news["meldungen"], spielplan,
                       next((q["url"] for q in m["quellen"] if q["name"] == quelle_name), url))
        if abl:
            m["text"].append(f"Nicht im Spieltagskader (laut {quelle_name}), obwohl im letzten Ligaspiel dabei: " + ", ".join(x["n"] for x in abl)
                             + ". Einen Grund nennt bisher keine Quelle.")
            for x in abl:
                if not any(y["n"] == x["n"] and y["verein"] == x["verein"] and y["zeit"] == x["zeit"] for y in live.setdefault("ableitungen", [])):
                    live["ableitungen"].append(x)
        for lm in live["meldungen"]:
            if lm["id"] == m["id"]:
                lm.update(m)
        if m["id"] not in {x["id"] for x in live["meldungen"]}:
            live["meldungen"].insert(0, m)
        print(f"Bank nachgetragen: {m['id']}")
        speichern(a, pn, pl, news, live, "Aufstellungen live: Bank nachgetragen " + m["id"])


def weiter_main(a, pn, pl, news, live, spielplan, kader, geaendert):

    # Comeback- und Erstmals-Meldungen (Finn 06.11.2026), auch für die Note von API-Football am Folgetag
    try:
        pa = os.path.join(a.repo, "apifootball.json")
        cb = CB.anwenden(news, live, spielplan, json.load(open(pa, encoding="utf-8")) if os.path.exists(pa) else {}, kader)
    except Exception as e:
        print(f"WARN comeback: {e}", file=sys.stderr)
        cb = []
    if cb:
        speichern(a, pn, pl, news, live, "Aufstellungen live: Comeback " + ", ".join(cb))
    punkt(a, pn, pl, news, live, spielplan)

    # Platzhalter ohne Aufstellung 15 Minuten nach Anpfiff entfernen
    jetzt_s = (datetime.now(TZ) - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    jetzt_ec = (datetime.now(TZ) - timedelta(minutes=EC_NACHLAUF)).strftime("%Y-%m-%dT%H:%M")
    alt_ph = [m["id"] for m in news["meldungen"] if m.get("platzhalter")
              and m.get("anstoss", "9") < (jetzt_ec if m.get("wettbewerb") == "Europa Cup" else jetzt_s)]
    if alt_ph:
        news["meldungen"] = [m for m in news["meldungen"] if m["id"] not in alt_ph]
        live["meldungen"] = [m for m in live["meldungen"] if m["id"] not in alt_ph]
        live["entfernt"] = list(dict.fromkeys(live["entfernt"] + alt_ph))
        speichern(a, pn, pl, news, live, "Aufstellungen live: Platzhalter nach Anpfiff entfernt")

    ende = time.time() + a.laufzeit * 60
    while True:
        jetzt = datetime.now(TZ)
        ids = {m["id"] for m in news["meldungen"]}
        offen = 0
        SPAETER.clear()
        for wb, basis, ma, an in spiele_heute(jetzt):
            pre = PRE.get(wb, "")
            h, g = ma.split("/")[1].split("_")
            soll = [f"aufstellung-{pre}{AB.KURZ[AB.SLUG[s]]}-{an.strftime('%d%m')}" for s in (h, g) if s in AB.SLUG and AB.SLUG[s] in AB.KURZ]
            if all(i in ids for i in soll):
                continue
            if wb == "Europa Cup":
                auf = europa_auf(ma, h, g)
            else:
                try:
                    auf = F.lies_aufstellung(ma, basis)
                except Exception as e:
                    print(f"WARN {ma}: {e}", file=sys.stderr)
                    auf = None
                if not auf or not (auf["bank_heim"] and auf["bank_gast"]):
                    auf = ergaenze_dfb(auf, h, g, wb)
            if not auf or auf["beendet"]:
                offen += 1
                pid_ = "aufstellung-folgt-" + ma.split("/")[0]
                if not auf and pid_ not in ids and pid_ not in live["entfernt"] and jetzt < an:
                    ph = platzhalter(pid_, wb, basis, ma, an, h, g, jetzt, spielplan)
                    news["meldungen"].insert(0, ph)
                    live["meldungen"].insert(0, ph)
                    ids.add(pid_)
                    print(f"Platzhalter: {ph['headline']}")
                    speichern(a, pn, pl, news, live, "Aufstellungen live: Platzhalter " + pid_)
                continue
            neu = [m for m in baue(wb, basis, ma, an, auf, kader, news["meldungen"], spielplan, jetzt.strftime("%Y-%m-%dT%H:%M"))
                   if m["id"] not in ids]
            if neu:
                pid_ = "aufstellung-folgt-" + ma.split("/")[0]
                news["meldungen"] = neu + [m for m in news["meldungen"] if m["id"] != pid_]
                live["meldungen"] = neu + [m for m in live["meldungen"] if m["id"] != pid_]
                if pid_ not in live["entfernt"]:
                    live["entfernt"].append(pid_)
                for m in neu:
                    for x in m.get("ableitungen", []):
                        if not any(y["n"] == x["n"] and y["verein"] == x["verein"] and y["zeit"] == x["zeit"] for y in live.setdefault("ableitungen", [])):
                            live["ableitungen"].append(x)
                geaendert = True
                print(f"neu: {[m['headline'] for m in neu]}")
                speichern(a, pn, pl, news, live, "Aufstellungen live: " + ", ".join(m["id"] for m in neu))
                try:
                    pa = os.path.join(a.repo, "apifootball.json")
                    cb = CB.anwenden(news, live, spielplan, json.load(open(pa, encoding="utf-8")) if os.path.exists(pa) else {}, kader)
                except Exception as e:
                    print(f"WARN comeback: {e}", file=sys.stderr)
                    cb = []
                if cb:
                    speichern(a, pn, pl, news, live, "Aufstellungen live: Comeback " + ", ".join(cb))
                punkt(a, pn, pl, news, live, spielplan)
        bank_nachtragen(a, pn, pl, news, live, spielplan, kader, (jetzt - timedelta(days=1)).strftime("%Y-%m-%d"))
        fehlt_meldungen(a, pn, pl, news, live, spielplan)
        try:
            SPAETER.extend(europa_berichte(a, pn, pl, news, live, spielplan, kader))
        except Exception as e:
            print(f"WARN Europa-Bericht: {e}", file=sys.stderr)
        if (not offen and not SPAETER) or time.time() + 60 > ende:
            break
        time.sleep(60)
    # Kette: solange heute noch ein Spiel mit Bundesliga-Verein ansteht oder läuft, startet die Action sich neu
    weiter = bool(offen or SPAETER)
    if os.environ.get("GITHUB_OUTPUT"):
        open(os.environ["GITHUB_OUTPUT"], "a").write(f"weiter={int(weiter)}\n")
    print(f"weiter={int(weiter)}")
    print(f"geaendert={int(geaendert)}")


if __name__ == "__main__":
    main()
