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


def aufstellung(heim, gast, wettbewerb=None):
    url = spiel_url(heim, gast, wettbewerb)
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
    return {"startelf_heim_voll": sh, "startelf_gast_voll": sg,
            "startelf_heim": nach(sh), "startelf_gast": nach(sg),
            "bank_heim": nach(_namen(bank[0], "home")) if bank else [], "bank_gast": nach(_namen(bank[0], "away")) if bank else [],
            "url": url}


if __name__ == "__main__":
    a = aufstellung(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(a)
