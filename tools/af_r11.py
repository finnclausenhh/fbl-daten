"""Runde 11 (Finn 04.11.2026 20:01), zunächst nur Testkopie:
Weitere Werte in drei Varianten zum Umschalten (Liga-Skala, Perzentil-Leisten, Kacheln mit Rang),
Spielerprofil-Netz mit absoluten Werten, Balken auch für Zweikämpfe und Dribblings,
Steckbrief neu (Fuß als L/R-Schalter mit Ligaanteil, Größe als Messlatte mit zwei Silhouetten),
Kader: Einsatzbalken rechts in jeder Zeile."""
import sys

LR_ALT = "return {p: Math.max(0, Math.min(100, p)), n: vals.length};"
LR_NEU = ("const pl = 1 + vals.filter(v => v > w + 1e-9).length, mn = Math.min(...vals), mx = Math.max(...vals), mw = vals.reduce((a, b) => a + b, 0) / vals.length;\n"
          "    return {p: Math.max(0, Math.min(100, p)), n: vals.length, platz: pl, min: mn, max: mx, mw, w};")

WW_NEU = r'''const M = x => (x.spiele || []).reduce((a, e) => a + (e.min || 0), 0), Sx = x => x.stat || {};
      const P = PLURAL[s.pos] || "Spielerinnen", d1 = v => dez(v, 1), pc = v => Math.round(v * 100) + " %";
      // [Wert, Titel, Unterzeile, Rang, Kurzname fürs Netz, Format der Skala, Einheit der Skala]
      if (st.sch && s.pos !== "TW") ww.push([st.sch, "Torschüsse", `${dez(st.sch / nSp)} pro Spiel`, ligaRang(s, x => Sx(x).sch != null && M(x) ? Sx(x).sch / M(x) * 90 : null), "Torschüsse", d1, "pro 90 Min.", dez(st.sch / nSp) + " pro Spiel"]);
      if (af.kp != null && s.pos !== "TW") ww.push([af.kp, "Schlüsselpässe", `${dez(af.kp90)} pro 90 Minuten`, ligaRang(s, x => (afSp(x.id) || {}).kp90 ?? null), "Schlüsselpässe", d1, "pro 90 Min.", dez(af.kp90) + " pro 90 Min."]);
      if (st.zk_ges) ww.push([`${st.zk_w}/${st.zk_ges}`, "Zweikämpfe gewonnen", `${st.zk_w} von ${st.zk_ges} · ${Math.round(st.zk_w / st.zk_ges * 100)} %`, ligaRang(s, x => Sx(x).zk_ges >= 10 ? Sx(x).zk_w / Sx(x).zk_ges : null), "Zweikämpfe", pc, "gewonnen", `${st.zk_w} von ${st.zk_ges} · ${Math.round(st.zk_w / st.zk_ges * 100)} %`]);
      if (st.p_ges) ww.push([`${st.p_ok}/${st.p_ges}`, "Pässe angekommen", `${st.p_ok} von ${st.p_ges} · ${Math.round(st.p_ok / st.p_ges * 100)} %`, ligaRang(s, x => Sx(x).p_ges >= 50 ? Sx(x).p_ok / Sx(x).p_ges : null), "Passquote", pc, "angekommen", `${st.p_ok} von ${st.p_ges} · ${Math.round(st.p_ok / st.p_ges * 100)} %`]);
      if (st.bk) ww.push([dez(st.bk / nSp, 0), "Ballkontakte pro Spiel", `${st.bk} gesamt`, ligaRang(s, x => Sx(x).bk && M(x) ? Sx(x).bk / M(x) * 90 : null), "Ballkontakte", v => dez(v, 0), "pro 90 Min.", dez(st.bk / nSp, 0) + " pro Spiel"]);
      if (af.drib) ww.push([`${af.drib[0]}/${af.drib[1]}`, "Dribblings erfolgreich", `${af.drib[0]} von ${af.drib[1]} · ${Math.round(af.drib[0] / af.drib[1] * 100)} %`, af.drib[1] >= 5 ? ligaRang(s, x => { const d = (afSp(x.id) || {}).drib; return d && d[1] >= 5 ? d[0] / d[1] : null; }) : null, "Dribblings", pc, "erfolgreich", `${af.drib[0]} von ${af.drib[1]} · ${Math.round(af.drib[0] / af.drib[1] * 100)} %`]);
      if (af.parsp) ww.push([dez(af.par / af.parsp, 1), "Paraden pro Spiel", `${af.par} in ${af.parsp} Spielen`, ligaRang(s, x => (afSp(x.id) || {}).parsp >= 3 ? afSp(x.id).par / afSp(x.id).parsp : null), "Paraden", d1, "pro Spiel", dez(af.par / af.parsp, 1) + " pro Spiel"]);
      const gelb = sp.filter(e => e.gelb && !e.gr).length; if (gelb || st.fouls != null) { const fr = ligaRang(s, x => Sx(x).fouls != null && M(x) ? -Sx(x).fouls / M(x) * 90 : null);
        ww.push([gelb + (gelb >= 4 ? " ⚠" : ""), gelb === 1 ? "Gelbe Karte" : "Gelbe Karten", gelb >= 4 ? "bei der 5. ein Spiel Sperre" : `${st.fouls || 0} ${st.fouls === 1 ? "Foul" : "Fouls"} · ${st.gef || 0}-mal gefoult`, fr ? Object.assign({}, fr, {fair: 1}) : null]); }
      const pfarbe = p => p >= 67 ? "#4ADE80" : p >= 34 ? "#F5C26B" : "#FF6B6B";
      const satz = r => r.fair ? (r.p >= 50 ? "foult seltener als " + r.p + " % der " + P : "foult häufiger als " + (100 - r.p) + " % der " + P) : r.p >= 100 ? "Bestwert aller " + P : r.p <= 0 ? "niedrigster Wert aller " + P : r.p >= 50 ? "besser als " + r.p + " % der " + P : "schlechter als " + (100 - r.p) + " % der " + P;
      const mitR = ww.filter(w => w[3] && !w[3].fair);
      if (ww.length) {
        // Netz: Perzentile gegen die eigene Position, gestrichelter Ring = Durchschnitt
        let netz = "";
        const nz = mitR.slice(0, 6);
        if (nz.length >= 3) {
          const C = 150, R = 62, n = nz.length, pt = (i, f) => { const a = -Math.PI / 2 + i * 2 * Math.PI / n; return [C + Math.cos(a) * R * f, 112 + Math.sin(a) * R * f]; };
          const ring = f => nz.map((_, i) => pt(i, f).map(v => v.toFixed(1)).join(",")).join(" ");
          const sie = nz.map((w, i) => pt(i, Math.max(.06, w[3].p / 100)).map(v => v.toFixed(1)).join(",")).join(" ");
          const lab = nz.map((w, i) => { const [x, y] = pt(i, 1.22), an = x < C - 8 ? "end" : x > C + 8 ? "start" : "middle";
            const yy = y - 10 + (y > 150 ? 8 : y < 70 ? -10 : 0);
            return `<text x="${x.toFixed(0)}" y="${yy.toFixed(0)}" text-anchor="${an}" class="nl">${esc(w[4])}</text><text x="${x.toFixed(0)}" y="${(yy + 12).toFixed(0)}" text-anchor="${an}" class="nw">${esc(w[7])}</text><text x="${x.toFixed(0)}" y="${(yy + 24).toFixed(0)}" text-anchor="${an}" class="nv" fill="${pfarbe(w[3].p)}">${w[3].p >= 50 ? "besser als " + w[3].p : "schlechter als " + (100 - w[3].p)} %</text>`; }).join("");
          netz = `<svg class="ww-netz" viewBox="-10 2 320 222" role="img" aria-label="Spielerprofil im Vergleich zu allen ${esc(P)}">
            ${[.25, .75, 1].map(f => `<polygon points="${ring(f)}" fill="none" stroke="rgba(255,255,255,.08)"/>`).join("")}
            <polygon points="${ring(.5)}" fill="none" stroke="rgba(255,255,255,.35)" stroke-dasharray="3 3"/>
            ${nz.map((_, i) => { const [x, y] = pt(i, 1); return `<line x1="${C}" y1="112" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(255,255,255,.06)"/>`; }).join("")}
            <polygon points="${sie}" fill="rgba(143,176,255,.28)" stroke="#8FB0FF" stroke-width="2"/>
            ${lab}</svg><p class="ww-nl"><i class="sie"></i>sie <i class="mw"></i>Ø aller ${esc(P)}</p>`;
        }
        const kurz = r => r.fair ? (r.p >= 50 ? "foult seltener als " + r.p + " %" : "foult häufiger als " + (100 - r.p) + " %") : r.p >= 100 ? "Bestwert" : r.p <= 0 ? "niedrigster Wert" : r.p >= 50 ? "besser als " + r.p + " %" : "schlechter als " + (100 - r.p) + " %";
        const kacheln = `<div class="af-ww kw">${ww.map(w => { const r = w[3];
          return `<div><b>${w[0]}</b><span class="lb">${esc(w[1])}</span>${w[2] ? `<span class="su">${esc(w[2])}</span>` : ""}${r ? `<span class="pl-l"><i style="left:${Math.max(3, Math.min(97, r.p))}%"></i></span><span class="rg" style="color:${pfarbe(r.p)}">Platz ${r.platz} von ${r.n}</span><span class="ps">${esc(kurz(r))}</span>` : ""}</div>`; }).join("")}</div>`;
        h += `<section class="pf-box">${kap("Weitere Werte")}${netz}${kacheln}<p class="af-st">Platz und Prozent: Vergleich mit allen ${esc(P)} der Liga ab 270 Minuten. Rot, gelb, grün zeigt, wo sie in der Liga steht. Schlüsselpässe, Dribblings und Paraden: API-Football, übrige Werte: Spielstatistik der Sportschau.</p></section>`;
      }
      const alleAF = Object.values((AF && AF.sp) || {}), grL = alleAF.map(x => x.gr).filter(Boolean), alL = alleAF.map(x => x.alter).filter(Boolean);
      const grP = ((SPN && SPN.spielerinnen) || []).filter(x => x.pos === s.pos).map(x => (afSp(x.id) || {}).gr).filter(Boolean);
      const mw = l => l.length ? l.reduce((a, b) => a + b, 0) / l.length : null, grLm = mw(grL), grPm = mw(grP);
      const grPct = af.gr && grL.length ? Math.round(grL.filter(g => g < af.gr).length / grL.length * 100) : null;
      const fu = af.fuss, fl = flagge(s.nation), fuL = alleAF.map(x => x.fuss).filter(Boolean);
      const fuAnt = fu && fuL.length >= 20 ? Math.round(fuL.filter(x => x === fu).length / fuL.length * 100) : null;
      const FUW = {rechts: "Rechts", links: "Links", "beidfüßig": "Beidfüßig"};
      const fuV = ["rechts", "links", "beidfüßig"].map(f => [f, fuL.length ? fuL.filter(x => x === f).length / fuL.length * 100 : 0]);
      const fuF = {rechts: "#8FB0FF", links: "#C9A7FF", "beidfüßig": "#4ADE80"};
      const t1 = `<div class="sb-fu"><span class="kl">Starker Fuß</span><b>${fu ? FUW[fu] || esc(fu) : "unbekannt"}</b>${fuL.length >= 20 ? `<span class="fu-v" aria-hidden="true">${fuV.map(([f, q]) => `<i style="flex:${q.toFixed(1)};background:${f === fu ? fuF[f] : "rgba(255,255,255,.12)"}"></i>`).join("")}</span>` : ""}<span>${fuAnt != null ? `${fuAnt} % der Liga sind ${fu === "beidfüßig" ? "beidfüßig" : fu === "links" ? "Linksfüßerinnen" : "Rechtsfüßerinnen"}` : ""}</span></div>`;
      const t2 = `<div><span class="kl">Alter</span><b>${af.alter ? af.alter + " Jahre" : "–"}</b><span>${alL.length ? "Liga-Durchschnitt " + Math.round(mw(alL)) + " Jahre" : ""}</span></div>`;
      const t4 = `<div class="na"><span class="kl">Nationalität</span><b>${fl ? `<span class="fl">${fl}</span>` : ""}${esc(s.nation || "–")}</b></div>`;
      // Größe: Messlatte 1,40 bis 1,90 m, zwei Silhouetten im gleichen Maßstab, Hilfslinien zur Latte
      let t3 = "";
      if (af.gr && grLm) {
        const ref = grPm || grLm, refT = grPm ? ({TW: "Ø Torhüterinnen", ABW: "Ø Abwehr", MF: "Ø Mittelfeld", ST: "Ø Sturm"}[s.pos] || "Ø Position") : "Liga-Ø";
        // Latte ab 1,00 m (unten unterbrochen), Silhouetten reichen vom Boden bis zur Größe
        const Y0 = 196, k = 1.9, y = cm => Y0 - (cm - 100) * k;
        const fig = (x, cm, farbe) => { const top = y(cm), hh = (cm - 100) * k / 100;
          return `<g transform="translate(${x} ${top.toFixed(1)}) scale(${hh.toFixed(3)})" fill="${farbe}" stroke="${farbe}" stroke-linecap="round"><circle cx="20" cy="8" r="7" stroke="none"/><path d="M10 18q10-4 20 0l6 14-4 2-3-6 0 22H11l0-22-3 6-4-2z" stroke="none"/><line x1="7" y1="34" x2="5" y2="50" stroke-width="4.5"/><line x1="33" y1="34" x2="35" y2="50" stroke-width="4.5"/><path d="M11 49h18l1.5 13h-8.5l-2-6-2 6H9.5z" stroke="none"/><line x1="14.5" y1="63" x2="14" y2="94" stroke-width="6"/><line x1="25.5" y1="63" x2="26" y2="94" stroke-width="6"/><ellipse cx="13" cy="97" rx="4.5" ry="3" stroke="none"/><ellipse cx="27" cy="97" rx="4.5" ry="3" stroke="none"/></g>`; };
        const ticks = [110, 120, 130, 140, 150, 160, 170, 180, 190].map(c => `<line x1="38" x2="44" y1="${y(c).toFixed(1)}" y2="${y(c).toFixed(1)}" stroke="rgba(255,255,255,.35)"/><text x="34" y="${(y(c) + 3.5).toFixed(1)}" text-anchor="end" class="tk">${dez(c / 100, 2)}</text>`).join("");
        const hl = (cm, farbe, dash) => `<line x1="44" x2="186" y1="${y(cm).toFixed(1)}" y2="${y(cm).toFixed(1)}" stroke="${farbe}" stroke-width="1.2" ${dash ? 'stroke-dasharray="3 3"' : ""}/>`;
        t3 = `<div class="sb-gr"><div class="gt"><b>${dez(af.gr / 100, 2)} m</b><span class="gs">${grPct != null ? (grPct >= 50 ? `größer als ${grPct} % der Liga` : `kleiner als ${100 - grPct} % der Liga`) : "Größe"}</span>
          <span class="lg"><i class="sie"></i>sie ${dez(af.gr / 100, 2)} m</span><span class="lg"><i class="mw"></i>${esc(refT)} ${dez(ref / 100, 2)} m</span>${grPm ? `<span class="lg"><i></i>Liga-Ø ${dez(grLm / 100, 2)} m</span>` : ""}</div>
          <svg viewBox="0 0 190 210" role="img" aria-label="Größe ${dez(af.gr / 100, 2)} Meter im Vergleich zu ${esc(refT)} ${dez(ref / 100, 2)} Meter">
          <line x1="44" x2="44" y1="${y(190).toFixed(1)}" y2="${Y0}" stroke="rgba(255,255,255,.35)" stroke-width="2"/>${ticks}
          <line x1="44" x2="186" y1="${Y0}" y2="${Y0}" stroke="rgba(255,255,255,.18)"/><path d="M38 ${Y0 - 6}l12-4M38 ${Y0 - 2}l12-4" stroke="rgba(255,255,255,.5)"/><text x="34" y="${Y0 + 3}" text-anchor="end" class="tk">1,00</text>
          ${hl(ref, "rgba(255,255,255,.5)", true)}${hl(af.gr, "#8FB0FF", false)}
          ${fig(72, af.gr, "#8FB0FF")}${fig(128, ref, "rgba(255,255,255,.3)")}</svg></div>`;
      } else if (af.gr) t3 = `<div class="sb-gr"><p><b>${dez(af.gr / 100, 2)} m</b></p></div>`;
      if (af.fuss || af.alter || af.gr) h += `<section class="pf-box">${kap("Steckbrief")}<div class="sb3"${fu ? "" : ' style="grid-template-columns:1fr 1fr"'}>${fu ? t1 : ""}${t2}${t4}</div>${t3}<p class="af-st">${af.gr && grLm ? "Messlatte ab 1,00 m, damit die Unterschiede sichtbar werden. " : ""}Größe und Alter: API-Football, Fuß: unsere Stammdaten.</p></section>`; }
'''

CSS_NEU = r'''
/* Runde 11 (Finn 04.11.2026): Weitere Werte mit Umschalter, Netz, Steckbrief neu, Einsatzbalken im Kader */
.ww-netz{width:100%;max-width:360px;justify-self:center;display:block;overflow:visible}
.ww-netz .nl{font:600 10.5px var(--f-body,inherit);fill:var(--ink,#E8EEFF)}
.ww-netz .nw{font:700 11px var(--f-body,inherit);fill:var(--ink)}
.ww-netz .nv{font:600 9.5px var(--f-body,inherit)}
.ww-nl{font-size:10.5px;color:var(--muted);text-align:center;margin:0 0 4px}
.ww-nl i{display:inline-block;width:10px;height:10px;border-radius:3px;vertical-align:-1px;margin:0 4px 0 8px}
.ww-nl i.sie{background:rgba(143,176,255,.5);border:1.5px solid #8FB0FF;box-sizing:border-box}
.ww-nl i.mw{border:1.5px dashed rgba(255,255,255,.5);box-sizing:border-box}
.ww-sw{display:flex;gap:4px;background:var(--soft);border-radius:9px;padding:3px}
.ww-sw button{flex:1;border:0;background:none;color:var(--muted);font:600 12px inherit;padding:6px 4px;border-radius:7px;cursor:pointer}
.ww[data-v="a"] .ww-sw [data-v="a"],.ww[data-v="b"] .ww-sw [data-v="b"],.ww[data-v="c"] .ww-sw [data-v="c"]{background:var(--card);color:var(--ink,#fff)}
.ww .wv{display:none}
.ww[data-v="a"] .wa,.ww[data-v="b"] .wb,.ww[data-v="c"] .wc{display:grid;gap:8px}
.sk,.pl{background:var(--soft);border-radius:10px;padding:9px 10px;display:grid;gap:5px}
.sk-k{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:baseline}
.sk-k span{font-size:12px;color:var(--muted)}
.sk-k b{font-family:var(--f-display);font-weight:800;font-size:17px;text-align:right;white-space:nowrap}
.sk-k em{font:500 11px var(--f-body,inherit);font-style:normal;color:var(--muted);margin-left:6px}
.sk-l{position:relative;height:6px;border-radius:3px;background:rgba(255,255,255,.08);margin:5px 6px 2px}
.sk-l i{position:absolute;top:50%;transform:translate(-50%,-50%)}
.sk-l .mw{width:2px;height:14px;background:rgba(255,255,255,.55);border-radius:1px}
.sk-l .ich{width:13px;height:13px;border-radius:50%;border:2px solid var(--card);box-sizing:content-box}
.sk-u{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:8px;font-size:10px;color:var(--muted);align-items:center}
.sk-u small{font-size:11px;font-weight:600;text-align:center}
.pl-l{position:relative;height:8px;border-radius:4px;background:linear-gradient(90deg,#F5C26B,#8FB0FF 50%,#4ADE80);margin:4px 4px 0}
.pl-l i{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:#fff;transform:translateX(-50%);box-shadow:0 0 0 2px var(--soft)}
.pl small{font-size:11px;font-weight:600}
.af-ww .rg{font:700 10.5px var(--f-mono);margin-top:3px}
.sb3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.sb3 > div{background:var(--soft);border-radius:10px;padding:9px 8px;display:grid;gap:2px;align-content:start;min-width:0}
.sb3 b{font-size:15px;font-weight:700;line-height:1.2}
.sb3 .na b{font-size:13.5px;white-space:normal;overflow-wrap:anywhere;hyphens:auto}
.sb3 .na .fl{font-size:18px;line-height:20px;margin:0 0 2px}
.sb3 span{font-size:10.5px;color:var(--muted);line-height:1.3}
.sb3 .fl{font-size:15px;margin-right:4px;color:initial}
.sb-fu .lr{display:flex;gap:3px;margin-bottom:3px}
.sb-fu .lr i{display:inline-flex;align-items:center;gap:3px;font:800 10px var(--f-mono);font-style:normal;color:rgba(255,255,255,.35);border:1px solid rgba(255,255,255,.15);border-radius:6px;padding:2px 6px;line-height:13px}
.sb-fu .lr i.an{background:#8FB0FF;border-color:#8FB0FF;color:#0B1220}
.sb-gr{background:var(--soft);border-radius:10px;padding:10px;display:grid;grid-template-columns:minmax(0,1fr) 150px;gap:8px;align-items:center}
.sb-gr svg{width:150px;height:auto;display:block}
.sb-gr .gt{display:grid;gap:3px;align-content:center}
.sb-gr .gt > b{font-size:22px;font-weight:800;font-family:var(--f-display);line-height:1}
.sb-gr .gs{font-size:12px;font-weight:600;color:var(--ink);margin-bottom:6px}
.sb-gr .lg{font-size:11px;color:var(--muted);white-space:nowrap}
.sb-gr .lg i{display:inline-block;width:12px;height:0;border-top:2px solid rgba(255,255,255,.2);vertical-align:3px;margin-right:6px}
.sb-gr .lg i.sie{border-top-color:#8FB0FF}
.sb-gr .lg i.mw{border-top:2px dashed rgba(255,255,255,.55)}
.sb-gr .tk{font:600 9.5px var(--f-mono);fill:rgba(255,255,255,.5)}
.sb-gr .hl{font:700 11.5px var(--f-body,inherit)}
.sb-gr p{margin:0;font-size:11.5px;color:var(--muted);text-align:center}
.sb-gr p b{color:var(--ink,#fff)}
.kd-e{display:grid;gap:4px;width:116px;justify-items:end}
.kd-b{display:block;width:116px;height:6px;border-radius:3px;background:rgba(255,255,255,.1);overflow:hidden}
.kd-b i{display:block;height:100%;border-radius:3px}
.kd-e small{font:600 9.5px var(--f-mono);color:var(--muted);white-space:nowrap}
.kd-e .pf-st{font-size:9px;padding:1px 4px}

.kw > div{gap:2px;align-content:start}
.kw .lb{font-size:11.5px;color:var(--ink);font-weight:600}
.kw .su{font-size:11px;color:var(--muted)}
.kw .pl-l{display:block;margin:7px 2px 3px;height:6px}
.kw .pl-l i{top:-4px;height:14px;width:4px}
.kw .rg{font:700 10.5px var(--f-mono)}
.kw .ps{font-size:10.5px;color:var(--muted)}
.pl-l{background:linear-gradient(90deg,#FF6B6B,#F5C26B 50%,#4ADE80)!important}
.sb3 > div{gap:3px}
.sb3 .kl{font:700 9.5px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.sb3 .fu-v{display:flex;gap:2px;height:6px;border-radius:3px;overflow:hidden;margin:3px 0 2px}
.sb3 .fu-v i{display:block;height:100%}
.sb3 .na b{display:grid;gap:2px;hyphens:none;overflow-wrap:normal;font-size:14px}
.sb3 .na .fl{font-size:20px;line-height:22px;margin:0}
'''

KD_ALT = 'const zeile = s => { const st = stArt(s.status); return `<button class="pf-tr" data-profil="${esc(s.id)}">${pfFoto(s, 44, 44, 8)}<span class="pf-tx"><b>${esc(s.n)}</b><small>${s.nr ? "Nr. " + esc(s.nr) : ""}</small></span>${st !== "fit" ? `<i class="pf-st" style="color:${STFARBE[st]};border-color:${STFARBE[st]}">${STWORT[st] || esc(st)}</i>` : ""}</button>`; };'
KD_NEU = ('const kdMd = [...new Set(L.flatMap(x => (x.spiele || []).filter(e => e.erg).map(e => e.md)))].length || 1;\n'
          '    const einsatz = (s, STX) => { const sp = s.spiele || [], mi = sp.reduce((a, e) => a + (e.min || 0), 0), st11 = sp.filter(e => e.art === "S").length, q = Math.min(100, mi / (kdMd * 90) * 100);\n'
          '      return `<span class="kd-e" title="${mi} Minuten, ${st11} von ${kdMd} Spielen in der Startelf"><span class="kd-b"><i style="width:${Math.max(mi ? 4 : 0, q).toFixed(0)}%;background:${q >= 75 ? "#4ADE80" : q >= 35 ? "#8FB0FF" : "rgba(255,255,255,.3)"}"></i></span><small>${mi.toLocaleString("de-DE")}\' · ${st11}/${kdMd} Startelf</small>${STX}</span>`; };\n'
          '    const zeile = s => { const st = stArt(s.status); return `<button class="pf-tr kd" data-profil="${esc(s.id)}">${pfFoto(s, 44, 44, 8)}<span class="pf-tx"><b>${esc(s.n)}</b><small>${s.nr ? "Nr. " + esc(s.nr) : ""}</small></span>${einsatz(s, st !== "fit" ? `<i class="pf-st" style="color:${STFARBE[st]};border-color:${STFARBE[st]}">${STWORT[st] || esc(st)}</i>` : "")}</button>`; };')


def r11(h):
    assert h.count(LR_ALT) == 1, "ligaRang"
    h = h.replace(LR_ALT, LR_NEU)
    a = h.index("const M = x => (x.spiele || []).reduce((a, e) => a + (e.min || 0), 0), Sx = x => x.stat || {};")
    b = h.index("    const f = FOTOS[s.n];", a)
    h = h[:a] + WW_NEU.lstrip() + h[b:]
    i = h.index("function vereinsKader")
    j = h.index(KD_ALT, i)
    h = h[:j] + KD_NEU + h[j + len(KD_ALT):]
    k = h.index("</style>")
    h = h[:k] + CSS_NEU + h[k:]
    return h


if __name__ == "__main__":
    p = sys.argv[1]
    h = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(r11(h))
    print("r11 ok")
