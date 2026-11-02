// 100 İl — il adayı modeli (Python referans uygulamasının birebir karşılığı: scripts/model.py)
(function (root) {
  const DEFAULTS = {
    w_hinter: 35, w_own: 20, w_dist: 25, w_sege: 20,
    core_km: 30, chain_density: 500, chain_link: 20,
    min_own: 40000, min_hinter: 150000, min_parent: 250000,
    n_new: 19,
  };

  const lin = (x, a, b) => Math.max(0, Math.min(1, (x - a) / (b - a)));
  const loglin = (x, a, b) => lin(Math.log10(Math.max(x, 1)), Math.log10(a), Math.log10(b));

  function prepare(veri) {
    const F = veri.alanlar.reduce((o, k, i) => ((o[k] = i), o), {});
    const n = veri.ilceler.length;
    const I = {
      il: new Int16Array(n), pop: new Float64Array(n), mdk: new Float64Array(n), mkm: new Float64Array(n),
      sege: new Float64Array(n), alan: new Float64Array(n), ad: new Array(n), basin: new Uint8Array(n),
      segeSira: new Int16Array(n), lat: new Float64Array(n), lon: new Float64Array(n),
    };
    for (const r of veri.ilceler) {
      const id = r[F.id];
      I.il[id] = r[F.il]; I.ad[id] = r[F.ilce]; I.pop[id] = r[F.nufus];
      I.mdk[id] = r[F.merkez_dk]; I.mkm[id] = r[F.merkez_km]; I.sege[id] = r[F.sege];
      I.segeSira[id] = r[F.sege_sira]; I.alan[id] = r[F.alan]; I.lat[id] = r[F.lat]; I.lon[id] = r[F.lon];
      I.basin[id] = r[F.basin];
    }
    const byIl = veri.iller.map(() => []);
    const dk = new Map(); // key a*1000+b
    for (const [ilIdx, m] of Object.entries(veri.matris)) {
      byIl[+ilIdx] = m.ids.slice();
      m.ids.forEach((a, i) => m.ids.forEach((b, j) => {
        if (a !== b) dk.set(a * 1000 + b, m.dk[i][j] == null ? 1e9 : m.dk[i][j]);
      }));
    }
    return { n, I, byIl, dk, iller: veri.iller };
  }

  function run(D, opts) {
    const p = Object.assign({}, DEFAULTS, opts || {});
    const { n, I, byIl, dk } = D;
    const getDk = (a, b) => { const v = dk.get(a * 1000 + b); return v === undefined ? 1e9 : v; };

    // 1) kent çekirdeği
    const core = new Uint8Array(n);
    for (let i = 0; i < n; i++) core[i] = I.mkm[i] <= p.core_km ? 1 : 0;
    let grew = true;
    while (grew) {
      grew = false;
      for (let j = 0; j < n; j++) {
        if (core[j] || I.pop[j] / I.alan[j] < p.chain_density) continue;
        for (const k of byIl[I.il[j]]) {
          if (core[k] && getDk(j, k) <= p.chain_link) { core[j] = 1; grew = true; break; }
        }
      }
    }

    const tTo = (j, c) => (c === null ? (core[j] ? 0 : I.mdk[j]) : (j === c ? 0 : getDk(j, c)));

    function assignIl(il, centers) {
      const out = new Map();
      for (const j of byIl[il]) {
        if (core[j]) { out.set(j, null); continue; }
        if (centers.includes(j)) { out.set(j, j); continue; }
        let best = null, bt = tTo(j, null);
        for (const c of centers) { const v = tTo(j, c); if (v < bt) { bt = v; best = c; } }
        out.set(j, best);
      }
      return out;
    }

    function score(c, hpop) {
      const comp = {
        s_hinter: loglin(hpop, 80000, 1000000),
        s_own: loglin(I.pop[c], 30000, 600000),
        s_dist: lin(I.mdk[c], 30, 180),
        s_sege: lin(I.sege[c], -1.5, 2.5),
      };
      const W = p.w_hinter + p.w_own + p.w_dist + p.w_sege || 1;
      const s = (100 * (p.w_hinter * comp.s_hinter + p.w_own * comp.s_own + p.w_dist * comp.s_dist + p.w_sege * comp.s_sege)) / W;
      return { s, comp };
    }

    function tryAdd(c, chosen) {
      const il = I.il[c];
      const centers = chosen.filter((x) => I.il[x] === il).concat([c]);
      const a = assignIl(il, centers);
      const grp = new Map();
      for (const [j, cc] of a) { const k = cc === null ? -1 : cc; if (!grp.has(k)) grp.set(k, []); grp.get(k).push(j); }
      const sum = (arr) => (arr || []).reduce((s, j) => s + I.pop[j], 0);
      const hpop = sum(grp.get(c));
      const parent = sum(grp.get(-1));
      const othersOk = centers.every((x) => x === c || sum(grp.get(x)) >= p.min_hinter);
      const { s, comp } = score(c, hpop);
      const reasons = [];
      if (hpop < p.min_hinter) reasons.push("yeni il nüfusu yetersiz");
      if (parent < p.min_parent) reasons.push("geride kalan il çok küçülüyor");
      if (!othersOk) reasons.push("komşu yeni ili eşiğin altına düşürüyor");
      return { id: c, il, hpop, parent, members: grp.get(c), ok: reasons.length === 0, reasons, puan: Math.round(s * 10) / 10, comp };
    }

    const cands = [];
    for (let i = 0; i < n; i++) if (!core[i] && I.pop[i] >= p.min_own) cands.push(i);
    const first = cands.map((c) => tryAdd(c, [])).sort((a, b) => b.puan - a.puan);
    const firstById = new Map(first.map((r, k) => [r.id, Object.assign(r, { rank: k + 1 })]));

    const chosen = [], steps = [];
    while (chosen.length < p.n_new) {
      let best = null;
      for (const c of cands) {
        if (chosen.includes(c)) continue;
        const r = tryAdd(c, chosen);
        if (r.ok && (best === null || r.puan > best.puan)) best = r;
      }
      if (!best) break;
      chosen.push(best.id); steps.push(best);
    }

    // nihai atama
    const final = new Array(n).fill(null);
    byIl.forEach((ids, il) => {
      const a = assignIl(il, chosen.filter((x) => I.il[x] === il));
      for (const [j, cc] of a) final[j] = cc;
    });
    const sel = chosen.map((c, k) => {
      const members = []; let hpop = 0;
      for (let j = 0; j < n; j++) if (final[j] === c) { members.push(j); hpop += I.pop[j]; }
      let parent = 0;
      for (const j of byIl[I.il[c]]) if (final[j] === null) parent += I.pop[j];
      const { s, comp } = score(c, hpop);
      return { sira: k + 1, id: c, il: I.il[c], hpop, members, parent, puan: Math.round(s * 10) / 10, comp };
    });
    return { p, core, final, sel, first, firstById, cands };
  }

  const api = { DEFAULTS, prepare, run };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.IlModel = api;
})(this);
