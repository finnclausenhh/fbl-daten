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

TZ = ZoneInfo("Europe/Berlin")
BASIS = "https://www.sportschau.de/live-und-ergebnisse/fussball/"
WETTBEWERBE = [("deutschland-bundesliga-frauen", None), ("deutschland-dfb-pokal-frauen", "DFB-Pokal"),
               ("uefa-champions-league-frauen", "Champions League")]
VORLAUF = 80
LAUFZEIT = 13


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


def ableiten(verein, start, bank, zeit, gegner, wb, news, spielplan, quelle):
    """Fehlt ohne bekannten Grund (Finn 01.11.2026): stand im letzten Ligaspiel im Kader, jetzt weder Startelf noch Bank.
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
    wtext = {"DFB-Pokal": "im DFB-Pokal", "Champions League": "in der Champions League"}.get(wb, "in der Liga")
    return {"id": pid_, "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"), "spielerin": "Spielansetzung", "verein": verein, "nr": "",
            "pos": "Spielansetzung", "tags": ["AUFSTELLUNG"] + (["POKAL"] if wb == "DFB-Pokal" else ["EUROPAPOKAL"] if wb else []),
            "headline": f"Aufstellung {name(h)} gegen {name(g)} folgt", "kurz": f"Aufstellung folgt, Anpfiff {an.strftime('%H:%M')}",
            "text": [f"Anpfiff {wtext} ist um {an.strftime('%H:%M')} Uhr. " + ("Die offizielle Aufstellung kommt meist rund 60 Minuten "
                     "vorher" if an - jetzt > timedelta(minutes=60) else "Die offizielle Aufstellung sollte in Kürze kommen")
                     + ", wir ergänzen sie hier automatisch, sobald sie veröffentlicht ist.",
                     "Bis dahin steht unsere Prognose im Spielplan bei der Partie." if partie else
                     "Für Pokal- und Europapokalspiele gibt es keine Prognose, die Aufstellung kommt hier automatisch."],
            "kickbase": "", "quellen": [{"name": "Sportschau", "url": basis + ma + "/aufstellung"}],
            "platzhalter": True, "anstoss": an.strftime("%Y-%m-%dT%H:%M"), **({"partie_id": partie} if partie else {})}


def baue(wb, basis, ma, an, a, kader, news, spielplan, zeit):
    url = basis + ma + "/aufstellung"
    gr = {} if a.get("nur_dfb") else AB.grafik(url)
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
        vgl = F.vergleich(alt, a[st], a[bk])
        t = AB.team(slug, gs, a[st], a[bk], vgl, kader, news, gr.get(sd))
        if wb:
            t["wettbewerb"] = wb
            if not a[bk]:
                # Sportschau zeigt im Pokal vor Anpfiff keine Bank: niemand als "fehlt" führen, nur im Text nennen
                t["bank"] = []
                t["fehlt"] = []
                t["bank_offen"] = True
                t["nicht_startelf"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader))
                                       for n in (vgl or {}).get("nicht_mehr_in_startelf", [])]
        pre = "pokal-" if wb == "DFB-Pokal" else "cl-" if wb else ""
        text = []
        if t.get("bank_offen"):
            raus = (vgl or {}).get("nicht_mehr_in_startelf", [])
            text = [("Nicht mehr in der Startelf gegenüber dem letzten Ligaspiel: " + ", ".join(raus) + ". " if raus else "")
                    + "Die Bank zeigt die Sportschau im Pokal erst nach Abpfiff. Rotation im Pokal heißt nicht Verletzung, "
                    "oft wird nur die Belastung gesteuert."]
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
                    + ", ".join(x["n"] for x in abl) + ". Einen Grund nennt bisher keine Quelle"
                    + (", im Pokal kann es auch Belastungssteuerung sein." if wb else ".")]
                out[-1]["ableitungen"] = abl
    return out


def speichern(a, pn, pl, news, live, nachricht):
    news["stand"] = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
    json.dump(news, open(pn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(live, open(pl, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not a.push:
        return
    g = ["git", "-C", a.repo]
    st = {"letzter_lauf": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M"), "lauf": "Aufstellungen live", "news_neu": 1, "spielplan_geaendert": False}
    json.dump(st, open(os.path.join(a.repo, "status.json"), "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(g + ["add", "news.json", "tools/aufstellungen_live.json", "status.json"], check=True)
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
        news["stand"] = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
        json.dump(news, open(pn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(live, open(pl, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        subprocess.run(g + ["add", "news.json", "tools/aufstellungen_live.json"], check=True)
        subprocess.run(g + ["-c", "user.name=WOSOINSIDER", "-c", "user.email=finnclausenhh@users.noreply.github.com",
                            "commit", "-qm", nachricht], check=True)
        time.sleep(3)
    print("WARN push fehlgeschlagen", file=sys.stderr)
    sys.exit(1)


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
    live["meldungen"] = [m for m in live["meldungen"] if m["zeit"][:10] >= grenze]
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

    # Pokal: Bank nach Abpfiff nachtragen (Meldungen mit bank_offen von heute und gestern)
    for m in news["meldungen"]:
        au = m.get("aufstellung") or {}
        if not au.get("bank_offen") or m["zeit"][:10] < grenze:
            continue
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
        bank = auf[f"bank_{seite}"]
        verein = m["verein"]
        im = {nk(x) for x in auf[f"startelf_{seite}"] + bank}
        alt_l = letzte_liga(spielplan, verein, m["zeit"]) or {"start": [], "bank": []}
        alt_s = {nk(x) for x in alt_l["start"]}
        au["bank"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader), **({"f": "raus"} if nk(n) in alt_s else {}))
                      for n in bank]
        au["fehlt"] = [dict(n=n, p=AB.pos_von(n, verein, kader), pid=AB.pid_von(n, verein, kader), f="raus")
                       for n in alt_l["start"] + alt_l["bank"] if nk(n) not in im]
        au.pop("bank_offen")
        au.pop("nicht_startelf", None)
        m["text"] = [x.replace(" Die Bank zeigt die Sportschau im Pokal erst nach Abpfiff.", "") for x in m["text"] if "erst nach Abpfiff" not in x or "Nicht mehr in der Startelf" in x]
        abl = ableiten(verein, auf[f"startelf_{seite}"], bank, m["zeit"], au.get("gegner", ""), au.get("wettbewerb"), news["meldungen"], spielplan,
                       next((q["url"] for q in m["quellen"] if q["name"] == quelle_name), url))
        if abl:
            m["text"].append(f"Nicht im Spieltagskader (laut {quelle_name}), obwohl im letzten Ligaspiel dabei: " + ", ".join(x["n"] for x in abl)
                             + ". Einen Grund nennt bisher keine Quelle, im Pokal kann es auch Belastungssteuerung sein.")
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

    # Platzhalter ohne Aufstellung 15 Minuten nach Anpfiff entfernen
    jetzt_s = (datetime.now(TZ) - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    alt_ph = [m["id"] for m in news["meldungen"] if m.get("platzhalter") and m.get("anstoss", "9") < jetzt_s]
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
            pre = "pokal-" if wb == "DFB-Pokal" else "cl-" if wb else ""
            h, g = ma.split("/")[1].split("_")
            soll = [f"aufstellung-{pre}{AB.KURZ[AB.SLUG[s]]}-{an.strftime('%d%m')}" for s in (h, g) if s in AB.SLUG and AB.SLUG[s] in AB.KURZ]
            if all(i in ids for i in soll):
                continue
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
