#!/usr/bin/env python3
"""WOSOINSIDER: Klickzahlen aus GoatCounter für die Themenwahl in Inside.

Holt die Zählung der letzten Wochen (Standard 28 Tage) über die GoatCounter-API und rechnet sie
auf "Öffnungen pro Meldung" je Verein und Spielerin um. Grundlage sind die Ereignisse, die der Ticker
beim Öffnen einer Meldung sendet (meldung/<id>, spielerin/<slug>, verein/<slug>).

Warum pro Meldung: Vereine mit vielen Meldungen bekommen sonst automatisch mehr Klicks und damit mehr
Analysen. Die Zahl der Meldungen im Zeitraum kommt aus der Git-Historie von news.json, weil die Datei
selbst nur die letzten 50 Meldungen enthält.

    GOATCOUNTER_TOKEN=... python3 tools/klicks.py --repo . --out klickzahlen.json
    python3 tools/klicks.py --repo . --rohdaten roh.json --out klickzahlen.json   (ohne API, zum Testen)

Der Token wird nur als HTTP-Header verwendet und nirgends geschrieben. Zählt nur die Webversion,
die App sendet keine Zählung.
"""
import argparse, json, os, re, subprocess, time, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
API = "https://wosoinsider.goatcounter.com/api/v0"

VEREINE = {  # Name in news.json -> Kürzel wie in inside.json
    "FC Bayern": "FCB", "VfL Wolfsburg": "WOB", "Eintracht Frankfurt": "SGE", "Bayer Leverkusen": "B04",
    "1. FC Köln": "KOE", "RB Leipzig": "RBL", "Werder Bremen": "SVW", "SC Freiburg": "SCF",
    "Union Berlin": "FCU", "VfB Stuttgart": "VFB", "TSG Hoffenheim": "TSG", "Hamburger SV": "HSV",
    "1. FC Nürnberg": "FCN", "Mainz 05": "M05",
}
TOP_TEAMS = {"FCB", "WOB", "SGE", "B04"}
GLAETTUNG = 3      # Meldungen, mit denen der Ligaschnitt in jede Vereinsquote eingeht (kleine Zahlen dämpfen)
MIN_OEFFNUNGEN = 150  # ab so vielen geöffneten Meldungen im Zeitraum gelten die Zahlen als belastbar
IGNORIEREN = re.compile(r"^(intern/|/claude-test)")


def slug(s):
    """Gleich wie slug() in wosoinsider-web/tools/zaehler_ticker.js."""
    s = str(s).lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s))


# ------------------------------------------------------------------ GoatCounter
def api(pfad, token, params):
    url = f"{API}/{pfad}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    for versuch in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and versuch < 3:
                time.sleep(2 + versuch * 3)
                continue
            raise SystemExit(f"GoatCounter {pfad}: HTTP {e.code}")
        except urllib.error.URLError as e:
            if versuch < 3:
                time.sleep(3)
                continue
            raise SystemExit(f"GoatCounter {pfad}: {e.reason}")


def hole_hits(token, start, ende):
    """Alle Pfade mit Tageswerten. Blättern über exclude_paths, Drosselung der API beachten."""
    basis = {"start": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": ende.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "limit": 100, "daily": "true"}
    hits, gesehen = [], []
    for _ in range(50):
        p = dict(basis)
        if gesehen:
            p["exclude_paths"] = ",".join(map(str, gesehen))
        d = api("stats/hits", token, p)
        neu = d.get("hits") or []
        hits += neu
        gesehen += [h["path_id"] for h in neu]
        if not d.get("more") or not neu:
            break
        time.sleep(0.5)
    return hits


# ------------------------------------------------------------------ Meldungen im Zeitraum
def meldungen_im_zeitraum(repo, ab):
    """Alle Meldungen, die seit 'ab' in news.json standen, aus der Git-Historie (eindeutig nach id)."""
    seit = (ab - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        commits = subprocess.run(["git", "-C", repo, "log", f"--since={seit}", "--format=%H", "--", "news.json"],
                                 capture_output=True, text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commits = []
    staende = [open(os.path.join(repo, "news.json"), encoding="utf-8").read()]
    for c in commits:
        r = subprocess.run(["git", "-C", repo, "show", f"{c}:news.json"], capture_output=True, text=True)
        if r.returncode == 0:
            staende.append(r.stdout)
    alle = {}
    for text in staende:
        try:
            ms = json.loads(text).get("meldungen", [])
        except (json.JSONDecodeError, AttributeError):
            continue
        for m in ms:
            if m.get("typ") == "punkt" or not m.get("id"):
                continue
            try:
                t = datetime.fromisoformat(m.get("zeit", "")).replace(tzinfo=BERLIN)
            except ValueError:
                continue
            if t >= ab:
                alle.setdefault(m["id"], m)
    return alle, len(commits)


# ------------------------------------------------------------------ Auswertung
def summe(h, ab=None):
    if ab is None:
        return h.get("count", 0)
    return sum(s.get("daily", 0) for s in h.get("stats", []) if s.get("day", "") >= ab)


def auswerten(hits, meldungen, tage, jetzt):
    ab7 = (jetzt - timedelta(days=7)).strftime("%Y-%m-%d")
    hits = [h for h in hits if not IGNORIEREN.match(h.get("path", ""))]
    ereignis = {h["path"]: h for h in hits if h.get("event")}
    # Geklickte Meldungen, die in keinem gespiegelten Stand von news.json vorkommen, zählen mit (ohne Verein)
    for p in ereignis:
        if p.startswith("meldung/") and p.split("/", 1)[1] not in meldungen:
            meldungen[p.split("/", 1)[1]] = {"id": p.split("/", 1)[1], "headline": ereignis[p].get("title", "")}
    seiten = [h for h in hits if not h.get("event")]

    # Meldungen je Verein und Spielerin im Zeitraum
    je_verein, je_spielerin = {}, {}
    for m in meldungen.values():
        v = m.get("verein")
        if v:
            je_verein.setdefault(v, []).append(m["id"])
        if m.get("spielerin") and m.get("pos") not in ("Trainer", "Trainerin", "Spielansetzung"):
            je_spielerin.setdefault((m["spielerin"], v), []).append(m["id"])

    oeffnungen = sum(summe(h) for p, h in ereignis.items() if p.startswith("meldung/"))
    belastbar = oeffnungen >= MIN_OEFFNUNGEN

    vereine = []
    for name, kz in VEREINE.items():
        h = ereignis.get(f"verein/{slug(name)}", {})
        n = len(je_verein.get(name, []))
        vereine.append({"k": kz, "name": name, "top_team": kz in TOP_TEAMS, "meldungen": n,
                        "oeffnungen": summe(h), "oeffnungen_7t": summe(h, ab7)})
    ges_m = sum(v["meldungen"] for v in vereine)
    ges_o = sum(v["oeffnungen"] for v in vereine)
    schnitt = ges_o / ges_m if ges_m else 0
    for v in vereine:
        v["pro_meldung"] = round(v["oeffnungen"] / v["meldungen"], 2) if v["meldungen"] else None
        # Interesse: geglättete Quote im Verhältnis zum Ligaschnitt, 1.0 = Schnitt
        if not belastbar:
            v["interesse"] = None
        elif schnitt:
            g = (v["oeffnungen"] + GLAETTUNG * schnitt) / (v["meldungen"] + GLAETTUNG)
            v["interesse"] = round(g / schnitt, 2)
        else:
            v["interesse"] = 1.0
    vereine.sort(key=lambda v: (-(v["interesse"] or 0), -v["oeffnungen"], -v["meldungen"]))

    spielerinnen = []
    for (name, verein), ids in je_spielerin.items():
        h = ereignis.get(f"spielerin/{slug(name)}", {})
        if not summe(h):
            continue
        spielerinnen.append({"n": name, "k": VEREINE.get(verein, ""), "meldungen": len(ids),
                             "oeffnungen": summe(h), "oeffnungen_7t": summe(h, ab7),
                             "pro_meldung": round(summe(h) / len(ids), 2)})
    spielerinnen.sort(key=lambda s: (-s["oeffnungen"], -s["pro_meldung"]))

    meld = []
    for p, h in ereignis.items():
        if p.startswith("meldung/"):
            mid = p.split("/", 1)[1]
            m = meldungen.get(mid, {})
            meld.append({"id": mid, "headline": h.get("title") or m.get("headline", ""),
                         "verein": VEREINE.get(m.get("verein", ""), ""), "tags": m.get("tags", []),
                         "oeffnungen": summe(h)})
    meld.sort(key=lambda x: -x["oeffnungen"])

    # Interesse je Tag (Thema), z. B. ob VERLETZUNG oder SPIELBERICHT mehr gelesen wird
    tags = {}
    for x in meld:
        for t in x["tags"] or ["OHNE"]:
            e = tags.setdefault(t, {"oeffnungen": 0, "meldungen": 0})
            e["oeffnungen"] += x["oeffnungen"]
    for m in meldungen.values():
        for t in m.get("tags") or ["OHNE"]:
            tags.setdefault(t, {"oeffnungen": 0, "meldungen": 0})["meldungen"] += 1
    for e in tags.values():
        e["pro_meldung"] = round(e["oeffnungen"] / e["meldungen"], 2) if e["meldungen"] else None

    reiter = {p.split("/", 1)[1]: summe(h) for p, h in ereignis.items() if p.startswith("reiter/")}
    return {
        "belastbar": belastbar,
        "hinweis": ("Genug Daten: Interesse darf zwischen gleich starken Themen entscheiden." if belastbar else
                    f"Noch zu wenig Daten ({oeffnungen} von {MIN_OEFFNUNGEN} geöffneten Meldungen). "
                    "Themenwahl ohne Klickzahlen, Top-Teams bevorzugen."),
        "summen": {"besuche_seiten": sum(summe(h) for h in seiten), "meldungen_geoeffnet": oeffnungen,
                   "meldungen_veroeffentlicht": len(meldungen),
                   "analyse_geoeffnet": summe(ereignis.get("inside/analyse", {})),
                   "spiele_geoeffnet": sum(summe(h) for p, h in ereignis.items() if p.startswith("spiel/"))},
        "reiter": dict(sorted(reiter.items(), key=lambda x: -x[1])),
        "vereine": vereine,
        "spielerinnen": spielerinnen[:20],
        "meldungen_top": meld[:15],
        "tags": dict(sorted(tags.items(), key=lambda x: -(x[1]["pro_meldung"] or 0))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="klickzahlen.json")
    ap.add_argument("--tage", type=int, default=28)
    ap.add_argument("--rohdaten", help="gespeicherte Antwort von stats/hits statt API (Test)")
    a = ap.parse_args()

    jetzt = datetime.now(timezone.utc)
    start = (jetzt - timedelta(days=a.tage)).replace(hour=0, minute=0, second=0, microsecond=0)
    if a.rohdaten:
        hits = json.load(open(a.rohdaten, encoding="utf-8"))["hits"]
    else:
        token = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
        if not token:
            raise SystemExit("GOATCOUNTER_TOKEN fehlt")
        hits = hole_hits(token, start, jetzt + timedelta(hours=1))

    meldungen, n_commits = meldungen_im_zeitraum(a.repo, start.astimezone(BERLIN))
    erg = auswerten(hits, meldungen, a.tage, jetzt)
    out = {"stand": jetzt.astimezone(BERLIN).strftime("%Y-%m-%dT%H:%M"), "zeitraum_tage": a.tage,
           "quelle": "GoatCounter (nur Webversion, die App zählt nicht)", **erg,
           "_technik": {"pfade": len(hits), "news_staende": n_commits + 1}}
    with open(os.path.join(a.repo, a.out) if not os.path.isabs(a.out) else a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({"belastbar": out["belastbar"], **out["summen"], "pfade": len(hits)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
