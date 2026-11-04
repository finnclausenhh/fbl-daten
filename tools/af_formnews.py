# Wird von apifootball_bau.py per exec eingebunden (gleicher Namensraum).
# Formtief/Formhoch als Meldung (Finn 04.11.2026):
# - Headline als Frage ("Kommt X aus dem Formtief?"), keine Noten in Headline, Teaser und Text.
#   Noten sind nur eine Tendenz, Kickbase rechnet anders.
# - Nie eine Spielerin herauspicken, wenn das ganze Team oder ihre Mannschaftsteil genauso abfällt:
#   Meldung nur, wenn ihr Abfall (bzw. Anstieg) deutlich größer ist als bei den Mitspielerinnen derselben Position.
# - Einordnung: Lage des Teams, Ergebnisse der letzten 3 Spiele, belegbare Fakten zu den nächsten Gegnern.
# - Grafik "formvergleich": die Spielerinnen ihres Mannschaftsteils, vorher gegen die letzten 3 Spiele, ohne Zahlen.
KNK = {"FCB": "Bayern", "WOB": "Wolfsburg", "SGE": "Frankfurt", "B04": "Leverkusen", "KOE": "Köln", "RBL": "Leipzig", "SVW": "Werder",
       "SCF": "Freiburg", "FCU": "Union", "VFB": "Stuttgart", "TSG": "Hoffenheim", "HSV": "der HSV", "FCN": "Nürnberg", "M05": "Mainz"}
KNK_N = lambda k: KNK.get(k, k).replace("der HSV", "HSV")
TEIL = {"MF": "MF", "DM": "MF", "OM": "MF", "ABW": "ABW", "ST": "ST"}
TEILW = {"MF": "Mittelfeld", "ABW": "Abwehr", "ST": "Sturm"}
# Artikel: (das ganze, im)
TEILA = {"MF": ("das ganze", "im"), "ABW": ("die ganze", "in der"), "ST": ("der ganze", "im")}
ABSTAND = 0.5   # so viel deutlicher als der Schnitt der Mitspielerinnen

def _bilanz(k):
    L = []
    for (m, h, g), p in sorted(PARTIE.items()):
        if p.get("status") != "beendet" or k not in (h, g): continue
        si = 0 if k == h else 1; t, gg = int(p["ergebnis"][si]), int(p["ergebnis"][1 - si])
        L.append({"md": m, "gk": g if si == 0 else h, "t": t, "g": gg, "pkt": 3 if t > gg else 1 if t == gg else 0})
    return L

_GA = {k: sum(x["g"] for x in _bilanz(k)) for k in SPN["vereine"]}
_GF = {k: sum(x["t"] for x in _bilanz(k)) for k in SPN["vereine"]}
_GAR = sorted(_GA, key=lambda k: -_GA[k])     # meiste Gegentore zuerst
_GFR = sorted(_GF, key=lambda k: _GF[k])      # wenigste Tore zuerst

def _formwerte(sid):
    voll = [n for n in (profil.get(sid) or {}).get("no", []) if n[2] >= 60]
    if len(voll) < 4: return None
    l3 = voll[-3:]; vor = voll[:-3]
    if len(vor) < 1: return None
    return round(sum(n[1] for n in vor) / len(vor), 2), round(sum(n[1] for n in l3) / 3, 2)

def _gruppe(f):
    teil = TEIL.get(f.get("pos"))
    if not teil: return None, []
    L = []
    for s in WIR:
        if s["k"] != f["k"] or TEIL.get(s.get("pos")) != teil: continue
        w = _formwerte(s["id"])
        if not w: continue
        L.append({"id": s["id"], "n": s["n"], "k": s["k"], "pos": s.get("pos"), "vorher": w[0], "l3": w[1], "d": round(w[1] - w[0], 2), "hervor": s["id"] == f["id"]})
    L.sort(key=lambda x: (not x["hervor"], x["d"] if f["diff"] < 0 else -x["d"]))
    return teil, L

def _ergebnisse(L):
    t = [f"{KNK_N(x['gk'])} ({x['t']}:{x['g']})" for x in L]
    return ", ".join(t[:-1]) + " und " + t[-1] if len(t) > 1 else (t[0] if t else "")

def _gegner_fakten(k, schwach):
    fakten = []
    for gk, ha, r in (programm(k).get("next") or []):
        L = _bilanz(gk); l4 = L[-4:]; tf4 = sum(x["t"] for x in l4)
        ga_r = _GAR.index(gk) + 1; gf_r = _GFR.index(gk) + 1
        if schwach:
            if len(l4) == 4 and tf4 <= 1: fakten.append(f"{KNK_N(gk)} traf in den letzten vier Ligaspielen {'nur einmal' if tf4 == 1 else 'gar nicht'}")
            elif ga_r <= 3:
                mehr = [x for x in _GAR[:ga_r - 1]]
                zus = "die meisten der Liga" if ga_r == 1 else ("mehr hat nur " + (f"{KNK_N(mehr[0])} selbst" if mehr[0] == k else KNK_N(mehr[0]))) if ga_r == 2 else "die drittmeisten der Liga"
                fakten.append(f"{KNK_N(gk)} kassierte {_GA[gk]} Gegentore, {zus}")
        else:
            if _GAR.index(gk) >= len(_GAR) - 3: fakten.append(f"{KNK_N(gk)} ließ erst {_GA[gk]} Gegentore zu")
            elif len(_GFR) - gf_r < 3: fakten.append(f"{KNK_N(gk)} traf schon {_GF[gk]}-mal")
    return fakten

def _team_satz(k):
    L = _bilanz(k); pk = sum(x["pkt"] for x in L); tf = sum(x["t"] for x in L); ga = sum(x["g"] for x in L)
    return f"{KNK_N(k)} {'wartet' if pk == 0 else 'steht'} nach {len(L)} Spieltagen {'noch auf den ersten Punkt' if pk == 0 else f'bei {pk} Punkten'}, das Torverhältnis ist {tf}:{ga}."

def formmeldung(f, tief_):
    nach = f["n"].split()[-1]; pr = PSW.get(f["prog"] or "", "offen")
    teil, grp = _gruppe(f)
    andere = [x for x in grp if not x["hervor"]]
    if andere:
        schnitt = sum(x["d"] for x in andere) / len(andere)
        if (tief_ and f["diff"] > schnitt - ABSTAND) or (not tief_ and f["diff"] < schnitt + ABSTAND):
            return None   # nicht deutlich anders als die Mitspielerinnen: keine Einzelmeldung
    L = _bilanz(f["k"]); l3 = L[-3:]
    mit = [x for x in andere if (x["d"] <= -0.3 if tief_ else x["d"] >= 0.3)]
    tw = TEILW.get(teil, "Team")
    t1 = _team_satz(f["k"]) if tief_ else ""
    if andere:
        if len(mit) * 2 >= len(andere):
            t2 = f"In den letzten drei Spielen gegen {_ergebnisse(l3)} {'ließ' if tief_ else 'zog'} {TEILA[teil][0]} {tw} von {KNK_N(f['k'])} {'nach' if tief_ else 'an'}, bei {nach} ist der {'Knick' if tief_ else 'Sprung'} am deutlichsten."
        else:
            t2 = f"In den letzten drei Spielen gegen {_ergebnisse(l3)} hielten die meisten {TEILA[teil][1]} {tw} ihr Niveau, bei {nach} zeigt die Tendenz klar nach {'unten' if tief_ else 'oben'}."
    else:
        t2 = f"Die letzten drei Spiele: {_ergebnisse(l3)}."
    fak = _gegner_fakten(f["k"], f.get("ns") != "schwer")
    nx = f.get("next") or []
    t3 = ""
    if nx:
        t3 = "Als Nächstes: " + ", ".join(f"{'zu Hause gegen' if h == 'H' else 'auswärts gegen'} {KNK_N(g)} ({r}.)" for g, h, r in nx) + "."
        if fak: t3 += " " + ". ".join(fak) + "."
    t4 = "Die Form lesen wir aus den Noten von API-Football (Einsätze ab 60 Minuten). Sie zeigen eine Tendenz, Kickbase rechnet seine Punkte anders."
    head = f"Kommt {nach} aus dem Formtief?" if tief_ else f"Hält {nach} ihr Formhoch?"
    m = meld(f["id"], ["FORMTIEF" if tief_ else "FORMHOCH", "INSIDER"], head, head, [t1, t2, t3, t4],
             f"Minuten der letzten 3 Ligaspiele: {' · '.join(str(x) + chr(39) for x in f['min3'])}. Prognose fürs nächste Spiel: {pr}.", "formtief" if tief_ else "formhoch")
    if len(grp) >= 2:
        m["grafik"] = {"typ": "formvergleich", "titel": f"{tw} von {KNK_N(f['k'])}", "unter": "vorher und in den letzten 3 Spielen",
                       "sp": [{k: x[k] for k in ("n", "k", "pos", "vorher", "l3", "hervor")} for x in grp][:6],
                       "hinweis": "Tendenz aus den Noten von API-Football, Einsätze ab 60 Minuten. Keine Kickbase-Punkte."}
    return m
