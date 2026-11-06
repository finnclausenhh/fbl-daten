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
import argparse, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbl_fetch as F  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
FENSTER = 150  # Minuten nach Anstoß
WARTE = 90
MINUTE_TAKT = 300  # nur Minute geändert: höchstens alle 5 Minuten pushen, sonst bricht GitHub Pages jeden Deploy ab (Bau dauert ca. 2 Min.)
LETZTER = [0.0]


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
    return {"text": status, "ergebnis": [er.group(1), er.group(2)], "minute": minute, "tore": tore_lesen(s), "karten": karten_lesen(s), "wechsel": wechsel_lesen(s)}


def wechsel_lesen(s):
    """Wechsel aus dem Liveticker (data-event_action enthält "sub" oder "change"): seite, ein, aus (Nachnamen), min.
    Format der Sportschau beim ersten echten Wechsel geprüft? Noch nicht (Stand 06.11.2026, 19:30), daher großzügig."""
    heim = (re.search(r'team_home="(\d+)"', s) or [None, ""])[1]
    out = []
    for li in re.finditer(r'<li class="liveticker"[^>]*data-event_action="([^"]*)"[^>]*>(.*?)</li>', s, re.S):
        if not re.search(r"sub|change|wechsel", li.group(1), re.I):
            continue
        b = li.group(2)
        te = (re.search(r'/verein/te(\d+)/', b) or [None, ""])[1]
        namen = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r'class="person-name[^"]*">(.*?)</div>', b, re.S)]
        txt = re.sub(r"<[^>]+>", " ", (re.search(r"<b>(.*?)</b>", b, re.S) or [None, ""])[1])
        m = re.search(r"([A-ZÄÖÜ][^,:()]*?)\s+(?:kommt\s+)?für\s+([A-ZÄÖÜ][^,:().]*)", txt)
        ein, aus = (m.group(1), m.group(2)) if m else (namen[0] if namen else "", namen[1] if len(namen) > 1 else "")
        add = re.sub(r"<[^>]+>", "", (re.search(r'class="person-shortname[^"]*person-additional[^"]*">(.*?)</div>', b, re.S) or [None, ""])[1]).strip()
        if not aus and add:
            aus = re.sub(r"^[A-ZÄÖÜ]\. ", "", add)
        mi = (re.search(r'class="liveticker-minute">([^<]*)<', b) or [None, ""])[1].strip().rstrip(".").replace(".+", "+").replace(".", "")
        if ein:
            out.append({"seite": "heim" if te == heim else "gast", "ein": ein.split()[-1], "aus": aus.split()[-1] if aus else "", "min": mi})
    return sorted(out, key=lambda k: int(re.sub(r"\D.*", "", k["min"]) or 0))


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
    if r.get("tore") or p.get("status") == "live":
        p["tore"] = r.get("tore") or []
    if r.get("karten") or p.get("status") == "live":
        p["karten"] = r.get("karten") or []
    if r.get("wechsel") or p.get("status") == "live":
        p["wechsel"] = r.get("wechsel") or []
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
    return alt != (p.get("status"), p.get("ergebnis"), p.get("minute"), p.get("tore"), p.get("karten"), p.get("wechsel"))


def live_json(a, sp):
    """Kleine live.json für den Web-Ticker, der sie direkt von raw.githubusercontent.com liest (GitHub Pages braucht zu lange)."""
    heute = datetime.now(TZ).strftime("%Y-%m-%d")
    sp_ = {p["id"]: {k: p.get(k) for k in ("status", "ergebnis", "minute", "tore", "karten", "wechsel") if p.get(k) is not None}
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
    for p in offen:
        r = lesen(p["url"])
        vorher = (p.get("status"), p.get("ergebnis"), p.get("tore"), p.get("karten"), p.get("wechsel"))
        if r and anwenden(p, r):
            wichtig = wichtig or vorher != (p.get("status"), p.get("ergebnis"), p.get("tore"), p.get("karten"), p.get("wechsel"))
            neu[p["id"]] = {k: p.get(k) for k in ("status", "ergebnis", "minute", "tore", "karten", "wechsel")}
            print(f"{jetzt:%H:%M} {p['heim_k']}-{p['gast_k']} {':'.join(p['ergebnis'])} {p.get('minute') or p['status']}")
    if neu and not wichtig and time.time() - LETZTER[0] < MINUTE_TAKT:
        return True, {}  # nur die Minute: beim nächsten Takt mitnehmen
    if neu:
        LETZTER[0] = time.time()
        open(pfad, "w", encoding="utf-8").write(json.dumps(sp, ensure_ascii=False, separators=(",", ":")))
        live_json(a, sp)
        if a.push:
            pushen(a, neu)
    return True, neu


def pushen(a, neu):
    nachricht = "Live-Ergebnis: " + ", ".join(f"{i} {':'.join(v['ergebnis'])} {v.get('minute') or v['status']}" for i, v in neu.items())
    for _ in range(4):
        git(a, "add", "spielplan.json", "live.json")
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
