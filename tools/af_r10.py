"""Runde 10 (Finn 04.11.2026, 19:43): Gefragt weiter unten, Einsehbar immer mit Wort und neuer Satz, Team-Form unter die Tabelle,
Standard-Wechsel aus Inside (kommen als Meldung), Freistöße pro Spiel, Elfmeter-Grafik, Daten zum Spiel ab den Duellen grafisch,
Verletzungs-Einschätzung aus typischen Verläufen. python3 tools/af_r10.py <datei.html>"""
import sys

CSS10 = """
.elf-l{display:grid;gap:6px}
.elf-r{display:grid;grid-template-columns:22px minmax(0,1fr) auto 34px;gap:10px;align-items:center;background:var(--soft);border-radius:10px;padding:8px 10px;width:100%;text-align:left;box-sizing:border-box}
.elf-r b{font-size:13.5px;font-weight:600}
.elf-r small{display:block;font-size:11px;color:var(--muted)}
.elf-r .pk{display:flex;gap:4px}
.elf-r .pk i{width:12px;height:12px;border-radius:50%;display:block}
.elf-r .pk i.t{background:#4ADE80}
.elf-r .pk i.v{box-shadow:inset 0 0 0 2px #FF8A8A}
.elf-r .q{font:700 13px var(--f-mono);text-align:right}
.dz-dl{display:grid;gap:6px}
.dz-db{display:flex;height:22px;border-radius:6px;overflow:hidden;font:700 11px/22px var(--f-mono);color:#0B1220;text-align:center}
.dz-db span{display:block;min-width:22px}
.dz-dk{display:flex;justify-content:space-between;font-size:11.5px;color:var(--muted)}
.dz-sa{display:grid;gap:8px}
.dz-sa > div:not(.kap){display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;align-items:start;font-size:13px;line-height:1.45}
.dz-sa > div:not(.kap) i{width:22px;height:22px;border-radius:6px;display:grid;place-items:center;font-style:normal;font:700 12px var(--f-mono);color:#0B1220}
"""

TYP = r"""  const VERL_TYP = [[/kreuzband/i, "Kreuzbandriss", 180, 300], [/achilles/i, "Achillessehnenriss", 180, 300], [/meniskus/i, "Meniskusverletzung", 42, 120],
    [/syndesmose/i, "Syndesmoseverletzung", 42, 84], [/(außen|innen)?band(riss|verletzung)|bänderriss|bänder/i, "Bänderriss", 21, 56], [/bruch|fraktur/i, "Knochenbruch", 42, 84],
    [/muskelbündel/i, "Muskelbündelriss", 28, 56], [/muskelfaser|faserriss/i, "Muskelfaserriss", 14, 35], [/zerrung/i, "Zerrung", 7, 14], [/gehirnersch|kopfverletzung/i, "Gehirnerschütterung", 7, 21]];
  function verletzungEinsch(s){
    const st = s.status || {}; if (st.s !== "raus" || !st.grund) return null;
    const t = VERL_TYP.find(x => x[0].test(st.grund)); if (!t) return null;
    const v = (s.verlauf || []).slice().reverse().find(x => x.status === "raus"), seit = (v && v.stand) || st.stand; if (!seit) return null;
    const d0 = new Date(seit + "T12:00"), plus = n => new Date(d0.getTime() + n * 864e5), iso = d => d.toISOString().slice(0, 10), kd = d => `${d.getDate()}.${d.getMonth() + 1}.`;
    const lang = n => n >= 150 ? `${Math.round(n / 30)} Monate` : `${Math.round(n / 7)} Wochen`, a = plus(t[2]), b = plus(t[3]);
    return {seit, typisch: [t[2], t[3]], stand: st.stand, satz: `Bei einem ${t[1]} fehlen Spielerinnen meist ${t[2] >= 150 ? Math.round(t[2] / 30) + " bis " + Math.round(t[3] / 30) + " Monate" : Math.round(t[2] / 7) + " bis " + Math.round(t[3] / 7) + " Wochen"}. Frühestens um den ${kd(a)} wieder im Kader, realistisch ${b.getMonth() >= 5 && b.getMonth() <= 7 ? "zur neuen Saison" : "um den " + kd(b)}.${st.rueckkehr ? " Laut Bericht: " + st.rueckkehr + "." : ""}`,
      phasen: [{d: kd(d0), iso: seit, t: t[1], typ: "verletzung"}, {d: kd(a), iso: iso(a), t: "frühestens wieder im Kader", typ: "kader", prog: true}, {d: kd(b), iso: iso(b), t: "realistisch zurück", typ: "startelf", prog: true}],
      vergleich: "Erfahrungswerte aus typischen Verläufen dieser Verletzung, keine ärztliche Prognose. Der tatsächliche Verlauf hängt von Schwere, OP und Reha ab."};
  }
"""

def r10(h):
    def e(a, b, n=1):
        nonlocal h
        if h.count(a) != n: raise SystemExit(f"R10: {h.count(a)}x statt {n}x: {a[:90]!r}")
        h = h.replace(a, b)
    i = h.rfind("</style>"); h = h[:i] + CSS10 + h[i:]

    e("const SONDER = [[gefragtZeile, 15]], MINAB = 2;", "const SONDER = [[gefragtZeile, 21]], MINAB = 2;")
    # Einsehbar: immer mit Wort, verständlicher Satz
    e("""const einsTag = nur => nur ? `<span class="eins" title="Aufstellung vor dem Kickbase-Schluss einsehbar" role="img" aria-label="Aufstellung einsehbar">${svg(AUGE)}</span>` : `<span class="eins">${svg(AUGE)}EINSEHBAR</span>`;""",
      """const einsTag = nur => `<span class="eins" title="Offizielle Startelf steht fest, bevor Kickbase die Aufstellung sperrt">${svg(AUGE)}EINSEHBAR</span>`;""")
    e("""<span>Aufstellung vor dem Kickbase-Schluss</span>""", """<span>Startelf steht fest, bevor Kickbase sperrt</span>""")
    e("""<span>Aufstellung kommt vor dem Kickbase-Schluss (erstes Spiel des Spieltags)</span>""", """<span>Startelf steht fest, bevor Kickbase sperrt (erstes Spiel des Spieltags)</span>""")

    # Team-Form unter die Tabelle, vor die Fairnesstabelle
    e("""      ${teamForm()}
      <p class="af-st">${NOTE_ERKL}</p></div>`;""", """      <p class="af-st">${NOTE_ERKL}</p></div>`;""")
    e("""Ergebnisse: Sportschau.</p>${fairHtml(L)}</div>`;""", """Ergebnisse: Sportschau.</p>${teamForm()}${fairHtml(L)}</div>`;""")

    # Standard-Wechsel aus Inside (erscheinen als Meldung)
    e("""${sektion("03", "Standards", "Standard-Wechsel", "Wer übernimmt, wenn die Schützin fehlt.")}""", """${sektion("03", "Standards", "Standards", "Wer Ecken, Freistöße und Elfmeter schießt. Wechsel bei den Schützinnen kommen als Meldung.")}""")
    i1 = h.index("""      ${!w.length ? '<p class="dat">Bei deinen Vereinen hat sich diese Woche nichts geändert.</p>' : ""}""")
    i2 = h.index("""${kbBox(s.kb)}</div>`).join("")}""", i1) + len("""${kbBox(s.kb)}</div>`).join("")}""")
    h = h[:i1] + h[i2:]

    # Freistöße pro Spiel (gleiches Design wie Ecken) und Elfmeter als Grafik
    e("""      ${el.length ? `<h3 class="disp" style="font-size:19px;margin-top:8px">Elfmeter in der Liga</h3>""",
      r"""      ${AF.freist ? (() => { const f = Object.entries(AF.freist).filter(([k]) => STDALLE || zeigen(k)).sort((a, b) => b[1].f - a[1].f), m2 = Math.max(...Object.values(AF.freist).map(x => x.f), 1);
        return `<h3 class="disp" style="font-size:21px;margin-top:8px">Freistöße pro Spiel</h3><p class="af-st" style="font-size:12px">Gezählt als Fouls des Gegners. Viele Freistöße heißen viele Chancen für die Schützin.</p>
        <div class="eck"><div class="eck-h"><span></span><span>EIGENE</span><span></span><span>GEGEN</span></div>${f.map(([k, x]) => { const st = (IN.standards || []).find(q => q.k === k), w = st && (st.fs || [])[0], t = AF.stdt && AF.stdt[k], sz = w ? w[0] : t && t.fs[0] ? nachN(t.fs[0][0]) : null;
          return `<div class="eck-r">${logo(k, 22)}<span class="f">${dez(x.f)}</span><span class="bw"><span class="bb"><i style="width:${x.f / m2 * 100}%"></i></span>${sz ? `<small>Freistöße: <b>${esc(sz)}</b></small>` : ""}</span><span class="g">${x.g != null ? dez(x.g) : "–"}</span></div>`; }).join("")}</div>`; })() : ""}
      ${el.length ? `<h3 class="disp" style="font-size:21px;margin-top:8px">Elfmeter in der Liga</h3><div class="elf-l">${el.map(x => `<button class="elf-r" data-profil="${esc(x.id)}">${logo(x.k, 22)}<span><b>${esc(x.n)}</b><small>${esc(kname(x.k))}${x.fuss ? " · " + esc(x.fuss) : ""}</small></span><span class="pk">${"<i class=t></i>".repeat(x.t)}${"<i class=v></i>".repeat(x.v)}</span><span class="q">${x.t}/${x.t + x.v}</span></button>`).join("")}</div><p class="af-st">Grün: verwandelt, roter Ring: verschossen oder gehalten.</p>` : ""}
      ${false && el.length ? `<h3 class="disp" style="font-size:19px;margin-top:8px">Elfmeter in der Liga</h3>""")

    # Daten zum Spiel: Duelle als Balken, Einordnung mit Symbolen
    e("""${du ? `<div style="display:grid;gap:5px;justify-items:center;text-align:center">${kap("Direkte Duelle seit 2023")}<span style="font-size:12px;color:var(--muted)">${esc(kname(v.h))}: ${v.dus[0]} ${v.dus[0] === 1 ? "Sieg" : "Siege"}, ${v.dus[1]} Remis, ${v.dus[2]} ${v.dus[2] === 1 ? "Niederlage" : "Niederlagen"}</span></div>` : ""}""",
      """${du ? (() => { const n = v.dus[0] + v.dus[1] + v.dus[2] || 1, pz = x => x / n * 100;
        return `<div class="dz-dl">${kap("Direkte Duelle seit 2023 · " + n + " Spiele")}<div class="dz-db">${v.dus[0] ? `<span style="width:${pz(v.dus[0])}%;background:#4ADE80">${v.dus[0]}</span>` : ""}${v.dus[1] ? `<span style="width:${pz(v.dus[1])}%;background:#A9B4C6">${v.dus[1]}</span>` : ""}${v.dus[2] ? `<span style="width:${pz(v.dus[2])}%;background:#FF8A8A">${v.dus[2]}</span>` : ""}</div><div class="dz-dk"><span>${esc(kname(v.h))} gewinnt</span><span>Remis</span><span>${esc(kname(v.g))} gewinnt</span></div></div>`; })() : ""}""")
    e("""${(v.satz || []).length ? `<div class="dz-s">${kap("Was die Daten sagen")}${v.satz.map(t => `<p>${esc(t)}</p>`).join("")}</div>` : ""}""",
      """${(v.satz || []).length ? `<div class="dz-sa">${kap("Was die Daten sagen")}${v.satz.map(t => { const s = /Zufall|nicht fortschreiben|nichts über/.test(t) ? ["!", "#F5C26B"] : /klar stärker|Vorteile/.test(t) ? ["↑", "#4ADE80"] : ["=", "#8FB0FF"]; return `<div><i style="background:${s[1]}">${s[0]}</i><span>${esc(t)}</span></div>`; }).join("")}</div>` : ""}""")

    # Verletzungs-Einschätzung aus typischen Verläufen, wenn keine eigene vorliegt
    e("""  function verlaufGrafik(s){""", TYP + """  function verlaufGrafik(s){""")
    e("""  function profilSeite(s){""", """  function profilSeite(s){
    if (!s.einschaetzung) { const ve = verletzungEinsch(s); if (ve) s = Object.assign({}, s, {einschaetzung: ve}); }""")
    return h

if __name__ == "__main__":
    p = sys.argv[1]; t = r10(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
