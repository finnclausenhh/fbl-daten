#!/usr/bin/env python3
""""Spieltag N auf den Punkt" lebt bis zum letzten Anpfiff (Finn, 06.11.2026). Ohne Claude.

Die Meldung (typ "punkt", geschrieben vom Lauf nach engine/punkt_auftrag.md) bekommt hier automatisch:
- "updates": Liste [{zeit, k, text}] (neueste zuerst):
  * Prognose-Änderungen gegen den Stand bei Erscheinen ("Bender startet statt Tomasiak"), mit Anlass aus einer neuen
    Meldung zu einer der beiden Spielerinnen, falls vorhanden (dann zählt deren Uhrzeit);
  * neue Meldungen mit Personalbezug (Verletzung, Rückkehr, Sperre, nicht im Kader, TOP) zu Teams des Spieltags,
    solange ihr Spiel noch nicht angepfiffen war;
  * "Offizielle Aufstellung da" je Partie.
- Hinweis "update" an Einträgen in Sicher/Finger weg/Tipp/Achtung, wenn es zu der Spielerin später eine Meldung gab.
- "wackel": Wackelkandidaten aus der aktuellen Prognose (Feld alternativ: "Bender oder Platner") für Spiele ohne
  offizielle Aufstellung; verletzte oder gesperrte Spielerinnen fallen raus.
- headline "Spieltag N auf den Punkt · Update HH:MM" (Uhrzeit des neuesten Updates), pin_bis = letzter Anpfiff.
Stand der Prognose bei Erscheinen und erste Sichtung je Änderung: tools/punkt_stand.json.
Die Meldung steht auch in tools/aufstellungen_live.json, damit "Aufstellungen schützen" sie nach einem Spiegel einsetzt.

Als Modul: anwenden(news, live, spielplan, repo) -> True bei Änderung. Test: python3 tools/punkt_update.py --repo .
"""
import argparse, json, os, re, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbl_fetch as F  # noqa: E402
import aufstellung_bau as AB  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
RELEVANT = {"VERLETZUNG", "RÜCKKEHR", "SPERRE", "AUFSTELLUNG", "TOP", "ROTATION"}
KNAME = {"Eintracht Frankfurt": "Frankfurt", "VfL Wolfsburg": "Wolfsburg", "Werder Bremen": "Werder", "Bayer Leverkusen": "Leverkusen",
         "Hamburger SV": "HSV", "SC Freiburg": "Freiburg", "1. FC Nürnberg": "Nürnberg", "Union Berlin": "Union", "TSG Hoffenheim": "Hoffenheim",
         "Mainz 05": "Mainz", "VfB Stuttgart": "Stuttgart", "1. FC Köln": "Köln", "RB Leipzig": "Leipzig", "FC Bayern": "Bayern"}


def nk(n):
    return F.norm(str(n)).split()[-1] if str(n).strip() else ""


def partien(sp, md):
    for t in sp.get("spieltage", []):
        if t.get("nr") == md:
            return [p for p in t.get("partien", []) if p.get("anstoss") and "T00:00" not in p["anstoss"]]
    return []


def startelf(p, seite):
    a = p.get(seite + "_aufstellung") or {}
    return a.get("typ"), [s.get("voll") or s["n"] for s in a.get("startelf", [])], a


def anwenden(news, live, sp, repo, jetzt=None):
    jetzt = jetzt or datetime.now(TZ)
    js = jetzt.strftime("%Y-%m-%dT%H:%M")
    pfad = os.path.join(repo, "tools", "punkt_stand.json")
    stand = json.load(open(pfad, encoding="utf-8")) if os.path.exists(pfad) else {}
    geaendert = False
    for m in [x for x in news["meldungen"] if x.get("typ") == "punkt" and x.get("md") is not None]:
        md = int(m["md"])
        ps = partien(sp, md)
        if not ps:
            continue
        letzter = max(p["anstoss"] for p in ps)
        if letzter < (jetzt.replace(hour=0, minute=0)).strftime("%Y-%m-%dT%H:%M")[:10]:
            continue
        st = stand.setdefault(m["id"], {"basis": {}, "gesehen": {}})
        # Stand bei Erscheinen festhalten (einmal, nur für Spiele ohne offizielle Aufstellung)
        if not st["basis"]:
            for p in ps:
                for seite in ("heim", "gast"):
                    typ, elf, _ = startelf(p, seite)
                    if typ == "prognose":
                        st["basis"][f"{p['id']}|{seite}"] = elf
            st["basis_zeit"] = js
        ab = m["zeit"]
        teams = {p[s]: p for p in ps for s in ("heim", "gast")}
        neu_m = sorted([x for x in news["meldungen"] if x.get("verein") in teams and x["zeit"] > ab and x.get("typ") != "punkt"
                        and not x["id"].startswith(("aufstellung-", "punkt-")) and RELEVANT & set(x.get("tags", []))
                        and x["zeit"] <= teams[x["verein"]]["anstoss"]], key=lambda x: x["zeit"])
        von = (datetime.fromisoformat(ab) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")  # Anlass darf auch kurz vor Erscheinen liegen
        vorher_m = sorted([x for x in news["meldungen"] if x.get("verein") in teams and x["zeit"] > von and x.get("typ") != "punkt"
                           and RELEVANT & set(x.get("tags", []))], key=lambda x: x["zeit"])
        ups, verbraucht = [], set()
        # 1. Prognose-Änderungen
        for key, alt in st["basis"].items():
            pid, seite = key.split("|")
            p = next((q for q in ps if q["id"] == pid), None)
            if not p:
                continue
            typ, elf, _ = startelf(p, seite)
            if typ != "prognose":
                continue
            rein = [n for n in elf if nk(n) not in {nk(x) for x in alt}]
            raus = [n for n in alt if nk(n) not in {nk(x) for x in elf}]
            for i in range(max(len(rein), len(raus))):
                r, a = (rein[i] if i < len(rein) else None), (raus[i] if i < len(raus) else None)
                gk = f"{key}|{nk(r or '')}|{nk(a or '')}"
                anlass = next((x for x in reversed(vorher_m) if nk(x.get("spielerin", "")) in {nk(r or "-"), nk(a or "-")} and x.get("verein") == p[seite]), None)
                zeit = st["gesehen"].setdefault(gk, max(anlass["zeit"], ab) if anlass else js)
                nach = lambda n: n.split()[-1]
                txt = (f"{nach(r)} startet statt {nach(a)}" if r and a else f"{nach(r)} neu in der Startelf" if r else f"{nach(a)} nicht mehr in der Startelf")
                if anlass:
                    txt += f" ({anlass['kurz'] if anlass.get('kurz') else anlass['headline']})"
                    verbraucht.add(anlass["id"])
                ups.append({"zeit": zeit, "k": p.get(seite + "_k"), "text": txt, "art": "prognose"})
        # 2. Neue Meldungen
        for x in neu_m:
            if x["id"] in verbraucht:
                continue
            p = teams[x["verein"]]
            ups.append({"zeit": x["zeit"], "k": p["heim_k"] if p["heim"] == x["verein"] else p["gast_k"], "text": x.get("kurz") or x["headline"],
                        "art": "meldung", "id": x["id"]})
        # 3. Offizielle Aufstellungen
        for p in ps:
            if all((p.get(s + "_aufstellung") or {}).get("typ") == "offiziell" for s in ("heim", "gast")):
                am = next((x for x in news["meldungen"] if x["id"].startswith(f"aufstellung-{(p.get('heim_k') or '').lower()}-")
                           and x["zeit"][:10] == p["anstoss"][:10]), None)
                zeit = st["gesehen"].setdefault(f"auf|{p['id']}", am["zeit"] if am else js)
                ups.append({"zeit": zeit, "k": p.get("heim_k"), "text": f"Offizielle Aufstellung: {KNAME.get(p['heim'], p['heim'])} gegen {KNAME.get(p['gast'], p['gast'])}",
                            "art": "aufstellung", "partie": p["id"]})
        ups.sort(key=lambda u: u["zeit"], reverse=True)
        # 4. Hinweise an den Einträgen
        sektionen = {}
        for sek in ("sicher", "finger_weg", "tipp", "achtung"):
            l = []
            for e in m.get(sek) or []:
                e = {k: v for k, v in e.items() if k != "update"}
                spaeter = [x for x in neu_m if nk(x.get("spielerin", "")) == nk(e["n"]) and (x.get("verein") and AB.KURZ.get(x["verein"], "").upper() == e.get("k"))]
                if spaeter:
                    e["update"] = {"zeit": spaeter[-1]["zeit"], "text": spaeter[-1].get("kurz") or spaeter[-1]["headline"]}
                l.append(e)
            sektionen[sek] = l
        # 5. Wackelkandidaten
        inf = {}
        for v in teams:
            inf.update({(v, nk(k)): s for k, s in AB.infos(v, [], news["meldungen"]).items()})
        wackel, weg = [], {(e.get("k"), nk(e["n"])) for e in m.get("finger_weg") or []}  # Finger weg = fällt aus, kein Wackelkandidat
        for p in sorted(ps, key=lambda q: q["anstoss"]):
            if p["anstoss"] <= js:
                continue
            for seite in ("heim", "gast"):
                typ, elf, a = startelf(p, seite)
                if typ != "prognose":
                    continue
                for alt in (a.get("alternativ") or [])[:2]:
                    x, y = alt.get("statt"), alt.get("fuer")
                    if (p.get(seite + "_k"), nk(x)) in weg or (p.get(seite + "_k"), nk(y)) in weg:
                        continue
                    if not x or not y or (p[seite], nk(x)) in inf and inf[(p[seite], nk(x))] in ("verletzt", "gesperrt") \
                            or (p[seite], nk(y)) in inf and inf[(p[seite], nk(y))] in ("verletzt", "gesperrt"):
                        continue
                    wackel.append({"k": p.get(seite + "_k"), "p": alt.get("p", ""), "a": x, "b": y, "anstoss": p["anstoss"]})
        titel = re.sub(r"\s*·\s*Update \d\d:\d\d$", "", m.get("titel_basis") or m["headline"])
        head = titel + (f" · Update {ups[0]['zeit'][11:16]}" if ups else "")
        neu = dict(m, titel_basis=titel, headline=head, updates=ups, wackel=wackel, pin_bis=letzter, **sektionen)
        if ups:
            neu["aktualisiert"] = ups[0]["zeit"]
        if neu != m:
            news["meldungen"] = [neu if x["id"] == m["id"] else x for x in news["meldungen"]]
            live["meldungen"] = [neu] + [x for x in live.get("meldungen", []) if x["id"] != m["id"]]
            geaendert = True
            print(f"Punkt: {head} ({len(ups)} Updates, {len(wackel)} Wackelkandidaten)")
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    json.dump(stand, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return geaendert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--schreiben", action="store_true")
    a = ap.parse_args()
    lade = lambda f, d=None: json.load(open(os.path.join(a.repo, f), encoding="utf-8")) if os.path.exists(os.path.join(a.repo, f)) else d
    news, sp, live = lade("news.json"), lade("spielplan.json"), lade("tools/aufstellungen_live.json", {"meldungen": []})
    if anwenden(news, live, sp, a.repo):
        m = next(x for x in news["meldungen"] if x.get("typ") == "punkt" and x.get("updates") is not None)
        print(json.dumps({k: m[k] for k in ("headline", "updates", "wackel", "pin_bis")}, ensure_ascii=False, indent=1))
        print(json.dumps([(e["n"], e.get("update")) for s in ("sicher", "finger_weg", "tipp", "achtung") for e in m[s] if e.get("update")], ensure_ascii=False))
        if a.schreiben:
            json.dump(news, open(os.path.join(a.repo, "news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            json.dump(live, open(os.path.join(a.repo, "tools/aufstellungen_live.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
