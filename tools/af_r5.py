"""Runde 5 (Finn 04.11.2026): Inside entschlacken, Form-Bereich mit Noten zusammenführen, Tabelle mit Fairness,
Spielseite mit Team-Umschalter, Standards mit Elfmeter aus API-Football.
Wird von af_ticker_patch.py am Ende angewendet und kann allein auf eine bereits gepatchte Datei laufen:
python3 tools/af_r5.py <datei.html>
"""
import sys

CSS5 = """
.fkomp .tx{align-items:center;text-align:center}
.fkomp .tx .fbadge{align-self:center}
.fkomp .vn{justify-content:center}
.fnc{display:grid;gap:6px;background:var(--soft);border-radius:10px;padding:9px 10px}
.fnc .r{display:flex;justify-content:space-between;align-items:center;gap:10px}
.fnc .r > span:first-child{display:grid;gap:2px}
.fnc .r small{font-size:11.5px;color:#C9D3E3;line-height:1.4}
.fnc .w{display:grid;justify-items:end;gap:2px;font-size:12px;white-space:nowrap}
.pf-fm{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--soft);border-radius:10px;padding:8px 10px}
.pf-fm .l{display:grid;gap:2px}
.pf-fm .l b{font:700 10px var(--f-mono);letter-spacing:.04em}
.pf-fm .l span{font-size:12.5px}
.af-tw{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.af-tw button{display:flex;gap:8px;align-items:center;justify-content:center;background:var(--soft);border-radius:10px;padding:9px 6px;font-weight:600;font-size:13.5px;color:var(--ink)}
.af-tw button[aria-pressed="true"]{outline:2px solid #6E9BFF;background:rgba(110,155,255,.14)}
.eck-r .bw{display:grid;gap:2px}
.eck-r .bw small{font-size:10px;color:var(--muted);line-height:1}
"""

def r5(h):
    def e(a, b, n=1):
        nonlocal h
        if h.count(a) != n: raise SystemExit(f"R5: {h.count(a)}x statt {n}x: {a[:90]!r}")
        h = h.replace(a, b)
    i = h.rfind("</style>"); h = h[:i] + CSS5 + h[i:]
    # Warteschlange: Meldungen ohne Zeit sind noch nicht freigegeben
    e("""!N.some(m => m.id === n.id) && dt(n.zeit) <= new Date()""", """!N.some(m => m.id === n.id) && n.zeit && dt(n.zeit) <= new Date()""")

    # ---------- Inside: Form-Bereich mit API-Football-Noten (je Gruppe bis 10 Spielerinnen)
    e("""  const formListe = key => (((IN.form || {})[key]) || []).filter(f => zeigen(f.k));""",
      r"""  function afKarte(x, lauf){
    const s = (SPN && (spById(x.id) || findeSP(x.k, nachN(x.n)))) || {}, sp = s.spiele || [];
    const PS = {sicher: "sicher in der Startelf", erwartet: "erwartet in der Startelf", unsicher: "unsicher", unwahrscheinlich: "eher Bank", ausgeschlossen: "fällt aus"};
    return {n: x.n, k: x.k, id: x.id, af: true, lauf, big: dez(x.l3), big_txt: x.vorher ? `Ø Note letzte 3 (vorher ${dez(x.vorher)})` : "Ø Note letzte 3 Spiele",
      s: sp.map(z => [z.min || 0, z.art === "S" ? 1 : 0, (z.tore || []).length]),
      text: lauf ? `Starke Noten zuletzt und ein leichtes Programm: Die nächsten drei Gegner stehen im Schnitt auf Platz ${Math.round(x.nr)}.` : Math.abs(x.diff) < .3 ? `Konstant starke Noten: zuletzt ${dez(x.l3)}, davor ${dez(x.vorher)}.` : x.diff < 0 ? `Ihre Noten sind zuletzt deutlich gefallen, von ${dez(x.vorher)} auf ${dez(x.l3)}.` : `Ihre Noten sind zuletzt deutlich gestiegen, von ${dez(x.vorher)} auf ${dez(x.l3)}.`,
      kb: `Minuten der letzten 3 Ligaspiele: ${x.min3.map(m => m + "'").join(" · ")}${x.prog && PS[x.prog] ? `, nächstes Spiel ${PS[x.prog]}` : ""}.`};
  }
  const formListe = key => { const l = (((IN.form || {})[key]) || []).slice(), F = (AF && AF.form) || {}, dabei = new Set(l.map(f => f.k + "|" + normS(nachN(f.n))));
    const dazu = key === "up" ? (F.hoch || []).map(x => afKarte(x, false)).concat((F.lauf || []).map(x => afKarte(x, true))) : key === "down" ? (F.tief || []).map(x => afKarte(x, false)) : key === "hold" ? (F.stabil || []).map(x => afKarte(x, false)) : [];
    dazu.forEach(f => { const s = f.k + "|" + normS(nachN(f.n)); if (!dabei.has(s)) { dabei.add(s); l.push(f); } });
    return l.slice(0, 10).filter(f => zeigen(f.k)); };
  function programmVon(k){
    const L = (((SPN && SPN.vereine) || {})[k] || {}).kommend; if (!L) return null;
    const n = L.filter(z => z.wb === "Liga" && z.gk).slice(0, 3); if (!n.length) return null;
    const r = n.map(z => z.rang).filter(Boolean), av = r.length ? r.reduce((a, b) => a + b, 0) / r.length : null;
    return {next: n.map(z => [z.gk, z.ha, z.rang]), nr: av, ns: av == null ? null : av <= 5.5 ? "schwer" : av >= 9.5 ? "leicht" : "mittel"};
  }
  function afFormZeile(f){
    if (!AF || !AF.sp) return "";
    const s = SPN && (f.id ? spById(f.id) : findeSP(f.k, nachN(f.n))); if (!s) return "";
    const a = afSp(s.id), v = a && (a.no || []).filter(x => x[2] >= 60); if (!v || v.length < 4) return "";
    const n = v.map(x => x[1]), l3 = n.slice(-3).reduce((x, y) => x + y, 0) / 3, vor = n.length > 3 ? n.slice(0, -3).reduce((x, y) => x + y, 0) / (n.length - 3) : l3;
    const fl = (AF.form ? [].concat(AF.form.tief || [], AF.form.hoch || [], AF.form.lauf || [], AF.form.stabil || []) : []).find(x => x.id === s.id) || {};
    const c = l3 - vor <= -.6 ? "#F59E0B" : l3 - vor >= .6 ? "#4ADE80" : "#8FB0FF", e = fl.id ? einordnungSatz(fl) : "";
    return `<div class="fnc"><div class="r"><span><span class="kap">Noten ab 60 Minuten</span>${e ? `<small>${esc(e)}</small>` : ""}</span><span class="w">${spark(n.slice(-6), c)}<span><span class="mu">${dez(vor)}</span> → <b style="color:${c}">${dez(l3)}</b></span></span></div></div>`;
  }""")
    e("""    return `<article class="fk">${kopf}<div class="finh">${minutenBalken(f.s || [], /Tor/.test(f.big_txt || "") && !/Gegentor/.test(f.big_txt || ""))}<p>${esc(f.text)}</p>""",
      """    return `<article class="fk">${kopf}<div class="finh">${minutenBalken(f.s || [], /Tor/.test(f.big_txt || "") && !/Gegentor/.test(f.big_txt || ""))}${afFormZeile(f)}<p>${esc(f.text)}</p>""")
    # Noten-Check ohne die fünf Gruppen: nur noch xG-Check und Team-Form
    i1 = h.index("  function notenCheck(){"); i2 = h.index("  function formIndexAnzeigen")
    h = h[:i1] + r"""  function notenCheck(){
    if (!AF || !AF.form) return "";
    const x = (AF.xg || []).filter(f => zeigen(f.k)).slice(0, 4);
    return `<div style="display:grid;gap:8px;padding-top:14px">
      ${x.length ? `<h3 class="disp" style="font-size:19px">xG-Check ${(AF.xgmd || []).join(". und ")}. Spieltag</h3><div class="nc">${x.map(r => `<div class="nc-r">${logo(r.k, 26)}<span class="nm"><b>${esc(kname(r.k))} gegen ${esc(kname(r.gg))}</b><small>${r.md}. Spieltag: ${r.t} ${r.t === 1 ? "Tor" : "Tore"} bei ${dez(r.xg, 2)} xG. ${r.d > 0 ? "Mehr getroffen als erspielt, das gleicht sich meist aus." : "Chancen ungenutzt, die Offensive war besser als das Ergebnis."}</small></span><span class="w"><b style="color:${r.d > 0 ? "#4ADE80" : "#FF8A8A"}">${r.d > 0 ? "+" : ""}${dez(r.d)}</b><span>Tore minus xG</span></span></div>`).join("")}</div>` : ""}
      ${teamForm()}
      <p class="af-st">${NOTE_ERKL}</p></div>`;
  }
""" + h[i2:]
    e("""  function inside(){
    if (!IN){""", """  function inside(){
    if (!SPN) ladeSPN().then(() => { if (VIEW === "inside") { const y = window.scrollY; inside(); window.scrollTo(0, y); } }).catch(() => {});
    if (!IN){""")

    # ---------- Profil: Formkurve im Kickbase-Kasten
    e("""${pr ? `<p class="pf-w">${esc(warumSatz(s, pr))}</p>` : `<p class="pf-w">Für den nächsten Spieltag gibt es noch keine Prognose.</p>`}""",
      """${pr ? `<p class="pf-w">${esc(warumSatz(s, pr))}</p>` : `<p class="pf-w">Für den nächsten Spieltag gibt es noch keine Prognose.</p>`}${(() => { const a = afSp(s.id), v = a && (a.no || []).filter(x => x[2] >= 60); if (!v || v.length < 4) return "";
        const n = v.map(x => x[1]), l3 = n.slice(-3).reduce((x, y) => x + y, 0) / 3, vor = n.length > 3 ? n.slice(0, -3).reduce((x, y) => x + y, 0) / (n.length - 3) : l3, d = l3 - vor;
        const g = d <= -.6 ? ["FORMTIEF", "#F59E0B"] : d >= .6 ? ["AUFWIND", "#4ADE80"] : ["STABIL", "#8FB0FF"], pg = programmVon(s.k);
        return `<div class="pf-fm"><span class="l"><b style="color:${g[1]}">${g[0]}</b><span>Note <span class="mu">${dez(vor)}</span> → <b style="color:${g[1]}">${dez(l3)}</b> in den letzten 3</span>${pg && pg.ns && pg.ns !== "mittel" ? `<span style="font:700 10px var(--f-mono);color:${pg.ns === "schwer" ? "#FF8A8A" : "#4ADE80"}">${pg.ns === "schwer" ? "SCHWERES" : "LEICHTES"} PROGRAMM (Ø PLATZ ${Math.round(pg.nr)})</span>` : ""}</span>${spark(n.slice(-6), g[1])}</div>`; })()}""")

    # ---------- Standards: Elfmeter aus API-Football, wenn unsere Zelle offen ist; Ecken mit Schützin
    e("""${zelle(s.ecken)}${zelle(s.fs)}${zelle(s.elfer)}""",
      """${zelle(s.ecken)}${zelle(s.fs)}${zelle((s.elfer || []).length ? s.elfer : ((AF && AF.elf) || []).filter(x => x.k === s.k).map(x => [nachN(x.n), 1]))}""")
    e("""<div class="eck-r">${logo(k, 22)}<span class="f">${dez(x.f)}</span><span class="bb"><i style="width:${x.f / mx * 100}%"></i></span>""",
      """<div class="eck-r">${logo(k, 22)}<span class="f">${dez(x.f)}</span><span class="bw"><span class="bb"><i style="width:${x.f / mx * 100}%"></i></span>${(() => { const st = (IN.standards || []).find(q => q.k === k), w = st && (st.ecken || [])[0]; return w ? `<small>Ecken: ${esc(w[0])}</small>` : ""; })()}</span>""")

    # ---------- Statistik nur Spielerinnen: Fairnesstabelle zur Tabelle
    e(""",["fair","Fairnesstabelle","Kartenpunkte der Spielerinnen je Verein, wenigste oben"]""", "")
    e("""Verein antippen öffnet den Kader. Ergebnisse: Sportschau.</p></div>`;""", """Verein antippen öffnet den Kader. Ergebnisse: Sportschau.</p>${fairHtml(L)}</div>`;""")
    e("""  function ligaStand(){""", r"""  function fairHtml(L){
    const W = ligaWerte(L.spiele), F = {}; ALLE.forEach(c => F[c] = {k: c, gelb: 0, gr: 0, rot: 0});
    W.forEach(v => { const f = F[v.s.k]; if (f) { f.gelb += v.gelb; f.gr += v.gr; f.rot += v.rot; } });
    const FL = Object.values(F).map(f => Object.assign(f, {p: f.gelb + 3 * f.gr + 5 * f.rot})).sort((a, b) => a.p - b.p || kname(a.k).localeCompare(kname(b.k), "de"));
    return `<section class="stk" id="st-fair" style="margin-top:18px"><div class="stk-k"><h2>Fairnesstabelle</h2><small>Kartenpunkte der Spielerinnen je Verein, wenigste oben (Gelb 1, Gelb-Rot 3, Rot 5)</small></div><div class="ft"><div class="ft-r ft-h"><span>#</span><span></span><span>VEREIN</span><span><i class="kg"></i></span><span><i class="kgr"></i></span><span><i class="kr"></i></span><span>PKT</span></div>
      ${FL.map((f, i) => `<button class="ft-r" data-statverein="${f.k}"><span class="tb-pl">${i && f.p === FL[i - 1].p ? "" : i + 1}</span>${logo(f.k, 18)}<span class="tb-vn">${esc(kname(f.k))}</span><span>${f.gelb}</span><span>${f.gr}</span><span>${f.rot}</span><span class="tb-pk">${f.p}</span></button>`).join("")}</div></section>`;
  }
  function ligaStand(){""")

    # ---------- Spielseite: vor dem Spiel Aufstellungen per Umschalter, Daten zum Spiel darunter, ohne Sprungleiste
    e("""    const sprung = hatV && hatA ? '<div class="af-sprung"><button data-afsprung="af-dz">Daten zum Spiel ↓</button></div>' : "";""", """    const sprung = "";""")
    e("""teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim", p.status === "beendet", p.anstoss) + teamBlock(p.gast, p.gast_k, p.gast_aufstellung, "gast", p.status === "beendet", p.anstoss)""",
      """(p.status !== "beendet" ? teamSchalter(p) : teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim", p.status === "beendet", p.anstoss) + teamBlock(p.gast, p.gast_k, p.gast_aufstellung, "gast", p.status === "beendet", p.anstoss))""")
    e("""  function teamBlock(name, k, a, seite, vorbei, anstoss){""", r"""  const AFSEITE = {};
  function teamSchalter(p){
    const sel = AFSEITE[p.id] || "heim";
    return `<div class="af-tw" role="tablist">${[["heim", p.heim, p.heim_k], ["gast", p.gast, p.gast_k]].map(([s, n, k]) => `<button role="tab" data-afseite="${s}" aria-pressed="${sel === s}">${logo(k, 22)}<span>${esc(KNAME[k] || n)}</span></button>`).join("")}</div>`
      + (sel === "heim" ? teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim", false, p.anstoss) : teamBlock(p.gast, p.gast_k, p.gast_aufstellung, "gast", false, p.anstoss));
  }
  document.addEventListener("click", e => { const b = e.target.closest("[data-afseite]"); if (!b || !GAME) return; AFSEITE[GAME] = b.dataset.afseite; spiel(GAME, true); });
  function teamBlock(name, k, a, seite, vorbei, anstoss){""")
    # Daten zum Spiel: Tabelle und Heim-/Auswärtstabelle, Duelle nur als Bilanz
    e("""<small>${v.rang[0]}. Platz · zu Hause</small>""", """<small>Tabelle ${v.rang[0]}.${v.rolle && v.rolle[0] ? ` · Heim ${v.rolle[0]}.` : ""}</small>""")
    e("""<small>${v.rang[1]}. Platz · auswärts</small>""", """<small>Tabelle ${v.rang[1]}.${v.rolle && v.rolle[1] ? ` · Auswärts ${v.rolle[1]}.` : ""}</small>""")
    e("""<div class="dz-du">${du}</div>""", "")
    e("""Duelle aus API-Football, Sicht ${esc(kname(v.h))}.""", """Heim/Auswärts = Platz in der Heim- bzw. Auswärtstabelle. Duelle aus API-Football.""")
    e(""" H/A = Heim- oder Auswärtsspiel von ${esc(kname(v.h))}.""", "")
    return h

if __name__ == "__main__":
    p = sys.argv[1]; t = r5(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
