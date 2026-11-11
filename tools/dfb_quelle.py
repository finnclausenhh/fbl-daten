#!/usr/bin/env python3
"""Zweite Quelle für Aufstellungen: DFB-Datencenter (offiziell, mit Ersatzbank schon vor Anpfiff).

Finn 01.11.2026: Die Sportschau zeigt im Pokal die Bank erst nach Abpfiff und hat manche Spiele gar nicht sauber.
Das DFB-Datencenter liefert Startelf und Auswechselspielerinnen serverseitig als HTML.

  aufstellung(heim_slug, gast_slug, wettbewerb) -> {"startelf_heim", "startelf_gast", "bank_heim", "bank_gast", "url"} oder None
Slugs wie bei der Sportschau (z. B. "1-fc-nuernberg", "eintracht-frankfurt"). Namen kommen als Nachnamen zurück.
"""
import html, re, sys, unicodedata, urllib.request

SEITEN = {
    None: "https://datencenter.dfb.de/competitions/google-pixel-frauen-bundesliga/seasons/google-pixel-frauen-bundesliga-2026-2027",
    "DFB-Pokal": "https://datencenter.dfb.de/competitions/dfb-pokal-1132/seasons/2026-27",
    "Europa Cup": "https://datencenter.dfb.de/competitions/uefa-womens-europa-cup/seasons/19573",
}
# Kennwort je Verein, das im DFB-Slug sicher vorkommt
KENN = {"bayern-muenchen": "bayern-muenchen", "vfl-wolfsburg": "wolfsburg", "eintracht-frankfurt": "eintracht-frankfurt",
        "bayer-leverkusen": "leverkusen", "1-fc-koeln": "koeln", "rb-leipzig": "rb-leipzig", "werder-bremen": "werder-bremen",
        "sc-freiburg": "sc-freiburg", "1-fc-union-berlin": "union-berlin", "vfb-stuttgart": "vfb-stuttgart",
        "tsg-hoffenheim": "hoffenheim", "hamburger-sv": "hamburger-sv", "1-fc-nuernberg": "1-fc-nuernberg", "1-fsv-mainz-05": "mainz-05"}
_CACHE = {}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "WOSOINSIDER (+https://wosoinsider.de)"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


def _kenn(slug):
    if slug in KENN:
        return KENN[slug]
    teile = [t for t in slug.split("-") if len(t) > 3 and t not in ("frauen", "damen")]
    return max(teile, key=len) if teile else slug


def spiel_url(heim, gast, wettbewerb=None):
    basis = SEITEN.get(wettbewerb)
    if not basis:
        return None
    if basis not in _CACHE:
        try:
            _CACHE[basis] = sorted(set(re.findall(r'https://datencenter\.dfb\.de/matches/([a-z0-9-]+-\d{6,})', _get(basis))))
        except Exception as e:
            print(f"WARN DFB {basis[-40:]}: {e}", file=sys.stderr)
            _CACHE[basis] = []
    kh, kg = _kenn(heim), _kenn(gast)
    for s in _CACHE[basis]:
        i, j = s.find(kh), s.find(kg)
        if i >= 0 and j > i:
            return "https://datencenter.dfb.de/matches/" + s
    return None


def _namen(tabelle, seite):
    out = []
    for z in re.findall(r"<tr>(.*?)</tr>", tabelle.split("<tbody>", 1)[-1].split("</tbody>", 1)[0], re.S):
        m = re.search(r'm-MatchDetails-lineup-person--' + seite + r'">(.*?)</td>', z, re.S)
        if not m:
            continue
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        t = re.sub(r"\s*\((?:T|C|K)\)\s*", " ", t).strip()
        if t:
            out.append(t)
    return out


def slugify(name):
    t = unicodedata.normalize("NFKD", html.unescape(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def aufstellung(heim, gast, wettbewerb=None):
    url = spiel_url(heim, gast, wettbewerb)
    return aufstellung_url(url) if url else None


def aufstellung_url(url):
    """Startelf und Bank einer DFB-Spielseite (auch Europa Cup). Dazu heim_name und gast_name aus dem Seitentitel."""
    if not url:
        return None
    try:
        roh = _get(url)
    except Exception as e:
        print(f"WARN DFB Spiel: {e}", file=sys.stderr)
        return None
    tab = re.findall(r'<table class="m-MatchDetails-lineup-table">(.*?)</table>', roh, re.S)
    if not tab:
        return None
    start = [t for t in tab if "Aufstellung" in t.split("</thead>")[0]]
    bank = [t for t in tab if "Auswechsel" in t.split("</thead>")[0]]
    if not start:
        return None
    sh, sg = _namen(start[0], "home"), _namen(start[0], "away")
    if len(sh) < 11 and len(sg) < 11:
        return None
    nach = lambda l: [n.split()[-1] if n.split() else n for n in l]
    ti = re.search(r"<title>\s*(.*?)\s*-\s*(.*?),\s", roh)
    fo = dict(re.findall(r'lineup-person--(home|away)">\s*(\d(?:-\d){2,4})\s*<', roh))  # Formation (Fußzeile der Aufstellung)
    return {"formation_heim": fo.get("home", ""), "formation_gast": fo.get("away", ""),"startelf_heim_voll": sh, "startelf_gast_voll": sg,
            "startelf_heim": nach(sh), "startelf_gast": nach(sg),
            "bank_heim": nach(_namen(bank[0], "home")) if bank else [], "bank_gast": nach(_namen(bank[0], "away")) if bank else [],
            "heim_name": html.unescape(ti.group(1)) if ti else "", "gast_name": html.unescape(ti.group(2)) if ti else "",
            "url": url}


def europa_spiele():
    """Europa-Cup-Spiele mit Bundesliga-Verein aus der DFB-Saisonseite (der Europa Cup steht nicht bei der Sportschau,
    Finn 11.11.2026: Wolfsburg bei Feyenoord ohne Aufstellung und Bericht).
    [{"id", "url", "heim", "gast", "heim_slug", "gast_slug", "anstoss" (Berlin, YYYY-MM-DDTHH:MM), "ergebnis" oder None}]"""
    try:
        seite = _get(SEITEN["Europa Cup"])
    except Exception as e:
        print(f"WARN DFB Europa Cup: {e}", file=sys.stderr)
        return []
    out = []
    for z in seite.split('class="c-MatchTable-row"')[1:]:
        z = z[:6000]
        mid = re.search(r'id="match_(\d+)"', z)
        dt = re.search(r"(\d\d)\.(\d\d)\.(\d{4})\s+(\d\d):(\d\d)\s+Uhr", z)
        sl = re.search(r'datencenter\.dfb\.de/matches/([a-z0-9-]+-\d{6,})', z)
        th = re.search(r'c-MatchTable-team--home"[^>]*>(.*?)</div>', z, re.S)
        ta = re.search(r'c-MatchTable-team--away"[^>]*>(.*?)</div>', z, re.S)
        if not (mid and dt and sl and th and ta):
            continue
        klar = lambda x: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()
        heim, gast = klar(th.group(1)), klar(ta.group(1))
        hs, gs = slugify(heim), slugify(gast)
        if not any(k in hs or k in gs for k in ("wolfsburg", "eintracht-frankfurt", "bayern-muenchen")):
            continue
        erg = re.search(r"c-MatchTable-score\">.*?(\d+)\s*:\s*(\d+)", z, re.S)
        d, mo, y, hh, mm = dt.groups()
        out.append({"id": mid.group(1), "url": "https://datencenter.dfb.de/matches/" + sl.group(1), "heim": heim, "gast": gast,
                    "heim_slug": hs, "gast_slug": gs, "anstoss": f"{y}-{mo}-{d}T{hh}:{mm}",
                    "ergebnis": [erg.group(1), erg.group(2)] if erg else None})
    return out


def spielverlauf(url):
    """Tore und Karten aus dem Spielverlauf einer DFB-Spielseite: {"ergebnis": [h, g] oder None, "tore": [...], "karten": [...]}.
    Namen als Nachnamen, seite "heim"/"gast"."""
    try:
        roh = _get(url)
    except Exception as e:
        print(f"WARN DFB Spielverlauf: {e}", file=sys.stderr)
        return None
    erg = re.search(r"<title>[^<]*?,\s*(\d+):(\d+),", roh)
    tore, karten = [], []
    for item in roh.split('class="m-MatchDetails-history-item"')[1:]:
        mi = re.search(r"history-minute\">\s*([0-9+]+)'", item)
        if not mi:
            continue
        for seite, sd in (("heim", "home"), ("gast", "away")):
            blk = re.search(r'm-MatchDetails-history-event m-MatchDetails-history-event--' + sd + r'">(.*?)(?=m-MatchDetails-history-event m-MatchDetails-history-event--|$)', item, re.S)
            if not blk:
                continue
            b = blk.group(1)
            seg = re.findall(r'history-event-text-segment">(.*?)</div>', b, re.S)
            namen = [html.unescape(re.sub(r"<[^>]+>", "", x)).replace("\xa0", " ").strip() for x in seg]
            namen = [re.sub(r"\s*für$", "", n).strip() for n in namen if n]
            if not namen:
                continue
            n = namen[0].split()[-1]
            if "icon-goal--goal" in b or "icon-goal--penalty" in b or "icon-goal--own" in b:
                art = "Eigentor" if "icon-goal--own" in b else "Elfmeter" if "icon-goal--penalty" in b else ""
                tore.append({"seite": seite, "n": n, "min": mi.group(1), **({"art": art} if art else {})})
            elif "icon-card--yellow-red" in b or "icon-card--yellowred" in b:
                karten.append({"seite": seite, "n": n, "min": mi.group(1), "art": "gelbrot"})
            elif "icon-card--red" in b:
                karten.append({"seite": seite, "n": n, "min": mi.group(1), "art": "rot"})
            elif "icon-card--yellow" in b:
                karten.append({"seite": seite, "n": n, "min": mi.group(1), "art": "gelb"})
    dedup = lambda l: [x for i, x in enumerate(l) if x not in l[:i]]  # die Seite enthält den Spielverlauf doppelt
    rd = re.search(r"<title>[^<]*?\d{4}/\d{2}\s+([^<-]+?)\s+-\s+DFB", roh)
    return {"ergebnis": [erg.group(1), erg.group(2)] if erg else None, "tore": dedup(tore), "karten": dedup(karten),
            "runde": rd.group(1).strip() if rd else ""}


if __name__ == "__main__":
    a = aufstellung(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(a)
