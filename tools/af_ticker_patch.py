#!/usr/bin/env python3
"""Baut die Testkopie des Tickers mit den API-Football-Daten (Finn 03.11.2026).

python3 tools/af_ticker_patch.py <ticker/index.html> <ziel/index.html> [datenpfad]
Datenpfad Standard: test/apifootball.json (relativ zur base https://finnclausenhh.github.io/fbl-daten/)
"""
import sys

QUELLE, ZIEL = sys.argv[1], sys.argv[2]
DATEN = sys.argv[3] if len(sys.argv) > 3 else "test/apifootball.json"
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
ers("""        ${(g.fakten || []).map(x => `<div class="fakt"><i></i><span>${fett(x)}</span></div>`).join("")}${kbBox(g.kb)}</div>`).join("")}</section>`;""",
    """        ${(g.fakten || []).map(x => `<div class="fakt"><i></i><span>${fett(x)}</span></div>`).join("")}${kbBox(g.kb)}${(() => { const v = AF && (AF.vorschau || []).find(v => v.h === g.heim && v.g === g.gast); return v ? `<details class="dzb"><summary>Daten zum Spiel</summary>${datenZumSpiel(v)}</details>` : ""; })()}</div>`).join("")}</section>`;""")

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

open(ZIEL, "w", encoding="utf-8").write(h)
print("ok", ZIEL, len(h))
