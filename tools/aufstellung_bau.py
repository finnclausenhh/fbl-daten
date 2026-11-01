#!/usr/bin/env python3
"""Baut aus den Aufstellungs-Kandidaten fertige Aufstellungs-Meldungen (eine je Verein) im Format der Seite.

Aufruf: python3 engine/aufstellung_bau.py kandidaten.json engine/kader.csv aufstellungen_neu.json [news.json]
Schreibt eine Liste von Meldungen mit Feld "aufstellung". Nur Aufstellungen mit Status "vor Anpfiff".
"""
import csv, html, json, re, sys, unicodedata, urllib.request

SLUG = {"bayern-muenchen": "FC Bayern", "vfl-wolfsburg": "VfL Wolfsburg", "eintracht-frankfurt": "Eintracht Frankfurt",
        "bayer-leverkusen": "Bayer Leverkusen", "1-fc-koeln": "1. FC Köln", "rb-leipzig": "RB Leipzig",
        "werder-bremen": "Werder Bremen", "sc-freiburg": "SC Freiburg", "1-fc-union-berlin": "Union Berlin",
        "vfb-stuttgart": "VfB Stuttgart", "tsg-hoffenheim": "TSG Hoffenheim", "hamburger-sv": "Hamburger SV",
        "1-fc-nuernberg": "1. FC Nürnberg", "1-fsv-mainz-05": "Mainz 05"}
KURZ = {"FC Bayern": "fcb", "VfL Wolfsburg": "wob", "Eintracht Frankfurt": "sge", "Bayer Leverkusen": "b04", "1. FC Köln": "koe",
        "RB Leipzig": "rbl", "Werder Bremen": "svw", "SC Freiburg": "scf", "Union Berlin": "fcu", "VfB Stuttgart": "vfb",
        "TSG Hoffenheim": "tsg", "Hamburger SV": "hsv", "1. FC Nürnberg": "fcn", "Mainz 05": "m05"}
KADER_VEREIN = {"FC Bayern": "FC Bayern München", "Bayer Leverkusen": "Bayer 04 Leverkusen",
                "Union Berlin": "1. FC Union Berlin", "Mainz 05": "1. FSV Mainz 05"}


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def pos_von(name, verein, kader):
    """Position aus kader.csv (Kickbase-Position). Passt auf Nachname oder vollen Namen."""
    v = KADER_VEREIN.get(verein, verein)
    n = norm(name)
    for r in kader:
        if r["verein"] != v:
            continue
        k = norm(r["name"])
        if k == n or k.endswith(" " + n) or k.split()[-1] == n.split()[-1]:
            return r["position"]
    return "MF"


POS = ["TW", "ABW", "DM", "MF", "OM", "ST"]
LINIEN = {3: ["TW", "ABW", "MF"], 4: ["TW", "ABW", "MF", "ST"], 5: ["TW", "ABW", "DM", "OM", "ST"],
          6: ["TW", "ABW", "DM", "MF", "OM", "ST"]}


def grafik(url):
    """Positionen aus der Spielfeldgrafik der Sportschau (gleiche ypos = eine Linie).
    Gibt {"home"/"away": {"formation": "4-2-3-1", "pos": {nachname: (linie, reihenfolge)}}} zurück, bei Fehlern {}."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FBL-Insider)"})
        roh = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print(f"WARN Grafik {url[-60:]}: {e}", file=sys.stderr)
        return {}
    out = {}
    for seite in ("home", "away"):
        i = roh.find(f'class="hs-starter {seite}"')
        j = roh.find("<!--end module tactic-->", i)
        if i < 0:
            continue
        sp = []
        for teil in roh[i:j].split('<div class="tactic playing-lineup')[1:]:
            x = re.search(r'data-xpos="([0-9.]+)"', teil)
            y = re.search(r'data-ypos="([0-9.]+)"', teil)
            n = re.search(r'spielerkarte/pe\d+/([a-z0-9-]+)/person-profil">([^<]+)<', teil)
            if x and y and n:
                sp.append({"slug": n.group(1), "n": html.unescape(n.group(2)).strip(), "x": float(x.group(1)), "y": round(float(y.group(1)), 3)})
        ys = sorted({p["y"] for p in sp})
        namen = LINIEN.get(len(ys))
        reihen = [sorted([p for p in sp if p["y"] == y], key=lambda p: -p["x"]) for y in ys]
        if len(sp) != 11 or not namen or len(reihen[0]) != 1:
            continue
        pos = {}
        for lab, r in zip(namen, reihen):
            for k, p in enumerate(r):
                for schl in (norm(p["n"]), norm(p["slug"].replace("-", " ")), norm(p["n"]).split()[-1]):
                    pos.setdefault(schl, (lab, k))
        out[seite] = {"formation": "-".join(str(len(r)) for r in reihen[1:]), "pos": pos}
    return out


def grafik_pos(name, g):
    """Linie und Reihenfolge einer Startelf-Spielerin aus der Grafik, sonst None."""
    if not g:
        return None
    n = norm(name)
    return g["pos"].get(n) or g["pos"].get(n.split()[-1]) if n else None


def pid_von(name, verein, kader):
    """Spielerinnen-ID aus kader.csv, nur wenn die Zuordnung eindeutig ist (sonst leer)."""
    v = KADER_VEREIN.get(verein, verein)
    n = norm(name)
    t = [r for r in kader if r["verein"] == v and (norm(r["name"]) == n or norm(r["name"]).split()[-1] == n.split()[-1])]
    return t[0].get("id", "") if len(t) == 1 else ""


def infos(verein, kader, news):
    """Status-Hinweise je Spielerin aus news.json (verletzt/gesperrt, optional Ausfallzeit im Feld 'ausfall')."""
    out = {}
    for m in sorted(news, key=lambda m: m["zeit"]):  # neueste gewinnt
        if m.get("verein") == verein and m.get("status") in ("verletzt", "gesperrt", "fraglich"):
            out[norm(m["spielerin"]).split()[-1]] = m.get("ausfall") or m["status"]
        elif m.get("verein") == verein and m.get("status") == "fit":
            out.pop(norm(m["spielerin"]).split()[-1], None)
    return out


def team(slug, gegner_slug, start, bank, vgl, kader, news=(), g=None, lern=None):
    verein = SLUG[slug]
    bank = list(dict.fromkeys(bank))
    neu_s = set((vgl or {}).get("neu_in_startelf", []))
    raus_s = set((vgl or {}).get("nicht_mehr_in_startelf", []))
    neu_k = set((vgl or {}).get("neu_im_kader", []))
    fehlt = (vgl or {}).get("fehlt_im_kader", [])
    P = lambda n: pos_von(n, verein, kader)
    I = lambda n: pid_von(n, verein, kader)
    abgeleitet = None
    if not g and lern and len(start) == 11:
        form, pos, hinweis = ableiten_pos(start, verein, kader, lern)
        g = {"formation": form, "pos": {k: v for k, v in pos.items()}}
        abgeleitet = hinweis or "Positionen aus den bisherigen Liga-Einsätzen abgeleitet"
    ordnung = {p: i for i, p in enumerate(POS)}

    def S(n):  # Startelf: Position aus der Grafik, sonst Kaderposition
        gp = grafik_pos(n, g)
        kp = P(n)
        return dict(n=n, p=gp[0] if gp else kp, pid=I(n), _o=(ordnung.get(gp[0] if gp else kp, 9), gp[1] if gp else 9),
                    **({"kp": kp} if gp and gp[0] != kp else {}), **({"f": "neu"} if n in neu_s else {}))
    elf = sorted([S(n) for n in start], key=lambda c: c["_o"])  # ohne Grafik nach Kaderposition TW, ABW, MF, ST
    for c in elf:
        c.pop("_o")
    return {"gegner": SLUG[gegner_slug], **({"formation": g["formation"]} if g else {}),
            **({"geschaetzt": True, "hinweis": abgeleitet} if abgeleitet else {}),
            "startelf": elf,
            "bank": [dict(n=n, p=P(n), pid=I(n), **({"f": "raus"} if n in raus_s else {"f": "neu"} if n in neu_k else {})) for n in bank],
            "fehlt": fehlt_liste(verein, start, bank, fehlt, kader, news, P)}


def fehlt_liste(verein, start, bank, raus, kader, news, P):
    """RAUS nur, wenn sie im letzten Spieltagskader standen. Alle anderen Nicht-Berufenen: nur Name, ggf. (Hinweis)."""
    inf = infos(verein, kader, news)
    im_kader = {norm(n).split()[-1] for n in list(start) + list(bank)}
    raus_k = {norm(n).split()[-1] for n in raus}
    out = [dict(n=n, p=P(n), f="raus", **({"i": inf[norm(n).split()[-1]]} if norm(n).split()[-1] in inf else {})) for n in raus]
    for r in kader:
        if r["verein"] != KADER_VEREIN.get(verein, verein):
            continue
        k = norm(r["name"]).split()[-1]
        if k in im_kader or k in raus_k:
            continue
        out.append(dict(n=r["name"].split()[-1], p=r["position"], **({"i": inf[k]} if k in inf else {})))
    return out


# ---------- Positionen lernen (Finn 01.11.2026) ----------
from collections import Counter
TIEF = {"ABW": 1, "DM": 2, "MF": 3, "OM": 4, "ST": 5}
KB_TIEF = {"ABW": 1, "DM": 2, "MF": 3, "OM": 4, "ST": 5}


def _kz(n):
    return norm(n).split()[-1] if n else ""


def lernen(spielplan, verein):
    """Liga-Aufstellungen mit Sportschau-Grafik dieser Saison: je Spielerin Linie und Seite (0 rechts, 1 links), je Verein die Formationen."""
    kz = KURZ.get(verein)
    hist, forms = {}, Counter()
    for t in (spielplan or {}).get("spieltage", []):
        for p in t.get("partien", []):
            for sd in ("heim", "gast"):
                if p.get(sd + "_k") != (kz or "").upper() and p.get(sd + "_k") != kz:
                    continue
                a = p.get(sd + "_aufstellung")
                if not a or not a.get("formation"):
                    continue
                forms[a["formation"]] += 1
                zeilen = {}
                for x in a["startelf"]:
                    zeilen.setdefault(x["p"], []).append(x)
                for lin, xs in zeilen.items():
                    if lin == "TW":
                        continue
                    for i, x in enumerate(xs):
                        frac = i / (len(xs) - 1) if len(xs) > 1 else 0.5
                        hist.setdefault(_kz(x["n"]), []).append((lin, frac, p.get("md", 0)))
    return {"spielerinnen": hist, "formationen": forms}


def _plausibel(abw, st, formationen):
    if not 3 <= abw <= 5 or not 1 <= st <= 3 or 10 - abw - st < 2:
        return False
    ruecken = {int(f.split("-")[0]) for f in formationen}
    return not ruecken or abw in ruecken


def ableiten_pos(start, verein, kader, lern):
    """Formation und Linien einer Startelf ohne Grafik, aus den bisherigen Liga-Einsätzen. Gibt (formation, {kz: (linie, frac)}, hinweis)."""
    h = lern["spielerinnen"]
    tw = next((n for n in start if pos_von(n, verein, kader) == "TW"), None)
    feld = [n for n in start if n != tw]
    info = {}
    for n in feld:
        eintr = h.get(_kz(n), [])
        if eintr:
            lin = Counter(l for l, _, _ in eintr).most_common(1)[0][0]
            tief = sum(TIEF[l] for l, _, _ in eintr) / len(eintr)
            fr = [f for l, f, _ in eintr if l == lin]
            info[n] = dict(lin=lin, tief=tief, frac=sum(fr) / len(fr), n=len(eintr), kb=False)
        else:
            kp = pos_von(n, verein, kader)
            info[n] = dict(lin={"ABW": "ABW", "ST": "ST"}.get(kp, "MF"), tief=KB_TIEF.get({"ABW": "ABW", "ST": "ST"}.get(kp, "MF")), frac=0.5, n=0, kb=True)
    zaehl = Counter(i["lin"] for i in info.values())
    hinweis = ""
    if _plausibel(zaehl["ABW"], zaehl["ST"], lern["formationen"]) and len(feld) == 10:
        reihen = [[n for n in feld if info[n]["lin"] == l] for l in ("ABW", "DM", "MF", "OM", "ST")]
        reihen = [sorted(r, key=lambda n: info[n]["frac"]) for r in reihen if r]
        marker = [l for l in ("ABW", "DM", "MF", "OM", "ST") if zaehl[l]]
        zeilen = list(zip(marker, reihen))
        if any(info[n]["kb"] for n in feld):
            hinweis = "Ohne Einsatzdaten: " + ", ".join(n for n in feld if info[n]["kb"])
    else:
        ziel = (lern["formationen"].most_common(1)[0][0] if lern["formationen"] else "4-2-3-1")
        zahlen = [int(x) for x in ziel.split("-")]
        sortiert = sorted(feld, key=lambda n: (info[n]["tief"], info[n]["frac"]))
        reihen, k = [], 0
        for z in zahlen:
            reihen.append(sorted(sortiert[k:k + z], key=lambda n: info[n]["frac"]))
            k += z
        namen = LINIEN.get(len(zahlen) + 1, ["TW", "ABW", "MF", "ST"])[1:]
        zeilen = list(zip(namen, reihen))
        hinweis = f"Formation geschätzt ({ziel}, übliches System des Vereins), weil die Daten kein plausibles System ergaben"
    form = "-".join(str(len(r)) for _, r in zeilen)
    pos = {}
    for lab, r in zeilen:
        for i, n in enumerate(r):
            pos[_kz(n)] = (lab, i)
    if tw:
        pos[_kz(tw)] = ("TW", 0)
    return form, pos, hinweis


def main():
    kand = json.load(open(sys.argv[1], encoding="utf-8"))
    kader = list(csv.DictReader(open(sys.argv[2], encoding="utf-8")))
    news = json.load(open(sys.argv[4], encoding="utf-8"))["meldungen"] if len(sys.argv) > 4 else []
    zeit = kand["stand"]
    tt = zeit[8:10] + zeit[5:7]
    out = []
    for a in kand.get("aufstellungen", []):
        if a.get("status") != "vor Anpfiff":
            continue
        heim, gast = a["spiel"].split(" gegen ")
        gr = grafik(a["url"]) if a.get("url") else {}
        for slug, gs, st, bk, vg, sd in ((heim, gast, "startelf_heim", "bank_heim", "vergleich_heim", "home"),
                                         (gast, heim, "startelf_gast", "bank_gast", "vergleich_gast", "away")):
            if slug not in SLUG or SLUG[slug] not in KURZ:  # Pokalgegner ohne Bundesliga-Kader
                continue
            verein = SLUG[slug]
            wb = a.get("wettbewerb")
            if wb and gs not in SLUG:
                SLUG[gs] = gs.replace("fc-", "FC ").replace("-", " ").title()
            t = team(slug, gs, a[st], a[bk], a.get(vg), kader, news, gr.get(sd))
            if wb:
                t["wettbewerb"] = wb
                if not a[bk]:  # Sportschau zeigt im Pokal keine Bank: nur Abweichungen zur letzten Liga-Startelf
                    t["bank"] = []
                    t["fehlt"] = []  # ohne Bank nicht ablesbar; GitHub Action aufstellungen_live trägt die Bank nach Abpfiff nach
                    t["bank_offen"] = True
                    t["nicht_startelf"] = [dict(n=n, p=pos_von(n, verein, kader), pid=pid_von(n, verein, kader))
                                           for n in (a.get(vg) or {}).get("nicht_mehr_in_startelf", [])]
            out.append({"id": f"aufstellung-{'pokal-' if wb == 'DFB-Pokal' else 'cl-' if wb else ''}{KURZ[verein]}-{tt}", "zeit": zeit,
                        "spielerin": "Spielansetzung", "verein": verein,
                        "nr": "", "pos": "Spielansetzung", "tags": ["POKAL" if wb == "DFB-Pokal" else "EUROPAPOKAL" if wb else "TOP"],
                        "headline": f"Offizielle Aufstellung: {verein} gegen {t['gegner']}", "text": [], "kickbase": "",
                        "quellen": [{"name": "Sportschau", "url": a["url"]}], "aufstellung": t})
    json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"aufstellungs_meldungen": len(out)}))


if __name__ == "__main__":
    main()
