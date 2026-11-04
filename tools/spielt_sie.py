#!/usr/bin/env python3
"""Tippspiel "Spielt sie?": legt die Fragen eines Spieltags einmal fest (Finn 04.11.2026).

Bisher hat der Ticker die Fragen im Browser aus der aktuellen Prognose gerechnet. Ändert sich die Prognose,
ändern sich die Fragen, und abgegebene Tipps passen nicht mehr. Dieses Skript schreibt spielt_sie.json
für den aktuellen Spieltag genau einmal. Steht für den Spieltag schon eine Runde, bleibt sie unverändert.

Regeln (wie zuvor im Browser, claude/wosoinsider-gamification.md):
- Abgabe bis 90 Minuten vor dem ersten Anpfiff des Spieltags.
- Zuerst bis zu 2 bestehende Startelf-Umfragen des Spieltags (mit Infos und Einschätzung).
- Dann Startelf-Fragen aus der Prognose: nur Erwartet oder Unsicher, Einsatzwert 30 bis 94 %, Gewicht
  (Tore x2 + Vorlagen, Torhüterin +6) mindestens 3, Anlass nötig (zuletzt Bank oder nur eingewechselt, auch
  Pokal/Europapokal; Einschätzung der Redaktion; weniger als 3 Starts in den letzten 3 Ligaspielen), Foto nötig.
- Höchstens 2 Fragen je Verein, zuerst 2 zu nicht einsehbaren Spielen, insgesamt höchstens 5, sortiert nach Anstoß.
- Festgeschrieben wird frühestens 6 Tage vor dem ersten Anpfiff und nur vor dem Abgabeschluss.

Aufruf: python3 tools/spielt_sie.py [--repo .] [--neu]   (--neu erzwingt eine neue Runde, nur von Hand)
"""
import argparse, json, re, unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
SCHLUSS_MIN = 90
STUFE = {"sicher": "Sicher", "erwartet": "Erwartet", "unsicher": "Unsicher", "unwahrscheinlich": "Unwahrscheinlich", "ausgeschlossen": "Ausgeschlossen"}


def norm(s):
    s = str(s or "").replace("ð", "d").replace("ß", "ss").replace("ø", "o").replace("ł", "l")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


nach = lambda n: str(n or "").strip().split()[-1] if str(n or "").strip() else ""
hat_zeit = lambda z: bool(z) and len(z) >= 16 and not z.endswith("T00:00")
dt = lambda z: datetime.fromisoformat(z if len(z) > 10 else z + "T00:00")


def im_wb(wb):
    return "in der Liga" if wb == "Liga" else "in der Champions League" if wb == "Champions League" else "im " + wb


def runde(sp, spn, um, fotos, jetzt):
    t = next((x for x in sp.get("spieltage", []) if x.get("nr") == sp.get("aktuell")), None)
    if not t:
        return None, "kein aktueller Spieltag"
    ps = [p for p in t["partien"] if hat_zeit(p.get("anstoss"))]
    if not ps:
        return None, "keine Anstoßzeiten"
    erst = min(p["anstoss"] for p in ps)
    schluss = dt(erst) - timedelta(minutes=SCHLUSS_MIN)
    if jetzt >= schluss:
        return None, "Abgabeschluss vorbei"
    if jetzt < dt(erst) - timedelta(days=6):
        return None, "noch zu früh (mehr als 6 Tage vor dem ersten Anpfiff)"
    ein = {p["id"] for p in ps if p["anstoss"] == erst}
    alle = spn.get("spielerinnen", [])

    def finde(k, n):
        L = [x for x in alle if x["k"] == k and (norm(nach(x["n"])) == norm(n) or norm(x["n"]) == norm(n))]
        return L[0] if len(L) == 1 else None

    fragen, belegt, pro_v = [], set(), {}
    nimm = lambda k: pro_v.__setitem__(k, pro_v.get(k, 0) + 1)
    frei = lambda k: pro_v.get(k, 0) < 2
    ids = {p["id"] for p in t["partien"]}
    for u in [u for u in um if (u.get("art") or "startelf") == "startelf" and u.get("partie") in ids][:2]:
        p = next(x for x in t["partien"] if x["id"] == u["partie"])
        e = u.get("einschaetzung") or {}
        eo = next((o for o in u.get("optionen", []) if o["id"] == e.get("option")), None)
        for o in u.get("optionen", []):
            if o.get("nachname"): belegt.add(norm(o["nachname"]))
        nimm(u.get("verein"))
        fragen.append({"id": "u-" + u["id"], "art": "TOR" if u.get("position") == "TW" else "WER STARTET", "partie": p["id"], "k": u.get("verein"),
                       "umfrage": u["id"], "einsehbar": p["id"] in ein, "frage": u["frage"],
                       "warum": ("Torhüterinnen punkten bei Kickbase stark. " if u.get("position") == "TW" else "") + " · ".join(f"{o.get('nachname') or o['n']}: {o['info']}" for o in u.get("optionen", []) if o.get("info")),
                       "prognose": f"{STUFE.get(e.get('stufe'), '')}: {eo.get('nachname') or eo['n']}. {e.get('text', '')}".strip() if eo else "",
                       "optionen": [{"id": o["id"], "n": o.get("nachname") or ("Andere" if o["id"] == "andere" else o["n"])} for o in u.get("optionen", [])]})
    kand = []
    for p in t["partien"]:
        for k, a in ((p["heim_k"], p.get("heim_aufstellung")), (p["gast_k"], p.get("gast_aufstellung"))):
            if not a or a.get("typ") != "prognose":
                continue
            for x in (a.get("startelf") or []) + (a.get("bank") or []):
                if x.get("st") not in ("erwartet", "unsicher") or norm(x["n"]) in belegt:
                    continue
                s = finde(k, x["n"])
                if not s:
                    continue
                f = fotos.get(s["n"]) or {}
                if not f.get("portrait") and not f.get("datei"):
                    continue
                w = (s.get("prognose") or {}).get("wert")
                if w is None:
                    m = re.search(r"Einsatzwert (\d+)", x.get("warum") or "")
                    w = int(m.group(1)) if m else 0
                if w >= 95 or w < 30:
                    continue
                tore = sum(len(e.get("tore") or []) for e in s.get("spiele", []))
                vorl = sum(e.get("vorl") or 0 for e in s.get("spiele", []))
                tw = x.get("p") == "TW"
                gew = tore * 2 + vorl + (6 if tw else 0)
                if gew < 3:
                    continue
                ll = (s.get("spiele") or [None])[-1]
                lp = (s.get("pokal") or [None])[-1]
                letzt = [z for z in ([{"d": ll["datum"], "wb": "Liga", "g": ll["gegner"], "art": ll.get("art")}] if ll else []) +
                         ([{"d": lp["datum"], "wb": lp["wb"], "g": lp["gegner"], "art": lp.get("art")}] if lp else [])]
                letzt = max(letzt, key=lambda z: dt(z["d"])) if letzt else None
                einsch = (x.get("warum") or "").split("Einschätzung WOSOINSIDER:")
                einsch = einsch[1].strip() if len(einsch) > 1 else ""
                l3 = (s.get("spiele") or [])[-3:]
                s3 = sum(1 for e in l3 if e.get("art") == "S")
                if letzt and letzt["art"] == "B":
                    anlass = f"Zuletzt {im_wb(letzt['wb'])} gegen {letzt['g']} nur auf der Bank."
                elif letzt and letzt["art"] == "E":
                    anlass = f"Zuletzt {im_wb(letzt['wb'])} gegen {letzt['g']} nur eingewechselt."
                elif einsch:
                    anlass = einsch.rstrip(".") + "."
                elif len(l3) == 3 and s3 < 3:
                    anlass = f"In den letzten 3 Ligaspielen {s3}-mal in der Startelf."
                else:
                    continue
                stz = re.search(r"(\d)/5 Startelf", x.get("warum") or "")
                kand.append({"id": "s-" + s["id"], "art": "STARTELF", "partie": p["id"], "k": k, "sid": s["id"], "einsehbar": p["id"] in ein, "_g": gew,
                             "frage": f"Steht {nach(s['n'])} in der Startelf?",
                             "warum": f"{anlass} " + ("Torhüterinnen punkten bei Kickbase stark." if tw else f"Diese Saison {tore} {'Tor' if tore == 1 else 'Tore'}, {vorl} {'Vorlage' if vorl == 1 else 'Vorlagen'}."),
                             "prognose": f"{STUFE[x['st']]}. {stz.group(1) + ' von 5 zuletzt in der Startelf, ' if stz else ''}Einsatzwert {w} %.",
                             "optionen": [{"id": "ja", "n": "Ja"}, {"id": "nein", "n": "Nein"}]})
    kand.sort(key=lambda q: -q["_g"])

    def pick(q):
        if len(fragen) >= 5 or not frei(q["k"]) or any(f["id"] == q["id"] for f in fragen):
            return
        nimm(q["k"]); fragen.append(q)
    for q in [q for q in kand if not q["einsehbar"]][:2]: pick(q)
    for q in kand: pick(q)
    anst = {p["id"]: p["anstoss"] for p in t["partien"]}
    fragen.sort(key=lambda q: anst.get(q["partie"], ""))
    for q in fragen: q.pop("_g", None)
    return {"md": t["nr"], "erstellt": jetzt.strftime("%Y-%m-%dT%H:%M"), "erst": erst, "schluss": schluss.strftime("%Y-%m-%dT%H:%M"),
            "hinweis": "Fragen festgeschrieben von tools/spielt_sie.py, ändern sich bis zur Wertung nicht.", "fragen": fragen}, "neu"


def loesung(sp, spn, um, runde_):
    """tipp_loesung.json für die Datenbank (supabase/tippspiel.sql): {"md": 9, "loesung": {frage-id: antwort-id}}.
    Startelf-Fragen und Startelf-Umfragen, sobald die offizielle Aufstellung da ist (wie umfrageAufloesung im Ticker)."""
    if not runde_ or not runde_.get("fragen"): return None
    md = runde_["md"]
    t = next((x for x in sp.get("spieltage", []) if x.get("nr") == md), None)
    if not t: return None
    spid = {x["id"]: x for x in spn.get("spielerinnen", [])}
    umid = {u["id"]: u for u in um}
    L = {}
    for q in runde_["fragen"]:
        p = next((x for x in t["partien"] if x["id"] == q["partie"]), None)
        if not p: continue
        seite = "heim" if p["heim_k"] == q["k"] else "gast" if p["gast_k"] == q["k"] else None
        a = p.get(f"{seite}_aufstellung") if seite else None
        if not a or a.get("typ") != "offiziell": continue
        elf = a.get("startelf") or []
        if q.get("sid"):
            s = spid.get(q["sid"])
            if not s: continue
            drin = any(norm(x.get("voll") or "") == norm(s["n"]) or norm(x.get("n")) == norm(nach(s["n"])) for x in elf)
            L[q["id"]] = "ja" if drin else "nein"
        elif q.get("umfrage") and q["umfrage"] in umid:
            u = umid[q["umfrage"]]; O = u.get("optionen", [])
            sx = [x for x in elf if not u.get("position") or x.get("p") == u["position"]]
            tr = [o for o in O if o.get("nachname") and any(o["nachname"] in str(x.get("voll") or x.get("n")) for x in sx)]
            if len(tr) > 1 and any(o["id"] == "beide" for o in O): L[q["id"]] = "beide"
            elif tr: L[q["id"]] = tr[0]["id"]
            else:
                o = next((o for o in O if o["id"] == "keine"), None) or next((o for o in O if not o.get("nachname")), None)
                if o: L[q["id"]] = o["id"]
    return {"md": md, "stand": datetime.now(BERLIN).strftime("%Y-%m-%dT%H:%M"), "loesung": L}


def main():
    a = argparse.ArgumentParser(); a.add_argument("--repo", default="."); a.add_argument("--neu", action="store_true"); a = a.parse_args()
    R = Path(a.repo)
    lade = lambda f, d=None: json.load(open(R / f, encoding="utf-8")) if (R / f).exists() else d
    sp, spn = lade("spielplan.json"), lade("spielerinnen.json")
    um = (lade("umfragen.json", {}) or {}).get("umfragen", [])
    fotos = lade("fotos.json", {})
    alt = lade("spielt_sie.json", {}) or {}
    jetzt = datetime.now(BERLIN).replace(tzinfo=None, second=0, microsecond=0)
    # Auflösung für die Datenbank (tipp_loesung.json), auch für die zuletzt festgeschriebene Runde
    lo = loesung(sp, spn, um, alt)
    if lo is not None:
        vorher = lade("tipp_loesung.json", {}) or {}
        if vorher.get("md") != lo["md"] or vorher.get("loesung") != lo["loesung"]:
            json.dump(lo, open(R / "tipp_loesung.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"Auflösung Runde {lo['md']}: {len(lo['loesung'])} von {len(alt['fragen'])} Fragen")
    if not a.neu and alt.get("md") == sp.get("aktuell") and alt.get("fragen"):
        print(f"Runde {alt['md']} steht schon ({len(alt['fragen'])} Fragen), bleibt unverändert"); return
    r, grund = runde(sp, spn, um, fotos, jetzt)
    if not r:
        print("keine neue Runde:", grund); return
    if not r["fragen"]:
        print("keine Frage erfüllt die Regeln"); return
    json.dump(r, open(R / "spielt_sie.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Runde {r['md']} festgeschrieben: {len(r['fragen'])} Fragen, Abgabe bis {r['schluss']}")
    for q in r["fragen"]: print(" ", q["id"], q["frage"])


if __name__ == "__main__":
    main()
