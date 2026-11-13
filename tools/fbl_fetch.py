#!/usr/bin/env python3
"""FBL Insider: Vorfilter ohne KI.

Sammelt neue Meldungen zur Frauen-Bundesliga, filtert sie über die Kaderliste,
fasst Doppelungen zusammen und gibt nur Neues als kompaktes JSON aus.

Aufruf:
  python3 fbl_fetch.py --kader fbl-kader.csv --state fbl-state.json --out kandidaten.json [--tage 2]

Ergebnis (kandidaten.json):
  {"stand", "nichts_neu": bool, "meldungen": [...], "sperren_neu": [...], "aufstellungen": [...]}
Der Zustand (bereits gesehene Meldungen, Sperren, Aufstellungen) wird in --state fortgeschrieben.
"""
import argparse, csv, hashlib, html, json, re, sys, time, unicodedata
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
BERLIN = ZoneInfo("Europe/Berlin")  # mit Sommer- und Winterzeit
SP = "https://www.sportschau.de/live-und-ergebnisse/fussball/deutschland-bundesliga-frauen/"
POKAL_WETTBEWERBE = [("https://www.sportschau.de/live-und-ergebnisse/fussball/deutschland-dfb-pokal-frauen/", "DFB-Pokal"),
                     ("https://www.sportschau.de/live-und-ergebnisse/fussball/uefa-champions-league-frauen/", "Champions League")]

VEREINE = {
    "FC Bayern": ['"FC Bayern" Frauen', '"Bayern-Frauen"'],
    "VfL Wolfsburg": ['"VfL Wolfsburg" Frauen', '"Wolfsburgerinnen"'],
    "Eintracht Frankfurt": ['"Eintracht Frankfurt" Frauen'],
    "Bayer Leverkusen": ['"Bayer 04" Frauen', '"Leverkusen" Frauen-Bundesliga'],
    "1. FC Köln": ['"1. FC Köln" Frauen', '"FC-Frauen"'],
    "RB Leipzig": ['"RB Leipzig" Frauen'],
    "Werder Bremen": ['"Werder" Frauen', '"Werderfrauen"'],
    "SC Freiburg": ['"SC Freiburg" Frauen'],
    "Union Berlin": ['"Union" Frauen Bundesliga', '"Unionerinnen"'],
    "VfB Stuttgart": ['"VfB Stuttgart" Frauen', '"VfB-Frauen"'],
    "TSG Hoffenheim": ['"Hoffenheim" Frauen'],
    "Hamburger SV": ['"HSV" Frauen Bundesliga', '"HSV-Frauen"'],
    "1. FC Nürnberg": ['"Nürnberg" Frauen Bundesliga', '"Clubfrauen"'],
    "Mainz 05": ['"Mainz 05" Frauen'],
}
ALLGEMEIN = ['"Frauen-Bundesliga"', '"Frauen-Bundesliga" verletzt', '"Frauen-Bundesliga" Ausfall']
# Bevorzugte Quellen beim Zusammenfassen (Index = Rang)
RANG = ["dfb.de", "sportschau.de", "kicker.de", "fcbayern.com", "vfl-wolfsburg.de", "eintracht.de", "bayer04.de",
        "fc.de", "rbleipzig.com", "werder.de", "scfreiburg.com", "fc-union-berlin.de", "vfb.de", "tsg-hoffenheim.de",
        "hsv.de", "fcn.de", "mainz05.de", "butenunbinnen.de", "hessenschau.de", "ndr.de", "br.de", "zdf.de", "sport1.de"]
SPERR_TITEL = re.compile(r"Saison-Stats|Tickets?\b|im TV|TV-Programm|Liveticker|Kollektion|Trikot|Sonderkollektion|Hockey|Handball|Basketball|Volleyball|2\. (?:Frauen-)?Bundesliga|2\. Liga|Regionalliga|ÖFB|Männer|Relive|\blive\b|Hier läuft|Spiel-Infos|Aufstellung .*Spieltag|Tabelle - |besuchen|Rathaus|Bilanz gegen|\| Statistiken \||Spielschema|Spielerprofil|live score|Final Score|H2H|20(?:1\d|2[0-5])\b", re.I)
VEREIN_WORTE = {v: re.compile(p, re.I) for v, p in {
    "FC Bayern": r"Bayern|FCB", "VfL Wolfsburg": r"Wolfsburg|VfL", "Eintracht Frankfurt": r"Eintracht|Frankfurt|SGE",
    "Bayer Leverkusen": r"Leverkusen|Bayer 04", "1. FC Köln": r"Köln|FC-Frauen", "RB Leipzig": r"Leipzig|RBL",
    "Werder Bremen": r"Werder|Bremen", "SC Freiburg": r"Freiburg|SCF", "Union Berlin": r"Union Berlin|Unionerinnen|Eisernen", "VfB Stuttgart": r"VfB|Stuttgart",
    "TSG Hoffenheim": r"Hoffenheim|TSG", "Hamburger SV": r"HSV|Hamburg", "1. FC Nürnberg": r"Nürnberg|Club", "Mainz 05": r"Mainz"}.items()}
FRAUEN_SIGNAL = re.compile(r"Frauen|Fußballerinnen|Spielerin|Torhüterin|Kapitänin|Trainerin|FBL|-innen\b|erinnen\b", re.I)


def get(url, timeout=20, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            if versuch == 2:
                print(f"WARN {url[:80]}: {e}", file=sys.stderr)
                return ""
            time.sleep(2 * (versuch + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


IDS = {}  # Name -> Spielerinnen-ID (aus kader.csv)


def lade_kader(pfad):
    spielerinnen = []
    for r in csv.DictReader(open(pfad, encoding="utf-8")):
        name = r["name"].strip()
        teile = name.split()
        nach = teile[-1] if teile else name
        spielerinnen.append({"id": r.get("id", "").strip(), "name": name, "nach": nach, "verein": r.get("verein", ""), "pos": r.get("position", ""),
                             "kanji": [k for k in (r.get("kanji") or "").split("|") if k]})  # japanische Schreibweisen, mit | getrennt
    # Nachnamen, die mehrfach vorkommen oder zu kurz/allgemein sind, nur mit Vornamen zählen
    zaehl = {}
    for s in spielerinnen:
        zaehl[norm(s["nach"])] = zaehl.get(norm(s["nach"]), 0) + 1
    allgemein = {"weiss", "muller", "schneider", "simon", "kramer", "berg", "martin", "lein", "wolter", "fischer", "schulz",
                 "richter", "karl", "steiner", "frank", "bauer", "koch", "wagner", "becker", "hoffmann", "schmitz", "ernst",
                 "kraus", "may", "lang", "haas", "graf", "vogt", "hahn", "doorn", "imai", "kats", "starke", "hagel", "schon",
                 "wieder", "schick", "bremer", "harder", "dunst", "kett", "bender", "platner", "weber", "grund", "jansen",
                 "schafer", "elsen", "lein", "bleil", "steinert", "gutmann", "jaron", "kehrer", "stolze", "simmen",
                 "hecke", "norman", "beck", "dick", "kolb", "karl", "berger", "kurz", "stark", "freitag", "sommer", "winter"}
    for s in spielerinnen:
        n = norm(s["nach"]).strip()
        s["nur_voll"] = len(n) < 5 or zaehl[n] > 1 or n in allgemein
    return spielerinnen


def finde_spielerinnen(text, kader):
    """Voller Name zählt immer. Nachname allein nur, wenn der Titel auch Frauen-Bezug oder den Verein der Spielerin nennt."""
    t = " " + norm(text) + " "
    kontext = bool(FRAUEN_SIGNAL.search(text) or "Frauen-Bundesliga" in text)
    treffer = []
    for s in kader:
        if " " + norm(s["name"]).strip() + " " in t or any(k in text for k in s.get("kanji", [])):
            treffer.append(s["name"])
        elif not s["nur_voll"] and " " + norm(s["nach"]).strip() + " " in t:
            vw = VEREIN_WORTE.get(s["verein"]) or VEREIN_WORTE.get(KURZ.get(s["verein"], ""))
            if kontext or (vw and vw.search(text)):
                treffer.append(s["name"])
    return treffer


KURZ = {"FC Bayern München": "FC Bayern", "Bayer 04 Leverkusen": "Bayer Leverkusen", "SV Werder Bremen": "Werder Bremen",
        "1. FC Union Berlin": "Union Berlin", "1. FSV Mainz 05": "Mainz 05"}


def ist_bundesliga_team_meldung(text):
    return bool((FRAUEN_SIGNAL.search(text) or "Frauen-Bundesliga" in text) and any(p.search(text) for p in VEREIN_WORTE.values()))


def google_news(query, tage):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{query} when:{tage}d", "hl": "de", "gl": "DE", "ceid": "DE:de"})
    xml = get(url)
    if not xml:
        return []
    out = []
    try:
        for it in ET.fromstring(xml).findall(".//item"):
            src = it.find("source")
            titel = re.sub(r"\s+-\s+[^-]+$", "", it.findtext("title") or "").strip()
            try:
                zeit = parsedate_to_datetime(it.findtext("pubDate")).astimezone(BERLIN)
            except Exception:
                zeit = None
            out.append({"titel": titel, "quelle": src.text if src is not None else "",
                        "domain": urllib.parse.urlparse(src.attrib.get("url", "")).netloc.replace("www.", "") if src is not None else "",
                        "zeit": zeit, "glink": it.findtext("link") or ""})
    except ET.ParseError:
        pass
    return out


def sportschau_rss():
    xml = get("https://www.sportschau.de/fussball/frauen-bundesliga/index~rss2.xml")
    out = []
    try:
        for it in ET.fromstring(xml).findall(".//item"):
            try:
                zeit = parsedate_to_datetime(it.findtext("pubDate")).astimezone(BERLIN)
            except Exception:
                zeit = None
            out.append({"titel": (it.findtext("title") or "").strip(), "quelle": "sportschau.de", "domain": "sportschau.de",
                        "zeit": zeit, "url": it.findtext("link") or "", "teaser": html.unescape(re.sub("<[^>]+>", "", it.findtext("description") or ""))[:300]})
    except ET.ParseError:
        pass
    return out


def google_aufloesen(glink):
    """Wandelt einen news.google.com-Link in die Original-URL um."""
    try:
        aid = glink.split("/articles/")[1].split("?")[0]
        body = get(glink)
        sig = re.search(r'data-n-a-sg="([^"]+)"', body)
        ts = re.search(r'data-n-a-ts="([^"]+)"', body)
        if not (sig and ts):
            return glink
        req = [["Fbv4je", json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                                                     "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], aid, int(ts.group(1)), sig.group(1)])]]
        r = get("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                data=urllib.parse.urlencode({"f.req": json.dumps([req])}).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        m = re.search(r'https?://[^"\\]+', r.split("garturlres", 1)[1]) if "garturlres" in r else None
        return m.group(0) if m else glink
    except Exception:
        return glink


def auszug(url, zeichen=1200):
    """Kurzer Textauszug: zuerst strukturierte Artikeldaten (JSON-LD), dann Absätze ohne Code und Cookie-Texte."""
    if "news.google.com" in url:
        return ""
    seite = get(url, timeout=15)
    if not seite:
        return ""
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', seite, re.S):
        m = re.search(r'"articleBody"\s*:\s*"((?:[^"\\]|\\.)+)"', block)
        if m:
            try:
                return html.unescape(json.loads('"' + m.group(1) + '"'))[:zeichen]
            except Exception:
                pass
    beschreibung = ""
    m = re.search(r'<meta[^>]+(?:property|name)="(?:og:description|description)"[^>]+content="([^"]+)"', seite)
    if m:
        beschreibung = html.unescape(m.group(1)).strip()
    absaetze = [html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", p))).strip()
                for p in re.findall(r"<p[^>]*>(.*?)</p>", seite, re.S)]
    schlecht = re.compile(r"Cookie|Datenschutz|JavaScript|Newsletter|Abonn|Zählpixel|Drittanbieter|Funktionen der Website|[{}=]|&&|function\(")
    absaetze = [p for p in absaetze if len(p) > 60 and not schlecht.search(p)]
    text = " ".join(([beschreibung] if beschreibung else []) + absaetze)
    return text[:zeichen]


def sperren(state):
    seite = get("https://www.dfb.de/ueber-uns/verbandsrecht/sperren")
    t = html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", seite)))
    m = re.search(r"aktuellen Sperren in der Google Pixel Frauen-Bundesliga(.*?)(?:Teamoffizielle|aktuellen Sperren in der 2\.)", t)
    if not m:
        return []
    block = re.sub(r"Stand: \d\d\.\d\d\.\d{4}", " ", m.group(1)).replace("Spielerin Verein Urteil Grund", " ")
    vereine = ["FC Bayern München", "VfL Wolfsburg", "Eintracht Frankfurt", "Bayer 04 Leverkusen", "Bayer Leverkusen", "1. FC Köln",
               "RB Leipzig", "SV Werder Bremen", "Werder Bremen", "SC Freiburg", "1. FC Union Berlin", "Union Berlin", "VfB Stuttgart",
               "TSG Hoffenheim", "TSG 1899 Hoffenheim", "Hamburger SV", "1. FC Nürnberg", "1. FSV Mainz 05", "Mainz 05"]
    vre = "|".join(re.escape(v) for v in sorted(vereine, key=len, reverse=True))
    eintraege = re.findall(r"\s*(.+?) (" + vre + r") ((?:ein|zwei|drei|vier|fünf|\d+) Meisterschaftsspiele?) ((?:Gelb-)?Rote Karte|\S+)", block)
    neu = []
    alt = set(state.get("sperren", []))
    aktuell = []
    for name, verein, urteil, grund in eintraege:
        key = h(name + urteil)
        aktuell.append(key)
        if key not in alt:
            neu.append({"spielerin": name, "verein": verein.strip(), "urteil": urteil, "grund": grund,
                        "quelle": "https://www.dfb.de/ueber-uns/verbandsrecht/sperren"})
    state["sperren"] = aktuell
    return neu


def lies_aufstellung(ma, basis=None):
    """Liest Startelfen und Bänke einer Partie. Gibt None zurück, solange keine Aufstellung veröffentlicht ist."""
    roh = get((basis or SP) + ma + "/aufstellung")
    i = roh.find("hs-lineup")
    if i < 0:
        return None
    t = html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "|", roh[i:i + 40000])))
    tok = [x.strip() for x in t.split("|") if x.strip()]
    if "Auswechslungen" not in tok:
        return None
    start = tok[1:tok.index("Auswechslungen")]
    namen = [w for j, w in enumerate(start) if j > 0 and not re.fullmatch(r"\d+\.?", w) and re.fullmatch(r"\d+", start[j - 1])]
    if len(namen) < 22:
        # Spielerinnen ohne Rückennummer (z. B. Pokalgegner aus unteren Ligen): alle Namens-Tokens nehmen (Finn 01.11.2026)
        alle = [w for w in start if not re.fullmatch(r"\d+\.?", w) and not re.fullmatch(r"\d+'?", w)]
        if len(alle) == 22:
            namen = alle
        else:
            return None
    beendet = any(re.fullmatch(r"\d+\.", x) for x in start)
    bank = tok[tok.index("Reservebank") + 1: tok.index("Trainer")] if "Reservebank" in tok and "Trainer" in tok else []
    heim, gast = ma.split("/")[1].split("_")
    # Bank der Heimelf steht vor der Bank der Gäste. Trennstelle: erste Bankspielerin aus dem Gästekader.
    # Ist nur ein Kader bekannt (Champions League: nur der Bundesliga-Verein), trennt der bekannte Kader.
    # Fehlt eine Bank noch ganz (Sportschau 10.11.2026: nur PSG-Bank, Bayern-Bank kam später), bleibt diese Seite leer
    # statt die Liste in der Mitte zu teilen (sonst bekam Bayern die halbe PSG-Bank).
    def im(n, kader):
        return norm(n.split()[-1]).strip() in kader
    gast_namen = KADER_NACH_SLUG.get(gast, set())
    heim_namen = KADER_NACH_SLUG.get(heim, set())
    if gast_namen:
        halb = next((j for j, n in enumerate(bank) if im(n, gast_namen)), len(bank))
    elif heim_namen:
        halb = next((j for j, n in enumerate(bank) if not im(n, heim_namen)), len(bank))
    else:
        halb = (len(bank) + 1) // 2
    return {"heim": heim, "gast": gast, "beendet": beendet,
            "startelf_heim": namen[:11], "startelf_gast": namen[11:22],
            "bank_heim": bank[:halb], "bank_gast": bank[halb:]}


SLUG_VEREIN = {"bayern-muenchen": "FC Bayern München", "vfl-wolfsburg": "VfL Wolfsburg", "eintracht-frankfurt": "Eintracht Frankfurt",
               "bayer-leverkusen": "Bayer 04 Leverkusen", "1-fc-koeln": "1. FC Köln", "rb-leipzig": "RB Leipzig",
               "werder-bremen": "Werder Bremen", "sc-freiburg": "SC Freiburg", "1-fc-union-berlin": "1. FC Union Berlin",
               "vfb-stuttgart": "VfB Stuttgart", "tsg-hoffenheim": "TSG Hoffenheim", "hamburger-sv": "Hamburger SV",
               "1-fc-nuernberg": "1. FC Nürnberg", "1-fsv-mainz-05": "1. FSV Mainz 05"}
KADER_NACH_SLUG = {}


def setze_kader_slugs(kader):
    for slug, verein in SLUG_VEREIN.items():
        KADER_NACH_SLUG[slug] = {norm(s["nach"]).strip() for s in kader if s["verein"] == verein}


def vergleich(alt, start, bank):
    if not alt:
        return None
    kader_alt = set(alt["start"]) | set(alt["bank"])
    kader_neu = set(start) | set(bank)
    return {"neu_in_startelf": sorted(set(start) - set(alt["start"])),
            "nicht_mehr_in_startelf": sorted(set(alt["start"]) - set(start)),
            "fehlt_im_kader": sorted(kader_alt - kader_neu),
            "neu_im_kader": sorted(kader_neu - kader_alt)}


def merke_kader(state, a):
    k = state.setdefault("letzter_kader", {})
    k[a["heim"]] = {"start": a["startelf_heim"], "bank": a["bank_heim"]}
    k[a["gast"]] = {"start": a["startelf_gast"], "bank": a["bank_gast"]}


def zusatz_spiele(pfad, tage):
    """Spiele von heute und gestern aus spielplan.json, z. B. Nachholspiele, die nicht auf der aktuellen Spieltagsseite stehen."""
    try:
        sp = json.load(open(pfad, encoding="utf-8"))
    except Exception:
        return []
    out = []
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            m = re.search(r"deutschland-bundesliga-frauen/(ma\d+/[a-z0-9\-_]+)/", p.get("url", ""))
            an = p.get("anstoss", "")
            if not m or len(an) < 10:
                continue
            datum = f"{an[8:10]}.{an[5:7]}.{an[0:4]}"
            if datum in tage and (datum, m.group(1)) not in out:
                out.append((datum, m.group(1)))
    return out


def aufstellungen(state, jetzt, spielplan_pfad=""):
    """Offizielle Aufstellungen von heute und gestern, mit Abgleich zum letzten Spiel des jeweiligen Teams.
    Quelle: aktuelle Spieltagsseite der Sportschau plus Spiele von heute und gestern aus spielplan.json (Nachholspiele)."""
    seite = get(SP + "spiele-und-ergebnisse")
    ev = [(m.start(), "D", m.group(0)) for m in re.finditer(r"\b\d\d\.\d\d\.20\d\d\b", seite)]
    ev += [(m.start(), "M", m.group(1)) for m in re.finditer(r"deutschland-bundesliga-frauen/(ma\d+/[a-z0-9\-_]+)/", seite)]
    ev.sort()
    tage = {jetzt.strftime("%d.%m.%Y"), (jetzt - timedelta(days=1)).strftime("%d.%m.%Y")}
    datum, spiele = None, []
    for _, art, wert in ev:
        if art == "D":
            datum = wert
        elif datum in tage and wert not in [s[1] for s in spiele]:
            spiele.append((datum, wert))
    if spielplan_pfad:
        for datum, ma in zusatz_spiele(spielplan_pfad, tage):
            if ma not in [s[1] for s in spiele]:
                spiele.append((datum, ma))
    spiele = [(d, m, SP, None) for d, m in spiele]
    # Pokal und Champions League (Finn, 01.11.2026): gleiche Sportschau-Logik, nur Spiele mit Bundesliga-Verein
    for basis, wb in POKAL_WETTBEWERBE:
        try:
            ps = get(basis + "spiele-und-ergebnisse")
        except Exception as e:
            print(f"WARN {wb}: {e}", file=sys.stderr)
            continue
        pfad = basis.rstrip("/").split("/")[-1]
        pev = [(m.start(), "D", m.group(0)) for m in re.finditer(r"\b\d\d\.\d\d\.20\d\d\b", ps)]
        pev += [(m.start(), "M", m.group(1)) for m in re.finditer(pfad + r"/(ma\d+/[a-z0-9\-_]+)/", ps)]
        pev.sort()
        pd = None
        for _, art, wert in pev:
            if art == "D":
                pd = wert
            elif pd in tage and wert not in [x[1] for x in spiele]:
                h, g = wert.split("/")[1].split("_")
                if h in SLUG_VEREIN or g in SLUG_VEREIN:
                    spiele.append((pd, wert, basis, wb))
    erledigt = set(state.get("aufstellungen", []))
    out = []
    for datum, ma, basis, wb in spiele:
        a = lies_aufstellung(ma, basis)
        if not a:
            continue
        key = ma + ("-ende" if a["beendet"] else "-start")
        if key in erledigt:
            continue
        letzte = state.get("letzter_kader", {})
        out.append({"spiel": f"{a['heim']} gegen {a['gast']}", "datum": datum,
                    "status": "beendet oder läuft" if a["beendet"] else "vor Anpfiff",
                    "startelf_heim": a["startelf_heim"], "startelf_gast": a["startelf_gast"],
                    "bank_heim": a["bank_heim"], "bank_gast": a["bank_gast"],
                    "vergleich_heim": vergleich(letzte.get(a["heim"]), a["startelf_heim"], a["bank_heim"]),
                    "vergleich_gast": vergleich(letzte.get(a["gast"]), a["startelf_gast"], a["bank_gast"]),
                    "url": basis + ma + "/aufstellung", **({"wettbewerb": wb} if wb else {})})
        erledigt.add(key)
        if a["beendet"] and not wb:  # Vergleichsbasis bleibt das letzte Ligaspiel
            merke_kader(state, a)  # erst nach dem Spiel als Vergleichsbasis übernehmen
    state["aufstellungen"] = sorted(erledigt)[-60:]
    return out


def kader_vorbelegen(state, ma_liste):
    """Einmalig: letzte Aufstellungen als Vergleichsbasis speichern."""
    for ma in ma_liste:
        a = lies_aufstellung(ma)
        if a:
            merke_kader(state, a)


VQ_NAMEN = {"FC Bayern München": "FC Bayern", "Bayer 04 Leverkusen": "Bayer Leverkusen", "SV Werder Bremen": "Werder Bremen",
            "1. FC Union Berlin": "Union Berlin", "1. FSV Mainz 05": "Mainz 05"}
JUGEND = re.compile(r"\bU ?1\d\b|\bU ?2[03]\b|Juniorinnen|Mädchen|zweite Mannschaft|Zweite Frauen|Frauen II|\bII\b|2\. Frauen-Bundesliga", re.I)


def vereinsquellen(pfad, tage):
    """Direkte Vereinsquellen (RSS, Sitemap, Schnittstellen, Listenseiten). Fehler einer Quelle stoppen den Lauf nicht."""
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vereinsquellen as vq
    out = []
    for q in json.load(open(pfad, encoding="utf-8")):
        try:
            items = vq.pruefe(q, tage)
        except Exception as e:
            print(f"WARN Vereinsquelle {q['verein']}: {e}", file=sys.stderr)
            continue
        verein = VQ_NAMEN.get(q["verein"], q["verein"])
        if verein.startswith("Geissblog"):
            verein = "1. FC Köln"
        if verein.startswith(("DFB", "International", "Medien")):  # Sammelquellen ohne Verein: Kaderabgleich entscheidet
            verein = ""
        for i in items[:15]:
            zeit = i["datum"].replace(tzinfo=timezone.utc).astimezone(BERLIN) if i.get("datum") else None
            titel = re.sub(r"\s+-\s+[^-]+$", "", i["titel"]).strip() if q["typ"] == "googlenews" else i["titel"].strip()
            link = i["url"]
            eintrag = {"titel": titel, "quelle": q["verein"], "domain": urllib.parse.urlparse(link).netloc.replace("www.", ""),
                       "zeit": zeit, "verein_hint": verein, "vereinsquelle": bool(verein)}
            if "news.google.com" in link:
                eintrag["glink"] = link
            else:
                eintrag["url"] = link
            out.append(eintrag)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kader", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tage", type=int, default=2)
    ap.add_argument("--max", type=int, default=12, help="maximale Anzahl Meldungsgruppen")
    ap.add_argument("--quellen", default="", help="Pfad zu vereinsquellen.json")
    ap.add_argument("--spielplan", default="", help="Pfad zu spielplan.json (Nachholspiele für Aufstellungen)")
    ap.add_argument("--nur-merken", action="store_true", help="alles Gefundene als gesehen markieren, nichts ausgeben (Erststart)")
    ap.add_argument("--vorbelegen", nargs="*", help="Spiel-IDs (ma.../slug), deren Aufstellung als Vergleichsbasis gespeichert wird; danach Ende")
    a = ap.parse_args()

    jetzt = datetime.now(BERLIN)
    try:
        state = json.load(open(a.state, encoding="utf-8"))
    except Exception:
        state = {}
    setze_kader_slugs(lade_kader(a.kader))
    if a.vorbelegen:
        kader_vorbelegen(state, a.vorbelegen)
        json.dump(state, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(json.dumps({"vorbelegt": sorted(state.get("letzter_kader", {}))}, ensure_ascii=False))
        return
    gesehen = state.get("gesehen", {})  # hash -> datum
    kader = lade_kader(a.kader)
    IDS.update({k["name"]: k["id"] for k in kader})

    roh = []
    for verein, queries in VEREINE.items():
        for q in queries:
            for it in google_news(q, a.tage):
                it["verein_hint"] = verein
                roh.append(it)
            time.sleep(0.6)
    for q in ALLGEMEIN:
        roh += google_news(q, a.tage)
        time.sleep(0.6)
    roh += sportschau_rss()
    if a.quellen:
        roh += vereinsquellen(a.quellen, a.tage)

    # Filtern: Spielerin im Titel oder Verein plus Frauen-Signal
    gruppen = {}
    grenze = jetzt - timedelta(days=a.tage)
    for it in roh:
        if it["zeit"] and it["zeit"] < grenze:
            continue
        text = it["titel"] + " " + it.get("teaser", "")
        if SPERR_TITEL.search(it["titel"]):
            continue
        namen = finde_spielerinnen(text, kader)
        if not namen:
            if JUGEND.search(it["titel"]):
                continue
            if not (it.get("vereinsquelle") or ist_bundesliga_team_meldung(text)):
                continue
        tk = h(norm(it["titel"]))
        if tk in gesehen:
            continue
        if namen:
            schluessel = "|".join(sorted(set(namen)))
        else:  # Vereinsmeldung ohne Namen: pro Verein und Tag zusammenfassen
            verein = it.get("verein_hint") if it.get("vereinsquelle") else next((v for v, p in VEREIN_WORTE.items() if p.search(it["titel"])), "Liga")
            schluessel = "team:" + verein + ":" + (it["zeit"].strftime("%Y-%m-%d") if it["zeit"] else "")
        g = gruppen.setdefault(schluessel, {"spielerinnen": sorted(set(namen)), "artikel": [],
                                            "verein": schluessel.split(":")[1] if schluessel.startswith("team:") else ""})
        if any(norm(x["titel"]) == norm(it["titel"]) for x in g["artikel"]):
            continue
        g["artikel"].append(it)

    # Gruppen ordnen: mit Spielerin zuerst, dann nach Aktualität
    def rang(it):
        d = it.get("domain", "")
        return next((i for i, r in enumerate(RANG) if r in d), 99)

    from concurrent.futures import ThreadPoolExecutor
    sortiert = sorted(gruppen.values(), key=lambda g: (not g["spielerinnen"], -max((x["zeit"] or jetzt).timestamp() for x in g["artikel"])))
    def bearbeite(g):
        arts = sorted(g["artikel"], key=lambda x: (rang(x), -(x["zeit"] or jetzt).timestamp()))[:3]
        haupt = arts[0]
        url = haupt.get("url") or google_aufloesen(haupt["glink"])
        if "news.google.com" in url:  # Finn 13.11.2026: Vereinsquellen über Google News kamen nur als Google-Link ohne Text an
            url = google_aufloesen(url)
        return {
            "spielerinnen": g["spielerinnen"],
            "spielerinnen_ids": [IDS.get(x, "") for x in g["spielerinnen"]],
            "gruppe": "spielerin" if g["spielerinnen"] else "verein",
            "verein_hint": g["verein"] or haupt.get("verein_hint", ""),
            "titel": haupt["titel"],
            "zeit": haupt["zeit"].strftime("%Y-%m-%dT%H:%M") if haupt["zeit"] else "",
            "quelle": haupt["quelle"], "url": url,
            "auszug": (ausz := auszug(url, 8000 if (haupt.get("vereinsquelle") or re.search(r"vorbericht|nachbericht|spielbericht|vorschau|pressekonferenz|personal", url + " " + haupt["titel"], re.I)) else 1200)),
            # Namen aus dem ganzen Auszug (Vorberichte nennen das Personal erst unten, nicht im Titel)
            "spielerinnen_im_text": sorted(set(finde_spielerinnen(ausz, kader)) - set(g["spielerinnen"])),
            "weitere": [{"titel": x["titel"], "quelle": x["quelle"]} for x in arts[1:]],
        }

    if a.nur_merken:
        for g in gruppen.values():
            for x in g["artikel"]:
                gesehen[h(norm(x["titel"]))] = jetzt.strftime("%Y-%m-%d")
        state["gesehen"] = gesehen
        sperren(state)
        json.dump(state, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(json.dumps({"gemerkt": sum(len(g["artikel"]) for g in gruppen.values())}))
        return
    auswahl = sortiert[: a.max]
    with ThreadPoolExecutor(max_workers=8) as ex:
        meldungen = list(ex.map(bearbeite, auswahl))
    for g in auswahl:
        for x in g["artikel"]:
            gesehen[h(norm(x["titel"]))] = jetzt.strftime("%Y-%m-%d")
    # Auch nicht ausgewählte Gruppen nicht als gesehen markieren: sie kommen beim nächsten Lauf wieder dran.

    ergebnis = {
        "stand": jetzt.strftime("%Y-%m-%dT%H:%M"),
        "meldungen": meldungen,
        "sperren_neu": sperren(state),
        "aufstellungen": aufstellungen(state, jetzt, a.spielplan),
        "rest_gruppen": max(0, len(sortiert) - a.max),
    }
    ergebnis["nichts_neu"] = not (ergebnis["meldungen"] or ergebnis["sperren_neu"] or ergebnis["aufstellungen"])

    # Zustand schlank halten: nur 10 Tage merken
    grenze_s = (jetzt - timedelta(days=10)).strftime("%Y-%m-%d")
    state["gesehen"] = {k: v for k, v in gesehen.items() if v >= grenze_s}
    state["letzter_lauf"] = ergebnis["stand"]
    json.dump(state, open(a.state, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(ergebnis, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"nichts_neu": ergebnis["nichts_neu"], "meldungen": len(meldungen),
                      "sperren_neu": len(ergebnis["sperren_neu"]), "aufstellungen": len(ergebnis["aufstellungen"]),
                      "rest_gruppen": ergebnis["rest_gruppen"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
