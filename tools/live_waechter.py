#!/usr/bin/env python3
"""Live-Wächter (Finn, 06.11.2026): merkt Fehler während der Spiele vor den Nutzern und schickt einen Push aufs Handy.

Läuft unabhängig von live_ergebnis.py (eigene Action), damit er auch merkt, wenn die Live-Action selbst hängt oder ausfällt.
Liest unseren Stand so, wie ihn die Webapp sieht (GitHub-Contents-API), und vergleicht jede Minute mit der Sportschau.

Prüfungen je Partie (Fenster 70 Min. vor bis 150 Min. nach Anpfiff):
 1. Aufstellung: ab 40 Min. vor Anpfiff, Sportschau hat sie, wir nach 4 Min. noch nicht.
 2. Live-Start: Sportschau läuft, unser live.json nach 4 Min. noch nicht live.
 3. Spielstand: Sportschau hat mehr Tore, länger als 3 Min.; wir mehr als die Sportschau länger als 8 Min. (Tor zurückgenommen?).
 4. Halbzeit und Abpfiff: bei der Sportschau seit 4 bzw. 5 Min., bei uns nicht.
 5. Stillstand: Partie live, aber live.json seit 12 Min. ohne neuen Stand.
 6. Hängende Sportschau: 125 Min. nach Anpfiff noch nicht beendet.
 7. Neue Ereignisart im Liveticker, die unser Code nicht kennt (z. B. erstmals Elfmeterschießen), sofort.
 8. Leselogik: gelesene Tore je Seite passen nicht zum Ergebnis der Sportschau, länger als 2 Min.
 9. Endstand-Meldung fehlt 8 Min. nach unserem Abpfiff.
Dazu alle 5 Min.: fehlgeschlagene Actions in fbl-daten und wosoinsider-web (u. a. Pages-Deploy), Webapp erreichbar.

Ein Alarm geht einmal raus und wiederholt sich höchstens alle 20 Min.; ist das Problem weg, kommt eine Entwarnung.
Gab es einen Alarm, endet der Lauf mit Exit 1 (zusätzlich Mail von GitHub).
Aufruf: python3 tools/live_waechter.py --laufzeit 170 [--trocken]
"""
import argparse, json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_ergebnis as L  # noqa: E402
import parser_test as PT  # noqa: E402
import alarm as A  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
REPO = "finnclausenhh/fbl-daten"
WEB = "finnclausenhh/wosoinsider-web"
TICKER = "https://wosoinsider.de/ticker/"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
WIEDERHOLEN = timedelta(minutes=20)


def api(pfad, roh=False):
    h = {"User-Agent": "WOSOINSIDER-Waechter", "Accept": "application/vnd.github.raw+json" if roh else "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    try:
        with urllib.request.urlopen(urllib.request.Request("https://api.github.com/" + pfad, headers=h), timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"WARN API {pfad}: {e}", file=sys.stderr)
        return None


def starten(workflow, abbrechen=False):
    """Action neu anstoßen (Selbstheilung), höchstens alle 10 Min. je Workflow. abbrechen: laufende (hängende) Läufe
    vorher abbrechen, sonst wartet der neue Lauf wegen concurrency hinter dem hängenden."""
    t = jetzt()
    if STARTS.get(workflow) and t - STARTS[workflow] < timedelta(minutes=10):
        return False
    STARTS[workflow] = t
    if abbrechen:
        for st in ("in_progress", "queued"):
            for run in (api(f"repos/{REPO}/actions/workflows/{workflow}/runs?status={st}&per_page=5") or {}).get("workflow_runs", []):
                try:
                    urllib.request.urlopen(urllib.request.Request(f"https://api.github.com/repos/{REPO}/actions/runs/{run['id']}/cancel", method="POST",
                                                                  headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "WOSOINSIDER-Waechter"}), timeout=20)
                    print(f"{t:%H:%M:%S} hängenden Lauf {run['id']} abgebrochen")
                except Exception as e:
                    print(f"WARN Abbruch {run['id']}: {e}", file=sys.stderr)
        time.sleep(15)
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches", method="POST",
                                     data=b'{"ref":"main"}', headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                                                                      "User-Agent": "WOSOINSIDER-Waechter"})
        urllib.request.urlopen(req, timeout=20).read()
        print(f"{t:%H:%M:%S} {workflow} neu gestartet")
        return True
    except Exception as e:
        print(f"WARN Start {workflow}: {e}", file=sys.stderr)
        return False


STARTS = {}


def datei(f):
    return api(f"repos/{REPO}/contents/{f}?ref=main", roh=True)


def jetzt():
    return datetime.now(TZ)


class Waechter:
    def __init__(self, trocken=False):
        self.seit = {}      # Bedingung -> erstmals gesehen
        self.gesendet = {}  # Schlüssel -> zuletzt gesendet
        self.offen = {}     # Schlüssel -> Titel (für Entwarnung)
        self.trocken = trocken
        self.alarme = 0
        self.runs_gesehen = set()
        self.start = jetzt()

    def dauer(self, key, aktiv):
        """Wie lange eine Bedingung schon ununterbrochen gilt (timedelta) oder None."""
        if not aktiv:
            self.seit.pop(key, None)
            return None
        self.seit.setdefault(key, jetzt())
        return jetzt() - self.seit[key]

    def melden(self, key, titel, text, url=None):
        t = jetzt()
        if key in self.gesendet and t - self.gesendet[key] < WIEDERHOLEN:
            return
        self.gesendet[key] = t
        self.offen[key] = titel
        self.alarme += 1
        print(f"{t:%H:%M:%S} ALARM {titel}: {text}")
        if not self.trocken:
            A.senden(titel, text, url=url)

    def ok(self, key):
        if key in self.offen:
            titel = self.offen.pop(key)
            self.gesendet.pop(key, None)
            print(f"{jetzt():%H:%M:%S} Entwarnung: {titel}")
            if not self.trocken:
                A.senden("Entwarnung", f"Behoben: {titel}", prio="default", tags="white_check_mark")

    def pruefe(self, key, bedingung, minuten, titel, text, url=None):
        d = self.dauer(key, bedingung)
        if d is not None and d >= timedelta(minutes=minuten):
            self.melden(key, titel, text, url)
        elif not bedingung:
            self.ok(key)

    # ---------------------------------------------------------------- Partien
    def partie(self, p, live, news):
        an = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=TZ)
        t = jetzt()
        name = f"{p.get('heim_k')}-{p.get('gast_k')}"
        k = p["id"]
        tt = p["anstoss"][8:10] + p["anstoss"][5:7]
        ids = {m["id"]: m for m in news.get("meldungen", [])}
        # 1. Aufstellung
        if an - timedelta(minutes=40) <= t <= an + timedelta(minutes=10):
            fehlt = [s for s in ("heim", "gast") if not (ids.get(f"aufstellung-{(p.get(s + '_k') or '').lower()}-{tt}") or {}).get("aufstellung", {}).get("startelf")]
            ss = False
            if fehlt:
                roh = L.F.get(p["url"].replace("/liveticker", "/aufstellung"))
                ss = bool(roh and "playing-lineup" in roh)
            if bool(fehlt) and ss and (self.dauer(f"{k}:aufst0", True) or timedelta()) >= timedelta(minutes=2) and not self.trocken:
                starten("aufstellungen.yml")
            elif not (fehlt and ss):
                self.dauer(f"{k}:aufst0", False)
            self.pruefe(f"{k}:aufst", bool(fehlt) and ss, 4, f"Aufstellung fehlt: {name}",
                        f"Bei der Sportschau steht die Aufstellung, bei uns fehlt sie ({', '.join(p.get(s + '_k') or s for s in fehlt)}). "
                        "Action \"Aufstellungen live\" prüfen.", f"https://github.com/{REPO}/actions/workflows/aufstellungen.yml")
        if t < an - timedelta(minutes=2):
            return
        r = L.lesen(p["url"])
        unser = (live.get("spiele") or {}).get(k) or {}
        if not r:
            self.pruefe(f"{k}:ss", True, 6, f"Sportschau nicht lesbar: {name}",
                        "Der Liveticker der Sportschau liefert seit 6 Min. nichts Lesbares. Format geändert oder Seite down?", p["url"])
            return
        self.ok(f"{k}:ss")
        q = {x: None for x in ("status", "ergebnis", "minute", "tore", "karten", "wechsel")}
        L.anwenden(q, r)
        ss_status = q.get("status")  # None = noch nicht angepfiffen
        ss_min = q.get("minute")
        u_status = unser.get("status") or p.get("status")
        u_erg = unser.get("ergebnis") or p.get("ergebnis") or ["0", "0"]
        # 2. Live-Start (nach 2 Min. selbst neu anstoßen, nach 4 Min. Alarm)
        nicht_live = ss_status in ("live", "beendet") and u_status not in ("live", "beendet")
        if (self.dauer(f"{k}:start0", nicht_live) or timedelta()) >= timedelta(minutes=2) and not self.trocken:
            starten("live-ergebnis.yml", abbrechen=True)
        self.pruefe(f"{k}:start", ss_status in ("live", "beendet") and u_status not in ("live", "beendet"), 4,
                    f"Live-Ergebnis läuft nicht: {name}", "Die Sportschau zeigt das Spiel als laufend, unser Live-Stand nicht. "
                    "Action \"Live-Ergebnis\" prüfen oder von Hand starten.", f"https://github.com/{REPO}/actions/workflows/live-ergebnis.yml")
        if ss_status:
            s_sum, u_sum = sum(map(int, q["ergebnis"])), sum(map(int, u_erg))
            # 3. Spielstand
            self.pruefe(f"{k}:tor", s_sum > u_sum, 3, f"Spielstand veraltet: {name}",
                        f"Sportschau {':'.join(q['ergebnis'])}, bei uns {':'.join(u_erg)}.", p["url"])
            self.pruefe(f"{k}:tor+", u_sum > s_sum, 8, f"Mehr Tore als die Sportschau: {name}",
                        f"Bei uns {':'.join(u_erg)}, Sportschau {':'.join(q['ergebnis'])}. Tor zurückgenommen (VAR, API-Football)?", p["url"])
            # 4. Halbzeit und Abpfiff
            self.pruefe(f"{k}:hz", ss_min == "HZ" and unser.get("minute") != "HZ" and u_status != "beendet", 4,
                        f"Halbzeit fehlt: {name}", "Sportschau zeigt Halbzeit, wir nicht.", p["url"])
            self.pruefe(f"{k}:ende", ss_status == "beendet" and u_status != "beendet", 5,
                        f"Abpfiff fehlt: {name}", f"Sportschau: Spielende {':'.join(q['ergebnis'])}, bei uns noch {u_status or 'nicht live'}.", p["url"])
            # 7. Neue Ereignisarten
            s = L.F.get(p["url"]) or ""
            for art in sorted(set(re.findall(r'data-event_action="([^"]*)" data-event_kind="([^"]*)"', s)) - PT.BEKANNT):
                self.melden(f"{k}:art:{art}", f"Neue Ereignisart: {name}",
                            f"Im Liveticker steht {art[0]}/{art[1]}, das unser Code noch nicht kennt. Bitte Anzeige prüfen.", p["url"])
            # 8. Leselogik
            falsch = [sd for sd, i in (("heim", 0), ("gast", 1)) if sum(1 for x in r["tore"] if x["seite"] == sd) != int(q["ergebnis"][i])]
            self.pruefe(f"{k}:parser", bool(falsch), 2, f"Tore falsch gelesen: {name}",
                        f"Ergebnis {':'.join(q['ergebnis'])}, gelesene Tore passen nicht ({', '.join(falsch)}). Torschützinnen prüfen.", p["url"])
        # 5. Stillstand: läuft die Live-Action überhaupt? (Halbzeit ohne Push ist normal, daher Lauf statt Alter von live.json)
        if ss_status == "live":
            laeuft = self.live_lauf()
            if laeuft is False and (self.dauer(f"{k}:lauf0", True) or timedelta()) >= timedelta(minutes=2) and not self.trocken:
                starten("live-ergebnis.yml")
            elif laeuft is not False:
                self.dauer(f"{k}:lauf0", False)
            self.pruefe(f"{k}:still", laeuft is False, 5, f"Live-Action läuft nicht: {name}",
                        "Das Spiel läuft, aber keine Live-Ergebnis-Action. Neu angestoßen, bitte prüfen.",
                        f"https://github.com/{REPO}/actions/workflows/live-ergebnis.yml")
        # Rückstand gegenüber der Sportschau: Lauf hängt vermutlich, abbrechen und neu starten
        haengt = any(self.seit.get(f"{k}:{x}") and t - self.seit[f"{k}:{x}"] >= timedelta(minutes=m) for x, m in (("tor", 4), ("ende", 6), ("hz", 6)))
        if haengt and not self.trocken:
            starten("live-ergebnis.yml", abbrechen=True)
        # 6. Hängende Sportschau
        self.pruefe(f"{k}:haengt", t > an + timedelta(minutes=125) and ss_status != "beendet" and u_status != "beendet", 0,
                    f"Spiel endet nicht: {name}", f"125 Min. nach Anpfiff zeigt die Sportschau noch '{r['text']}'. Ergebnis von Hand prüfen.", p["url"])
        # 9. Endstand-Meldung
        es = f"endstand-{(p.get('heim_k') or '').lower()}-{tt}"
        self.pruefe(f"{k}:endstand", u_status == "beendet" and es not in ids, 8, f"Endstand-Meldung fehlt: {name}",
                    "Das Spiel ist beendet, die Endstand-Meldung fehlt im Ticker.")

    def live_lauf(self):
        """True, wenn eine Live-Ergebnis-Action läuft, False wenn nicht, None wenn unbekannt (API-Fehler). Je Runde einmal gefragt."""
        if getattr(self, "_lauf_t", None) and jetzt() - self._lauf_t < timedelta(seconds=50):
            return self._lauf
        d = api(f"repos/{REPO}/actions/workflows/live-ergebnis.yml/runs?status=in_progress&per_page=3")
        self._lauf_t, self._lauf = jetzt(), (None if d is None else bool(d.get("workflow_runs")))
        return self._lauf

    # ---------------------------------------------------------------- Actions und Webapp
    def actions(self):
        seit = (self.start - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for repo in (REPO, WEB):
            d = api(f"repos/{repo}/actions/runs?per_page=20") or {}
            for run in d.get("workflow_runs", []):
                if run.get("conclusion") not in ("failure", "timed_out") or run["id"] in self.runs_gesehen:
                    continue
                if datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00")) < self.start.astimezone(ZoneInfo("UTC")) - timedelta(minutes=30):
                    continue
                self.runs_gesehen.add(run["id"])
                if run.get("name") == "Live-Wächter":
                    continue
                self.melden(f"run:{run['id']}", f"Action fehlgeschlagen: {run.get('name')}",
                            f"{repo.split('/')[1]}: {run.get('name')} ({run.get('event')}) ist um "
                            f"{datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00')).astimezone(TZ):%H:%M} fehlgeschlagen.", run.get("html_url"))
        del seit
        try:
            with urllib.request.urlopen(urllib.request.Request(TICKER, headers={"User-Agent": "WOSOINSIDER-Waechter"}), timeout=20) as r:
                ok = r.status == 200
        except Exception:
            ok = False
        self.pruefe("web", not ok, 3, "Webapp nicht erreichbar", f"{TICKER} antwortet seit 3 Min. nicht.", TICKER)

    def runde(self):
        sp, live, news = datei("spielplan.json"), datei("live.json") or {}, datei("news.json") or {"meldungen": []}
        if not sp:
            self.pruefe("api", True, 5, "Daten nicht lesbar", "spielplan.json über die GitHub-API seit 5 Min. nicht lesbar.")
            return True
        self.ok("api")
        t = jetzt()
        aktiv = False
        for p in L.partien(sp):
            if not p.get("url") or "T00:00" in p.get("anstoss", "T00:00") or p.get("status") == "abgesagt":
                continue
            an = datetime.fromisoformat(p["anstoss"]).replace(tzinfo=TZ)
            if an - timedelta(minutes=70) <= t <= an + timedelta(minutes=150):
                aktiv = True
                try:
                    self.partie(p, live, news)
                except Exception as e:  # der Wächter selbst darf nie ausfallen
                    print(f"WARN Partie {p['id']}: {e}", file=sys.stderr)
        bald = any(t < datetime.fromisoformat(p["anstoss"]).replace(tzinfo=TZ) - timedelta(minutes=70) <= t + timedelta(minutes=30)
                   for p in L.partien(sp) if p.get("url") and "T00:00" not in p.get("anstoss", "T00:00") and p.get("status") != "beendet")
        return aktiv or bald


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laufzeit", type=int, default=170)
    ap.add_argument("--takt", type=int, default=60)
    ap.add_argument("--trocken", action="store_true", help="nichts senden, nur ausgeben")
    a = ap.parse_args()
    w = Waechter(a.trocken)
    ende = time.time() + a.laufzeit * 60
    n = 0
    while time.time() < ende:
        weiter = w.runde()
        if n % 5 == 0:
            w.actions()
        n += 1
        if not weiter:
            print("Kein Spiel im Fenster, Ende.")
            break
        time.sleep(a.takt)
    print(f"Ende, {w.alarme} Alarm(e).")
    sys.exit(1 if w.alarme else 0)


if __name__ == "__main__":
    main()
