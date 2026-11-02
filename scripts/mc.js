// Sağlamlık analizi: 1000 rastgele ağırlık seti (Dirichlet(2,2,2,2)) ile modelin seçtiği ilçelerin sıklığı
const M = require('../docs/model.js'), fs = require('fs'), path = require('path');
const D = M.prepare(JSON.parse(fs.readFileSync(path.join(__dirname, '../docs/data/veri.json'))));
let s = 42;
const rnd = () => { s |= 0; s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const g2 = () => -Math.log(rnd()) - Math.log(rnd()); // Gamma(2,1)
const N = 1000, cnt = {};
for (let k = 0; k < N; k++) {
  const g = [g2(), g2(), g2(), g2()], S = g.reduce((a, b) => a + b);
  const w = g.map(x => 100 * x / S);
  const r = M.run(D, { w_hinter: w[0], w_own: w[1], w_dist: w[2], w_sege: w[3] });
  for (const x of r.sel) cnt[x.id] = (cnt[x.id] || 0) + 1;
}
const out = Object.entries(cnt).map(([id, c]) => [+id, Math.round(1000 * c / N) / 1000]).sort((a, b) => b[1] - a[1]);
fs.writeFileSync(path.join(__dirname, '../docs/data/saglamlik.json'), JSON.stringify({ n: N, dagilim: "Dirichlet(2,2,2,2)", oran: Object.fromEntries(out) }));
console.log(out.length, 'farklı ilçe en az bir kez seçildi');
console.log(out.slice(0, 40).map(([id, r]) => `${D.I.ad[id]} (${D.iller[D.I.il[id]]}) %${Math.round(r * 100)}`).join('\n'));
const press = [...Array(D.n).keys()].filter(i => D.I.basin[i]);
console.log('\nBasın listesi:');
console.log(press.map(i => `${D.I.ad[i]} %${Math.round((cnt[i] || 0) / N * 100)}`).join(', '));
