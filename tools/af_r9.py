"""Runde 9 (Finn 04.11.2026, 16:34): Tippspiel aus dem Feed, Gefragt diese Woche erst ab der 15. Meldung."""
import sys
def r9(h):
    a = "const SONDER = [[tippZeile, 1], [gefragtZeile, 9]], MINAB = 2;"
    if h.count(a) != 1: raise SystemExit("R9: Stelle fehlt")
    return h.replace(a, "const SONDER = [[gefragtZeile, 15]], MINAB = 2;")
if __name__ == "__main__":
    p = sys.argv[1]; t = r9(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
