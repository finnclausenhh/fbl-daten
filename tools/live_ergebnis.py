#!/usr/bin/env python3
"""Live-Ergebnis im Spielplan (Finn, 06.11.2026). Läuft als GitHub Action, ohne Claude.

Für jede Partie in spielplan.json, deren Anstoß höchstens 150 Minuten zurückliegt und die nicht "beendet" ist, liest es
die Liveticker-Seite der Sportschau (Feld "url") und schreibt in spielplan.json:
  status "live" mit "ergebnis" [heim, gast] und "minute" ("12", "45+2" oder "HZ"),
  bei Abpfiff status "beendet" mit Endstand (Torschützinnen ergänzt später der Spieltage-Lauf).
App und Web zeigen "live" schon an (Ergebnis mit Minute statt Uhrzeit).
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
    return {"text": status, "ergebnis": [er.group(1), er.group(2)], "minute": minute}


def anwenden(p, r):
    """Gibt True zurück, wenn sich die Partie geändert hat."""
    t = r["text"].lower()
    alt = (p.get("status"), p.get("ergebnis"), p.get("minute"))
    if any(w in t for w in ("ende", "beendet", "abpfiff", "abgeschlossen")):
        p["status"] = "beendet"
        p["ergebnis"] = r["ergebnis"]
        p.pop("minute", None)
    elif "halbzeit" in t or "verlängerung" in t or "elfmeterschießen" in t:
        p["status"] = "live"
        p["ergebnis"] = r["ergebnis"]
        p["minute"] = "HZ" if t == "halbzeit" else (r["minute"] or r["text"])
    else:
        return False  # noch nicht angepfiffen oder unbekannter Text
    return alt != (p.get("status"), p.get("ergebnis"), p.get("minute"))


def git(a, *args, check=True):
    return subprocess.run(["git", "-C", a.repo, *args], check=check)


def runde(a):
    pfad = os.path.join(a.repo, "spielplan.json")
    jetzt = datetime.now(TZ)
    sp = json.load(open(pfad, encoding="utf-8"))
    offen = [p for p in partien(sp) if im_fenster(p, jetzt)]
    if not offen:
        return False, {}
    neu = {}
    for p in offen:
        r = lesen(p["url"])
        if r and anwenden(p, r):
            neu[p["id"]] = {k: p.get(k) for k in ("status", "ergebnis", "minute")}
            print(f"{jetzt:%H:%M} {p['heim_k']}-{p['gast_k']} {':'.join(p['ergebnis'])} {p.get('minute') or p['status']}")
    if neu:
        open(pfad, "w", encoding="utf-8").write(json.dumps(sp, ensure_ascii=False, separators=(",", ":")))
        if a.push:
            pushen(a, neu)
    return True, neu


def pushen(a, neu):
    nachricht = "Live-Ergebnis: " + ", ".join(f"{i} {':'.join(v['ergebnis'])} {v.get('minute') or v['status']}" for i, v in neu.items())
    for _ in range(4):
        git(a, "add", "spielplan.json")
        if subprocess.run(["git", "-C", a.repo, "diff", "--cached", "--quiet"]).returncode == 0:
            return
        git(a, "-c", "user.name=WOSOINSIDER", "-c", "user.email=finnclausenhh@users.noreply.github.com", "commit", "-qm", nachricht)
        if git(a, "push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
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
            git(a, "pull", "-q", "--rebase", "origin", "main", check=False)
        laeuft, _ = runde(a)
        if a.einmal or not laeuft or time.time() + WARTE > ende:
            print("kein Spiel im Fenster" if not laeuft else "Ende der Laufzeit")
            break
        time.sleep(WARTE)


if __name__ == "__main__":
    main()
