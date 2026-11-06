#!/usr/bin/env python3
"""Push-Alarm aufs Handy über ntfy.sh (kostenlos, ohne Konto). Finn abonniert in der ntfy-App das Thema unten.

Thema aus der Umgebungsvariable NTFY_TOPIC (Repo-Secret), sonst das feste, nicht erratbare Thema.
Aufruf als Modul: senden(titel, text, prio="high", url=None). Testweise: python3 tools/alarm.py "Test" "Hallo"
"""
import base64, os, sys, urllib.request

THEMA = os.environ.get("NTFY_TOPIC") or "wosoinsider-alarm-88d52e8c91"


def senden(titel, text, prio="high", url=None, tags="warning"):
    h = {"Title": "=?UTF-8?B?" + base64.b64encode(titel.encode("utf-8")).decode() + "?=", "Priority": prio, "Tags": tags}  # RFC 2047 für Umlaute
    if url:
        h["Click"] = url
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{THEMA}", data=text.encode("utf-8"), headers=h, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
        print(f"ALARM gesendet: {titel}: {text}")
        return True
    except Exception as e:
        print(f"WARN Alarm nicht gesendet ({e}): {titel}: {text}", file=sys.stderr)
        return False


if __name__ == "__main__":
    senden(sys.argv[1] if len(sys.argv) > 1 else "WOSOINSIDER Test", sys.argv[2] if len(sys.argv) > 2 else "Testalarm", prio="default", tags="white_check_mark")
