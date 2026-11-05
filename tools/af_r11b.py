"""Runde 11b (05.11.2026), nach af_r11.py anwenden: Gleichstände fair werten (mittlerer Rang),
Platz 1 heißt immer Bestwert, nie "schlechter als 100 %", Paraden ohne Wertung (wenige Paraden heißt wenig zu tun)."""
import sys
def rep(s, old, new):
    n = s.count(old); assert n == 1, (old[:90], n); return s.replace(old, new)

def patch(s):
    s = rep(s, "    const p = Math.round(vals.filter(v => v < w).length / (vals.length - 1) * 100);",
               "    const eq = vals.filter(v => Math.abs(v - w) < 1e-9).length, p = Math.round((vals.filter(v => v < w - 1e-9).length + (eq - 1) / 2) / (vals.length - 1) * 100);")
    s = rep(s, "return {p: Math.max(0, Math.min(100, p)), n: vals.length, platz: pl, min: mn, max: mx, mw, w};",
               "return {p: Math.max(0, Math.min(100, p)), n: vals.length, platz: pl, min: mn, max: mx, mw, w, eq};")
    s = rep(s, '''ligaRang(s, x => (afSp(x.id) || {}).parsp >= 3 ? afSp(x.id).par / afSp(x.id).parsp : null), "Paraden"''',
               '''(r => r ? Object.assign({}, r, {neutral: 1}) : null)(ligaRang(s, x => (afSp(x.id) || {}).parsp >= 3 ? afSp(x.id).par / afSp(x.id).parsp : null)), "Paraden"''')
    s = rep(s, '      const pfarbe = p => p >= 67 ? "#4ADE80" : p >= 34 ? "#F5C26B" : "#FF6B6B";',
               '''      const pfarbe0 = p => p >= 67 ? "#4ADE80" : p >= 34 ? "#F5C26B" : "#FF6B6B";
      const rFarbe = r => r.neutral ? "#8FB0FF" : r.platz === 1 ? "#4ADE80" : r.w <= r.min + 1e-9 ? "#FF6B6B" : pfarbe0(r.p), pfarbe = p => pfarbe0(p);
      const rText = r => { const mit = r.eq > 1 ? `, gleichauf mit ${r.eq - 1}` : "";
        if (r.neutral) return r.platz === 1 ? "die meisten Paraden" + mit : r.w <= r.min + 1e-9 ? "die wenigsten Paraden" + mit : r.p >= 50 ? "mehr als " + r.p + " %" : "weniger als " + (100 - r.p) + " %";
        if (r.platz === 1) return (r.fair ? "die wenigsten Fouls" : "Bestwert") + mit;
        if (r.w <= r.min + 1e-9) return (r.fair ? "die meisten Fouls" : "niedrigster Wert") + mit;
        if (r.fair) return r.p >= 50 ? "foult seltener als " + r.p + " %" : "foult häufiger als " + (100 - r.p) + " %";
        return r.p >= 50 ? "besser als " + r.p + " %" : "schlechter als " + (100 - r.p) + " %"; };''')
    s = rep(s, '''class="nv" fill="${pfarbe(w[3].p)}">${w[3].p >= 50 ? "besser als " + w[3].p : "schlechter als " + (100 - w[3].p)} %</text>''',
               '''class="nv" fill="${rFarbe(w[3])}">${esc(rText(w[3]))}</text>''')
    s = rep(s, '''<span class="rg" style="color:${pfarbe(r.p)}">Platz ${r.platz} von ${r.n}</span><span class="ps">${esc(kurz(r))}</span>''',
               '''<span class="rg" style="color:${rFarbe(r)}">Platz ${r.platz} von ${r.n}</span><span class="ps">${esc(rText(r))}</span>''')
    s = rep(s, '<span class="pl-l"><i style="left:${Math.max(3, Math.min(97, r.p))}%"></i></span>', '<span class="pl-l${r.neutral ? " neu" : ""}"><i style="left:${Math.max(3, Math.min(97, r.platz === 1 && !r.neutral ? 100 : r.p))}%"></i></span>')
    s = rep(s, "Rot, gelb, grün zeigt, wo sie in der Liga steht.", "Rot, gelb, grün zeigt, wo sie in der Liga steht.${ww.some(w => w[3] && w[3].neutral) ? \" Paraden in Blau ohne Wertung: wenige Paraden heißen oft nur, dass die Abwehr wenig zulässt.\" : \"\"}")
    i = s.find("</style>", s.find("--f-display")); s = s[:i] + ".kw .pl-l.neu{background:linear-gradient(90deg,#2A3B5E,#8FB0FF)!important}" + s[i:]
    return s

if __name__ == "__main__":
    for f in sys.argv[1:]:
        s = open(f, encoding="utf-8").read()
        if "const rText = r =>" in s: print("schon drin", f); continue
        t = patch(s); open(f, "w", encoding="utf-8").write(t); print("r11b ok", f)
