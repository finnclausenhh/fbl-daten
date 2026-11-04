"""Runde 6 (Finn 04.11.2026, 09:57): Form-Karten wieder linksbündig, Notenkurve über die ganze Saison
direkt neben dem Foto statt eigenem Kasten. python3 tools/af_r6.py <datei.html>"""
import sys

CSS6 = """
.fkomp .tx{align-items:stretch;text-align:left}
.fkomp .tx .fbadge{align-self:flex-start}
.fkomp .vn{justify-content:flex-start}
.fkk{display:grid;gap:2px;margin-top:6px}
.fkk svg{width:100%;height:40px;display:block;overflow:visible}
.fkk small{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;gap:6px}
.fkk small b{font-weight:700}
.finh > p.fke{font-size:12.5px;color:var(--muted);line-height:1.4;margin:-4px 0 0}
"""

def r6(h):
    def e(a, b, n=1):
        nonlocal h
        if h.count(a) != n: raise SystemExit(f"R6: {h.count(a)}x statt {n}x: {a[:90]!r}")
        h = h.replace(a, b)
    i = h.rfind("</style>"); h = h[:i] + CSS6 + h[i:]
    # Kurve neben dem Foto (kompakte Karte), alle Ligaspiele, Kurzeinsätze blass
    e("""<span class="vn">${logo(f.k, 18)}${esc(kname(f.k))}</span><span class="big">""",
      """<span class="vn">${logo(f.k, 18)}${esc(kname(f.k))}</span>${afKurve(f)}<span class="big">""")
    e("""${afFormZeile(f)}<p>${esc(f.text)}</p>""", """${afEinordnung(f)}<p>${esc(f.text)}</p>""")
    e("""  function afFormZeile(f){""", r"""  function afKurve(f){
    if (!AF || !AF.sp || !SPN) return "";
    const s = f.id ? spById(f.id) : findeSP(f.k, nachN(f.n)), a = s && afSp(s.id); if (!a || !(a.no || []).length) return "";
    const sp = s.spiele || [], N = Math.max(...sp.map(z => z.md), ...a.no.map(x => x[0]), 2), voll = a.no.filter(x => x[2] >= 60);
    const W = 200, H = 40, X = md => 4 + (md - 1) / (N - 1) * (W - 8), Y = n => 4 + (10 - Math.max(4, Math.min(10, n))) / 6 * (H - 8);
    const n3 = voll.slice(-3).map(x => x[1]), l3 = n3.length ? n3.reduce((x, y) => x + y, 0) / n3.length : null;
    const vor = voll.length > 3 ? voll.slice(0, -3).reduce((x, y) => x + y[1], 0) / (voll.length - 3) : null;
    const c = vor == null ? "#8FB0FF" : l3 - vor <= -.6 ? "#F59E0B" : l3 - vor >= .6 ? "#4ADE80" : "#8FB0FF";
    const linie = voll.map(x => X(x[0]).toFixed(1) + "," + Y(x[1]).toFixed(1)).join(" ");
    return `<span class="fkk"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-label="Noten je Spieltag">
      ${sp.map(z => `<line x1="${X(z.md).toFixed(1)}" x2="${X(z.md).toFixed(1)}" y1="${H - 2}" y2="${H}" stroke="rgba(255,255,255,.18)" vector-effect="non-scaling-stroke"/>`).join("")}
      ${voll.length > 1 ? `<polyline points="${linie}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>` : ""}
      ${a.no.map(x => `<circle cx="${X(x[0]).toFixed(1)}" cy="${Y(x[1]).toFixed(1)}" r="${x[2] >= 60 ? 3 : 2.4}" fill="${x[2] >= 60 ? NFARBE(x[1]) : "none"}" stroke="${x[2] >= 60 ? "#16223A" : "rgba(255,255,255,.45)"}" stroke-width="1.2" vector-effect="non-scaling-stroke"/>`).join("")}
    </svg><small><span>Note je Spieltag</span><span>${vor != null ? `<span class="mu">${dez(vor)}</span> → <b style="color:${c}">${dez(l3)}</b>` : `Ø <b>${dez(a.avg || a.no.reduce((x, y) => x + y[1], 0) / a.no.length)}</b>`}</span></small></span>`;
  }
  function afEinordnung(f){
    if (!AF || !AF.form || !SPN) return "";
    const s = f.id ? spById(f.id) : findeSP(f.k, nachN(f.n)); if (!s) return "";
    const fl = [].concat(AF.form.tief || [], AF.form.hoch || [], AF.form.lauf || [], AF.form.stabil || []).find(x => x.id === s.id), t = fl ? einordnungSatz(fl) : "";
    return t ? `<p class="fke">${esc(t)}</p>` : "";
  }
  function afFormZeile(f){""")
    return h

if __name__ == "__main__":
    p = sys.argv[1]; t = r6(open(p, encoding="utf-8").read()); open(p, "w", encoding="utf-8").write(t); print("ok", p)
