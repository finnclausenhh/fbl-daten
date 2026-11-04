"""Runde 7 (Finn 04.11.2026, 12:16): weniger Logos vor dem Spiel, Begründung als kleine Analyse mit Profil-Link,
Form-Karten mit Nummer und Position, Zahl und Text nebeneinander, Reihenfolge nach Notenentwicklung,
Standards aus dem Liveticker, Test: Umfragen im Feed, Inside-Inhalte in den News.
python3 tools/af_r7.py <datei.html>"""
import sys

CSS7 = """
.af-tw button{font-size:14px}
.af-swb .tb-k > .kd-btn{display:none}
.af-swb .tb-k{justify-content:flex-end}
.begr{gap:6px}
.begr .ba{display:grid;gap:5px}
.begr .ba .k1{display:flex;justify-content:space-between;align-items:center;gap:8px}
.begr .ba .k1 b{font-size:14.5px}
.begr .ba .z{font-size:12.5px;line-height:1.45;color:#C9D3E3}
.begr .ba .z b{color:var(--ink);font-weight:600}
.begr .ba .pl{justify-self:start;background:var(--soft);border-radius:999px;padding:6px 12px;font-weight:600;font-size:12.5px;color:#C7D7FF;margin-top:2px}
.bigr{display:flex;align-items:center;gap:10px;margin-top:auto}
.bigr .big{margin:0;font-size:36px}
.bigr .bt{line-height:1.25}
.fkomp .vn{flex-wrap:wrap;row-gap:2px}
.eck-r .bw small b{color:#C9D3E3;font-weight:600}
.af-innews{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--soft);border-radius:12px;padding:10px 12px;font-size:13px;width:100%;text-align:left}
"""

def r7(h):
    def e(a, b, n=1):
        nonlocal h
        if h.count(a) != n: raise SystemExit(f"R7: {h.count(a)}x statt {n}x: {a[:90]!r}")
        h = h.replace(a, b)
    i = h.rfind("</style>"); h = h[:i] + CSS7 + h[i:]

    # ---------- Spiel vor Anpfiff: Logo nur noch im Kopf, Umschalter mit Namen, Team-Kopf im Block ausgeblendet
    e("""`<button role="tab" data-afseite="${s}" aria-pressed="${sel === s}">${logo(k, 22)}<span>${esc(KNAME[k] || n)}</span></button>`""",
      """`<button role="tab" data-afseite="${s}" aria-pressed="${sel === s}"><span>${esc(KNAME[k] || n)}</span></button>`""")
    e("""      + (sel === "heim" ? teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim", false, p.anstoss) : teamBlock(p.gast, p.gast_k, p.gast_aufstellung, "gast", false, p.anstoss));""",
      """      + `<div class="af-swb">${sel === "heim" ? teamBlock(p.heim, p.heim_k, p.heim_aufstellung, "heim", false, p.anstoss) : teamBlock(p.gast, p.gast_k, p.gast_aufstellung, "gast", false, p.anstoss)}</div>`;""")

    # ---------- Begründung: kleine Analyse je Spielerin mit Link zum Profil
    e("""${g ? `<span class="begr1"><b>${esc(nachN(g.voll || g.n))}</b> · ${esc(kurzWarum(g.warum))}</span>` : '<span class="mu">Spielerin antippen, dann steht hier, warum wir sie so einschätzen.</span>'}""",
      """${g ? begrAnalyse(k, g) : '<span class="mu">Spielerin antippen, dann steht hier, warum wir sie so einschätzen.</span>'}""")
    e("""  function prognose(a, seite, k){""", r"""  function begrAnalyse(k, g){
    const s = spAus(k, g), st = STUFE[g.st], z = [];
    z.push(`<span class="z"><b>Prognose:</b> ${esc(kurzWarum(g.warum))}</span>`);
    if (s) {
      const l3 = (s.spiele || []).slice(-3);
      if (l3.length) z.push(`<span class="z"><b>Letzte 3 Ligaspiele:</b> ${l3.map(e => (e.art === "S" ? "Startelf " : e.art === "E" ? "Joker " : e.art === "B" ? "Bank" : "fehlte") + (e.art === "S" || e.art === "E" ? e.min + "'" : "")).join(" · ")}</span>`);
      const a = afSp(s.id), v = a && (a.no || []).filter(x => x[2] >= 60);
      if (v && v.length >= 4) { const n = v.map(x => x[1]), l = n.slice(-3).reduce((x, y) => x + y, 0) / 3, o = n.slice(0, -3).reduce((x, y) => x + y, 0) / (n.length - 3), d = l - o;
        z.push(`<span class="z"><b>Form:</b> Note ${dez(o)} → ${dez(l)} in den letzten 3${d <= -.6 ? ", im Formtief" : d >= .6 ? ", im Aufwind" : ", stabil"}</span>`); }
      const sp = s.spiele || [], to = sp.reduce((x, e) => x + (e.tore || []).length, 0), vo = sp.reduce((x, e) => x + (e.vorl || 0), 0);
      if (to || vo) z.push(`<span class="z"><b>Saison:</b> ${to} ${to === 1 ? "Tor" : "Tore"}, ${vo} ${vo === 1 ? "Vorlage" : "Vorlagen"}</span>`);
      const std = Object.keys(s.standards || {}).map(x => ({ecken: "Ecken", freistoesse: "Freistöße", elfmeter: "Elfmeter"}[x] || x));
      if (std.length) z.push(`<span class="z"><b>Standards:</b> ${esc(std.join(", "))}</span>`);
      if (s.status && s.status.s !== "fit" && s.status.grund) z.push(`<span class="z"><b>Status:</b> ${esc(s.status.grund)}</span>`);
    }
    return `<div class="ba"><span class="k1"><b>${esc(g.voll || g.n)}</b>${st ? `<span style="display:inline-flex;gap:5px;align-items:center;font-size:12px">${stufeSym(g.st, 14)}${esc(st[2])}</span>` : ""}</span>${z.join("")}${s ? `<button class="pl" data-profil="${esc(s.id)}">Zum Profil ›</button>` : ""}</div>`;
  }
  function prognose(a, seite, k){""")

    # ---------- Form-Karten: Nummer und Position, Zahl und Text nebeneinander, Reihenfolge nach Noten
    e("""<span class="vn">${logo(f.k, 18)}${esc(kname(f.k))}</span>${afKurve(f)}<span class="big">${esc(f.big)}</span><span class="bt">${esc(f.big_txt)}</span>""",
      """<span class="vn">${logo(f.k, 18)}${esc(kname(f.k))}${(() => { const s = SPN && (f.id ? spById(f.id) : findeSP(f.k, nachN(f.n))); if (!s) return ""; const pos = (s.slots && s.slots[0] && s.slots[0][2]) || ({TW: "Tor", ABW: "Abwehr", MF: "Mittelfeld", ST: "Sturm"})[s.pos] || ""; return `<span class="mu" style="flex-basis:100%;font-weight:500">${s.nr ? "Nr. " + esc(s.nr) + " · " : ""}${esc(pos)}</span>`; })()}</span>${afKurve(f)}<span class="bigr"><span class="big">${esc(f.big)}</span><span class="bt">${esc(f.big_txt)}</span></span>""")
    e("""    return l.slice(0, 10).filter(f => zeigen(f.k)); };""",
      """    const wert = f => { const s = SPN && (f.id ? spById(f.id) : findeSP(f.k, nachN(f.n))), a = s && afSp(s.id), v = a && (a.no || []).filter(x => x[2] >= 60);
      if (!v || v.length < 4) return null; const n = v.map(x => x[1]), l = n.slice(-3).reduce((x, y) => x + y, 0) / 3; return key === "hold" ? a.avg : l - n.slice(0, -3).reduce((x, y) => x + y, 0) / (n.length - 3); };
    const sortiert = l.map((f, i) => ({f, i, w: wert(f)})).sort((a, b) => (a.w == null) - (b.w == null) || (key === "down" ? a.w - b.w : b.w - a.w) || a.i - b.i).map(x => x.f);
    return sortiert.slice(0, 10).filter(f => zeigen(f.k)); };""")

    # ---------- Standards: Ecken-Abnehmerinnen aus dem Liveticker, Freistoß-Schützin wenn offen
    e("""return w ? `<small>Ecken: ${esc(w[0])}</small>` : ""; })()}</span>""",
      """const t = AF && AF.stdt && AF.stdt[k], ab = t && t.kopf.filter(x => x[1] || x[2]).slice(0, 2), ec = w ? w[0] : t && t.ecke[0] ? nachN(t.ecke[0][0]) : null;
        return (ec ? `<small>Ecken: <b>${esc(ec)}</b></small>` : "") + (ab && ab.length ? `<small>Kopfball nach Standard: ${ab.map(x => `<b>${esc(nachN(x[0]))}</b> ${[x[1] ? x[1] + "x" : "", x[2] ? x[2] + " Tor" + (x[2] > 1 ? "e" : "") : ""].filter(Boolean).join(", ")}`).join(" · ")}</small>` : ""); })()}</span>""")
    e("""${zelle(s.ecken)}${zelle(s.fs)}""", """${zelle(s.ecken)}${zelle((s.fs || []).length ? s.fs : ((AF && AF.stdt && AF.stdt[s.k] && AF.stdt[s.k].fs) || []).slice(0, 1).map(x => [nachN(x[0]), 1]))}""")
    e("""<p class="af-st">Quelle: API-Football, Stand nach dem ${AF.md}. Spieltag. Fuß aus unseren Stammdaten.</p>""",
      """<p class="af-st">Ecken pro Spiel und Elfmeter: API-Football, Stand nach dem ${AF.md}. Spieltag. Schützinnen und Kopfbälle nach Standards: ausgewertet aus dem Sportschau-Liveticker (nur beschriebene Szenen). Fuß aus unseren Stammdaten.</p>""")

    e("""  function begrAnalyse(k, g){""", """  document.addEventListener("click", e => { if (e.target.closest("[data-anaart]") && typeof anaArticle === "function") anaArticle(); });
  function begrAnalyse(k, g){""")
    # ---------- Test (Finn 04.11.): Umfragen direkt im Feed
    e("""uT = u && u.top ? u : null""", """uT = u ? u : null""")
    # ---------- Inside-Inhalte, die in den News stehen, fallen in Inside weg
    e("""      ${A ? `<section class="sek" id="analyse">${sektion("06", "Analyse")}""",
      """      ${A && A.news_zeit && dt(A.news_zeit) <= new Date() ? `<button class="af-innews" data-anaart="1"><span><b>Analyse der Woche</b><br><span class="mu">${esc(A.titel || "")}: steht jetzt in den News</span></span><span>›</span></button>` : A ? `<section class="sek" id="analyse">${sektion("06", "Analyse")}""")
    e("""      ${x.length ? `<h3 class="disp" style="font-size:19px">xG-Check""", """      ${x.length && !(AF.news || []).some(n => /^af-xg-/.test(n.id) && n.zeit && dt(n.zeit) <= new Date()) ? `<h3 class="disp" style="font-size:19px">xG-Check""")
    return h

if __name__ == "__main__":
    p = sys.argv[1]; t = r7(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
