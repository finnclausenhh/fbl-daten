#!/usr/bin/env python3
"""Baut die Testkopie des Tickers mit den API-Football-Daten (Finn 03.11.2026).

python3 tools/af_ticker_patch.py <ticker/index.html> <ziel/index.html> [datenpfad]
Datenpfad Standard: test/apifootball.json (relativ zur base https://finnclausenhh.github.io/fbl-daten/)
"""
import sys

QUELLE, ZIEL = sys.argv[1], sys.argv[2]
DATEN = sys.argv[3] if len(sys.argv) > 3 else "test/apifootball.json"
LIVE = "--live" in sys.argv
h = open(QUELLE, encoding="utf-8").read()

def ers(alt, neu, n=1):
    global h
    c = h.count(alt)
    if c != n: raise SystemExit(f"Stelle {c}x statt {n}x gefunden: {alt[:90]!r}")
    h = h.replace(alt, neu)

CSS = r"""
/* API-Football (Testkopie 03.11.2026) */
.af-st{font-size:10.5px;color:var(--muted);line-height:1.45}
.pf-tag.fu{background:rgba(110,155,255,.14);color:#C7D7FF}
.pf-blick small.e{font-size:10.5px}
.pf-kbz{display:grid;gap:4px}
.pf-kbz div{display:flex;gap:8px;align-items:baseline;font-size:13.5px;line-height:1.35}
.pf-kbz b{font-family:var(--f-display);font-weight:800;font-size:17px;min-width:34px;text-align:center}
.pf-std.el{background:rgba(46,184,114,.18);color:#A6EBC4}
.pf-sae .tz{display:flex;gap:2px;justify-content:center;align-items:center}
.pf-sae .tz i{font:700 9px var(--f-mono);font-style:normal;border-radius:4px;padding:0 3px;margin:0;line-height:13px;color:#0B1220}
.pf-sae .tz i.t{background:#4ADE80}
.pf-sae .tz i.v{background:#8FB0FF}
.pf-sae .nt{font:700 9.5px var(--f-mono);height:12px;line-height:12px}
.pf-sae .nt.k{opacity:.5}
.pf-leg .lt,.pf-leg .lv{width:auto;height:auto;font:700 9px var(--f-mono);font-style:normal;color:#0B1220;border-radius:3px;padding:0 3px;line-height:12px}
.pf-leg .lt{background:#4ADE80}
.pf-leg .lv{background:#8FB0FF}
.af-noten{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;text-align:center;margin-top:4px}
.af-noten div{background:var(--soft);border-radius:10px;padding:9px 2px 7px;display:grid;gap:2px;justify-items:center}
.af-noten b{font-family:var(--f-display);font-weight:800;font-size:22px;line-height:1}
.af-noten span{font-size:10.5px;color:var(--muted);white-space:nowrap}
.af-ww{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.af-ww div{background:var(--soft);border-radius:10px;padding:9px 10px;display:grid;gap:1px}
.af-ww b{font-family:var(--f-display);font-weight:800;font-size:20px;line-height:1.1}
.af-ww span{font-size:11px;color:var(--muted)}
.af-sb{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;text-align:center}
.af-sb div{background:var(--soft);border-radius:10px;padding:9px 2px 7px;display:grid;gap:3px;justify-items:center}
.af-sb b{font-size:16px;font-weight:700;line-height:1.1}
.af-sb span{font-size:10.5px;color:var(--muted)}
.spl .as{background:#8FB0FF;color:#0B1220;font:800 10px var(--f-mono)}
.spl .nt{position:absolute;left:50%;transform:translateX(-50%);bottom:-7px;z-index:3;min-width:24px;height:16px;padding:0 3px;border-radius:5px;font:700 9.5px/16px var(--f-mono);color:#0B1220;text-align:center;box-shadow:0 0 0 1.5px var(--card)}
.spl .nt.best{outline:1.5px solid #fff}
.spl:has(.nt) .nm{margin-top:8px}
.af-bar{display:grid;grid-template-columns:44px minmax(0,1fr) 44px;gap:8px;align-items:center;font-size:12.5px}
.af-bar .w{font-weight:700;font-variant-numeric:tabular-nums}
.af-bar .w.r{text-align:right}
.af-bar .m{display:grid;gap:3px;justify-items:center}
.af-bar .m span{font-size:10.5px;color:var(--muted);line-height:1}
.af-bar .bb{display:flex;width:100%;height:6px;border-radius:3px;overflow:hidden;background:rgba(255,255,255,.06);gap:2px}
.af-bar .bb i{display:block;height:100%}
.af-best{display:flex;flex-wrap:wrap;gap:6px}
.af-best span{background:var(--soft);border-radius:8px;padding:5px 8px;font-size:12.5px;display:flex;gap:6px;align-items:center}
.af-best b{font:700 11px var(--f-mono);color:#0B1220;border-radius:4px;padding:1px 4px}
.af-kb{background:rgba(110,155,255,.1);border-radius:10px;padding:9px 11px;font-size:13px;line-height:1.4}
.af-kb b{color:#C7D7FF}
.dz{display:grid;gap:10px}
.dz-k{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:8px;align-items:center;text-align:center}
.dz-k .t{display:grid;justify-items:center;gap:4px;font-size:12.5px;font-weight:600;min-width:0}
.dz-k .t small{font-weight:500;color:var(--muted);font-size:11px}
.dz-form{display:flex;gap:3px;justify-content:center}
.dz-form i{width:16px;height:16px;border-radius:4px;font:700 9px/16px var(--f-mono);font-style:normal;color:#0B1220;text-align:center}
.dz-form .S{background:#4ADE80}.dz-form .U{background:#A9B4C6}.dz-form .N{background:#FF8A8A}
.dz-t{display:grid;grid-template-columns:minmax(0,1fr) 92px minmax(0,1fr);gap:4px 8px;align-items:center;font-size:13px}
.dz-t .l{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.dz-t .r{text-align:left;font-weight:700;font-variant-numeric:tabular-nums}
.dz-t .m{text-align:center;font-size:10.5px;color:var(--muted);line-height:1.2}
.dz-t .bes{color:#4ADE80}
.dz-du{display:flex;flex-wrap:wrap;gap:5px;justify-content:center}
.dz-du span{background:var(--soft);border-radius:6px;padding:3px 6px;font:600 11px var(--f-mono)}
.dz-s{display:grid;gap:6px}
.dz-s p{margin:0;font-size:13px;line-height:1.45}
details.dzb{background:var(--soft);border-radius:10px;padding:0 10px}
details.dzb > summary{cursor:pointer;list-style:none;padding:9px 0;font-weight:600;font-size:13px;display:flex;justify-content:space-between;align-items:center}
details.dzb > summary::-webkit-details-marker{display:none}
details.dzb > summary::after{content:"›";transform:rotate(90deg);transition:transform .15s;color:var(--muted)}
details.dzb[open] > summary::after{transform:rotate(-90deg)}
details.dzb[open]{padding-bottom:10px}
.nc{display:grid;gap:8px}
.nc-r{box-sizing:border-box;display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:10px;align-items:center;background:var(--soft);border-radius:12px;padding:9px 10px;text-align:left;width:100%}
.nc-r .nm{display:grid;gap:3px;min-width:0}
.nc-r .nm b{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nc-r .nm small{font-size:11.5px;color:var(--muted);line-height:1.35}
.nc-r .dn{display:flex;gap:3px}
.nc-r .dn i{font:700 9.5px/15px var(--f-mono);font-style:normal;color:#0B1220;border-radius:4px;padding:0 3px;min-width:22px;text-align:center}
.nc-r .w{display:grid;justify-items:end;gap:1px}
.nc-r .w b{font-family:var(--f-display);font-weight:800;font-size:20px;line-height:1}
.nc-r .w span{font-size:10.5px;color:var(--muted);white-space:nowrap}
.nc-tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.nc-tabs button{background:var(--soft);border-radius:10px;padding:8px 6px;font-weight:600;font-size:13px;text-align:center}
.nc-tabs button[aria-pressed="true"]{outline:2px solid #6E9BFF}
.eck{display:grid;gap:5px}
.eck-r{display:grid;grid-template-columns:26px 40px minmax(0,1fr) 40px;gap:8px;align-items:center;font-size:12.5px}
.eck-r .f{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.eck-r .g{color:var(--muted);font-variant-numeric:tabular-nums}
.eck-r .bb{height:6px;border-radius:3px;background:rgba(255,255,255,.06);overflow:hidden}
.eck-r .bb i{display:block;height:100%;background:#6E9BFF;border-radius:3px}
.eck-h{display:grid;grid-template-columns:26px 40px minmax(0,1fr) 40px;gap:8px;font:600 10px var(--f-mono);color:var(--muted)}
.eck-h span:nth-child(2){text-align:right}
.af-test{position:sticky;top:0;z-index:50;background:#E0962B;color:#0B1220;font:700 11px var(--f-mono);text-align:center;padding:4px 6px;letter-spacing:.04em}
"""
i = h.rfind("</style>"); h = h[:i] + CSS + h[i:]

# Testbanner
ers("<body>", '<body><div class="af-test">TESTVERSION · neue Daten aus API-Football · nicht öffentlich</div>')

# ------------------------------------------------------------------ Laden und Helfer
ers("  const ladeSPN = () =>", r"""  // ---------------- API-Football (Testkopie): Noten, Teamwerte, Vorschau
  let AF = null;
  const ladeAF = () => AF ? Promise.resolve(AF) : json("%DATEN%").then(d => { AF = d || {}; return AF; }).catch(() => { AF = {}; return AF; });
  const dez = (x, n = 1) => Number(x).toFixed(n).replace(".", ",");
  const NFARBE = n => n >= 8 ? "#4ADE80" : n >= 7 ? "#A6E3B8" : n >= 6 ? "#F5C26B" : "#FF8A8A";
  const NOTE_ERKL = "* Note von 0 bis 10, berechnet von API-Football aus den Spielwerten (Pässe, Zweikämpfe, Schüsse, Tore). Keine Kickbase-Punkte. Für Formkurve und Schnitt zählen nur Einsätze ab 60 Minuten.";
  const afSp = id => (AF && AF.sp && AF.sp[id]) || null;
  function spAus(k, s){ if (!SPN) return null; if (!SPIDX) spOrt(k, s); return SPIDX && (SPIDX[k + "|" + nNorm(s.voll || "")] || SPIDX[k + "|" + nNorm(nachN(s.voll || s.n))]) || null; }
  let AFNOTEN = null, AFBEST = null;
  function afNeu(){
    if (BACK === "stat" && VIEW_STAT) { statView(VIEW_STAT, true); return; }
    const pf = document.querySelector(".det.pf .pf-teilen"); if (pf) { const s = spById(pf.dataset.teilen); if (s) { const y = window.scrollY; profilSeite(s); window.scrollTo(0, y); } return; }
    if (VIEW === "spielplan" && GAME) { spiel(GAME, true); return; }
    if (VIEW === "inside" && IN) neuZeichnen();
  }
  const ladeSPN = () =>""".replace("%DATEN%", DATEN))

ers('  fetch("patchnotes.json", {cache: "no-store"})', '  ladeAF().then(afNeu);\n  window.AFT = {spiel: id => { VIEW = "spielplan"; Promise.all([loadSP(), ladeSPN(), ladeAF()]).then(() => spiel(id)); }, show};\n  fetch("patchnotes.json", {cache: "no-store"})')

# ------------------------------------------------------------------ Profil
# Fuß-Tag
ers("""<div class="pf-tags">${stTag}<span class="pf-tag">${esc(KBNAME[s.pos] || s.pos || "")}</span></div>""",
    """<div class="pf-tags">${stTag}<span class="pf-tag">${esc(KBNAME[s.pos] || s.pos || "")}</span>${(afSp(s.id) || {}).fuss ? `<span class="pf-tag fu">${{rechts: "RECHTSFUSS", links: "LINKSFUSS", "beidfüßig": "BEIDFÜSSIG"}[afSp(s.id).fuss]}</span>` : ""}</div>""")

# Letzte 3 Liga: kurzer Text, passt immer in die Kachel
ers("""<small>${letzte3.length ? `Sp. ${letzte3[0].md} bis ${letzte3[letzte3.length - 1].md}: ` : ""}${eins.length}x dabei${istTW ? (zn3 ? ` · ${zn3}x zu Null` : "") : fT || fV ? ` · ${fT}T ${fV}V` : ""}</small>""",
    """${(() => { const nS = letzte3.filter(e => e.art === "S").length, nE = letzte3.filter(e => e.art === "E").length;
        const t = !letzte3.length ? "noch kein Spiel" : !nS && !nE ? "ohne Einsatz" : !nE ? nS + "x Startelf" : !nS ? nE + "x Joker" : nS + " Start · " + nE + " Joker";
        return `<small class="${t.length > 15 ? "e" : ""}" title="Spieltag ${letzte3.length ? letzte3[0].md + " bis " + letzte3[letzte3.length - 1].md : ""}${istTW && zn3 ? ", " + zn3 + "x zu Null" : fT || fV ? ", " + fT + " Tore, " + fV + " Vorlagen" : ""}">${t}</small>`; })()}""")

# Für Kickbase: Startelf-Bilanz der letzten 5, Elfmeter aus API-Football
ers("""    h += `<section class="pf-box pf-kb">${kap("Für Kickbase")}${pr ? `<p class="pf-w">${esc(warumSatz(s, pr))}</p>` : `<p class="pf-w">Für den nächsten Spieltag gibt es noch keine Prognose.</p>`}
      ${std ? kap("Standards") + `<div class="pf-stds">${std}</div>` : ""}""",
    """    const l5 = sp.slice(-5), s5 = l5.filter(e => e.art === "S"), aus5 = s5.filter(e => (e.min || 0) < 85 && !e.rot).length, e5 = l5.filter(e => e.art === "E").length;
    const kbz = l5.length ? `<div class="pf-kbz"><div><b>${s5.length}/${l5.length}</b><span>in der Startelf (letzte ${l5.length} Ligaspiele)${aus5 ? `, davon ${aus5}x vorzeitig ausgewechselt` : s5.length ? ", immer durchgespielt" : ""}${e5 ? `, ${e5}x eingewechselt` : ""}</span></div></div>` : "";
    const elf = (afSp(s.id) || {}).elf, elfC = elf ? `<span class="pf-std el">Elfmeter <i>${elf[0]} von ${elf[0] + elf[1]} verwandelt</i></span>` : "";
    h += `<section class="pf-box pf-kb">${kap("Für Kickbase")}${pr ? `<p class="pf-w">${esc(warumSatz(s, pr))}</p>` : `<p class="pf-w">Für den nächsten Spieltag gibt es noch keine Prognose.</p>`}
      ${std || elfC ? kap("Standards") + `<div class="pf-stds">${std}${elfC}</div>` : ""}""")

# Saison: Tore/Vorlagen als T/V, Note* unter jedem Ligaspiel
ers("""<span class="tz">${(e.tore || []).length ? "⚽".repeat(Math.min(3, e.tore.length)) : ""}${e.vorl ? `<i>${e.vorl} Vorl.</i>` : ""}</span>""",
    """<span class="tz">${(e.tore || []).length ? `<i class="t">${e.tore.length}T</i>` : ""}${e.vorl ? `<i class="v">${e.vorl}V</i>` : ""}</span>""")
ers("""<span class="md">${lab}</span></button>`; }).join("")}</div>""",
    """<span class="md">${lab}</span>${(() => { const af = afSp(s.id), n = e.typ === "Liga" && af && (af.no || []).find(x => x[0] === e.md); return AF && AF.sp ? `<span class="nt${n && n[2] < 60 ? " k" : ""}" style="color:${n ? NFARBE(n[1]) : "transparent"}">${n ? dez(n[1]) : "–"}</span>` : ""; })()}</button>`; }).join("")}</div>""")
ers("""<span><i class="po"></i>Pokal</span><span><i class="cl"></i>UWCL</span></div>` : '<p class="pf-w">Noch keine Ligaspiele.</p>'}</section>`;""",
    """<span><i class="po"></i>Pokal</span><span><i class="cl"></i>UWCL</span></div>
      <div class="pf-leg"><span><i class="lt">T</i>Tor</span><span><i class="lv">V</i>Vorlage</span>${AF && AF.sp ? "<span>Zahl darunter: Note*</span>" : ""}</div>
      ${(() => { const af = afSp(s.id); if (!af || !af.avg) return "";
        return `<div class="af-noten"><div><b style="color:${NFARBE(af.avg)}">${dez(af.avg)}</b><span>Ø Note*</span></div><div><b style="color:${af.l3 ? NFARBE(af.l3) : "var(--muted)"}">${af.l3 ? dez(af.l3) : "–"}</b><span>Ø letzte 3*</span></div><div><b style="color:${NFARBE(af.best)}">${dez(af.best)}</b><span>Beste Note*</span></div></div>
        <p class="af-st">${NOTE_ERKL}${(af.no || []).some(x => x[2] < 60) ? " Blasse Noten: unter 60 Minuten, zählen nicht." : ""}</p>`; })()}` : '<p class="pf-w">Noch keine Ligaspiele.</p>'}</section>`;""")

# Weitere Werte und Steckbrief nach den News
ers("""    const f = FOTOS[s.n];
    h += `<div class="pf-fuss">""",
    """    { const af = afSp(s.id) || {}, st = s.stat || {}, ww = [];
      if (st.sch) ww.push([st.sch, "Torschüsse"]);
      if (af.kp90 != null) ww.push([dez(af.kp90, 1), "Schlüsselpässe pro 90*"]);
      if (st.zk_ges) ww.push([Math.round(st.zk_w / st.zk_ges * 100) + " %", `Zweikämpfe gewonnen (${st.zk_w} von ${st.zk_ges})`]);
      if (af.drib) ww.push([af.drib[0] + "/" + af.drib[1], "Dribblings erfolgreich*"]);
      if (af.parsp) ww.push([dez(af.par / af.parsp, 1), `Paraden pro Spiel* (${af.parsp} Spiele)`]);
      const gelb = sp.filter(e => e.gelb).length; if (gelb || st.fouls) ww.push([gelb + (gelb >= 4 ? " ⚠" : ""), gelb >= 4 ? "Gelbe, bei der 5. ein Spiel Sperre" : `Gelbe Karten${st.fouls ? ", " + st.fouls + (st.fouls === 1 ? " Foul" : " Fouls") : ""}`]);
      if (ww.length) h += `<section class="pf-box">${kap("Weitere Werte")}<div class="af-ww">${ww.map(w => `<div><b>${w[0]}</b><span>${esc(w[1])}</span></div>`).join("")}</div>${ww.some(w => /\\*/.test(w[1])) ? '<p class="af-st">* aus API-Football, übrige Werte aus der Spielstatistik der Sportschau.</p>' : ""}</section>`;
      const sb = [[af.fuss ? af.fuss[0].toUpperCase() + af.fuss.slice(1) : "–", "Starker Fuß"], [af.alter ? af.alter + " J." : "–", "Alter"], [af.gr ? dez(af.gr / 100, 2) + " m" : "–", "Größe"], [esc(s.nation || "–"), "Nation"]];
      if (af.fuss || af.alter || af.gr) h += `<section class="pf-box">${kap("Steckbrief")}<div class="af-sb">${sb.map(w => `<div><b>${w[0]}</b><span>${w[1]}</span></div>`).join("")}</div></section>`; }
    const f = FOTOS[s.n];
    h += `<div class="pf-fuss">""")

# ------------------------------------------------------------------ Spielfeld: Vorlage als V, Note-Badge
ers("""if (s.vorl > 0) ex += `<span class="as">${s.vorl} Vorl.</span>`;""",
    """if (s.vorl > 0) ex += `<span class="as">${s.vorl}V</span>`; { const x = AFNOTEN && spAus(k, s), n = x && AFNOTEN[x.id]; if (n) ex += `<span class="nt${AFBEST && AFBEST.has(x.id) ? " best" : ""}" style="background:${NFARBE(n)}">${dez(n)}</span>`; }""")

# ------------------------------------------------------------------ Spielseite: Statistik, Noten, Daten zum Spiel
ers("""    const pv = p.platzverweise || [], bs = belSeiten(p);""",
    """    const pv = p.platzverweise || [], bs = belSeiten(p);
    const AS = AF && AF.spiele && AF.spiele[p.id];
    AFNOTEN = AS ? AS.no : null; AFBEST = null;
    if (AS && SPN) { AFBEST = new Set(); [p.heim_k, p.gast_k].forEach(k => { const l = Object.entries(AS.no).filter(([id]) => (spById(id) || {}).k === k).sort((a, b) => b[1] - a[1]); if (l[0]) AFBEST.add(l[0][0]); }); }
    const afBox = AS ? afStatBox(p, AS) : p.status !== "beendet" && AF && (AF.vorschau || []).find(v => v.id === p.id) ? `<div class="kartebox">${kap("Daten zum Spiel")}${datenZumSpiel(AF.vorschau.find(v => v.id === p.id))}</div>` : "";""")
ers("""${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""", """${afBox}${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""")
ers("""    window.scrollTo(0, halten ? y : 0);
  }
  function teamBlock(""",
    """    AFNOTEN = null; AFBEST = null;
    window.scrollTo(0, halten ? y : 0);
  }
  function afStatBox(p, AS){
    const w = AS.w || {}, Z = [["xg", "Expected Goals (xG)", 2], ["sch", "Torschüsse"], ["tor", "aufs Tor"], ["bes", "Ballbesitz", 0, " %"], ["eck", "Ecken"], ["par", "Paraden"], ["fou", "Fouls"], ["pq", "Passquote", 0, " %"]];
    const hf = "#6E9BFF", gf = "#A9B4C6";
    const zeilen = Z.filter(z => w[z[0]] && w[z[0]][0] != null && w[z[0]][1] != null).map(([k, t, d, e]) => { const [a, b] = w[k], s = a + b || 1, f = x => (d ? dez(x, d) : Math.round(x)) + (e || "");
      return `<div class="af-bar"><span class="w">${f(a)}</span><div class="m"><span>${t}</span><span class="bb"><i style="width:${a / s * 100}%;background:${hf}"></i><i style="width:${b / s * 100}%;background:${gf}"></i></span></div><span class="w r">${f(b)}</span></div>`; }).join("");
    if (!zeilen) return "";
    const best = [p.heim_k, p.gast_k].map(k => Object.entries(AS.no || {}).filter(([id]) => (spById(id) || {}).k === k).sort((a, b) => b[1] - a[1])[0]).filter(Boolean);
    const kb = []; if (w.xg) [[p.heim, 0], [p.gast, 1]].forEach(([n, i]) => { const t = Number((p.ergebnis || [])[i]), d = t - w.xg[i];
      if (d >= 1.5) kb.push(`<b>${esc(n)}</b> traf ${t}-mal bei ${dez(w.xg[i])} xG. So effizient bleibt kaum ein Team, daraus folgt für das nächste Spiel nicht automatisch so viel Offensive.`);
      if (d <= -1.5) kb.push(`<b>${esc(n)}</b> erspielte ${dez(w.xg[i])} xG, traf aber nur ${t}-mal. Die Chancen waren da, das spricht eher für mehr Tore im nächsten Spiel.`); });
    return `<div class="kartebox">${kap("Statistik")}<div style="display:grid;gap:9px">${zeilen}</div>
      ${best.length ? kap("Beste Note* je Team") + `<div class="af-best">${best.map(([id, n]) => { const x = spById(id); return x ? `<span>${logo(x.k, 16)}${esc(nachN(x.n))}<b style="background:${NFARBE(n)}">${dez(n)}</b></span>` : ""; }).join("")}</div>` : ""}
      ${kb.length ? `<div class="af-kb">${kb.join("<br>")}</div>` : ""}<p class="af-st">Teamwerte und Noten: API-Football. ${NOTE_ERKL}</p></div>`;
  }
  function datenZumSpiel(v){
    const H = v.heim, G = v.gast, f = x => x == null ? "–" : dez(x, 1);
    const reihe = (t, a, b, besser) => { const ba = a != null && b != null && a !== b ? (besser === "hoch" ? a > b : a < b) : null;
      return `<span class="l${ba === true ? " bes" : ""}">${a == null ? "–" : a}</span><span class="m">${t}</span><span class="r${ba === false ? " bes" : ""}">${b == null ? "–" : b}</span>`; };
    const fo = s => `<span class="dz-form">${String(s || "").split("").map(c => `<i class="${c}">${c}</i>`).join("")}</span>`;
    const sz = d => { if (d.includes("md")) { const j = Number(d.slice(0, 4)); return String(j).slice(2) + "/" + String(j + 1).slice(2); } const j = Number(d.slice(0, 4)) - (Number(d.slice(5, 7)) < 7 ? 1 : 0); return String(j).slice(2) + "/" + String(j + 1).slice(2); };
    const du = (v.du || []).map(d => `<span>${sz(d.d)} ${d.h === v.h ? "H" : "A"} ${d.t[0]}:${d.t[1]}</span>`).join("");
    return `<div class="dz"><div class="dz-k"><div class="t">${logo(v.h, 30)}<span>${esc(kname(v.h))}</span><small>${v.rang[0]}. Platz · zu Hause</small>${fo(v.form[0])}</div><span class="mu" style="font-size:11px">Form<br>letzte 5</span><div class="t">${logo(v.g, 30)}<span>${esc(kname(v.g))}</span><small>${v.rang[1]}. Platz · auswärts</small>${fo(v.form[1])}</div></div>
      <div class="dz-t">${reihe("Punkte pro Spiel", f(H.pkt), f(G.pkt), "hoch")}${reihe("Tore pro Spiel", f(H.t), f(G.t), "hoch")}${reihe("Gegentore", f(H.g), f(G.g), "tief")}${reihe("Spiele zu Null", H.zn, G.zn, "hoch")}${reihe("Ecken pro Spiel", f(H.eck), f(G.eck), "hoch")}</div>
      ${du ? `<div style="display:grid;gap:5px;justify-items:center;text-align:center">${kap("Direkte Duelle seit 2023")}<span style="font-size:12px;color:var(--muted)">${esc(kname(v.h))}: ${v.dus[0]} ${v.dus[0] === 1 ? "Sieg" : "Siege"}, ${v.dus[1]} Remis, ${v.dus[2]} ${v.dus[2] === 1 ? "Niederlage" : "Niederlagen"}</span><div class="dz-du">${du}</div></div>` : ""}
      ${(v.satz || []).length ? `<div class="dz-s">${kap("Was die Daten sagen")}${v.satz.map(t => `<p>${esc(t)}</p>`).join("")}</div>` : ""}
      ${(v.kb || []).length ? `<div class="af-kb"><b>Für Kickbase:</b> ${v.kb.map(esc).join(" ")}</div>` : ""}
      <p class="af-st">Heimwerte von ${esc(kname(v.h))} (${H.sp} Spiele), Auswärtswerte von ${esc(kname(v.g))} (${G.sp} Spiele), nur diese Saison. H/A = Heim- oder Auswärtsspiel von ${esc(kname(v.h))}. Grün = besserer Wert. Duelle aus API-Football, Sicht ${esc(kname(v.h))}.</p></div>`;
  }
  function teamBlock(""")

# ------------------------------------------------------------------ Inside: Noten-Check und xG-Check im Form-Bereich
ers("""      <div class="rail" id="rail">${l.map(f => formKarte(f, g)).join("")}</div>`}</section>`;
  }""",
    """      <div class="rail" id="rail">${l.map(f => formKarte(f, g)).join("")}</div>`}${notenCheck()}</section>`;
  }
  let NCDIR = "tief";
  function notenCheck(){
    if (!AF || !AF.form) return "";
    const l = (AF.form[NCDIR] || []).filter(f => zeigen(f.k)), x = (AF.xg || []).filter(f => zeigen(f.k)).slice(0, 4);
    const PS = {sicher: "Sicher", erwartet: "Erwartet", unsicher: "Unsicher", unwahrscheinlich: "Unwahrscheinlich", ausgeschlossen: "fällt aus"};
    return `<div style="display:grid;gap:8px;padding-top:14px"><h3 class="disp" style="font-size:21px">Noten-Check*</h3>
      <p class="af-st" style="font-size:12px">Letzte 3 Noten gegen die Noten davor, nur Einsätze ab 60 Minuten und nur Stammspielerinnen. Die Minuten zeigen, ob sie trotzdem spielt.</p>
      <div class="nc-tabs"><button data-nc="tief" aria-pressed="${NCDIR === "tief"}">Formtief (${(AF.form.tief || []).filter(f => zeigen(f.k)).length})</button><button data-nc="hoch" aria-pressed="${NCDIR === "hoch"}">Formhoch (${(AF.form.hoch || []).filter(f => zeigen(f.k)).length})</button></div>
      <div class="nc">${l.length ? l.map(f => `<button class="nc-r" data-profil="${esc(f.id)}">${logo(f.k, 26)}<span class="nm"><b>${esc(f.n)}</b><span class="dn">${f.noten.map(n => `<i style="background:${NFARBE(n)}">${dez(n)}</i>`).join("")}</span>
        <small>Minuten letzte 3: ${f.min3.map(m => m + "'").join(" · ")}${f.prog && PS[f.prog] ? ` · nächstes Spiel: ${PS[f.prog]}` : ""}</small></span>
        <span class="w"><b style="color:${NCDIR === "tief" ? "#FF8A8A" : "#4ADE80"}">${f.diff > 0 ? "+" : ""}${dez(f.diff)}</b><span>${dez(f.l3)} statt ${dez(f.vorher)}</span></span></button>`).join("") : '<p class="dat">Keine Spielerin deiner Vereine in dieser Gruppe.</p>'}</div>
      ${x.length ? `<h3 class="disp" style="font-size:19px;margin-top:8px">xG-Check ${(AF.xgmd || []).join(". und ")}. Spieltag</h3><div class="nc">${x.map(r => `<div class="nc-r">${logo(r.k, 26)}<span class="nm"><b>${esc(kname(r.k))} gegen ${esc(kname(r.gg))}</b><small>${r.md}. Spieltag: ${r.t} ${r.t === 1 ? "Tor" : "Tore"} bei ${dez(r.xg, 2)} xG. ${r.d > 0 ? "Mehr getroffen als erspielt, das gleicht sich meist aus." : "Chancen ungenutzt, die Offensive war besser als das Ergebnis."}</small></span><span class="w"><b style="color:${r.d > 0 ? "#4ADE80" : "#FF8A8A"}">${r.d > 0 ? "+" : ""}${dez(r.d)}</b><span>Tore minus xG</span></span></div>`).join("")}</div>` : ""}
      <p class="af-st">${NOTE_ERKL}</p></div>`;
  }""")

# Standards: Ecken pro Spiel und Elfmeter
ers("""          ${s.hinweis ? `<div class="hw">${svg(P.warn, "").replace("<svg", '<svg style="width:13px;height:13px;flex:none;stroke:currentColor;fill:none;stroke-width:2"')}<span>${esc(s.hinweis)}</span></div>` : ""}</div>`).join("")}</div></section>`;""",
    """          ${s.hinweis ? `<div class="hw">${svg(P.warn, "").replace("<svg", '<svg style="width:13px;height:13px;flex:none;stroke:currentColor;fill:none;stroke-width:2"')}<span>${esc(s.hinweis)}</span></div>` : ""}</div>`).join("")}</div>${afStandards()}</section>`;
  }
  function afStandards(){
    if (!AF || !AF.ecken) return "";
    const e = Object.entries(AF.ecken).filter(([k]) => STDALLE || zeigen(k)).sort((a, b) => b[1].f - a[1].f), mx = Math.max(...Object.values(AF.ecken).map(x => x.f), 1);
    const el = (AF.elf || []).filter(x => STDALLE || zeigen(x.k));
    return `<div style="display:grid;gap:8px;padding-top:14px"><h3 class="disp" style="font-size:21px">Ecken pro Spiel*</h3><p class="af-st" style="font-size:12px">Viele eigene Ecken = viele Chancen für die Schützin und die Kopfballspielerinnen.</p>
      <div class="eck"><div class="eck-h"><span></span><span>EIGENE</span><span></span><span>GEGEN</span></div>${e.map(([k, x]) => `<div class="eck-r">${logo(k, 22)}<span class="f">${dez(x.f)}</span><span class="bb"><i style="width:${x.f / mx * 100}%"></i></span><span class="g">${x.g != null ? dez(x.g) : "–"}</span></div>`).join("")}</div>
      ${el.length ? `<h3 class="disp" style="font-size:19px;margin-top:8px">Elfmeter in der Liga*</h3><div class="af-best">${el.map(x => `<button class="pf-std${x.v ? "" : " el"}" data-profil="${esc(x.id)}" style="display:flex;gap:5px;align-items:center">${logo(x.k, 14)}${esc(nachN(x.n))} <i>${x.t}/${x.t + x.v}${x.fuss ? ", " + x.fuss : ""}</i></button>`).join("")}</div>` : ""}
      <p class="af-st">* aus API-Football, ${AF.md}. Spieltag. Fuß aus unseren Stammdaten.</p></div>`;""")

# Spiele mit Ansage: Daten zum Spiel aufklappbar
ers("""<span>${fett(x)}</span></div>`).join("")}${kbBox(g.kb)}""",
    """<span>${fett(x)}</span></div>`).join("")}${kbBox(g.kb)}${(() => { const v = AF && (AF.vorschau || []).find(v => v.h === g.heim && v.g === g.gast); return v ? `<details class="dzb"><summary>Daten zum Spiel</summary>${datenZumSpiel(v)}</details>` : ""; })()}""")

# ------------------------------------------------------------------ Statistik: neue Bestenlisten
ers("""["p90","Tore pro 90 Minuten","ab 270 Einsatzminuten"],""",
    """["p90","Tore pro 90 Minuten","ab 270 Einsatzminuten"],["note","Beste Note im Schnitt*","ab 4 Einsätzen über 60 Minuten"],["kp90","Schlüsselpässe pro 90*","ab 300 Einsatzminuten"],["par","Paraden pro Spiel*","Torhüterinnen ab 3 Spielen"],""")
ers("""v.voll = sp[s.k] > 0""",
    """{ const af = afSp(s.id) || {}; v.note = af.avg && (af.no || []).filter(x => x[2] >= 60).length >= 4 ? af.avg : 0; v.kp90 = af.kp90 && v.minuten >= 300 ? af.kp90 : 0; v.par = af.parsp >= 3 ? af.par / af.parsp : 0; }
      v.voll = sp[s.k] > 0""")
ers("""const stFmt = (k, x) => k === "minuten" ? x + "'" : k === "p90" ? x.toFixed(2).replace(".", ",") : String(x);""",
    """const stFmt = (k, x) => k === "minuten" ? x + "'" : k === "p90" || k === "note" ? x.toFixed(2).replace(".", ",") : k === "kp90" || k === "par" ? x.toFixed(1).replace(".", ",") : String(x);""")
ers("""Namen antippen öffnet das Profil.</p></div>`;""",
    """Namen antippen öffnet das Profil.</p>${AF && AF.sp ? `<p class="st-notiz">Mit * markiert: Werte von API-Football. ${NOTE_ERKL}</p>` : ""}</div>`;""")

# Klick für Noten-Check-Tabs
ers("""  function inside(){""", """  document.addEventListener("click", e => { const b = e.target.closest("[data-nc]"); if (!b) return; NCDIR = b.dataset.nc; const y = window.scrollY; inside(); window.scrollTo(0, y); });
  function inside(){""")

# ================================================================== Runde 2 (Finn 03.11.2026, 22:40)
# Sterne nur noch einmal erklären
for a, b in [("Ø Note*", "Ø Note"), ("Ø letzte 3*", "Ø letzte 3"), ("Beste Note*</span>", "Beste Note</span>"), ("Zahl darunter: Note*", "Zahl darunter: Note"),
             ("Beste Note* je Team", "Beste Note je Team"), ("Noten-Check*", "Noten-Check"), ("Ecken pro Spiel*", "Ecken pro Spiel"), ("Elfmeter in der Liga*", "Elfmeter in der Liga"),
             ('"Beste Note im Schnitt*"', '"Beste Note im Schnitt"'), ('"Schlüsselpässe pro 90*"', '"Schlüsselpässe pro 90"'), ('"Paraden pro Spiel*"', '"Paraden pro Spiel"'),
             ("Mit * markiert: Werte von API-Football. ", "Beste Note, Schlüsselpässe und Paraden: API-Football. "),
             ("<p class=\"af-st\">* aus API-Football, ${AF.md}. Spieltag. Fuß aus unseren Stammdaten.</p>", "<p class=\"af-st\">Quelle: API-Football, Stand nach dem ${AF.md}. Spieltag. Fuß aus unseren Stammdaten.</p>")]:
    if a not in h: raise SystemExit("Stern-Stelle fehlt: " + a)
    h = h.replace(a, b)
ers('const NOTE_ERKL = "* Note von 0 bis 10,', 'const NOTE_ERKL = "Note: 0 bis 10,')

CSS2 = r"""
.pf-sae .tz i.k{width:7px;height:10px;padding:0;border-radius:1.5px;transform:rotate(-8deg)}
.pf-sae .tz i.k.g{background:#F5C518}.pf-sae .tz i.k.r{background:#E24A4A}
.pf-leg .lk{width:8px;height:11px;border-radius:1.5px;background:#F5C518}
.pf-leg .lk.r{background:#E24A4A}
.fk-svg{width:100%;height:84px;display:block}
.af-ww .pz{display:grid;gap:3px;margin-top:5px}
.af-ww .pz .bb{display:block;height:5px;border-radius:3px;background:rgba(255,255,255,.07);overflow:hidden}
.af-ww .pz .bb i{display:block;height:100%;border-radius:3px}
.af-ww .pz small{font-size:10.5px;color:var(--muted);line-height:1.3}
.af-ww .su{font-size:11.5px;color:#C9D3E3}
.af-ww > div{align-content:start}
.sb2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.sb2 > div{position:relative;overflow:hidden;background:var(--soft);border-radius:10px;padding:10px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 8px;align-items:center;min-height:62px;box-sizing:border-box}
.sb2 .tx{display:grid;gap:2px;min-width:0}
.sb2 b{font-size:17px;font-weight:700;line-height:1.15}
.sb2 span{font-size:10.5px;color:var(--muted);line-height:1.3}
.sb2 .ic{display:flex;align-items:flex-end;gap:3px;opacity:.95}
.sb2 .fl{font-size:28px;line-height:1}
.spl .mt{display:flex;gap:3px;justify-content:center;margin-top:1px}
.spl .mt i{font:800 9px/13px var(--f-mono);font-style:normal;border-radius:3px;padding:0 3px}
.spl .mt .pn{background:#22C55E;color:#06210f}
.spl .mt .pa{background:rgba(226,74,74,.38);color:#FFD0D0}
.wx .p .t{font-size:12.5px;white-space:normal;overflow:visible;line-height:1.2}
.ncf{background:var(--soft);border-radius:12px;padding:11px 12px;display:grid;grid-template-columns:minmax(0,1fr) 112px;gap:6px 12px;align-items:center;text-align:left;width:100%;box-sizing:border-box}
.ncf .a{display:flex;gap:8px;align-items:center;min-width:0}
.ncf .a > span{display:grid;gap:2px;min-width:0}
.ncf .a b{font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ncf .a small{font-size:11px;color:var(--muted)}
.ncf .sp{display:grid;justify-items:end;gap:2px}
.ncf .sp div{font-size:12px;white-space:nowrap}
.ncf .u{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid rgba(255,255,255,.08);padding-top:8px}
.ncf .u > span{font-size:12px;color:#C9D3E3;line-height:1.4}
.ncf .st{font:700 10px var(--f-mono);padding:2px 6px;border-radius:4px;white-space:nowrap;flex:none}
.nc-tabs.v4{grid-template-columns:repeat(2,1fr)}
.tfm{display:grid;gap:6px}
.tfm-r{display:grid;grid-template-columns:24px minmax(0,1fr) 54px 62px;gap:8px;align-items:center;background:var(--soft);border-radius:10px;padding:8px 10px;box-sizing:border-box}
.tfm-r .n{display:grid;gap:3px;min-width:0}
.tfm-r .n b{font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tfm-r .n small{font-size:11px;color:var(--muted);line-height:1.3}
.tfm-r .c{display:grid;justify-items:center;gap:1px;text-align:center}
.tfm-r .c b{font-size:15px;font-weight:700}
.tfm-r .c span{font-size:10px;color:var(--muted);white-space:nowrap}
.tfm-h{display:grid;grid-template-columns:24px minmax(0,1fr) 54px 62px;gap:8px;padding:0 10px;font:600 9.5px var(--f-mono);color:var(--muted);text-align:center}
"""
i = h.rfind("</style>"); h = h[:i] + CSS2 + h[i:]

# Helfer: Flaggen, Silhouette, Fuß, Liga-Vergleich, Formkurve
ers("  let AFNOTEN = null, AFBEST = null;", r"""  let AFNOTEN = null, AFBEST = null;
  const FLAGGE = {Deutschland:"DE",Österreich:"AT",Schweiz:"CH",Niederlande:"NL",Belgien:"BE",Polen:"PL",Japan:"JP",Frankreich:"FR",Norwegen:"NO",Ungarn:"HU",Dänemark:"DK",Schweden:"SE",Island:"IS",Spanien:"ES",Kanada:"CA",Australien:"AU",Kosovo:"XK",Serbien:"RS",Montenegro:"ME",Slowenien:"SI",Elfenbeinküste:"CI",Slowakei:"SK",Marokko:"MA",Aserbaidschan:"AZ",Tschechien:"CZ",USA:"US",Türkei:"TR",Kroatien:"HR",Israel:"IL",Portugal:"PT",Russland:"RU",Luxemburg:"LU",Italien:"IT",Philippinen:"PH",Finnland:"FI",Irland:"IE",Schottland:"",Wales:"",Brasilien:"BR",Mexiko:"MX",Südkorea:"KR",China:"CN",Nigeria:"NG",Ghana:"GH",Kolumbien:"CO",Argentinien:"AR",Neuseeland:"NZ",Albanien:"AL",Bosnien:"BA",Griechenland:"GR",Rumänien:"RO",Ukraine:"UA",Bulgarien:"BG",Litauen:"LT",Lettland:"LV",Estland:"EE"};
  const flagge = n => n === "England" ? "\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}" : FLAGGE[n] ? [...FLAGGE[n]].map(c => String.fromCodePoint(127397 + c.charCodeAt(0))).join("") : "";
  const PLURAL = {TW: "Torhüterinnen", ABW: "Abwehrspielerinnen", MF: "Mittelfeldspielerinnen", ST: "Stürmerinnen"};
  const SILH = (hpx, farbe) => `<svg width="${Math.round(hpx * .42)}" height="${hpx}" viewBox="0 0 42 100" aria-hidden="true"><circle cx="21" cy="10" r="9" fill="${farbe}"/><path d="M8 24c0-3 3-5 6-5h14c3 0 6 2 6 5l3 34c0 2-2 3-4 3l-3-1-1 37c0 2-2 3-4 3h-3l-1-34-1 34h-3c-2 0-4-1-4-3l-1-37-3 1c-2 0-4-1-4-3z" fill="${farbe}"/></svg>`;
  const FUSS = (an) => `<svg width="15" height="26" viewBox="0 0 15 26" aria-hidden="true"><path d="M7.5 1c3.5 0 6 3 6 8 0 4-1 7-1.6 10-.5 3-2 5.5-4.4 5.5S3.6 22 3 19C2.4 16 1.5 13 1.5 9c0-5 2.5-8 6-8z" fill="${an ? "#8FB0FF" : "rgba(255,255,255,.12)"}"/></svg>`;
  function ligaRang(s, f, filt){
    const peers = ((SPN && SPN.spielerinnen) || []).filter(x => x.pos === s.pos && (x.spiele || []).reduce((a, e) => a + (e.min || 0), 0) >= 270 && (!filt || filt(x)));
    const w = f(s); if (w == null || peers.length < 8) return null;
    const vals = peers.map(f).filter(v => v != null); if (vals.length < 8) return null;
    const p = Math.round(vals.filter(v => v < w).length / (vals.length - 1) * 100);
    return {p: Math.max(0, Math.min(100, p)), n: vals.length};
  }
  function formkurve(s){
    const af = afSp(s.id); if (!af || !af.no) return "";
    const sp = s.spiele || [], N = Math.max(...sp.map(e => e.md), 1), voll = af.no.filter(x => x[2] >= 60);
    if (voll.length < 2) return "";
    const W = 300, H = 84, X = md => 14 + (md - 1) / Math.max(1, N - 1) * (W - 28), Y = n => 10 + (10 - n) / 6 * (H - 28);
    const pts = voll.map(x => [X(x[0]), Y(Math.max(4, Math.min(10, x[1]))), x]);
    const avgY = Y(af.avg);
    return `<div class="kap" style="margin-top:6px">Formkurve</div><svg class="fk-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="Formkurve der Noten">
      <line x1="8" x2="${W - 8}" y1="${avgY}" y2="${avgY}" stroke="rgba(255,255,255,.22)" stroke-dasharray="3 4" vector-effect="non-scaling-stroke"/>
      <polyline points="${pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" fill="none" stroke="#8FB0FF" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>
      ${pts.map(p => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3.4" fill="${NFARBE(p[2][1])}" stroke="#16223A" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`).join("")}
      ${sp.map(e => `<text x="${X(e.md).toFixed(1)}" y="${H - 3}" fill="rgba(169,180,198,.8)" font-size="9" font-family="ui-monospace,monospace" text-anchor="middle">${e.md}.</text>`).join("")}
    </svg><div class="af-st" style="display:flex;justify-content:space-between"><span>Linie: Note je Spieltag ab 60 Minuten</span><span>gestrichelt: Ø ${dez(af.avg)}</span></div>`;
  }""")

# Profil: Legende nur mit vorhandenen Einträgen, Karten in den Säulen, Formkurve
ers("""<span class="tz">${(e.tore || []).length ? `<i class="t">${e.tore.length}T</i>` : ""}${e.vorl ? `<i class="v">${e.vorl}V</i>` : ""}</span>""",
    """<span class="tz">${(e.tore || []).length ? `<i class="t">${e.tore.length}T</i>` : ""}${e.vorl ? `<i class="v">${e.vorl}V</i>` : ""}${e.rot || e.gr ? '<i class="k r"></i>' : e.gelb ? '<i class="k g"></i>' : ""}</span>""")
ers("""<div class="pf-leg"><span><i class="S"></i>Startelf</span><span><i class="E"></i>Joker</span><span><i class="B"></i>Bank</span><span><i class="X"></i>fehlte</span><span><i class="po"></i>Pokal</span><span><i class="cl"></i>UWCL</span></div>
      <div class="pf-leg"><span><i class="lt">T</i>Tor</span><span><i class="lv">V</i>Vorlage</span>${AF && AF.sp ? "<span>Zahl darunter: Note</span>" : ""}</div>""",
    """${(() => { const has = a => alle.some(e => e.typ === "Liga" && e.art === a), L1 = [["S", "Startelf"], ["E", "Joker"], ["B", "Bank"], ["X", "fehlte"]].filter(x => has(x[0])).map(x => `<span><i class="${x[0]}"></i>${x[1]}</span>`);
        if (alle.some(e => e.typ === "Pokal")) L1.push('<span><i class="po"></i>Pokal</span>'); if (alle.some(e => e.typ === "CL")) L1.push('<span><i class="cl"></i>UWCL</span>');
        const L2 = []; if (alle.some(e => (e.tore || []).length)) L2.push('<span><i class="lt">T</i>Tor</span>'); if (alle.some(e => e.vorl)) L2.push('<span><i class="lv">V</i>Vorlage</span>');
        if (alle.some(e => e.gelb && !e.rot && !e.gr)) L2.push('<span><i class="lk"></i>Gelb</span>'); if (alle.some(e => e.rot || e.gr)) L2.push('<span><i class="lk r"></i>Rot</span>');
        if (AF && AF.sp && afSp(s.id)) L2.push("<span>Zahl darunter: Note</span>");
        return `<div class="pf-leg">${L1.join("")}</div>${L2.length ? `<div class="pf-leg">${L2.join("")}</div>` : ""}`; })()}
      ${formkurve(s)}""")

# Weitere Werte mit Liga-Vergleich
ers("""    { const af = afSp(s.id) || {}, st = s.stat || {}, ww = [];
      if (st.sch) ww.push([st.sch, "Torschüsse"]);
      if (af.kp90 != null) ww.push([dez(af.kp90, 1), "Schlüsselpässe pro 90"]);
      if (st.zk_ges) ww.push([Math.round(st.zk_w / st.zk_ges * 100) + " %", `Zweikämpfe gewonnen (${st.zk_w} von ${st.zk_ges})`]);
      if (af.drib) ww.push([af.drib[0] + "/" + af.drib[1], "Dribblings erfolgreich*"]);
      if (af.parsp) ww.push([dez(af.par / af.parsp, 1), `Paraden pro Spiel* (${af.parsp} Spiele)`]);""",
    """    { const af = afSp(s.id) || {}, st = s.stat || {}, ww = [], minS = sp.reduce((a, e) => a + (e.min || 0), 0), nSp = st.spiele || sp.filter(e => e.art === "S" || e.art === "E").length || 1;
      const M = x => (x.spiele || []).reduce((a, e) => a + (e.min || 0), 0), Sx = x => x.stat || {};
      if (st.sch && s.pos !== "TW") ww.push([st.sch, "Torschüsse", `${dez(st.sch / nSp)} pro Spiel`, ligaRang(s, x => Sx(x).sch != null && M(x) ? Sx(x).sch / M(x) * 90 : null)]);
      if (af.kp != null && s.pos !== "TW") ww.push([af.kp, "Schlüsselpässe", `${dez(af.kp90)} pro 90 Minuten`, ligaRang(s, x => (afSp(x.id) || {}).kp90 ?? null)]);
      if (st.zk_ges) ww.push([`${st.zk_w}/${st.zk_ges}`, "Zweikämpfe gewonnen", `${Math.round(st.zk_w / st.zk_ges * 100)} % · ${dez(st.zk_ges / nSp)} pro Spiel`, ligaRang(s, x => Sx(x).zk_ges >= 20 ? Sx(x).zk_w / Sx(x).zk_ges : null)]);
      if (st.p_ges) ww.push([`${st.p_ok}/${st.p_ges}`, "Pässe angekommen", `${Math.round(st.p_ok / st.p_ges * 100)} % · ${dez(st.p_ges / nSp, 0)} pro Spiel`, ligaRang(s, x => Sx(x).p_ges >= 50 ? Sx(x).p_ok / Sx(x).p_ges : null)]);
      if (st.bk) ww.push([dez(st.bk / nSp, 0), "Ballkontakte pro Spiel", `${st.bk} gesamt`, ligaRang(s, x => Sx(x).bk && M(x) ? Sx(x).bk / M(x) * 90 : null)]);
      if (af.drib) ww.push([`${af.drib[0]}/${af.drib[1]}`, "Dribblings erfolgreich", `${Math.round(af.drib[0] / af.drib[1] * 100)} %`, null]);
      if (af.parsp) ww.push([dez(af.par / af.parsp, 1), "Paraden pro Spiel", `${af.par} in ${af.parsp} Spielen`, ligaRang(s, x => (afSp(x.id) || {}).parsp >= 3 ? afSp(x.id).par / afSp(x.id).parsp : null)]);""")
ers("""      const gelb = sp.filter(e => e.gelb).length; if (gelb || st.fouls) ww.push([gelb + (gelb >= 4 ? " ⚠" : ""), gelb >= 4 ? "Gelbe, bei der 5. ein Spiel Sperre" : `Gelbe Karten${st.fouls ? ", " + st.fouls + (st.fouls === 1 ? " Foul" : " Fouls") : ""}`]);
      if (ww.length) h += `<section class="pf-box">${kap("Weitere Werte")}<div class="af-ww">${ww.map(w => `<div><b>${w[0]}</b><span>${esc(w[1])}</span></div>`).join("")}</div>${ww.some(w => /\\*/.test(w[1])) ? '<p class="af-st">* aus API-Football, übrige Werte aus der Spielstatistik der Sportschau.</p>' : ""}</section>`;""",
    """      const gelb = sp.filter(e => e.gelb && !e.gr).length; if (gelb || st.fouls) ww.push([gelb + (gelb >= 4 ? " ⚠" : ""), "Gelbe Karten", gelb >= 4 ? "bei der 5. ein Spiel Sperre" : st.fouls ? st.fouls + (st.fouls === 1 ? " Foul" : " Fouls") + `, ${st.gef || 0}x gefoult worden` : "", null]);
      const pfarbe = p => p >= 75 ? "#4ADE80" : p >= 40 ? "#8FB0FF" : "#F5C26B";
      if (ww.length) h += `<section class="pf-box">${kap("Weitere Werte")}<div class="af-ww">${ww.map(w => `<div><b>${w[0]}</b><span>${esc(w[1])}</span>${w[2] ? `<span class="su">${esc(w[2])}</span>` : ""}${w[3] ? `<div class="pz"><span class="bb"><i style="width:${Math.max(4, w[3].p)}%;background:${pfarbe(w[3].p)}"></i></span><small>${w[3].p >= 100 ? "Bestwert aller " + (PLURAL[s.pos] || "Spielerinnen") : "besser als " + w[3].p + " % der " + (PLURAL[s.pos] || "Spielerinnen")}</small></div>` : ""}</div>`).join("")}</div><p class="af-st">Balken: Vergleich mit allen ${PLURAL[s.pos] || "Spielerinnen"} der Liga ab 270 Minuten. Schlüsselpässe, Dribblings und Paraden: API-Football, übrige Werte: Spielstatistik der Sportschau.</p></section>`;""")

# Steckbrief mit Fuß-Symbol, Silhouette, Flagge
ers("""      const sb = [[af.fuss ? af.fuss[0].toUpperCase() + af.fuss.slice(1) : "–", "Starker Fuß"], [af.alter ? af.alter + " J." : "–", "Alter"], [af.gr ? dez(af.gr / 100, 2) + " m" : "–", "Größe"], [esc(s.nation || "–"), "Nation"]];
      if (af.fuss || af.alter || af.gr) h += `<section class="pf-box">${kap("Steckbrief")}<div class="af-sb">${sb.map(w => `<div><b>${w[0]}</b><span>${w[1]}</span></div>`).join("")}</div></section>`; }""",
    """      const alleAF = Object.values((AF && AF.sp) || {}), grL = alleAF.map(x => x.gr).filter(Boolean), alL = alleAF.map(x => x.alter).filter(Boolean);
      const grP = ((SPN && SPN.spielerinnen) || []).filter(x => x.pos === s.pos).map(x => (afSp(x.id) || {}).gr).filter(Boolean);
      const mw = l => l.length ? l.reduce((a, b) => a + b, 0) / l.length : null, grLm = mw(grL), grPm = mw(grP);
      const grPct = af.gr && grL.length ? Math.round(grL.filter(g => g < af.gr).length / grL.length * 100) : null;
      const fu = af.fuss, fl = flagge(s.nation);
      const t1 = `<div><span class="tx"><b>${fu ? fu[0].toUpperCase() + fu.slice(1) : "–"}</b><span>Starker Fuß</span></span><span class="ic">${FUSS(fu === "links" || fu === "beidfüßig")}${FUSS(fu === "rechts" || fu === "beidfüßig")}</span></div>`;
      const t2 = `<div><span class="tx"><b>${af.alter ? af.alter + " Jahre" : "–"}</b><span>${alL.length ? "Liga-Ø " + Math.round(mw(alL)) + " Jahre" : "Alter"}</span></span></div>`;
      const t3 = `<div><span class="tx"><b>${af.gr ? dez(af.gr / 100, 2) + " m" : "–"}</b><span>${grPct != null ? `größer als ${grPct} % der Liga` : "Größe"}${grPm ? `<br>Ø ${esc(PLURAL[s.pos] || "Position")} ${dez(grPm / 100, 2)} m` : ""}</span></span>${af.gr && grLm ? `<span class="ic">${SILH(Math.round(af.gr / 190 * 50), "#8FB0FF")}${SILH(Math.round(grLm / 190 * 50), "rgba(255,255,255,.16)")}</span>` : ""}</div>`;
      const t4 = `<div><span class="tx"><b>${esc(s.nation || "–")}</b><span>Nation</span></span>${fl ? `<span class="ic fl">${fl}</span>` : ""}</div>`;
      if (af.fuss || af.alter || af.gr) h += `<section class="pf-box">${kap("Steckbrief")}<div class="sb2">${t1}${t2}${t3}${t4}</div>${af.gr && grLm ? '<p class="af-st">Silhouetten: blau sie, grau der Liga-Schnitt. Größe und Alter: API-Football, Fuß: unsere Stammdaten.</p>' : ""}</section>`; }""")

# Spielfeld: Namen nie abkürzen, NEU und Auswechslung gemeinsam unter dem Namen
ers("""        const neu = o.modus === "o" && (s.f === "neu" || (o.neu && o.neu.has(s.n))) ? '<span class="nb">NEU</span>' : "";""",
    """        const istNeu = o.modus === "o" && (s.f === "neu" || (o.neu && o.neu.has(s.n))), neu = "";
        const mwN = Math.min(84, 334 / (r.length + 1) - 4), fsN = [12, 11, 10.5, 9.5, 9].find(f => String(s.n).length * f * .56 <= mwN) || 9;""")
ers("""        const unten = o.modus === "o" && s.aus ? `<small>↓${esc(s.aus)}'</small>` : "";""",
    """        const unten = "", mt = istNeu || (o.modus === "o" && s.aus) ? `<span class="mt">${istNeu ? '<i class="pn">NEU</i>' : ""}${o.modus === "o" && s.aus ? `<i class="pa">↓${esc(s.aus)}'</i>` : ""}</span>` : "";""")
ers("""<span class="nm">${esc(s.n)}${unten}</span></${tag}>`;""",
    """<span class="nm" style="font-size:${fsN}px;max-width:none;overflow:visible">${esc(s.n)}${unten}</span>${mt}</${tag}>`;""")

# Daten zum Spiel: Stand
ers("""<p class="af-st">Heimwerte von ${esc(kname(v.h))} (${H.sp} Spiele),""", """<p class="af-st">Stand nach dem ${AF.md}. Spieltag (${esc(kurz(dt(AF.stand)))}). Heimwerte von ${esc(kname(v.h))} (${H.sp} Spiele),""")

# Inside: Noten-Check im Kurven-Design, vier Gruppen, Einordnung, Team-Form
i1 = h.index('  let NCDIR = "tief";'); i2 = h.index('  function formIndexAnzeigen')
h = h[:i1] + r"""  let NCDIR = "tief";
  const NCG = [["tief", "Formtief", "#F59E0B"], ["hoch", "Formhoch", "#4ADE80"], ["trifft", "Schwache Noten, trifft trotzdem", "#8FB0FF"], ["leer", "Starke Noten, ohne Ertrag", "#C9AEF7"]];
  const PST2 = {sicher: ["SICHER", "#1A2A55", "#8FB0FF"], erwartet: ["ERWARTET", "#12351F", "#4ADE80"], unsicher: ["UNSICHER", "#3A2A10", "#F5B041"], unwahrscheinlich: ["UNWAHRSCH.", "#3A1616", "#FF8A8A"], ausgeschlossen: ["FÄLLT AUS", "#2A2F3A", "#A9B4C6"]};
  function spark(noten, farbe){
    const W = 110, H = 30, n = noten.length; if (n < 2) return "";
    const pts = noten.map((v, i) => [i / (n - 1) * W, 3 + (10 - Math.max(4, Math.min(10, v))) / 6 * (H - 6)]);
    return `<svg width="110" height="30" viewBox="-3 -3 116 36" aria-hidden="true"><polyline points="${pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" fill="none" stroke="${farbe}" stroke-width="2"/><circle cx="${pts[n - 1][0]}" cy="${pts[n - 1][1].toFixed(1)}" r="3" fill="${farbe}"/></svg>`;
  }
  function einordnungSatz(f){
    const t = [];
    if (f.gr) t.push(`Gegner zuletzt Ø Platz ${Math.round(f.gr)}${f.gs === "stark" ? ", schwere Aufgaben" : f.gs === "schwach" ? ", eher leichte Gegner" : ""}`);
    if (f.last >= 4) t.push(`${f.last} Spiele in 14 Tagen inkl. Pokal/Europa`);
    if (f.tv) t.push(`${f.tv} ${f.tv === 1 ? "Scorerpunkt" : "Scorerpunkte"} in den letzten 3`);
    return t.join(" · ");
  }
  function teamForm(){
    const L = ((AF && AF.team) || []).filter(t => zeigen(t.k)); if (!L.length) return "";
    const fo = s => `<span class="dz-form" style="justify-content:flex-start">${String(s).split("").map(c => `<i class="${c}">${c}</i>`).join("")}</span>`;
    return `<div style="display:grid;gap:8px;padding-top:14px"><h3 class="disp" style="font-size:21px">Team-Form</h3>
      <p class="af-st" style="font-size:12px">Letzte 3 Ligaspiele gegen die Spiele davor: Ø Note der Spielerinnen ab 60 Minuten, Punkte und wie stark die Gegner waren.</p>
      <div class="tfm-h"><span></span><span style="text-align:left">TEAM</span><span>NOTE</span><span>PUNKTE</span></div>
      <div class="tfm">${L.map(t => `<button class="tfm-r kd-btn" data-kader="${esc(t.k)}" style="text-align:left">${logo(t.k, 22)}<span class="n"><b>${esc(kname(t.k))}</b>${fo(t.form)}<small>Tore ${dez(t.t3)} : ${dez(t.g3)} pro Spiel${t.xg3 != null ? ` · xG ${dez(t.xg3)} : ${dez(t.xgg3)}` : ""} · Gegner Ø Platz ${Math.round(t.gr3)}</small></span>
        <span class="c"><b style="color:${t.trend >= .2 ? "#4ADE80" : t.trend <= -.2 ? "#FF8A8A" : "var(--ink)"}">${t.trend > 0 ? "+" : ""}${dez(t.trend)}</b><span>${dez(t.n3)} statt ${dez(t.nv)}</span></span>
        <span class="c"><b>${dez(t.p3)}</b><span>statt ${dez(t.pv)}</span></span></button>`).join("")}</div>
      <p class="af-st">Punkte pro Spiel. Leichte Gegner (hoher Tabellenplatz) machen eine gute Form weniger aussagekräftig.</p></div>`;
  }
  function notenCheck(){
    if (!AF || !AF.form) return "";
    const g = NCG.find(x => x[0] === NCDIR) || NCG[0], l = (AF.form[NCDIR] || []).filter(f => zeigen(f.k)), x = (AF.xg || []).filter(f => zeigen(f.k)).slice(0, 4);
    const POSN = {TW: "Torhüterin", ABW: "Abwehr", MF: "Mittelfeld", ST: "Sturm"};
    return `<div style="display:grid;gap:8px;padding-top:14px"><h3 class="disp" style="font-size:21px">Noten-Check</h3>
      <p class="af-st" style="font-size:12px">Schnitt der letzten 3 Noten gegen die Spiele davor, nur Einsätze ab 60 Minuten, nur Stammspielerinnen. Unten: Minuten und Einordnung.</p>
      <div class="nc-tabs v4">${NCG.map(t => `<button data-nc="${t[0]}" aria-pressed="${NCDIR === t[0]}">${t[1]} (${(AF.form[t[0]] || []).filter(f => zeigen(f.k)).length})</button>`).join("")}</div>
      <div class="nc">${l.length ? l.map(f => { const sp = spById(f.id) || {}, ps = PST2[f.prog], e = einordnungSatz(f);
        return `<button class="ncf" data-profil="${esc(f.id)}"><span class="a">${logo(f.k, 24)}<span><b>${esc(f.n)}</b><small>${esc(kname(f.k))} · ${esc(POSN[f.pos || sp.pos] || "")}</small></span></span>
          <span class="sp">${spark(f.noten, g[2])}<div><span class="mu">${dez(f.vorher)}</span> → <b style="color:${g[2]}">${dez(f.l3)}</b></div></span>
          <span class="u"><span>Minuten letzte 3: ${f.min3.map(m => m + "'").join(" · ")}${e ? "<br>" + esc(e) : ""}</span>${ps ? `<span class="st" style="background:${ps[1]};color:${ps[2]}">${ps[0]}</span>` : ""}</span></button>`; }).join("") : '<p class="dat">Keine Spielerin deiner Vereine in dieser Gruppe.</p>'}</div>
      ${x.length ? `<h3 class="disp" style="font-size:19px;margin-top:8px">xG-Check ${(AF.xgmd || []).join(". und ")}. Spieltag</h3><div class="nc">${x.map(r => `<div class="nc-r">${logo(r.k, 26)}<span class="nm"><b>${esc(kname(r.k))} gegen ${esc(kname(r.gg))}</b><small>${r.md}. Spieltag: ${r.t} ${r.t === 1 ? "Tor" : "Tore"} bei ${dez(r.xg, 2)} xG. ${r.d > 0 ? "Mehr getroffen als erspielt, das gleicht sich meist aus." : "Chancen ungenutzt, die Offensive war besser als das Ergebnis."}</small></span><span class="w"><b style="color:${r.d > 0 ? "#4ADE80" : "#FF8A8A"}">${r.d > 0 ? "+" : ""}${dez(r.d)}</b><span>Tore minus xG</span></span></div>`).join("")}</div>` : ""}
      ${teamForm()}
      <p class="af-st">${NOTE_ERKL}</p></div>`;
  }
""" + h[i2:]

# News-Kandidaten aus API-Football in den Feed (nur Testkopie)
ers("  ladeAF().then(afNeu);", r"""  Object.assign(TAGF, {FORMTIEF: ["#F59E0B", "#1A1206"], FORMHOCH: ["#22C55E", "#06210f"], ELFMETER: ["#6E9BFF", "#0B1220"], JOKER: ["#4ADE80", "#06210f"], GELBSPERRE: ["#F5C518", "#1A1606"], "xG-CHECK": ["#9B6BE8", "#fff"], INSIDER: ["#2A3B5E", "#C7D7FF"]});
  ladeAF().then(afNeu).then(() => { const mische = () => { if (!N.length) return setTimeout(mische, 400);
    const neu = (AF.news || []).filter(n => !N.some(m => m.id === n.id) && dt(n.zeit) <= new Date()); if (!neu.length) return;
    N = N.concat(neu).sort((a, b) => String(b.zeit).localeCompare(String(a.zeit)));
    if (VIEW === "meldungen" && document.querySelector("#main .liste")) { const y = window.scrollY; list(); window.scrollTo(0, y); } }; mische(); });""")

# Runde 3 (Finn 22:53): Programm der nächsten Gegner, Lauf-Gruppe, Vorschau und Aufstellung sichtbar machen
ers('  const NCG = [["tief", "Formtief", "#F59E0B"], ["hoch", "Formhoch", "#4ADE80"],', '  const NCG = [["tief", "Formtief", "#F59E0B"], ["hoch", "Formhoch", "#4ADE80"], ["lauf", "Gute Form, leichte Gegner", "#4ADE80"],')
ers("""    if (f.tv) t.push(`${f.tv} ${f.tv === 1 ? "Scorerpunkt" : "Scorerpunkte"} in den letzten 3`);
    return t.join(" · ");""", """    if (f.tv) t.push(`${f.tv} ${f.tv === 1 ? "Scorerpunkt" : "Scorerpunkte"} in den letzten 3`);
    return t.join(" · ");
  }
  function programmZeile(f){
    if (!f.next || !f.next.length) return "";
    const c = f.ns === "schwer" ? "#FF8A8A" : f.ns === "leicht" ? "#4ADE80" : "#A9B4C6";
    return `<span style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px"><span class="mu" style="font-size:11px">Nächste:</span>${f.next.map(([g, h, r]) => `<span style="display:inline-flex;gap:3px;align-items:center;font-size:11px">${logo(g, 14)}${r}.${h === "A" ? " <small class=mu>A</small>" : ""}</span>`).join("")}<span style="font:700 10px var(--f-mono);color:${c}">${f.ns === "schwer" ? "SCHWERES PROGRAMM" : f.ns === "leicht" ? "LEICHTES PROGRAMM" : "GEMISCHT"}</span></span>`;""")
ers("""<span class="u"><span>Minuten letzte 3: ${f.min3.map(m => m + "'").join(" · ")}${e ? "<br>" + esc(e) : ""}</span>""",
    """<span class="u"><span>Minuten letzte 3: ${f.min3.map(m => m + "'").join(" · ")}${e ? "<br>" + esc(e) : ""}${programmZeile(f)}</span>""")
ers('INSIDER: ["#2A3B5E", "#C7D7FF"]});', 'INSIDER: ["#2A3B5E", "#C7D7FF"], AUFWIND: ["#22C55E", "#06210f"]});')
ers("""  ladeAF().then(afNeu).then(() => { const mische = () => { if (!N.length) return setTimeout(mische, 400);""",
    """  ladeAF().then(afNeu).then(() => { ladeSPN().catch(() => {}); const mische = () => { if (!N.length) return setTimeout(mische, 400);""")
ers("""      ${bs.length ? (klein ? `<div class="belh klein">""", """      ${p.status !== "beendet" ? (() => { const v = AF && (AF.vorschau || []).some(x => x.id === p.id), a = [p.heim_aufstellung, p.gast_aufstellung].filter(Boolean), off = a.some(x => x.typ === "offiziell");
        return v || a.length ? `<div class="af-hin">${v ? '<span class="v">VORSCHAU</span>' : ""}${a.length ? `<span class="${off ? "o" : "a"}">${off ? "OFFIZIELLE AUFSTELLUNG" : "MÖGLICHE AUFSTELLUNG"}</span>` : ""}</div>` : ""; })() : ""}
      ${bs.length ? (klein ? `<div class="belh klein">""")
ers("""    const afBox = AS ? afStatBox(p, AS) : p.status !== "beendet" && AF && (AF.vorschau || []).find(v => v.id === p.id) ? `<div class="kartebox">${kap("Daten zum Spiel")}""",
    """    const hatV = p.status !== "beendet" && AF && (AF.vorschau || []).some(v => v.id === p.id), hatA = p.status !== "beendet" && [p.heim_aufstellung, p.gast_aufstellung].some(Boolean), offA = [p.heim_aufstellung, p.gast_aufstellung].some(a => a && a.typ === "offiziell");
    const sprung = hatV || hatA ? `<div class="af-sprung"><span class="mu">In diesem Spiel:</span>${hatV ? '<button data-afsprung="af-dz">Vorschau ↓</button>' : ""}${hatA ? `<button data-afsprung="af-auf">${offA ? "Aufstellung" : "Aufstellungen"} ↓</button>` : ""}</div>` : "";
    const afBox = AS ? afStatBox(p, AS) : hatV ? `<div class="kartebox" id="af-dz">${kap("Vorschau: Daten zum Spiel")}""")
ers("""${afBox}${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""", """${sprung}${afBox}${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""")
ers("""        : teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim",""", """        : `<span id="af-auf"></span>` + teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim",""")
ers("""  document.addEventListener("click", e => { const b = e.target.closest("[data-nc]");""", """  document.addEventListener("click", e => { const b = e.target.closest("[data-afsprung]"); if (!b) return; const z = document.getElementById(b.dataset.afsprung); if (z) window.scrollTo({top: z.getBoundingClientRect().top + window.scrollY - 70, behavior: "smooth"}); });
  document.addEventListener("click", e => { const b = e.target.closest("[data-nc]");""")
CSS3 = """
.af-hin{display:flex;gap:5px;justify-content:center;margin-top:6px}
.af-hin span{font:700 9.5px var(--f-mono);letter-spacing:.03em;padding:2px 6px;border-radius:4px}
.af-hin .v{background:rgba(155,107,232,.22);color:#C9AEF7}
.af-hin .a{background:rgba(245,158,11,.18);color:#F7C27A}
.af-hin .o{background:rgba(34,197,94,.18);color:#86EFAC}
.af-sprung{display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:center;font-size:12px}
.af-sprung button{background:var(--soft);border-radius:999px;padding:6px 11px;font-weight:600;font-size:12.5px;color:var(--ink)}
"""
i = h.rfind("</style>"); h = h[:i] + CSS3 + h[i:]

# Runde 4 (Finn 23:20): ein Begriff im Spielplan, Aufstellung zuerst, Daten zum Spiel danach
def r4(h):
    def e(a, b):
        nonlocal h
        if h.count(a) != 1: raise SystemExit(f"R4: {h.count(a)}x: {a[:80]!r}")
        h = h.replace(a, b)
    e("""return v || a.length ? `<div class="af-hin">${v ? '<span class="v">VORSCHAU</span>' : ""}${a.length ? `<span class="${off ? "o" : "a"}">${off ? "OFFIZIELLE AUFSTELLUNG" : "MÖGLICHE AUFSTELLUNG"}</span>` : ""}</div>` : "";""",
      """return v || a.length ? `<div class="af-hin"><span class="${off ? "o" : "v"}">${off ? "OFFIZIELLE AUFSTELLUNG" : "VORSCHAU"}</span></div>` : "";""")
    e("""    const sprung = hatV || hatA ? `<div class="af-sprung"><span class="mu">In diesem Spiel:</span>${hatV ? '<button data-afsprung="af-dz">Vorschau ↓</button>' : ""}${hatA ? `<button data-afsprung="af-auf">${offA ? "Aufstellung" : "Aufstellungen"} ↓</button>` : ""}</div>` : "";""",
      """    const sprung = hatV && hatA ? '<div class="af-sprung"><button data-afsprung="af-dz">Daten zum Spiel ↓</button></div>' : "";""")
    e("""kap("Vorschau: Daten zum Spiel")""", """kap("Daten zum Spiel")""")
    e("""${sprung}${afBox}${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""", """${sprung}${AS ? afBox : ""}${pv.length ? `<div class="kartebox">${kap("Platzverweise")}""")
    i = h.index('So entsteht sie</span></span></button>` : ""}')
    j = h.index("\n    </div>`;", i)
    h = h[:j] + "\n      ${!AS ? afBox : \"\"}" + h[j:]
    return h

h = r4(h)

if LIVE:
    h = h.replace('<div class="af-test">TESTVERSION · neue Daten aus API-Football · nicht öffentlich</div>', "")
    h = h.replace('  window.AFT = {spiel: id => { VIEW = "spielplan"; Promise.all([loadSP(), ladeSPN(), ladeAF()]).then(() => spiel(id)); }, show};\n', "")
    assert "af-test\">TEST" not in h and "window.AFT" not in h
open(ZIEL, "w", encoding="utf-8").write(h)
print("ok", ZIEL, len(h))
