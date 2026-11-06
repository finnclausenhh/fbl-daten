#!/usr/bin/env python3
"""Live-Ergebnis im Spielplan (Finn, 06.11.2026). Läuft als GitHub Action, ohne Claude.

Für jede Partie in spielplan.json, deren Anstoß höchstens 150 Minuten zurückliegt und die nicht "beendet" ist, liest es
die Liveticker-Seite der Sportschau (Feld "url") und schreibt in spielplan.json:
  status "live" mit "ergebnis" [heim, gast] und "minute" ("12", "45+2" oder "HZ"),
  bei Abpfiff status "beendet" mit Endstand (Torschützinnen ergänzt später der Spieltage-Lauf).
App und Web zeigen "live" schon an (Ergebnis mit Minute statt Uhrzeit).
Tore und Status sofort, reine Minuten höchstens alle 5 Minuten (Pages-Deploy).
Schleife: alle WARTE Sekunden, bis kein Spiel mehr läuft oder LAUFZEIT Minuten vorbei sind.

Aufruf: python3 tools/live_ergebnis.py --repo . [--push] [--laufzeit 170] [--einmal]
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbl_fetch as F  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
FENSTER = 150  # Minuten nach Anstoß
WARTE = 45  # 06.11.2026: 90 -> 45 s, Sportschau-Seite ist klein genug
MINUTE_TAKT = 300  # nur Minute geändert: höchstens alle 5 Minuten pushen, sonst bricht GitHub Pages jeden Deploy ab (Bau dauert ca. 2 Min.)
LETZTER = [0.0]

# API-Football (Pro) als zweite Quelle (06.11.2026): ein Abruf je Runde für alle laufenden Spiele der Liga 82.
# Genutzt für: Tore, die dort früher stehen (Ergebnis sofort, Name nachgezogen, sobald die Sportschau sie hat), die laufende
# Minute und als Ersatz, wenn die Sportschau-Seite nicht lesbar ist. Wechsel und Karten nur aus der Sportschau.
# live_messung.json hält fest, welche Quelle ein Tor zuerst hatte (Vergleich für Finn).
AF_LIGA = 82
AF_TEAM = {1858: "TSG", 1859: "B04", 1860: "FCB", 1863: "WOB", 1867: "SCF", 1870: "SVW", 1871: "KOE",
           14014: "SGE", 20487: "FCN", 20498: "HSV", 20501: "RBL", 21564: "M05", 24130: "VFB", 24133: "FCU"}
MESS = {}


def af_live():
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        return {}
    try:
        req = urllib.request.Request(f"https://v3.football.api-sports.io/fixtures?live={AF_LIGA}",
                                     headers={"x-apisports-key": key, "User-Agent": "WOSOINSIDER-Live/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"WARN API-Football: {e}", file=sys.stderr)
        return {}
    if d.get("errors"):
        print(f"WARN API-Football: {d['errors']}", file=sys.stderr)
    out = {}
    for f in d.get("response", []):
        hk, gk = AF_TEAM.get(f["teams"]["home"]["id"]), AF_TEAM.get(f["teams"]["away"]["id"])
        if not hk or not gk:
            continue
        hid = f["teams"]["home"]["id"]
        tore = []
        for e in f.get("events") or []:
            if e.get("type") == "Goal" and "missed" not in (e.get("detail") or "").lower():
                t = {"seite": "heim" if e["team"]["id"] == hid else "gast", "n": (((e.get("player") or {}).get("name") or "").split() or [""])[-1],
                     "min": str(e["time"]["elapsed"]) + (f"+{e['time']['extra']}" if e["time"].get("extra") else ""), "quelle": "af"}
                if "own" in (e.get("detail") or "").lower():
                    t["art"] = "Eigentor"
                elif "penalty" in (e.get("detail") or "").lower():
                    t["art"] = "Elfmeter"
                tore.append(t)
        st = f["fixture"]["status"]
        out[(hk, gk)] = {"kurz": st.get("short"), "el": st.get("elapsed"), "ex": st.get("extra"),
                         "erg": [str(f["goals"]["home"] or 0), str(f["goals"]["away"] or 0)], "tore": tore}
    return out


def af_als_r(af):
    """Ersatz, wenn die Sportschau nichts liefert."""
    text = {"1H": "1. Halbzeit", "HT": "pause", "2H": "2. Halbzeit", "ET": "verlängerung", "BT": "pause", "P": "elfmeterschießen",
            "FT": "beendet", "AET": "beendet", "PEN": "beendet"}.get(af["kurz"])
    if not text:
        return None
    return {"text": text, "ergebnis": af["erg"], "minute": af_minute(af), "tore": af["tore"], "karten": [], "wechsel": [], "uhr": {}}


def af_minute(af):
    if af.get("kurz") not in ("1H", "2H", "ET") or not af.get("el"):
        return None
    return str(af["el"]) + (f"+{af['ex']}" if af.get("ex") else "")


def messen(p, quelle, erg):
    if not erg:
        return
    m = MESS.setdefault(p["id"], {"spiel": f"{p['heim_k']}-{p['gast_k']}"})
    m.setdefault(":".join(erg), {}).setdefault(quelle, datetime.now(TZ).strftime("%H:%M:%S"))


def mischen(p, r, af):
    """Sportschau (r) und API-Football (af) zusammenführen."""
    if r:
        messen(p, "sportschau", r["ergebnis"])
    if af:
        messen(p, "apifootball", af["erg"])
    if not af:
        return r
    if not r:
        return af_als_r(af)
    if sum(map(int, af["erg"])) > sum(map(int, r["ergebnis"])):
        # Tor zuerst bei API-Football: Ergebnis sofort, fehlende Tore je Seite aus API-Football anhängen
        tore = list(r.get("tore") or [])
        for seite, i in (("heim", 0), ("gast", 1)):
            fehlt = int(af["erg"][i]) - sum(1 for t in tore if t["seite"] == seite)
            if fehlt > 0:
                tore += [t for t in af["tore"] if t["seite"] == seite][-fehlt:]
        r = dict(r, ergebnis=af["erg"], tore=tore)
    m = af_minute(af)
    if m and "halbzeit" in r["text"].lower() and r["text"].lower() not in ("pause", "halbzeitpause", "halbzeit"):
        r = dict(r, minute=m)
    return r


def partien(sp):
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            yield p


def im_fenster(p, jetzt):
    if p.get("status") in ("beendet", "abgesagt") or not p.get("url") or "T00:00" in p.get("anstoss", "T00:00"):
        return False
    an = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=TZ)
    return an - timedelta(minutes=2) <= jetzt <= an + timedelta(minutes=FENSTER)


def lesen(url):
    s = F.get(url)
    if not s:
        return None
    st = re.search(r'class="match-status[^"]*">([^<]*)<', s)
    er = re.search(r'class="match-result match-result-0">\s*(\d+)\s*:\s*(\d+)\s*<', s)
    if not st or not er:
        return None
    status = st.group(1).strip()
    mins = [m.strip() for m in re.findall(r'class="liveticker-minute">([^<]+)<', s) if m.strip()]
    minute = None
    if mins:
        minute = mins[0].replace(" ", "").rstrip(".").replace(".+", "+").replace(".", "")
    return {"text": status, "ergebnis": [er.group(1), er.group(2)], "minute": minute, "tore": tore_lesen(s), "karten": karten_lesen(s), "wechsel": wechsel_lesen(s), "uhr": uhr_lesen(s)}


def uhr_lesen(s):
    """Echte Anpfiffzeiten (UTC) aus dem Liveticker: a1 = Anpfiff, a2 = Anpfiff 2. Halbzeit. Damit können Web und App die Minute
    selbst hochzählen, ohne für jede Minute zu pushen (06.11.2026)."""
    u = {}
    for kind, k in (("game-start", "a1"), ("second-half-start", "a2")):
        m = re.search(r'data-event_kind="' + kind + r'"[^>]*?data-event_created="([^"]*)"', s)
        if m:
            u[k] = m.group(1)
    return u


def wechsel_lesen(s):
    """Wechsel aus dem Liveticker: je Wechsel zwei direkt aufeinanderfolgende Einträge data-event_action="playing" mit
    data-event_kind "substitute-in" und "substitute-out" (Format geprüft am 06.11.2026, Ticker neueste zuerst)."""
    heim = (re.search(r'team_home="(\d+)"', s) or [None, ""])[1]
    folge = []
    for li in re.finditer(r'<li class="liveticker"[^>]*data-event_kind="substitute-(in|out)"[^>]*>(.*?)</li>', s, re.S):
        b = li.group(2)
        name = re.sub(r"<[^>]+>", "", (re.search(r'class="person-name[^"]*">(.*?)</div>', b, re.S) or [None, ""])[1]).strip()
        te = (re.search(r'/verein/te(\d+)/', b) or [None, ""])[1]
        mi = (re.search(r'class="liveticker-minute">([^<]*)<', b) or [None, ""])[1].strip().rstrip(".").replace(".+", "+").replace(".", "")
        if name and te:
            folge.append((li.group(1), name.split()[-1], te, mi))
    out, x = [], 0
    while x < len(folge):
        art, n, te, mi = folge[x]
        w = {"seite": "heim" if te == heim else "gast", "ein": "", "aus": "", "min": mi}
        w["ein" if art == "in" else "aus"] = n
        if x + 1 < len(folge) and folge[x + 1][0] != art and folge[x + 1][2:] == (te, mi):
            w["aus" if art == "in" else "ein"] = folge[x + 1][1]; x += 1
        out.append(w); x += 1
    return out[::-1]

def karten_lesen(s):
    """Karten aus dem Liveticker (data-event_action="card"): seite, n (Nachname), min, art gelb|gelbrot|rot."""
    heim = (re.search(r'team_home="(\d+)"', s) or [None, ""])[1]
    out = []
    for li in re.finditer(r'<li class="liveticker"[^>]*data-event_action="card" data-event_kind="([^"]*)"[^>]*>(.*?)</li>', s, re.S):
        kind, b = li.group(1).lower(), li.group(2)
        name = re.sub(r"<[^>]+>", "", (re.search(r'class="person-name[^"]*">(.*?)</div>', b, re.S) or [None, ""])[1]).strip()
        te = (re.search(r'/verein/te(\d+)/', b) or [None, ""])[1]
        if not name or not te:
            continue
        art = "gelbrot" if "yellow" in kind and "red" in kind else "rot" if "red" in kind else "gelb"
        mi = (re.search(r'class="liveticker-minute">([^<]*)<', b) or [None, ""])[1].strip().rstrip(".").replace(".+", "+").replace(".", "")
        out.append({"seite": "heim" if te == heim else "gast", "n": name.split()[-1], "min": mi, "art": art})
    return sorted(out, key=lambda k: int(re.sub(r"\D.*", "", k["min"]) or 0))


def tore_lesen(s):
    """Tore aus dem Ereignis-Modul der Sportschau, Format wie in spielplan.json: seite, n (Nachname), min, vorlage, art."""
    m = re.search(r'<div class="module-events">(.*?)</ul>', s, re.S)
    out = []
    for li in re.finditer(r'<li class="event ([^"]*)">(.*?)</li>', m.group(1) if m else "", re.S):
        kl = li.group(1).split()
        if "goal" not in kl and not any("goal" in k.lower() for k in kl):
            continue
        b = li.group(2)
        g = lambda c: (re.search(r'class="' + c + r'[^"]*">([^<]*)<', b) or [None, ""])[1].strip()
        t = {"seite": "heim" if "home" in kl else "gast", "n": g("person-surname") or g("person-name"),
             "min": g("match_event-minute").rstrip(".").replace(".+", "+").replace(".", "")}
        v = re.sub(r"^[A-ZÄÖÜ]\. ", "", g("person-shortname person-shortname- person-additional"))
        art = " ".join(kl).lower()
        if "own" in art:
            t["art"] = "Eigentor"
        elif "penalty" in art:
            t["art"] = "Elfmeter"
        elif v:
            t["vorlage"] = v
        out.append(t)
    return out


def schaetzung(p, t):
    """Minute ohne Liveticker-Eintrag: in der 1. Halbzeit aus dem Anstoß, sonst nur die Phase."""
    if t.startswith("1"):
        m = int((datetime.now(TZ) - datetime.fromisoformat(p["anstoss"]).replace(tzinfo=TZ)).total_seconds() // 60) + 1
        return str(max(m, 1)) if m <= 45 else "45+"
    return "2. HZ" if t.startswith("2") else "LIVE"


def anwenden(p, r):
    """Gibt True zurück, wenn sich die Partie geändert hat."""
    t = r["text"].lower()
    alt = (p.get("status"), p.get("ergebnis"), p.get("minute"), p.get("tore"), p.get("karten"), p.get("wechsel"))
    uhr_alt = p.get("uhr")
    if r.get("tore") or p.get("status") == "live":
        p["tore"] = r.get("tore") or []
    if r.get("karten") or p.get("status") == "live":
        p["karten"] = r.get("karten") or []
    if r.get("wechsel") or p.get("status") == "live":
        p["wechsel"] = r.get("wechsel") or []
    if r.get("uhr"):
        p["uhr"] = r["uhr"]
    if any(w in t for w in ("ende", "beendet", "abpfiff", "abgeschlossen")):
        p["status"] = "beendet"
        p["ergebnis"] = r["ergebnis"]
        p.pop("minute", None)
    elif t in ("pause", "halbzeitpause"):
        p["status"] = "live"
        p["ergebnis"] = r["ergebnis"]
        p["minute"] = "HZ"
    elif "halbzeit" in t or "verlängerung" in t or "elfmeterschießen" in t:
        p["status"] = "live"
        p["ergebnis"] = r["ergebnis"]
        p["minute"] = "HZ" if t == "halbzeit" else (r["minute"] or schaetzung(p, t))
    else:
        return False  # noch nicht angepfiffen oder unbekannter Text
    if p["status"] not in ("live", "beendet"):
        return False
    return alt != (p.get("status"), p.get("ergebnis"), p.get("minute"), p.get("tore"), p.get("karten"), p.get("wechsel")) or uhr_alt != p.get("uhr")


def live_json(a, sp):
    """Kleine live.json für den Web-Ticker, der sie direkt von raw.githubusercontent.com liest (GitHub Pages braucht zu lange)."""
    heute = datetime.now(TZ).strftime("%Y-%m-%d")
    sp_ = {p["id"]: {k: p.get(k) for k in ("status", "ergebnis", "minute", "tore", "karten", "wechsel", "uhr") if p.get(k) is not None}
           for p in partien(sp) if p.get("anstoss", "").startswith(heute) and p.get("ergebnis")}
    open(os.path.join(a.repo, "live.json"), "w", encoding="utf-8").write(
        json.dumps({"stand": datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S"), "spiele": sp_}, ensure_ascii=False))


def git(a, *args, check=True):
    return subprocess.run(["git", "-C", a.repo, *args], check=check)


def runde(a):
    pfad = os.path.join(a.repo, "spielplan.json")
    jetzt = datetime.now(TZ)
    sp = json.load(open(pfad, encoding="utf-8"))
    offen = [p for p in partien(sp) if im_fenster(p, jetzt)]
    if not offen:
        return False, {}
    neu, wichtig = {}, False
    AF = af_live() if any(p.get("heim_k") in AF_TEAM.values() for p in offen) else {}
    for p in offen:
        r = mischen(p, lesen(p["url"]), AF.get((p.get("heim_k"), p.get("gast_k"))))
        vorher = (p.get("status"), p.get("ergebnis"), p.get("tore"), p.get("karten"), p.get("wechsel"), p.get("uhr"), p.get("minute") == "HZ")
        if r and anwenden(p, r):
            wichtig = wichtig or vorher != (p.get("status"), p.get("ergebnis"), p.get("tore"), p.get("karten"), p.get("wechsel"), p.get("uhr"), p.get("minute") == "HZ")
            neu[p["id"]] = {k: p.get(k) for k in ("status", "ergebnis", "minute", "tore", "karten", "wechsel", "uhr")}
            print(f"{jetzt:%H:%M} {p['heim_k']}-{p['gast_k']} {':'.join(p['ergebnis'])} {p.get('minute') or p['status']}")
    if neu and not wichtig and time.time() - LETZTER[0] < MINUTE_TAKT:
        return True, {}  # nur die Minute: beim nächsten Takt mitnehmen
    if neu:
        LETZTER[0] = time.time()
        open(pfad, "w", encoding="utf-8").write(json.dumps(sp, ensure_ascii=False, separators=(",", ":")))
        live_json(a, sp)
        if MESS:
            open(os.path.join(a.repo, "live_messung.json"), "w", encoding="utf-8").write(
                json.dumps({"datum": datetime.now(TZ).strftime("%Y-%m-%d"), "spiele": MESS}, ensure_ascii=False, indent=1))
        if a.push:
            pushen(a, neu)
    return True, neu


def pushen(a, neu):
    nachricht = "Live-Ergebnis: " + ", ".join(f"{i} {':'.join(v['ergebnis'])} {v.get('minute') or v['status']}" for i, v in neu.items())
    for _ in range(4):
        git(a, "add", "spielplan.json", "live.json", *(["live_messung.json"] if os.path.exists(os.path.join(a.repo, "live_messung.json")) else []))
        if subprocess.run(["git", "-C", a.repo, "diff", "--cached", "--quiet"]).returncode == 0:
            return
        git(a, "-c", "user.name=WOSOINSIDER", "-c", "user.email=finnclausenhh@users.noreply.github.com", "commit", "-qm", nachricht)
        if git(a, "push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
            print("gepusht", flush=True)
            return
        # Konflikt: neu holen und nur unsere Felder erneut setzen
        git(a, "fetch", "-q", "origin", "main")
        git(a, "reset", "-q", "--hard", "origin/main")
        pfad = os.path.join(a.repo, "spielplan.json")
        sp = json.load(open(pfad, encoding="utf-8"))
        for p in partien(sp):
            if p.get("id") in neu and p.get("status") != "beendet":
                p.update({k: v for k, v in neu[p["id"]].items() if v is not None})
                if neu[p["id"]]["status"] == "beendet":
                    p.pop("minute", None)
        open(pfad, "w", encoding="utf-8").write(json.dumps(sp, ensure_ascii=False, separators=(",", ":")))
        live_json(a, sp)
        time.sleep(3)
    print("WARN push fehlgeschlagen", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--laufzeit", type=int, default=170)
    ap.add_argument("--einmal", action="store_true")
    a = ap.parse_args()
    ende = time.time() + a.laufzeit * 60
    while True:
        if a.push:
            git(a, "fetch", "-q", "--depth=1", "origin", "main", check=False)
            git(a, "reset", "-q", "--hard", "origin/main", check=False)
        laeuft, _ = runde(a)
        if a.einmal or not laeuft or time.time() + WARTE > ende:
            print("kein Spiel im Fenster" if not laeuft else "Ende der Laufzeit")
            break
        time.sleep(WARTE)


if __name__ == "__main__":
    main()
