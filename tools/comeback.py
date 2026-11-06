#!/usr/bin/env python3
"""Comeback- und Erstmals-Meldungen (Finn, 06.11.2026). Ohne Claude, aus spielplan.json, news.json und apifootball.json.

Wie bei Kickbase: Steht eine Spielerin nach einer Verletzung erstmals wieder im Spieltagskader, gibt es eine Meldung
"<Name> nach <Verletzung> zurück im Kader". Sobald sie spielt, wird dieselbe Meldung zu "<Name> feiert Comeback nach
<Verletzung>" mit Minuten, Toren, Vorlagen, Karten und (sobald API-Football sie hat) der Note, unabhängig von der
Spielzeit. Bleibt sie bis zum Abpfiff auf der Bank: "... zurück im Kader, aber ohne Einsatz".
Ebenso für Spielerinnen, die in dieser Saison zum ersten Mal im Spieltagskader stehen ("<Name> erstmals im Kader",
"<Name> feiert Saisondebüt").

Regeln:
- Rückkehr = es gibt eine Meldung mit Tag VERLETZUNG oder Status verletzt (höchstens 180 Tage alt), und seitdem stand sie
  in keinem Spieltagskader (Liga, Pokal, Europapokal), obwohl ihr Team mindestens ein Spiel mit Aufstellung hatte.
- Erstmals = in dieser Saison (ab 1. Juli) in keinem Spieltagskader, Team hatte schon mindestens 3 Spiele mit Aufstellung.
- Gibt es zur Rückkehr schon eine Meldung mit Tag RÜCKKEHR aus den letzten 3 Tagen (z. B. aus der Pressekonferenz),
  entsteht unsere Meldung erst, wenn sie spielt oder das Spiel ohne Einsatz endet (keine Doppelung).
- Id: comeback-<nachname>-<kürzel>-<TTMM> bzw. erstmals-...; die Meldung steht auch in tools/aufstellungen_live.json,
  damit "Aufstellungen schützen" sie nach einem Spiegel wieder einsetzt. Zeit springt nur, wenn die Stufe wechselt.
- Nur Spiele mit offizieller Aufstellung, Anstoß höchstens 3 Tage zurück.

Aufruf als Modul: anwenden(news, live, spielplan, af, kader) -> Liste geänderter Ids. Testweise: python3 tools/comeback.py --repo .
"""
import argparse, csv, json, os, re, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fbl_fetch as F  # noqa: E402
import aufstellung_bau as AB  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
SAISON_AB = "07-01"
VERL = re.compile(r"\b((?:[A-ZÄÖÜ][a-zäöüß]*)?(?:[Kk]reuzband|[Aa]ußenband|[Ii]nnenband|[Mm]eniskus|[Ss]yndesmose)[a-zäöüß]*"
                  r"|[A-ZÄÖÜ][a-zäöüß]*(?:riss|verletzung|zerrung|bruch|prellung|blessur|entzündung|problemen?|beschwerden|reizung|operation))\b")
NICHT = {"Verletzung", "Verletzungen", "Probleme", "Problemen", "Beschwerden", "Operation"}  # zu allgemein, dann lieber "Verletzungspause"


def nk(n):
    return F.norm(str(n)).split()[-1] if str(n).strip() else ""


def minute(m):
    z = re.match(r"\d+", str(m or ""))
    return int(z.group()) if z else None


def partien(sp):
    for t in sp.get("spieltage", []):
        for p in t.get("partien", []) + t.get("nachholspiele", []):
            yield p


def kader_eintraege(news, sp):
    """[(zeit, verein, {nachnamen})] aller Spieltagskader mit offizieller Aufstellung (Liga aus spielplan, Pokal/CL aus news)."""
    out = []
    for p in partien(sp):
        for seite in ("heim", "gast"):
            a = p.get(seite + "_aufstellung")
            if a and a.get("typ") == "offiziell" and a.get("startelf"):
                out.append((p["anstoss"], p[seite], {nk(s.get("voll") or s["n"]) for s in a.get("startelf", []) + a.get("bank", [])}, p.get("id")))
    for m in news["meldungen"]:
        a = m.get("aufstellung")
        if a and a.get("startelf") and m.get("wettbewerb") or (a and a.get("wettbewerb")):
            out.append((m["zeit"], m["verein"], {nk(s["n"]) for s in a.get("startelf", []) + a.get("bank", [])}, None))
    return out


def verletzung(news, verein, name):
    """(Zeit der letzten Verletzungsmeldung, Bezeichnung) oder (None, None)."""
    ms = sorted([m for m in news["meldungen"] if m.get("verein") == verein and nk(m.get("spielerin", "")) == nk(name)
                 and m.get("spielerin", "").split()[0][:1] == name.split()[0][:1]], key=lambda m: m["zeit"], reverse=True)
    t = next((m["zeit"] for m in ms if "VERLETZUNG" in m.get("tags", []) or m.get("status") == "verletzt"), None)
    if not t:
        return None, None
    bez = None
    for m in ms:  # neueste Meldung mit konkreter Diagnose
        if not ({"VERLETZUNG", "RÜCKKEHR", "UPDATE"} & set(m.get("tags", [])) or m.get("status") == "verletzt"):
            continue
        for x in VERL.findall(" ".join([m.get("headline", "")] + m.get("text", [])[:1])):  # nur Überschrift und erster Absatz
            if x not in NICHT and not x.endswith("verletzungen"):
                bez = x + "n" if x.endswith("probleme") else x  # "nach Muskelproblemen"
                break
        if bez:
            break
    return t, bez or "Verletzungspause"


def presse_rueckkehr(news, verein, name, jetzt):
    g = (jetzt - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    return any(m.get("verein") == verein and nk(m.get("spielerin", "")) == nk(name) and "RÜCKKEHR" in m.get("tags", [])
               and m["zeit"] >= g and not m["id"].startswith(("comeback-", "erstmals-")) for m in news["meldungen"])


def bei(v):
    """"des FC Bayern", "von Werder Bremen" usw."""
    if v.startswith("TSG"):
        return "der " + v
    if re.match(r"(FC|1\. FC|VfL|VfB|SC|Hamburger SV)\b", v):
        return "des " + v
    return "von " + v


def note_text(n):
    return "sehr gut" if n >= 7.5 else "gut" if n >= 7.0 else "ordentlich" if n >= 6.5 else "durchwachsen" if n >= 6.0 else "schwach"


def einsatz(p, seite, name, start):
    """(spielt, ein_min, aus_min, minuten, live) aus Wechseln (live.json) bzw. Aufstellung."""
    w = [x for x in p.get("wechsel") or [] if x.get("seite") == seite]
    ein = next((minute(x["min"]) for x in w if nk(x.get("ein", "")) == nk(name)), None)
    aus = next((minute(x["min"]) for x in w if nk(x.get("aus", "")) == nk(name)), None)
    a = p.get(seite + "_aufstellung") or {}
    chip = next((s for s in a.get("startelf", []) + a.get("bank", []) if nk(s.get("voll") or s["n"]) == nk(name)), {})
    if ein is None and chip.get("ein") is True:
        ein = minute(chip.get("ein_min"))
    if aus is None and chip.get("aus"):
        aus = minute(chip.get("aus"))
    spielt = start or ein is not None
    fertig = p.get("status") == "beendet"
    beg = 0 if start else (ein or 0)
    minuten = ((aus or 90) - beg) if fertig and spielt else None
    return spielt, ein, aus, (max(minuten, 1) if minuten is not None else None), not fertig


def bilanz(p, seite, name):
    t = [x for x in p.get("tore") or [] if x.get("seite") == seite and x.get("art") != "Eigentor"]
    tore = sum(1 for x in t if nk(x["n"]) == nk(name))
    vorl = sum(1 for x in t if nk(x.get("vorlage", "")) == nk(name))
    k = [x for x in p.get("karten") or [] if x.get("seite") == seite and nk(x["n"]) == nk(name)]
    z = []
    if tore:
        z.append("ein Tor" if tore == 1 else f"{tore} Tore")
    if vorl:
        z.append("eine Vorlage" if vorl == 1 else f"{vorl} Vorlagen")
    s = ""
    if z:
        s = "Dabei " + ("erzielte sie " + z[0] + (" und gab " + z[1] if len(z) > 1 else "") if tore else "gab sie " + z[0]) + "."
    for c in k:
        s += f" In der {c['min']}. Minute sah sie {'Gelb' if c['art'] == 'gelb' else 'Gelb-Rot' if c['art'] == 'gelbrot' else 'Rot'}."
    return s.strip()


def zeitpunkt(stufe, p, seite, start, ein, news, jetzt):
    """Zeit der Meldung = Zeit des Ereignisses, nicht des Laufs (Finn 06.11.2026): "zurück im Kader" direkt bei den
    Aufstellungen (gleiche Zeit wie die fehlt-Meldung des Vereins, sonst die Aufstellung), "feiert Comeback" zur Einwechslung
    (Startelf: Anpfiff). "ohne Einsatz" ist nur der Nachtrag zur Kader-Meldung und behält deren Zeit. Nie später als jetzt."""
    an = datetime.strptime(p["anstoss"], "%Y-%m-%dT%H:%M").replace(tzinfo=TZ)
    uhr = p.get("uhr") or {}
    utc = lambda k: datetime.fromisoformat(uhr[k].replace("Z", "+00:00")).astimezone(TZ) if uhr.get(k) else None
    k = (p.get(seite + "_k") or AB.KURZ.get(p[seite], "")).lower()
    tt = p["anstoss"][8:10] + p["anstoss"][5:7]
    if stufe in ("kader", "ohne") or (stufe == "einsatz" and start):
        z = [m["zeit"] for m in news["meldungen"] if m["id"].startswith("fehlt-") and m["id"].endswith(f"-{k}-{tt}")] \
            or [m["zeit"] for m in news["meldungen"] if m["id"] == f"aufstellung-{k}-{tt}"]
        t = datetime.strptime(max(z), "%Y-%m-%dT%H:%M").replace(tzinfo=TZ) if z else an
        if stufe == "einsatz":
            t = utc("a1") or an
    else:
        if ein is not None and ein > 45:
            t = (utc("a2") or an + timedelta(minutes=60)) + timedelta(minutes=ein - 45)
        else:
            t = (utc("a1") or an) + timedelta(minutes=ein or 0)
    return min(t, jetzt).strftime("%Y-%m-%dT%H:%M")


def meldung(art, p, seite, s, voll, bez, af, kader, jetzt, alt, news=None):
    verein, gegner = p[seite], p["gast" if seite == "heim" else "heim"]
    k = (p.get(seite + "_k") or AB.KURZ.get(verein, "")).lower()
    tt = p["anstoss"][8:10] + p["anstoss"][5:7]
    nach = voll.split()[-1] if voll else s["n"]
    start = s.get("_start", False)
    spielt, ein, aus, minuten, live = einsatz(p, seite, voll or s["n"], start)
    fertig = not live
    pid = AB.pid_von(voll or s["n"], verein, kader)
    note = ((af.get("spiele") or {}).get(p["id"]) or {}).get("no", {}).get(pid) if pid else None
    wort = "Comeback" if art == "comeback" else "Saisondebüt"
    vorher = f"nach {bez}" if art == "comeback" else ""
    if spielt:
        stufe = "einsatz"
        head = f"{nach} feiert {wort} {vorher}".strip() if art == "comeback" else f"{nach} feiert Saisondebüt"
    elif fertig:
        stufe = "ohne"
        head = f"{nach} {vorher} zurück im Kader, aber ohne Einsatz" if art == "comeback" else f"{nach} erstmals im Kader, aber ohne Einsatz"
    else:
        stufe = "kader"
        head = (f"{nach} steht {vorher} in der Startelf" if start else f"{nach} {vorher} zurück im Kader") if art == "comeback" \
            else (f"{nach} erstmals in der Startelf" if start else f"{nach} erstmals im Kader")
    head = re.sub(r"\s+", " ", head)
    if art == "comeback":
        t1 = f"{voll} ist {vorher} zurück im Spieltagskader {bei(verein)}."
    else:
        t1 = f"{voll} steht gegen {gegner} zum ersten Mal in dieser Saison im Spieltagskader {bei(verein)}."
    text = [t1]
    if start:
        e = f"Gegen {gegner} stand sie in der Startelf"
        e += (f" und wurde in der {aus}. Minute ausgewechselt" if aus else (" und spielte durch" if fertig else "")) + "."
    elif ein is not None:
        fuer = next((x.get("aus") for x in p.get("wechsel") or [] if nk(x.get("ein", "")) == nk(voll or s["n"])), "")
        e = f"Gegen {gegner} kam sie in der {ein}. Minute{' für ' + fuer if fuer else ''} ins Spiel."
    elif fertig:
        e = f"Gegen {gegner} saß sie die gesamte Spielzeit auf der Bank."
    else:
        e = f"Gegen {gegner} sitzt sie zunächst auf der Bank."
    if fertig and minuten and spielt:
        e += f" Insgesamt spielte sie {'rund ' if not start or aus else ''}{minuten} Minuten."
    text.append(e)
    b = bilanz(p, seite, voll or s["n"]) if spielt else ""
    if b:
        text.append(b)
    if note is not None:
        text.append(f"API-Football bewertet ihren Auftritt mit der Note {str(note).replace('.', ',')} ({note_text(note)}).")
    if art == "comeback":
        kb = ("Wieder einsatzbereit. Nach der Pause am nächsten Spieltag eher mit begrenzter Spielzeit rechnen, die Startelf ist noch offen."
              if spielt else "Zurück im Kader, aber noch ohne Spielpraxis. Ein Einsatz am nächsten Spieltag ist offen, die Startelf eher nicht.")
    else:
        kb = ("Erste Einsatzminuten der Saison. Für Kickbase vorerst eine Ergänzung, keine feste Größe."
              if spielt else "Neu im Spieltagskader. Für Kickbase vorerst nur eine Ergänzung.")
    tags = ["RÜCKKEHR"] if art == "comeback" else ["AUFSTELLUNG"]
    if alt and alt.get("comeback", {}).get("stufe") not in (None, stufe):
        tags.append("UPDATE")
    m = {"id": f"{art if art == 'erstmals' else 'comeback'}-{re.sub(r'[^a-z0-9]+', '-', F.norm(nach))}-{k}-{tt}", "pid": pid,
         "zeit": zeitpunkt(stufe, p, seite, start, ein, news or {"meldungen": []}, jetzt),
         "spielerin": voll, "verein": verein, "nr": s.get("nr", ""), "pos": AB.pos_von(voll or s["n"], verein, kader) or s.get("p", ""),
         "tags": tags, "status": "fit", "headline": head, "text": text, "kickbase": kb,
         "quellen": [{"name": "Sportschau", "url": p.get("url", "")}] + ([{"name": "API-Football (Note)", "url": "https://www.api-football.com"}] if note is not None else []),
         "quelle_live": True, "partie_id": p["id"], "comeback": {"art": art, "stufe": stufe}}
    if len(head) > 46:
        m["kurz"] = (f"{nach} feiert {wort}" if spielt else f"{nach} zurück im Kader" if art == "comeback" else f"{nach} erstmals im Kader")
    return m


def live_aufstellung(news, p, seite):
    """Aufstellung aus der Meldung aufstellung-<kürzel>-<TTMM> (vor dem nächsten Lauf von spielplan_bau), Namen voll aus kader.csv."""
    mid = f"aufstellung-{(p.get(seite + '_k') or '').lower()}-{p['anstoss'][8:10]}{p['anstoss'][5:7]}"
    m = next((x for x in news["meldungen"] if x["id"] == mid and (x.get("aufstellung") or {}).get("startelf")), None)
    if not m:
        return None
    a = m["aufstellung"]
    voll = lambda s: next((r["name"] for r in KADER if r.get("id") and r["id"] == s.get("pid")), None)
    return {"typ": "offiziell", "startelf": [dict(s, voll=voll(s) or s["n"]) for s in a["startelf"]],
            "bank": [dict(s, voll=voll(s) or s["n"]) for s in a.get("bank", [])]}


KADER = []


def kandidaten(news, sp, jetzt):
    """[(art, partie, seite, chip, vollname, bezeichnung)] für Spiele mit offizieller Aufstellung der letzten 3 Tage."""
    kd = kader_eintraege(news, sp)
    out = []
    for p in partien(sp):
        an = p.get("anstoss", "")
        if not an or "T00:00" in an or an > (jetzt + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M") \
                or an < (jetzt - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"):
            continue
        for seite in ("heim", "gast"):
            a = p.get(seite + "_aufstellung")
            if not a or a.get("typ") != "offiziell" or not a.get("startelf"):
                a = live_aufstellung(news, p, seite)  # offizielle Aufstellung ist erst als Meldung da (Aufstellungen live)
            if not a:
                continue
            verein = p[seite]
            frueher = [(z, n) for z, v, n, pid in kd if v == verein and z < an and pid != p["id"]]
            saison = an[:4] + "-" + SAISON_AB if an[5:] >= SAISON_AB else str(int(an[:4]) - 1) + "-" + SAISON_AB
            for s in [dict(x, _start=True) for x in a["startelf"]] + a.get("bank", []):
                voll = s.get("voll") or s["n"]
                k = nk(voll)
                t_v, bez = verletzung(news, verein, voll)
                if t_v and t_v >= (jetzt - timedelta(days=180)).strftime("%Y-%m-%d"):
                    seit = [n for z, n in frueher if z > t_v]
                    if seit and not any(k in n for n in seit):
                        out.append(("comeback", p, seite, s, voll, bez))
                        continue
                in_saison = [n for z, n in frueher if z >= saison]
                if len(in_saison) >= 3 and not any(k in n for n in in_saison):
                    out.append(("erstmals", p, seite, s, voll, None))
    return out


def anwenden(news, live, sp, af, kader, jetzt=None):
    jetzt = jetzt or datetime.now(TZ)
    KADER[:] = kader
    geaendert = []
    weg = set(live.get("entfernt", []))
    for art, p, seite, s, voll, bez in kandidaten(news, sp, jetzt):
        k = (p.get(seite + "_k") or "").lower()
        mid = f"{'comeback' if art == 'comeback' else 'erstmals'}-{re.sub(r'[^a-z0-9]+', '-', F.norm(voll.split()[-1]))}-{k}-{p['anstoss'][8:10]}{p['anstoss'][5:7]}"
        if mid in weg:
            continue
        alt = next((m for m in news["meldungen"] if m["id"] == mid), None)
        m = meldung(art, p, seite, s, voll, bez, af, kader, jetzt, alt, news)
        if alt is None and art == "comeback" and m["comeback"]["stufe"] == "kader" and presse_rueckkehr(news, p[seite], voll, jetzt):
            continue  # Rückkehr schon aus der Presse gemeldet: erst bei Einsatz oder Abpfiff
        vergl = lambda x: {kk: v for kk, v in (x or {}).items() if kk != "zeit"}
        if alt is not None and vergl(alt) == vergl(m) and alt.get("zeit") == m["zeit"]:
            continue
        news["meldungen"] = [m] + [x for x in news["meldungen"] if x["id"] != mid] if alt is None or m["zeit"] != alt.get("zeit") \
            else [m if x["id"] == mid else x for x in news["meldungen"]]
        live["meldungen"] = [m] + [x for x in live.get("meldungen", []) if x["id"] != mid]
        geaendert.append(mid)
        print(f"Comeback/Erstmals: {m['headline']}")
    return geaendert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--schreiben", action="store_true")
    a = ap.parse_args()
    lade = lambda f, d=None: json.load(open(os.path.join(a.repo, f), encoding="utf-8")) if os.path.exists(os.path.join(a.repo, f)) else d
    news, sp, af = lade("news.json"), lade("spielplan.json"), lade("apifootball.json", {})
    live = lade("tools/aufstellungen_live.json", {"meldungen": []})
    kader = list(csv.DictReader(open(os.path.join(a.repo, "tools/kader.csv"), encoding="utf-8")))
    ids = anwenden(news, live, sp, af, kader)
    for i in ids:
        m = next(x for x in news["meldungen"] if x["id"] == i)
        print(json.dumps(m, ensure_ascii=False, indent=1))
    if a.schreiben and ids:
        json.dump(news, open(os.path.join(a.repo, "news.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(live, open(os.path.join(a.repo, "tools/aufstellungen_live.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
