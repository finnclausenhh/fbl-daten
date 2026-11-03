#!/usr/bin/env python3
"""Testet alle Vereinsquellen aus vereinsquellen.json.

Ruft jede Quelle einmal ab (nur urllib, kein JavaScript), extrahiert
Frauen-News (Titel, URL, Datum) und gibt pro Verein Anzahl und die
3 neuesten Titel aus.

Aufruf:  python3 test_vereinsquellen.py [--tage 21] [--verein Köln]
"""
import argparse
import datetime as dt
import email.utils
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
HIER = os.path.dirname(os.path.abspath(__file__))
MONATE = {m: i + 1 for i, m in enumerate(
    ["januar", "februar", "märz", "april", "mai", "juni", "juli",
     "august", "september", "oktober", "november", "dezember"])}
_letzter_abruf = {}


def hole(url, timeout=30):
    """GET mit Browser-UA; wartet 2 s zwischen Abrufen derselben Domain."""
    host = urllib.parse.urlparse(url).netloc
    warte = 2.0 - (time.time() - _letzter_abruf.get(host, 0))
    if warte > 0:
        time.sleep(warte)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
        "Accept-Encoding": "gzip",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            daten = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or daten[:2] == b"\x1f\x8b":
                daten = gzip.decompress(daten)
            return daten.decode(r.headers.get_content_charset() or "utf-8", "replace")
    finally:
        _letzter_abruf[host] = time.time()


# ---------- Datums-Helfer ----------

def parse_datum(s):
    if not s:
        return None
    s = html.unescape(s).strip()
    try:  # RFC 822 (RSS)
        d = email.utils.parsedate_to_datetime(s)
        return d.replace(tzinfo=None) if d.tzinfo is None else d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        pass
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)(?:[T ](\d\d):(\d\d))?", s)  # ISO
    if m:
        return dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0), int(m[5] or 0))
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)  # 17.10.2026
    if m:
        return dt.datetime(int(m[3]), int(m[2]), int(m[1]))
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zä]+)\s+(\d{4})", s)  # Sonntag, 18. Oktober 2026
    if m and m[2].lower() in MONATE:
        return dt.datetime(int(m[3]), MONATE[m[2].lower()], int(m[1]))
    return None


def slug_titel(url):
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return slug.replace("-", " ").strip().capitalize()


def tag(s, name):
    m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), s, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip()


# ---------- Parser je Typ ----------

def parse_rss(text, q):
    out = []
    for it in re.findall(r"<item\b.*?</item>|<entry\b.*?</entry>", text, re.S):
        link = tag(it, "link")
        if not link:
            m = re.search(r'<link[^>]*href="([^"]+)"', it)
            link = m.group(1) if m else ""
        datum = tag(it, "pubDate") or tag(it, "updated") or tag(it, "published") or tag(it, "dc:date")
        out.append({"titel": tag(it, "title"), "url": link, "datum": parse_datum(datum)})
    return out


def parse_sitemap(text, q):
    out = []
    for i, block in enumerate(re.findall(r"<url>(.*?)</url>", text, re.S)):
        loc = tag(block, "loc")
        titel = tag(block, "news:title") or slug_titel(loc)
        datum = tag(block, "news:publication_date") or tag(block, "lastmod")
        out.append({"titel": titel, "url": loc, "datum": parse_datum(datum), "pos": i})
    return out


def parse_html(text, q):
    out = []
    basis = q["url"]
    m = re.search(r'<base href="([^"]+)"', text)
    if m:  # <base href> kann relativ sein (Angular: "/")
        basis = urllib.parse.urljoin(q["url"], m.group(1))
    letztes_datum = None
    for m in re.finditer(q["link_regex"], text, re.S):
        datum = parse_datum(m.group(3)) if m.lastindex and m.lastindex >= 3 and m.group(3) else None
        if datum:
            letztes_datum = datum
        out.append({
            "titel": html.unescape(re.sub(r"\s+", " ", m.group(2))).strip(),
            "url": urllib.parse.urljoin(basis, html.unescape(m.group(1))),
            "datum": datum or letztes_datum,
        })
    return out


def parse_union_api(text, q):
    d = json.loads(text)["data"]["news"]
    return [{"titel": n["headline"].strip(),
             "url": urllib.parse.urljoin("https://www.fc-union-berlin.de", n["detailLink"]),
             "datum": parse_datum(n.get("sortDate"))} for n in d]


def parse_fcde_turbostream(text, q):
    """fc.de bettet die News als turbo-stream (JSON-Array mit Indexverweisen) ein."""
    chunk = re.search(r'streamController\.enqueue\(("(?:[^"\\]|\\.)*")\);', text, re.S)
    if not chunk:
        return []
    arr = json.loads(json.loads(chunk.group(1)).split("\n")[0])
    frauen = {i for i, v in enumerate(arr) if isinstance(v, str) and v.strip() == "Frauen"}
    out, gesehen = [], set()
    for j, v in enumerate(arr):
        if (isinstance(v, str) and v.startswith("/aktuelles/news/") and j + 1 < len(arr)
                and isinstance(arr[j + 1], list) and set(arr[j + 1]) & frauen and v not in gesehen):
            gesehen.add(v)
            datum = next((x for x in arr[j + 2:j + 15]
                          if isinstance(x, str) and re.match(r"20\d\d-\d\d-\d\dT", x)), "")
            out.append({"titel": str(arr[j - 1]).strip(), "url": "https://fc.de" + v,
                        "datum": parse_datum(datum)})
    return out


PARSER = {"rss": parse_rss, "googlenews": parse_rss, "sitemap": parse_sitemap,
          "html": parse_html, "union_api": parse_union_api,
          "fcde_turbostream": parse_fcde_turbostream}


def pruefe(q, tage):
    name = q.get("parser") or q["typ"]
    text = hole(q["url"])
    items = PARSER[name](text, q)
    if q.get("filter"):
        rx = re.compile(q["filter"], re.I)
        items = [i for i in items if rx.search(i["url"]) or rx.search(i["titel"])]
    grenze = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=tage)
    if q["typ"] == "sitemap":
        if any(i["datum"] for i in items):
            items = [i for i in items if i["datum"] and i["datum"] >= grenze]
        else:  # Sitemap ohne Datum (HSV): Reihenfolge = neueste zuerst
            items = sorted(items, key=lambda i: i["pos"])[:15]
    else:
        items = [i for i in items if not i["datum"] or i["datum"] >= grenze]
    items.sort(key=lambda i: i["datum"] or dt.datetime.min, reverse=True)
    if q["typ"] == "sitemap" and not any(i["datum"] for i in items):
        items.sort(key=lambda i: i["pos"])
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tage", type=int, default=21, help="nur News der letzten N Tage zählen")
    ap.add_argument("--verein", default="", help="nur Vereine, deren Name diesen Text enthält")
    ap.add_argument("--config", default=os.path.join(HIER, "vereinsquellen.json"))
    a = ap.parse_args()

    quellen = json.load(open(a.config, encoding="utf-8"))
    ok_gesamt = 0
    print(f"Stand {dt.datetime.now():%d.%m.%Y %H:%M}, Fenster {a.tage} Tage\n")
    for q in quellen:
        if a.verein.lower() not in q["verein"].lower():
            continue
        try:
            items = pruefe(q, a.tage)
            status = "OK " if len(items) >= 3 else "WENIG"
            ok_gesamt += len(items) >= 3
        except Exception as e:  # noqa: BLE001
            items, status = [], f"FEHLER {type(e).__name__}: {e}"
        print(f"[{status}] {q['verein']}  ({q['typ']}{'/' + q['parser'] if q.get('parser') else ''})  -> {len(items)} Treffer")
        for i in items[:3]:
            d = i["datum"].strftime("%d.%m.") if i["datum"] else "  ?  "
            print(f"    {d}  {i['titel'][:85]}")
            print(f"           {i['url'][:110]}")
        print()
    print(f"{ok_gesamt}/{len([q for q in quellen if a.verein.lower() in q['verein'].lower()])} Quellen mit mindestens 3 Frauen-News")


if __name__ == "__main__":
    sys.exit(main())
