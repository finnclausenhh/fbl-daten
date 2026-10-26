#!/usr/bin/env python3
"""WOSOINSIDER Ausfall-Wächter: prüft, ob die gespiegelten Daten frisch sind.

Läuft als GitHub Action im Repo fbl-daten. Schlägt der Check fehl (Exit-Code 1), schickt GitHub
automatisch eine Mail an den Repo-Inhaber. Kein Claude-Lauf, keine Kosten.

Regeln:
  1. Ticker: Neuester Zeitstempel aus status.json (letzter_lauf, falls vorhanden) oder news.json (stand)
     darf höchstens --ticker-stunden alt sein (Standard 30 mit status.json, sonst 48).
  2. Spielplan: Keine Partie darf mehr als 3 Stunden nach Anstoß noch als "geplant" geführt werden.
  3. Inside: inside.json (stand) höchstens 8 Tage alt.

Aufruf: python3 tools/frische_check.py [--jetzt 2026-10-29T22:00]
"""
import argparse, json, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def zeit(s):
    if not s:
        return None
    d = datetime.fromisoformat(s if "T" in s else s + "T00:00")
    return d if d.tzinfo else d.replace(tzinfo=BERLIN)


def lade(pfad):
    try:
        return json.load(open(pfad, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--jetzt")
    ap.add_argument("--ticker-stunden", type=float)
    ap.add_argument("--inside-tage", type=float, default=8)
    a = ap.parse_args()
    jetzt = zeit(a.jetzt) if a.jetzt else datetime.now(BERLIN)
    r = Path(a.repo)
    probleme, info = [], {}

    status, news = lade(r / "status.json"), lade(r / "news.json")
    t_status = zeit((status or {}).get("letzter_lauf"))
    t_news = zeit((news or {}).get("stand"))
    grenze = a.ticker_stunden or (30 if t_status else 48)
    letzter = max(filter(None, [t_status, t_news]), default=None)
    info["ticker_letzter"] = letzter.isoformat() if letzter else None
    if not letzter:
        probleme.append("Ticker: weder status.json noch news.json mit Zeitstempel gefunden")
    elif jetzt - letzter > timedelta(hours=grenze):
        probleme.append(f"Ticker: seit {round((jetzt - letzter).total_seconds() / 3600)} Stunden kein Update (Grenze {grenze:g} h). "
                        "Geplante Aufgaben WOSOINSIDER Wochentage/Spieltage und das Spiegeln nach GitHub prüfen.")

    sp = lade(r / "spielplan.json")
    if sp:
        info["spielplan_stand"] = sp.get("stand")
        haengt, ids = [], set()
        for t in sp.get("spieltage", []):
            for p in t.get("partien", []) + t.get("nachholspiele", []):
                if p.get("id") in ids:
                    continue
                ids.add(p.get("id"))
                an = zeit(p.get("anstoss"))
                if p.get("status") == "geplant" and an and an.hour + an.minute > 0 and jetzt - an > timedelta(hours=3):
                    haengt.append(f"{p['heim']} gegen {p['gast']} ({p['anstoss']})")
        if haengt:
            probleme.append(f"Spielplan: {len(haengt)} Partie(n) nach Anstoß noch als geplant geführt, z. B. {haengt[0]}. "
                            "spielplan_bau.py läuft vermutlich nicht automatisch.")

    ins = lade(r / "inside.json")
    t_ins = zeit((ins or {}).get("stand"))
    info["inside_stand"] = t_ins.isoformat() if t_ins else None
    if t_ins and jetzt - t_ins > timedelta(days=a.inside_tage):
        probleme.append(f"Inside: seit {(jetzt - t_ins).days} Tagen nicht aktualisiert (Lauf Di 7:41 prüfen).")

    print(json.dumps({"ok": not probleme, "jetzt": jetzt.strftime("%Y-%m-%dT%H:%M"), **info, "probleme": probleme}, ensure_ascii=False, indent=1))
    if probleme and "GITHUB_STEP_SUMMARY" in __import__("os").environ:
        with open(__import__("os").environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## WOSOINSIDER Ausfall-Wächter\n\n" + "\n".join(f"- {x}" for x in probleme) + "\n")
    sys.exit(1 if probleme else 0)


if __name__ == "__main__":
    main()
