#!/usr/bin/env python3
"""WOSOINSIDER: Stimmen der Umfragen aus GoatCounter zählen.

Der Ticker sendet beim Abstimmen ein Ereignis "umfrage/<id>/<option>" an GoatCounter.
Dieses Skript holt die Zählung seit Start der ältesten offenen Umfrage und schreibt
umfragen_stand.json: {"stand": ..., "umfragen": {id: {"stimmen": {option: n}, "gesamt": n}}}.
Eigene Testaufrufe (intern/...) zählen nicht. Läuft alle 15 Minuten als GitHub Action.

    GOATCOUNTER_TOKEN=... python3 tools/umfragen.py --repo .
"""
import argparse, json, os, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from klicks import hole_hits  # noqa: E402  (gleiche API-Anbindung wie die Klickzahlen)

BERLIN = ZoneInfo("Europe/Berlin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--rohdaten", help="gespeicherte Antwort von stats/hits statt API (Test)")
    a = ap.parse_args()

    umfragen = json.load(open(os.path.join(a.repo, "umfragen.json"), encoding="utf-8")).get("umfragen", [])
    jetzt = datetime.now(timezone.utc)
    # Zeitraum: 21 Tage zurück deckt jede Umfrage ab (Meldungen leben 14 Tage)
    start = (jetzt - timedelta(days=21)).replace(hour=0, minute=0, second=0, microsecond=0)
    if a.rohdaten:
        hits = json.load(open(a.rohdaten, encoding="utf-8"))["hits"]
    else:
        token = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
        if not token:
            raise SystemExit("GOATCOUNTER_TOKEN fehlt")
        hits = hole_hits(token, start, jetzt + timedelta(hours=1))

    zaehlung = {}
    for h in hits:
        p = h.get("path", "")
        if h.get("event") and p.startswith("umfrage/"):
            teile = p.split("/")
            if len(teile) == 3:
                zaehlung.setdefault(teile[1], {})[teile[2]] = zaehlung.get(teile[1], {}).get(teile[2], 0) + h.get("count", 0)

    out = {"stand": jetzt.astimezone(BERLIN).strftime("%Y-%m-%dT%H:%M"), "umfragen": {}}
    for u in umfragen:
        erlaubt = {o["id"] for o in u.get("optionen", [])}
        st = {o: n for o, n in zaehlung.get(u["id"], {}).items() if o in erlaubt}  # nur bekannte Optionen
        out["umfragen"][u["id"]] = {"stimmen": {o["id"]: st.get(o["id"], 0) for o in u["optionen"]}, "gesamt": sum(st.values())}

    ziel = os.path.join(a.repo, "umfragen_stand.json")
    alt = None
    try:
        alt = json.load(open(ziel, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    # Nur schreiben, wenn sich Stimmen geändert haben (sonst ein Commit alle 15 Minuten)
    if alt and alt.get("umfragen") == out["umfragen"]:
        print(json.dumps({"geaendert": False, **{k: v["gesamt"] for k, v in out["umfragen"].items()}}))
        return
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(json.dumps({"geaendert": True, **{k: v["gesamt"] for k, v in out["umfragen"].items()}}))


if __name__ == "__main__":
    main()
