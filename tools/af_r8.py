"""Runde 8 (Finn 04.11.2026, 16:29): Sonderblöcke im Feed mit Abstand (Gefragt diese Woche frühestens nach 9 Meldungen),
Liga-Vergleich auch "schlechter als", Steckbrief mit Fußballschuhen und Spielerinnen-Silhouetten im echten Verhältnis,
Statistik: Beste Note zuerst, neue Bestenlisten aus der Spielstatistik. python3 tools/af_r8.py <datei.html>"""
import sys

CSS8 = """
.sb2 .ic.si{align-items:flex-end;gap:8px}
.sb2 > div.gr{grid-column:1/-1}
.af-ww .pz{display:grid !important;grid-template-columns:1fr !important}
.af-ww .pz .bb{display:block !important;width:100% !important}
.sb2 .ic.si span{display:grid;justify-items:center;gap:1px;font:600 9px var(--f-mono);color:var(--muted)}
.sb2 .ic.fu{gap:2px}
.sb2 .ic.fu span{display:grid;justify-items:center;gap:1px;font:700 9px var(--f-mono);color:var(--muted)}
.sb2 .ic.fu span.an{color:#8FB0FF}
"""

def r8(h):
    def e(a, b, n=1):
        nonlocal h
        if h.count(a) != n: raise SystemExit(f"R8: {h.count(a)}x statt {n}x: {a[:90]!r}")
        h = h.replace(a, b)
    i = h.rfind("</style>"); h = h[:i] + CSS8 + h[i:]

    # ---------- Feed: Sonderblöcke nie direkt untereinander, Gefragt diese Woche frühestens nach 9 Meldungen
    e("""    rest.forEach((m, gi) => { if (A && dt(A.news_zeit) >= (dt(m.zeit) || 0)) { h += anaTeaser(A); A = null; }""",
      """    let seit = 99; const SONDER = [[tippZeile, 1], [gefragtZeile, 9]], MINAB = 2;
    rest.forEach((m, gi) => { if (A && dt(A.news_zeit) >= (dt(m.zeit) || 0) && seit >= MINAB) { h += anaTeaser(A); A = null; seit = 0; }""")
    e(""": newsKarte(m); if (gi === 0) h += tippZeile(); if (gi === 2) h += gefragtZeile(); });""",
      """: newsKarte(m); seit++;
      if (SONDER.length && gi + 1 >= SONDER[0][1] && seit >= MINAB) { const x = SONDER.shift()[0](); if (x) { h += x; seit = 0; } } });""")

    # ---------- Liga-Vergleich: unter 50 % als "schlechter als"
    e("""w[3].p >= 100 ? "Bestwert aller " + (PLURAL[s.pos] || "Spielerinnen") : "besser als " + w[3].p + " % der " + (PLURAL[s.pos] || "Spielerinnen")""",
      """w[3].p >= 100 ? "Bestwert aller " + (PLURAL[s.pos] || "Spielerinnen") : w[3].p <= 0 ? "niedrigster Wert aller " + (PLURAL[s.pos] || "Spielerinnen") : w[3].p >= 50 ? "besser als " + w[3].p + " % der " + (PLURAL[s.pos] || "Spielerinnen") : "schlechter als " + (100 - w[3].p) + " % der " + (PLURAL[s.pos] || "Spielerinnen")""")

    # ---------- Steckbrief: Größe in beide Richtungen, Silhouetten als Spielerin im echten Verhältnis, Schuhe statt Fußsohlen
    e("""grPct != null ? `größer als ${grPct} % der Liga`""", """grPct != null ? (grPct >= 50 ? `größer als ${grPct} % der Liga` : `kleiner als ${100 - grPct} % der Liga`)""")
    i1 = h.index("  const SILH = "); i2 = h.index("\n", h.index("  const FUSS = "))
    h = h[:i1] + r"""  // Spielerin mit Ball (Seitenansicht), Höhe in Pixeln = Körpergröße im festen Maßstab
  const SILH = (hpx, farbe) => `<svg width="${Math.round(hpx * .5)}" height="${hpx}" viewBox="0 0 50 100" aria-hidden="true"><g fill="${farbe}"><circle cx="24" cy="8" r="7.5"/><path d="M16 19c2-2 5-3 8-3s7 1 9 3l4 21-6 2-3-14-1 22 4 18 9 19-7 3-10-20-3-13-3 14-4 19-7-1 4-21 1-21-2-13-3 13-6-2z"/><circle cx="43" cy="93" r="6"/></g></svg>`;
  const FUSS = (an, s) => `<span class="${an ? "an" : ""}"><svg width="24" height="15" viewBox="0 0 24 15" aria-hidden="true" style="transform:scaleX(${s === "L" ? -1 : 1})"><path d="M3 2h7l1 5c3 0 8 1 11 3 1 1 1 3-1 3H3c-1 0-2-1-2-2V3c0-1 1-1 2-1z" fill="${an ? "#8FB0FF" : "rgba(255,255,255,.14)"}"/><path d="M4 13v2M8 13v2M13 13v2M18 13v2" stroke="${an ? "#8FB0FF" : "rgba(255,255,255,.14)"}" stroke-width="1.4"/></svg>${s}</span>`;""" + h[i2:]
    e("""<span class="ic">${FUSS(fu === "links" || fu === "beidfüßig")}${FUSS(fu === "rechts" || fu === "beidfüßig")}</span>""",
      """<span class="ic fu">${FUSS(fu === "links" || fu === "beidfüßig", "L")}${FUSS(fu === "rechts" || fu === "beidfüßig", "R")}</span>""")
    e("""const t3 = `<div><span class="tx">""", """const t3 = `<div class="gr"><span class="tx">""")
    e("""const t4 = `<div><span class="tx">""", """const t4 = `<div class="gr"><span class="tx">""")
    e("""<span class="ic">${SILH(Math.round(af.gr / 190 * 50), "#8FB0FF")}${SILH(Math.round(grLm / 190 * 50), "rgba(255,255,255,.16)")}</span>""",
      """<span class="ic si"><span>${SILH(Math.round(af.gr / 185 * 58), "#8FB0FF")}SIE</span><span>${SILH(Math.round(grLm / 185 * 58), "rgba(255,255,255,.2)")}Ø</span></span>""")

    # ---------- Statistik: Beste Note zuerst, neue Bestenlisten
    e("""["note","Beste Note im Schnitt","ab 4 Einsätzen über 60 Minuten"],["kp90","Schlüsselpässe pro 90","ab 300 Einsatzminuten"],["par","Paraden pro Spiel","Torhüterinnen ab 3 Spielen"],""",
      """["kp90","Schlüsselpässe pro 90","ab 300 Einsatzminuten"],["schpg","Torschüsse pro Spiel","ab 4 Einsätzen"],["zkq","Zweikampfquote","gewonnene Zweikämpfe in Prozent, ab 40"],["pq","Passquote","angekommene Pässe in Prozent, ab 150"],["drib","Dribblings erfolgreich","Anzahl laut API-Football"],["bkpg","Ballkontakte pro Spiel","ab 4 Einsätzen"],["par","Paraden pro Spiel","Torhüterinnen ab 3 Spielen"],""")
    e("""const STKAT = [["tore","Tore",""],""", """const STKAT = [["note","Beste Note im Schnitt","ab 4 Einsätzen über 60 Minuten"],["tore","Tore",""],""")
    e("""v.par = af.parsp >= 3 ? af.par / af.parsp : 0; }""",
      """v.par = af.parsp >= 3 ? af.par / af.parsp : 0;
        const sp2 = (s.stat || {}).spiele || 0; v.schpg = sp2 >= 4 && st.sch ? st.sch / sp2 : 0; v.zkq = st.zk_ges >= 40 ? st.zk_w / st.zk_ges * 100 : 0; v.pq = st.p_ges >= 150 ? st.p_ok / st.p_ges * 100 : 0;
        v.drib = af.drib ? af.drib[0] : 0; v.bkpg = sp2 >= 4 && st.bk ? st.bk / sp2 : 0; }""")
    e("""k === "kp90" || k === "par" ? x.toFixed(1)""", """k === "zkq" || k === "pq" ? Math.round(x) + " %" : k === "kp90" || k === "par" || k === "schpg" || k === "bkpg" ? x.toFixed(1)""")
    return h

if __name__ == "__main__":
    p = sys.argv[1]; t = r8(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
