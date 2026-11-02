/* 100 İl Haritası — arayüz */
(async function () {
  const $ = (s) => document.querySelector(s);
  const fmt = new Intl.NumberFormat("tr-TR");
  const fmtK = (v) => (v >= 1e6 ? (v / 1e6).toLocaleString("tr-TR", { maximumFractionDigits: 2 }) + " milyon" : fmt.format(Math.round(v / 1000)) + " bin");
  const collator = new Intl.Collator("tr");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

  const [veri, topo, sag] = await Promise.all([
    fetch("data/veri.json").then((r) => r.json()),
    fetch("data/ilce.topo.json").then((r) => r.json()),
    fetch("data/saglamlik.json").then((r) => r.json()).catch(() => ({ oran: {} })),
  ]);
  const D = IlModel.prepare(veri);
  const I = D.I, iller = D.iller;
  const ilAdi = (id) => iller[I.il[id]];

  // ---------- kontroller ----------
  const W = [
    { k: "w_hinter", ad: "Yeni ilin toplam nüfusu", alt: "Bağlanacak ilçelerle birlikte" },
    { k: "w_own", ad: "İlçenin kendi nüfusu", alt: "Merkez olacak ilçe ne kadar büyük?" },
    { k: "w_dist", ad: "İl merkezine uzaklık", alt: "Sürüş süresi; uzak ilçe hizmete zor erişir" },
    { k: "w_sege", ad: "Gelişmişlik (SEGE-2022)", alt: "Ekonomik ve sosyal altyapı" },
  ];
  const R = [
    { k: "core_km", ad: "Kent çekirdeği", min: 10, max: 60, step: 5, u: (v) => v + " km" },
    { k: "min_hinter", ad: "Yeni il en az", min: 50000, max: 400000, step: 25000, u: fmtK },
    { k: "min_parent", ad: "Geride kalan il en az", min: 0, max: 500000, step: 25000, u: (v) => (v ? fmtK(v) : "sınır yok") },
  ];
  const SEN = [
    { ad: "Dengeli", w: [35, 20, 25, 20] },
    { ad: "Hizmete erişim", w: [25, 10, 50, 15] },
    { ad: "Nüfus", w: [50, 30, 10, 10] },
    { ad: "Ekonomi", w: [30, 15, 15, 40] },
  ];
  const state = Object.assign({}, IlModel.DEFAULTS);
  readHash();

  const wBox = $("#agirliklar"), rBox = $("#kurallar"), chips = $("#senaryolar");
  W.forEach((w) => wBox.append(slider(w.k, w.ad, 0, 100, 5, (v) => v, w.alt)));
  R.forEach((r) => rBox.append(slider(r.k, r.ad, r.min, r.max, r.step, r.u)));
  SEN.forEach((s) => {
    const b = document.createElement("button");
    b.className = "chip"; b.type = "button"; b.textContent = s.ad;
    b.addEventListener("click", () => {
      W.forEach((w, i) => { state[w.k] = s.w[i]; const el = document.getElementById(w.k); el.value = s.w[i]; el.dispatchEvent(new Event("sync")); });
      schedule();
    });
    chips.append(b);
  });

  function slider(k, ad, min, max, step, unit, alt) {
    const d = document.createElement("div"); d.className = "sl";
    d.innerHTML = `<label for="${k}"><span>${ad}</span><output for="${k}"></output></label>
      <input type="range" id="${k}" min="${min}" max="${max}" step="${step}" value="${state[k]}">${alt ? `<small>${alt}</small>` : ""}`;
    const inp = d.querySelector("input"), out = d.querySelector("output");
    const show = () => (out.textContent = unit(+inp.value));
    inp.addEventListener("input", () => { state[k] = +inp.value; show(); schedule(); });
    inp.addEventListener("sync", show);
    show();
    return d;
  }
  function syncChips() {
    chips.querySelectorAll(".chip").forEach((b, i) => {
      const on = SEN[i].w.every((v, j) => state[W[j].k] === v);
      b.setAttribute("aria-pressed", on);
    });
  }
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.get("w")) h.get("w").split(",").map(Number).forEach((v, i) => { if (!isNaN(v)) state[["w_hinter", "w_own", "w_dist", "w_sege"][i]] = v; });
    if (h.get("k")) h.get("k").split(",").map(Number).forEach((v, i) => { if (!isNaN(v)) state[["core_km", "min_hinter", "min_parent"][i]] = v; });
  }
  function writeHash() {
    const w = [state.w_hinter, state.w_own, state.w_dist, state.w_sege].join(",");
    const k = [state.core_km, state.min_hinter, state.min_parent].join(",");
    history.replaceState(null, "", `#w=${w}&k=${k}`);
  }

  // ---------- harita ----------
  const geo = topojson.feature(topo, topo.objects.ilce);
  geo.features.forEach((f) => { f.id = f.properties.i; });
  const oldBorders = topojson.mesh(topo, topo.objects.ilce, (a, b) => a === b || I.il[a.properties.i] !== I.il[b.properties.i]);
  const ilceBorders = topojson.mesh(topo, topo.objects.ilce, (a, b) => a !== b);

  const map = new maplibregl.Map({
    container: "map",
    style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": css("--paper") } }] },
    bounds: [[25.6, 35.8], [44.9, 42.15]],
    fitBoundsOptions: { padding: 24 },
    minZoom: 3, maxZoom: 10,
    attributionControl: false,
    dragRotate: false, pitchWithRotate: false, touchPitch: false,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
  map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "Sınırlar: geoBoundaries · Yol: OSRM/OSM · Nüfus: TÜİK 2025" }));
  await new Promise((r) => map.on("load", r));

  map.addSource("ilce", { type: "geojson", data: geo, promoteId: "i" });
  map.addSource("ilceB", { type: "geojson", data: ilceBorders });
  map.addSource("ilB", { type: "geojson", data: emptyFC() });
  map.addSource("newB", { type: "geojson", data: emptyFC() });
  map.addSource("basin", { type: "geojson", data: pressPoints() });

  map.addLayer({ id: "fill", type: "fill", source: "ilce", paint: {
    "fill-color": ["case",
      ["boolean", ["feature-state", "sel"], false], css("--plate-hi"),
      ["boolean", ["feature-state", "nw"], false], css("--plate"),
      ["boolean", ["feature-state", "hov"], false], css("--land-edge"),
      css("--land")],
    "fill-opacity": ["case", ["boolean", ["feature-state", "nw"], false], ["case", ["boolean", ["feature-state", "ctr"], false], 1, 0.82], 1],
  } });
  map.addLayer({ id: "ilceB", type: "line", source: "ilceB", paint: { "line-color": css("--panel"), "line-width": 0.4, "line-opacity": 0.55 } });
  map.addLayer({ id: "ilB", type: "line", source: "ilB", paint: { "line-color": css("--ink"), "line-width": ["interpolate", ["linear"], ["zoom"], 4, 0.7, 8, 1.6], "line-opacity": 0.7 } });
  map.addLayer({ id: "newB", type: "line", source: "newB", layout: { "line-join": "round" }, paint: { "line-color": css("--plate"), "line-width": ["interpolate", ["linear"], ["zoom"], 4, 2, 8, 3.5] } });
  map.addLayer({ id: "basin", type: "circle", source: "basin", paint: {
    "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3.6, 8, 7], "circle-color": css("--amber"),
    "circle-stroke-color": css("--panel"), "circle-stroke-width": 1.5 } });
  $("#yukleniyor").hidden = true;

  let hov = null;
  map.on("mousemove", "fill", (e) => {
    const id = e.features[0].id;
    if (hov !== null && hov !== id) map.setFeatureState({ source: "ilce", id: hov }, { hov: false });
    hov = id; map.setFeatureState({ source: "ilce", id }, { hov: true });
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mouseleave", "fill", () => { if (hov !== null) map.setFeatureState({ source: "ilce", id: hov }, { hov: false }); hov = null; map.getCanvas().style.cursor = ""; });
  map.on("click", "fill", (e) => openCard(e.features[0].id, false));

  $("#basinGoster").addEventListener("change", (e) => {
    map.setLayoutProperty("basin", "visibility", e.target.checked ? "visible" : "none");
    $("#lejant").classList.toggle("no-press", !e.target.checked);
  });

  function emptyFC() { return { type: "FeatureCollection", features: [] }; }
  function pressPoints() {
    const f = [];
    for (let i = 0; i < D.n; i++) if (I.basin[i]) f.push({ type: "Feature", properties: { i }, geometry: { type: "Point", coordinates: [I.lon[i], I.lat[i]] } });
    return { type: "FeatureCollection", features: f };
  }

  // ---------- hesap + çizim ----------
  let res = null, plateOf = new Map(), markers = [], selected = null, raf = 0;
  function schedule() { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => { compute(); draw(); }); }

  function compute() {
    res = IlModel.run(D, state);
    const names = res.sel.map((s) => s.id).sort((a, b) => collator.compare(I.ad[a], I.ad[b]));
    plateOf = new Map(names.map((id, k) => [id, 82 + k]));
    syncChips(); writeHash();
  }

  function draw(upto) {
    const show = upto === undefined ? res.sel.length : upto;
    const visible = new Set(res.sel.slice(0, show).map((s) => s.id));
    for (let j = 0; j < D.n; j++) {
      const c = res.final[j];
      const nw = c !== null && visible.has(c);
      map.setFeatureState({ source: "ilce", id: j }, { nw, ctr: nw && c === j, sel: selected !== null && nw && c === selected });
    }
    const key = (f) => { const j = f.properties.i, c = res.final[j]; return c === null || !visible.has(c) ? "P" + I.il[j] : "N" + c; };
    map.getSource("ilB").setData(topojson.mesh(topo, topo.objects.ilce, (a, b) => a === b || key(a) !== key(b)));
    map.getSource("newB").setData(topojson.mesh(topo, topo.objects.ilce, (a, b) => a !== b && I.il[a.properties.i] === I.il[b.properties.i] && key(a) !== key(b)));
    drawMarkers(visible);
    $("#ilSayisi").textContent = 81 + visible.size;
    if (upto === undefined) { renderList(); renderCompare(); if (selected !== null) openCard(selected, true); }
  }

  function drawMarkers(visible) {
    markers.forEach((m) => m.remove()); markers = [];
    for (const s of res.sel) {
      if (!visible.has(s.id)) continue;
      const el = document.createElement("button");
      el.className = "mk"; el.type = "button"; el.setAttribute("aria-label", `${I.ad[s.id]}, plaka ${plateOf.get(s.id)}`);
      el.innerHTML = `<span class="plate"><span class="plate-tr">TR</span><span class="plate-num">${plateOf.get(s.id)}</span></span>`;
      el.addEventListener("click", (e) => { e.stopPropagation(); openCard(s.id, false); });
      const m = new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat([I.lon[s.id], I.lat[s.id]]).addTo(map);
      m._ll = [I.lon[s.id], I.lat[s.id]];
      markers.push(m);
    }
    declutter();
  }
  // üst üste binen plakaları ayır: önce yukarı/aşağı bir adım kaydır, yine sığmazsa bu yakınlıkta gizle
  function declutter() {
    const BW = 46, BH = 22, boxes = [];
    const pts = markers.map((m) => ({ m, p: map.project(m._ll) })).sort((a, b) => a.p.y - b.p.y || a.p.x - b.p.x);
    for (const { m, p } of pts) {
      const hit = (y) => boxes.some((b) => Math.abs(b.x - p.x) < BW && Math.abs(b.y - y) < BH);
      const dy = [0, BH + 2, -(BH + 2)].find((d) => !hit(p.y + d));
      const el = m.getElement();
      if (dy === undefined) { el.style.visibility = "hidden"; continue; }
      el.style.visibility = "";
      boxes.push({ x: p.x, y: p.y + dy });
      m.setOffset([0, dy]);
    }
  }
  map.on("zoomend", declutter);

  // ---------- liste ----------
  function renderList() {
    const ol = $("#liste"); ol.innerHTML = "";
    const order = res.sel.slice().sort((a, b) => plateOf.get(a.id) - plateOf.get(b.id));
    $("#secimSayisi").textContent = res.sel.length < state.n_new ? `${res.sel.length} / 19 (koşulları sağlayan aday kalmadı)` : "19 il";
    for (const s of order) {
      const r = sag.oran[s.id] || 0, li = document.createElement("li");
      li.innerHTML = `<button type="button" aria-current="${selected === s.id}">
        <span class="plate plate-sm"><span class="plate-tr">TR</span><span class="plate-num">${plateOf.get(s.id)}</span></span>
        <span class="nm">${I.ad[s.id]}${I.basin[s.id] ? '<span class="press-dot" title="Basın listesinde"></span>' : ""}</span>
        <span class="pop">${fmtK(s.hpop)}</span>
        <span class="sub">${ilAdi(s.id)} ilinden, ${s.members.length} ilçe</span>
        <span class="rob" title="Seçilme sıklığı: %${Math.round(r * 100)} (1000 senaryo)"><i style="--v:${Math.round(r * 100)}%"></i>%${Math.round(r * 100)}</span>
      </button>`;
      li.querySelector("button").addEventListener("click", () => openCard(s.id, false));
      ol.append(li);
    }
  }

  // ---------- karşılaştırma ----------
  function whyNot(j) {
    if (res.core[j]) return `${ilAdi(j)} merkezine ${fmt.format(I.mkm[j])} km; kent çekirdeği sayıldı`;
    const c = res.final[j];
    if (c !== null && c !== j) return `${I.ad[c]} iline bağlandı`;
    const f = res.firstById.get(j);
    if (!f) return `nüfusu aday eşiğinin altında`;
    if (!f.ok) {
      const parts = f.reasons.map((r) => r === "geride kalan il çok küçülüyor" ? `il olsaydı ${ilAdi(j)} ${fmtK(f.parent)} nüfusa düşerdi (eşik ${fmtK(state.min_parent)})` : r === "yeni il nüfusu yetersiz" ? `yeni il yalnızca ${fmtK(f.hpop)} kişi olurdu (eşik ${fmtK(state.min_hinter)})` : r);
      return parts.join("; ");
    }
    return `puan sıralamasında ${f.rank}. (${f.puan.toLocaleString("tr-TR")} puan)`;
  }
  function renderCompare() {
    const box = $("#karsilastirma");
    const press = []; for (let i = 0; i < D.n; i++) if (I.basin[i]) press.push(i);
    const chosen = new Set(res.sel.map((s) => s.id));
    const hit = press.filter((i) => chosen.has(i)), miss = press.filter((i) => !chosen.has(i));
    const onlyModel = res.sel.filter((s) => !I.basin[s.id]).map((s) => s.id);
    const row = (i, cls, why) => `<tr class="${cls}"><td><button type="button" data-id="${i}">${I.ad[i]}</button></td><td class="why">${why}</td></tr>`;
    box.innerHTML = `<p class="tally">${hit.length} / 19<span>ilçe iki listede ortak</span></p>
      <table><tbody>
      ${hit.sort((a, b) => collator.compare(I.ad[a], I.ad[b])).map((i) => row(i, "hit", `modelde de seçildi, plaka ${plateOf.get(i)}`)).join("")}
      ${miss.sort((a, b) => collator.compare(I.ad[a], I.ad[b])).map((i) => row(i, "miss", whyNot(i))).join("")}
      </tbody></table>
      <h3>Yalnızca modelin seçtikleri</h3>
      <p class="note">${onlyModel.sort((a, b) => collator.compare(I.ad[a], I.ad[b])).map((i) => `<button type="button" data-id="${i}">${I.ad[i]}</button>`).join(", ") || "Yok"}</p>`;
    box.querySelectorAll("button[data-id]").forEach((b) => b.addEventListener("click", () => openCard(+b.dataset.id, false)));
  }

  // ---------- kart ----------
  function openCard(j, keep) {
    const card = $("#kart");
    const isNew = res.sel.find((s) => s.id === j);
    const c = res.final[j];
    selected = isNew ? j : null;
    if (!keep) draw();
    let html = `<button class="x" type="button" aria-label="Kapat">×</button>`;
    if (isNew) {
      const s = isNew, r = Math.round((sag.oran[j] || 0) * 100);
      const others = s.members.filter((m) => m !== j).map((m) => I.ad[m]).sort(collator.compare);
      html += `<span class="plate plate-sm"><span class="plate-tr">TR</span><span class="plate-num">${plateOf.get(j)}</span></span>
        <h3>${I.ad[j]}</h3><p class="from">${ilAdi(j)} ilinden ayrılır${I.basin[j] ? ", basın listesinde de var" : ""}</p>
        <dl>
          <dt>Yeni ilin nüfusu</dt><dd>${fmt.format(s.hpop)}</dd>
          <dt>${I.ad[j]} ilçesinin nüfusu</dt><dd>${fmt.format(I.pop[j])}</dd>
          <dt>${ilAdi(j)} merkezine</dt><dd>${Math.round(I.mdk[j])} dk, ${Math.round(I.mkm[j])} km</dd>
          <dt>SEGE-2022 sırası</dt><dd>${I.segeSira[j]} / 973</dd>
          <dt>Geride kalan ${ilAdi(j)}</dt><dd>${fmt.format(s.parent)}</dd>
          <dt>Model puanı</dt><dd>${s.puan.toLocaleString("tr-TR")}</dd>
          <dt>1000 senaryoda seçilme</dt><dd>%${r}</dd>
        </dl>
        <p class="members"><b>Bağlanan ilçeler:</b> ${others.length ? others.join(", ") : "yalnızca kendisi"}</p>`;
    } else {
      const newIl = c === null ? ilAdi(j) : I.ad[c];
      html += `<h3>${I.ad[j]}</h3><p class="from">${ilAdi(j)} ilçesi. 100 ilde bağlı olacağı il: <b>${newIl}</b>${c !== null ? ` (plaka ${plateOf.get(c)})` : ""}</p>
        <dl>
          <dt>Nüfus (2025)</dt><dd>${fmt.format(I.pop[j])}</dd>
          <dt>${ilAdi(j)} merkezine</dt><dd>${Math.round(I.mdk[j])} dk, ${Math.round(I.mkm[j])} km</dd>
          <dt>SEGE-2022 sırası</dt><dd>${I.segeSira[j]} / 973</dd>
        </dl>
        <p class="verdict">${I.basin[j] ? "Basın listesinde var. " : ""}Neden il olmadı: ${whyNot(j)}.</p>`;
    }
    card.innerHTML = html; card.hidden = false;
    card.querySelector(".x").addEventListener("click", closeCard);
    document.querySelectorAll(".plates button").forEach((b) => b.setAttribute("aria-current", "false"));
  }
  function closeCard() { $("#kart").hidden = true; selected = null; draw(); }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#kart").hidden) closeCard(); });

  // ---------- açılış: 81'den 100'e ----------
  compute();
  if (reduced) draw();
  else {
    let k = 0; draw(0);
    const tick = () => { k++; if (k < res.sel.length) { draw(k); setTimeout(tick, 110); } else draw(); };
    setTimeout(tick, 500);
  }
})();
