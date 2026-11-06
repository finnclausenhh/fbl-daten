#!/usr/bin/env python3
"""Tippspiel "Spielt sie?": legt die Fragen eines Spieltags einmal fest (Finn 04.11.2026).

Bisher hat der Ticker die Fragen im Browser aus der aktuellen Prognose gerechnet. Ändert sich die Prognose,
ändern sich die Fragen, und abgegebene Tipps passen nicht mehr. Dieses Skript schreibt spielt_sie.json
für den aktuellen Spieltag genau einmal. Steht für den Spieltag schon eine Runde, bleibt sie unverändert.

Mix ab 04.11.2026 (Finn): höchstens 2 Einsatzfragen (Umfragen und Startelf, nur mit Anlass), dazu MVP des Spieltags,
Weiße Weste, Reißt die Serie und Wer beendet die Torflaute (mix_fragen); nie dieselbe Spielerin in zwei Fragen.
Auflösung der neuen Typen in loesung_mix (Noten API-Football, Endergebnis, Torschützinnen), mehrere richtige mit Komma.

Regeln Einsatzfragen (wie zuvor im Browser, claude/wosoinsider-gamification.md):
- Abgabe bis 90 Minuten vor dem ersten Anpfiff des Spieltags.
- Zuerst bis zu 2 bestehende Startelf-Umfragen des Spieltags (mit Infos und Einschätzung).
- Dann Startelf-Fragen aus der Prognose: nur Erwartet oder Unsicher, Einsatzwert 30 bis 94 %, Gewicht
  (Tore x2 + Vorlagen, Torhüterin +6) mindestens 3, Anlass nötig (zuletzt Bank oder nur eingewechselt, auch
  Pokal/Europapokal; Einschätzung der Redaktion; weniger als 3 Starts in den letzten 3 Ligaspielen), Foto nötig.
- Höchstens 2 Fragen je Verein, zuerst 2 zu nicht einsehbaren Spielen, insgesamt höchstens 5, sortiert nach Anstoß.
- Festgeschrieben wird frühestens 6 Tage vor dem ersten Anpfiff und nur vor dem Abgabeschluss.

Aufruf: python3 tools/spielt_sie.py [--repo .] [--neu]   (--neu erzwingt eine neue Runde, nur von Hand)
"""
import argparse, collections, json, re, unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
TEAM = {}
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


def runde(sp, spn, um, fotos, jetzt, anlass_m=None, af=None):
    anlass_m = anlass_m or {}
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

    global TEAM
    TEAM = {}
    for tt in sp.get("spieltage", []):
        if tt.get("nr", 0) >= t["nr"]: continue
        for p in tt["partien"]:
            e = p.get("ergebnis")
            if p.get("status") != "beendet" or not e: continue
            a, b = int(e[0]), int(e[1])
            for k, f_, g_ in ((p["heim_k"], a, b), (p["gast_k"], b, a)):
                T = TEAM.setdefault(k, {"gf": 0, "ga": 0, "g": 0}); T["gf"] += f_; T["ga"] += g_; T["g"] += 1
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
                       # WARUM = Anlass (Feld anlass der Umfrage, sonst Überschrift der Meldung) plus Kickbase-Bezug; die Infos je Antwort stehen schon an den Karten (Finn 04.11.2026)
                       "warum": " ".join(x for x in [u["anlass"] if u.get("anlass") else (anlass_m.get(u.get("meldung")) or "").rstrip(".") + "." if anlass_m.get(u.get("meldung")) else "",
                                                       "Torhüterinnen punkten bei Kickbase stark." if u.get("position") == "TW" else "Wer startet, sammelt bei Kickbase die Punkte."] if x),
                       "prognose": f"{STUFE.get(e.get('stufe'), '')}: {eo.get('nachname') or eo['n']}. {e.get('text', '')}".strip() if eo else "",
                       "optionen": [{"id": o["id"], "n": o.get("nachname") or ("Andere" if o["id"] == "andere" else o["n"])} for o in u.get("optionen", [])],
                       "daten": eo["id"] if eo else None})
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
                st = s.get("status") or {}
                if st.get("s") in ("fraglich", "verletzt", "abwesend", "gesperrt", "aufbau"):
                    # Status immer nennen (Finn 04.11.2026: Tomasiak ohne Hinweis auf ihre Probleme)
                    seit = st.get("stand", "")
                    anlass = f"{st['s'].capitalize()}{' seit ' + seit[8:10] + '.' + seit[5:7] + '.' if len(seit) >= 10 else ''}: {st.get('grund') or 'Grund offen'}. " + anlass
                stz = re.search(r"(\d)/5 Startelf", x.get("warum") or "")
                kand.append({"id": "s-" + s["id"], "art": "STARTELF", "partie": p["id"], "k": k, "sid": s["id"], "einsehbar": p["id"] in ein, "_g": gew,
                             "frage": f"Steht {nach(s['n'])} in der Startelf?",
                             "warum": f"{anlass} " + ("Torhüterinnen punkten bei Kickbase stark." if tw else f"Diese Saison {tore} {'Tor' if tore == 1 else 'Tore'}, {vorl} {'Vorlage' if vorl == 1 else 'Vorlagen'}."),
                             "prognose": f"{STUFE[x['st']]}. {stz.group(1) + ' von 5 zuletzt in der Startelf, ' if stz else ''}Einsatzwert {w} %.",
                             "optionen": [{"id": "ja", "n": "Ja"}, {"id": "nein", "n": "Nein"}],
                             "daten": "ja" if x["st"] in ("sicher", "erwartet") else "nein"})
    kand.sort(key=lambda q: -q["_g"])
    # Mix (Finn 04.11.2026): MVP, Weiße Weste, höchstens 2 Einsatzfragen, Torflaute und/oder Serie, nie dieselbe Art doppelt
    einsatz = fragen[:2]
    for q in [q for q in kand if not q["einsehbar"]] + kand:
        if len(einsatz) >= 2: break
        if q["id"] not in {f["id"] for f in einsatz}: einsatz.append(q)
    belegt_sid = {q.get("sid") for q in einsatz if q.get("sid")}
    for q in einsatz:
        if q.get("umfrage"):
            u = next((x for x in um if x["id"] == q["umfrage"]), None)
            for o in (u or {}).get("optionen", []):
                s_ = finde(q["k"], o.get("nachname") or "")
                if s_: belegt_sid.add(s_["id"])
    for q in einsatz: q["typ"] = "einsatz"
    # Vereins-Mix (Finn 05.11.2026): jeder Verein in höchstens 2 Fragen (zählt Frageverein und Vereine der Antworten)
    vk = collections.Counter()
    for q in einsatz: vk.update({q["k"]})
    extra = mix_fragen(t, alle, af or {}, fotos, ein, belegt_sid, vk)
    fragen = (einsatz + extra)[:5]
    anst = {p["id"]: p["anstoss"] for p in t["partien"]}
    fragen.sort(key=lambda q: anst.get(q["partie"], ""))
    for q in fragen: q.pop("_g", None)
    return {"md": t["nr"], "erstellt": jetzt.strftime("%Y-%m-%dT%H:%M"), "erst": erst, "schluss": schluss.strftime("%Y-%m-%dT%H:%M"),
            "hinweis": "Fragen festgeschrieben von tools/spielt_sie.py, ändern sich bis zur Wertung nicht.", "fragen": fragen}, "neu"


KURZ_N = {"FCB": "Bayern", "WOB": "Wolfsburg", "SGE": "Frankfurt", "B04": "Leverkusen", "KOE": "Köln", "RBL": "Leipzig", "SVW": "Werder",
          "SCF": "Freiburg", "FCU": "Union", "VFB": "Stuttgart", "TSG": "Hoffenheim", "HSV": "den HSV", "FCN": "Nürnberg", "M05": "Mainz"}
ORT = {"FCB": "München", "WOB": "Wolfsburg", "SGE": "Frankfurt", "B04": "Leverkusen", "KOE": "Köln", "RBL": "Leipzig", "SVW": "Bremen",
       "SCF": "Freiburg", "FCU": "Berlin", "VFB": "Stuttgart", "TSG": "Hoffenheim", "HSV": "Hamburg", "FCN": "Nürnberg", "M05": "Mainz"}
NOM = lambda k: "der HSV" if k == "HSV" else KURZ_N.get(k, k)
kom = lambda x, d=1: f"{x:.{d}f}".replace(".", ",")


def mix_fragen(t, alle, af, fotos, ein, belegt, vk=None):
    """Neue Fragetypen (Finn 04.11.2026). Jede Auswahl folgt einer festen Regel, jede Frage nennt ihren Anlass."""
    md = t["nr"]
    sp_alle = [p for p in t["partien"]]
    def gegner(k):
        for p in sp_alle:
            if p["heim_k"] == k: return p, p["gast_k"], True
            if p["gast_k"] == k: return p, p["heim_k"], False
        return None, None, None
    def ort(k):
        p, o, heim = gegner(k)
        return f"gegen {KURZ_N.get(o, o)}" if heim else f"in {ORT.get(o, o)}"
    def prog(s):
        p, o, heim = gegner(s["k"])
        if not p: return None
        a = p.get(("heim" if heim else "gast") + "_aufstellung") or {}
        for x in (a.get("startelf") or []) + (a.get("bank") or []):
            if norm(x["n"]) == norm(nach(s["n"])) or norm(x.get("voll") or "") == norm(s["n"]):
                return x.get("st")
        return (s.get("prognose") or {}).get("st")
    def foto(s):
        f = fotos.get(s["n"]) or {}
        return bool(f.get("portrait") or f.get("datei"))
    spielt = lambda s: prog(s) in ("sicher", "erwartet") and foto(s) and s["id"] not in belegt
    liga = lambda s: [e for e in (s.get("spiele") or []) if e.get("md", 0) < md]
    def opt(s, info):
        return {"id": s["id"], "n": nach(s["n"]), "sid": s["id"], "k": s["k"], "info": info}
    def frage(typ, art, ids, frage_, warum, prognose, optionen):
        p, o, heim = gegner(ids[0]["k"])
        return {"id": f"{typ}-md{md}", "typ": typ, "art": art, "partie": p["id"], "k": ids[0]["k"], "multi": len({x["k"] for x in ids}) > 1,
                "einsehbar": all((gegner(x["k"])[0] or {}).get("id") in ein for x in ids), "frage": frage_, "warum": warum, "prognose": prognose, "optionen": optionen}
    def gt(k):
        return TEAM.get(k, {"gf": 0, "ga": 0, "g": 0})
    out = {}
    vk = vk if vk is not None else collections.Counter()
    voll = lambda k: vk[k] >= 2
    zaehle = lambda ks: vk.update(set(ks))
    # Serie: trifft in mindestens 60 % ihrer Ligaspiele (mind. 5 Einsätze, mind. 4 mit Tor)
    sc = []
    for s in alle:
        L = [e for e in liga(s) if e.get("art") in ("S", "E")]
        k = sum(1 for e in L if e.get("tore"))
        if len(L) >= 5 and k >= 4 and k / len(L) >= .6 and spielt(s):
            sc.append((k / len(L), sum(len(e.get("tore") or []) for e in L), s, k, len(L)))
    sc.sort(key=lambda x: (-x[0], -x[1]))
    sc = [x for x in sc if not voll(x[2]["k"])]
    if sc:
        r_, tore, s, k, n = sc[0]; zaehle([s["k"]]); o = gegner(s["k"])[1]; G = gt(o)
        out["serie"] = frage("serie", "SERIE", [s], f"Trifft {nach(s['n'])} zum {k + 1}. Mal?",
            f"Getroffen in {k} von {n} Ligaspielen, {tore} Tore. {NOM(o)[0].upper() + NOM(o)[1:]} hat {G['ga']} Gegentore in {G['g']} Spielen.",
            f"{'Eher ja' if r_ >= .6 else 'Offen'}: sie trifft in {round(r_ * 100)} % ihrer Spiele.",
            [{"id": "ja", "n": "Ja", "info": f"{nach(s['n'])} trifft"}, {"id": "nein", "n": "Nein", "info": "Serie reißt"}])
        out["serie"]["sid"] = s["id"]; out["serie"]["daten"] = "ja" if r_ >= .5 else "nein"; belegt.add(s["id"])
    # Torflaute: Stürmerinnen, mind. 5 Starts, die letzten 3 Ligaspiele in der Startelf und ohne Tor
    fl = []
    for s in alle:
        L = liga(s); st = [e for e in L if e.get("art") == "S"]
        if voll(s["k"]) or s.get("pos") != "ST" or len(st) < 5 or len(L) < 3 or not spielt(s): continue
        l3 = L[-3:]
        if not all(e.get("art") == "S" and not e.get("tore") for e in l3): continue
        tore = sum(len(e.get("tore") or []) for e in L); letzt = max([e["md"] for e in L if e.get("tore")], default=0)
        fl.append((tore, len(st), s, letzt))
    fl.sort(key=lambda x: (-x[0], -x[1]))
    fl2 = []
    for x in fl:
        if all(y[2]["k"] != x[2]["k"] for y in fl2): fl2.append(x)
        if len(fl2) == 2: break
    if len(fl2) == 2:
        os_ = [opt(s, f"{tore} Tore, zuletzt am {letzt}. Spieltag" if tore else f"{st} Starts, noch ohne Saisontor") for tore, st, s, letzt in fl2]
        schwach = max(fl2, key=lambda x: gt(gegner(x[2]["k"])[1])["ga"] / max(1, gt(gegner(x[2]["k"])[1])["g"]))
        o = gegner(schwach[2]["k"])[1]; G = gt(o)
        out["flaute"] = frage("flaute", "TORFLAUTE", [x[2] for x in fl2], "Wer beendet ihre Torflaute?",
            "Beide stehen fast immer in der Startelf, haben aber in den letzten 3 Ligaspielen nicht getroffen. Tore bringen bei Kickbase die meisten Punkte.",
            f"{nach(schwach[2]['n'])}: {NOM(o)[0].upper() + NOM(o)[1:]} kassiert {kom(G['ga'] / max(1, G['g']))} Tore pro Spiel.",
            os_ + [{"id": "beide", "n": "Beide"}, {"id": "keine", "n": "Keine"}])
        out["flaute"]["daten"] = schwach[2]["id"]
        for x in fl2: belegt.add(x[2]["id"])
        zaehle([x[2]["k"] for x in fl2])
    # Weiße Weste: erwartete Torhüterinnen, Wert = Tore des Gegners + eigene Gegentore pro Spiel (kleiner = besser), je Spiel höchstens eine
    ww = []
    for p in sp_alle:
        for seite, k, o in (("heim", p["heim_k"], p["gast_k"]), ("gast", p["gast_k"], p["heim_k"])):
            a = p.get(seite + "_aufstellung") or {}
            x = next((x for x in (a.get("startelf") or []) if x.get("p") == "TW" and x.get("st") in ("sicher", "erwartet")), None)
            if not x: continue
            s = next((y for y in alle if y["k"] == k and (norm(nach(y["n"])) == norm(x["n"]) or norm(y["n"]) == norm(x["n"]))), None)
            if not s or not foto(s) or s["id"] in belegt or voll(k): continue
            Go, Gk = gt(o), gt(k)
            ww.append((Go["gf"] / max(1, Go["g"]) + Gk["ga"] / max(1, Gk["g"]), p["id"], s, o))
    ww.sort(key=lambda x: x[0]); ww3 = []
    for x in ww:
        if all(y[1] != x[1] for y in ww3): ww3.append(x)
        if len(ww3) == 3: break
    if len(ww3) == 3:
        w = " · ".join(f"{nach(s['n'])}: {NOM(o)} trifft {kom(gt(o)['gf'] / max(1, gt(o)['g']))}-mal pro Spiel" for _, _, s, o in ww3)
        b = ww3[0][2]; Gb = gt(b["k"])
        out["weste"] = frage("weste", "WEISSE WESTE", [x[2] for x in ww3], "Welche Torhüterin bleibt ohne Gegentor?",
            w + ". Spiele ohne Gegentor bringen Torhüterin und Abwehr Kickbase-Punkte.",
            f"{nach(b['n'])}: {NOM(b['k'])[0].upper() + NOM(b['k'])[1:]} hat {Gb['ga']} Gegentore in {Gb['g']} Spielen.",
            [opt(s, ort(s["k"])) for _, _, s, o in ww3] + [{"id": "keine", "n": "Keine", "info": "Alle kassieren"}])
        out["weste"]["daten"] = ww3[0][2]["id"]
        for x in ww3: belegt.add(x[2]["id"])
        zaehle([x[2]["k"] for x in ww3])
    # MVP: die 4 besten Notenschnitte* (mind. 4 Noten), höchstens eine je Verein, nur wer laut Prognose spielt
    # gleicher Schnitt wie die Statistik im Ticker (apifootball.json sp.avg, mind. 4 Spiele mit 60+ Minuten)
    mv = []
    for s in alle:
        e = (af.get("sp") or {}).get(s["id"]) or {}
        if e.get("avg") and len([n for n in e.get("no", []) if n[2] >= 46]) >= 4 and spielt(s) and gegner(s["k"])[0] and not voll(s["k"]): mv.append((e["avg"], s))
    mv.sort(key=lambda x: -x[0]); mv4 = []
    for x in mv:
        if all(y[1]["k"] != x[1]["k"] for y in mv4): mv4.append(x)
        if len(mv4) == 4: break
    if len(mv4) == 4:
        a0, s0 = mv4[0]; o = gegner(s0["k"])[1]; G = gt(o)
        out["mvp"] = frage("mvp", "MVP", [x[1] for x in mv4], f"Wer wird MVP des {md}. Spieltags?",
            "Die vier besten Notenschnitte* der Saison unter allen, die laut Prognose spielen, höchstens eine je Verein. MVP ist, wer am Spieltag die beste Note* holt. *Note von API-Football, keine Kickbase-Punkte.",
            f"{nach(s0['n'])}: bester Schnitt der vier ({kom(a0)}*), {NOM(o)[0].upper() + NOM(o)[1:]} hat {G['ga']} Gegentore in {G['g']} Spielen.",
            [opt(s, f"Ø {kom(a)}* · {ort(s['k'])}") for a, s in mv4])
        out["mvp"]["daten"] = s0["id"]
    reihe = [out.get("mvp"), out.get("weste")] + [out.get(k) for k in ("serie", "flaute")]
    return [q for q in reihe if q]


def loesung(sp, spn, um, runde_, af=None):
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
        if q.get("typ") in ("mvp", "weste", "flaute", "serie"):
            r_ = loesung_mix(q, t, af or {})
            if r_: L[q["id"]] = r_
            continue
        seite = "heim" if p["heim_k"] == q["k"] else "gast" if p["gast_k"] == q["k"] else None
        a = p.get(f"{seite}_aufstellung") if seite else None
        if not a or a.get("typ") != "offiziell": continue
        elf = a.get("startelf") or []
        if q.get("sid"):
            s = spid.get(q["sid"])
            if not s: continue
            drin = any(norm(x.get("voll") or "") == norm(s["n"]) or norm(x.get("n")) == norm(nach(s["n"])) for x in elf)
            L[q["id"]] = "ja" if drin else "nein"
        elif q.get("typ") in ("mvp", "weste", "flaute", "serie"):
            r_ = loesung_mix(q, t, af or {})
            if r_: L[q["id"]] = r_
            continue
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


def loesung_mix(q, t, af):
    """Auflösung MVP, Weiße Weste, Torflaute, Serie, sobald alle beteiligten Spiele beendet sind. Mehrere richtige Antworten mit Komma."""
    def partie(k):
        return next((p for p in t["partien"] if k in (p["heim_k"], p["gast_k"])), None)
    sids = [o for o in q["optionen"] if o.get("sid")] or ([{"sid": q.get("sid"), "k": q["k"], "n": q["frage"].split()[1]}] if q.get("sid") else [])
    ps = [partie(o["k"]) for o in sids]
    if not ps or any(not p or p.get("status") != "beendet" or not p.get("ergebnis") for p in ps): return None
    def tore(o, p):
        seite = "heim" if p["heim_k"] == o["k"] else "gast"
        return sum(1 for x in p.get("tore") or [] if x.get("seite") == seite and not x.get("et") and norm(x.get("n")) == norm(o["n"]))
    if q["typ"] == "mvp":
        w = {o["id"]: ((af.get("spiele") or {}).get(p["id"]) or {}).get("no", {}).get(o["sid"]) for o, p in zip(sids, ps)}
        w = {k: v for k, v in w.items() if v is not None}
        if len(w) < len(sids): return None   # Noten noch nicht da
        m = max(w.values()); return ",".join(k for k, v in w.items() if v == m)
    if q["typ"] == "weste":
        rt = [o["id"] for o, p in zip(sids, ps) if int(p["ergebnis"][1 if p["heim_k"] == o["k"] else 0]) == 0]
        return ",".join(rt) if rt else "keine"
    if q["typ"] == "flaute":
        rt = [o["id"] for o, p in zip(sids, ps) if tore(o, p)]
        return "beide" if len(rt) == 2 else rt[0] if rt else "keine"
    if q["typ"] == "serie":
        o = next(o for o in q["optionen"] if o["id"] == "ja")
        s = {"k": q["k"], "n": q["frage"].split()[1]}
        return "ja" if tore(s, ps[0]) else "nein"


SB_URL = "https://tyhlxkgyfykxjwnqgnoj.supabase.co"
SB_KEY = "sb_publishable_8OOLyVhf2kPU7h_NfKAypg_FAC8P7h3"   # öffentlicher Schlüssel (wie kommentare/config.js), Rechte über RLS


def fans_stand(md):
    """Tippstand einer Runde aus Supabase (nach dem Tippschluss öffentlich): {frage: {antwort: anzahl}}."""
    import urllib.request
    rq = urllib.request.Request(SB_URL + "/rest/v1/rpc/tipp_stand", data=json.dumps({"p_md": md}).encode(), method="POST",
                                headers={"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(rq, timeout=20) as r:
        return json.loads(r.read().decode() or "{}") or {}


def auswertung(runde_, lo, stand, jetzt):
    """Fans gegen Daten (Finn 04.11.2026): erst wenn alle Fragen aufgelöst sind. FANS = Antwort mit den meisten Tipps
    (bei Gleichstand zählt sie nicht), DATEN = unsere Prognose (Feld daten). Ergebnis: eine normale Meldung."""
    md, L = runde_["md"], (lo or {}).get("loesung", {})
    if not runde_.get("fragen") or any(q["id"] not in L for q in runde_["fragen"]): return None
    zeilen, f_ok, d_ok, tipps = [], 0, 0, 0
    for q in runde_["fragen"]:
        st = stand.get(q["id"]) or {}; ges = sum(int(v) for v in st.values()); tipps = max(tipps, ges)
        rt = str(L[q["id"]]).split(",")
        top = sorted(st.items(), key=lambda x: -int(x[1]))
        fans = top[0][0] if top and (len(top) == 1 or int(top[0][1]) > int(top[1][1])) else None
        fo, do = fans in rt if fans else None, (q.get("daten") in rt) if q.get("daten") else None
        f_ok += 1 if fo else 0; d_ok += 1 if do else 0
        name = lambda i: next((o["n"] for o in q["optionen"] if o["id"] == i), i)
        zeilen.append({"frage": q["frage"], "richtig": " / ".join(name(i) for i in rt), "fans": fo, "daten": do,
                       "fans_n": name(fans) if fans else None, "fans_p": round(int(top[0][1]) / ges * 100) if fans and ges else None})
    n = len(runde_["fragen"])
    if f_ok > d_ok: h = f"Fans schlagen die Daten: {f_ok} von {n} richtig"
    elif d_ok > f_ok: h = f"Die Daten schlagen die Fans: {d_ok} von {n} richtig"
    else: h = f"Fans und Daten gleichauf: je {f_ok} von {n} richtig"
    return {"md": md, "news": [{"id": f"tipp-fans-md{md}", "zeit": jetzt.strftime("%Y-%m-%dT%H:%M"), "tags": ["SPIELT SIE?"], "typ": "auswertung",
            "headline": h, "kurz": h, "spielerin": f"{md}. Spieltag",
            "text": [f"Beim Tippspiel „Spielt sie?“ zum {md}. Spieltag lagen die Fans bei {f_ok} von {n} Fragen richtig, unsere Prognose bei {d_ok}.",
                     f"Als Fan-Tipp zählt die Antwort mit den meisten Stimmen. {tipps} {'Fan hat' if tipps == 1 else 'Fans haben'} mitgetippt."],
            "grafik": {"typ": "fansdaten", "md": md, "fans": f_ok, "daten": d_ok, "n": n, "tipps": tipps, "zeilen": zeilen}}]}


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
    lo = loesung(sp, spn, um, alt, lade("apifootball.json", {}))
    if lo is not None:
        vorher = lade("tipp_loesung.json", {}) or {}
        if vorher.get("md") != lo["md"] or vorher.get("loesung") != lo["loesung"]:
            json.dump(lo, open(R / "tipp_loesung.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"Auflösung Runde {lo['md']}: {len(lo['loesung'])} von {len(alt['fragen'])} Fragen")
    # Fans gegen Daten: einmal je Runde, sobald alles aufgelöst ist (tipp_auswertung.json, der Ticker mischt die Meldung in den Feed)
    aw_alt = lade("tipp_auswertung.json", {}) or {}
    if lo and alt.get("fragen") and aw_alt.get("md") != alt["md"] and jetzt >= dt(alt["schluss"]):
        try:
            aw = auswertung(alt, lo, fans_stand(alt["md"]), jetzt)
            if aw:
                json.dump(aw, open(R / "tipp_auswertung.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("Fans gegen Daten:", aw["news"][0]["headline"])
        except Exception as e:
            print("Auswertung nicht möglich:", e)
    if not a.neu and alt.get("md") == sp.get("aktuell") and alt.get("fragen"):
        print(f"Runde {alt['md']} steht schon ({len(alt['fragen'])} Fragen), bleibt unverändert"); return
    anlass_m = {m["id"]: m.get("headline", "") for m in (lade("news.json", {}) or {}).get("meldungen", [])}
    r, grund = runde(sp, spn, um, fotos, jetzt, anlass_m, lade("apifootball.json", {}))
    if not r:
        print("keine neue Runde:", grund); return
    if not r["fragen"]:
        print("keine Frage erfüllt die Regeln"); return
    json.dump(r, open(R / "spielt_sie.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Runde {r['md']} festgeschrieben: {len(r['fragen'])} Fragen, Abgabe bis {r['schluss']}")
    for q in r["fragen"]: print(" ", q["id"], q["frage"])


if __name__ == "__main__":
    main()
