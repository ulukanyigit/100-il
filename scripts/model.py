"""100 İl — veriye dayalı il adayı modeli (referans uygulama; web sürümü aynı mantığı JS'de çalıştırır).

Girdi : ilce_tablo.csv  (TÜİK 2025 nüfus, SEGE-2022, ilçe merkezi, il merkezine OSRM süresi, alan)
        il_ici_matris.csv (il içi ilçe→ilçe OSRM sürüş süreleri, dk)
Çıktı : adaylar.csv (ilk tur: her aday tek başına il olsaydı), secim.csv (seçilen yeni iller),
        atama.csv (973 ilçenin 100 ilde bağlı olacağı il)

Mantık
1. Kent çekirdeği: il merkezine ≤ core_km (yol km) olan ilçeler + kesintisiz kent dokusu (yoğunluk ≥ chain_density
   ve çekirdekteki bir ilçeye ≤ chain_link dk). Çekirdek ilçeler aday olamaz, ana ilde kalır.
2. Atama: çekirdek dışındaki her ilçe, ilindeki merkezlerden (mevcut il merkezi + seçilen yeni merkezler)
   sürüş süresi en kısa olana bağlanır.
3. Puan: hinterland nüfusu, kendi nüfusu, il merkezine uzaklık, SEGE-2022 — ağırlıklı, 0–100.
4. Seçim: her turda, eklendiğinde tüm koşulları sağlayan en yüksek puanlı aday yeni il olur; ilçeler yeniden
   dağıtılır. Koşullar: yeni il ≥ min_hinter, geride kalan il ≥ min_parent, önceki yeni iller ≥ min_hinter.
5. İsteğe bağlı denge kuralları (varsayılan kapalı): il_max = bir ilden en fazla kaç yeni il çıkabileceği;
   kota = önce her coğrafi bölgeden en az kaç yeni il seçileceği (kalan koltuklar puan sırasıyla).
"""
import math
import pandas as pd

DEFAULTS = dict(
    w_hinter=35, w_own=20, w_dist=25, w_sege=20,
    core_km=30, chain_density=500, chain_link=20,
    min_own=40_000, min_hinter=150_000, min_parent=250_000,
    il_max=0, kota=0,  # il_max: bir ilden en fazla kaç yeni il (0 = sınırsız); kota: her bölgeden en az kaç yeni il
    n_new=19,
)

# basında yer alan aday listesi (gzt.com, 2 Kasım 2026) — resmî liste değil
PRESS_LIST = [("Antalya", "Alanya"), ("Antalya", "Manavgat"), ("Balıkesir", "Bandırma"),
              ("Balıkesir", "Edremit"), ("Muğla", "Fethiye"), ("Aydın", "Nazilli"),
              ("Ankara", "Polatlı"), ("Tekirdağ", "Çorlu"), ("Kırklareli", "Lüleburgaz"),
              ("Hatay", "İskenderun"), ("Ordu", "Ünye"), ("Kahramanmaraş", "Elbistan"),
              ("Şanlıurfa", "Siverek"), ("Adıyaman", "Kâhta"), ("Diyarbakır", "Ergani"),
              ("Mardin", "Midyat"), ("Şırnak", "Cizre"), ("Van", "Erciş"), ("Hakkâri", "Yüksekova")]


# coğrafi bölgeler (ilce_tablo.csv 'bolge' kodu → ad); sıra web sürümüyle aynı
BOLGE_AD = {"MB": "Marmara", "EB": "Ege", "AB": "Akdeniz", "İAB": "İç Anadolu", "KB": "Karadeniz",
            "DAB": "Doğu Anadolu", "GAB": "Güneydoğu Anadolu"}
BOLGELER = list(BOLGE_AD.values())


def lin(x, a, b):
    return max(0.0, min(1.0, (x - a) / (b - a)))


def loglin(x, a, b):
    return lin(math.log10(max(x, 1)), math.log10(a), math.log10(b))


class Model:
    def __init__(self, t: pd.DataFrame, mat: pd.DataFrame, **kw):
        self.p = p = {**DEFAULTS, **kw}
        self.t = t = t.set_index("id")
        self.dk = {(a, b): (d if pd.notna(d) else 1e9)
                   for a, b, d in mat[["kaynak_id", "hedef_id", "dk"]].itertuples(index=False)}
        core = (t.il_merkez_km <= p["core_km"]).copy()
        dens = t.nufus2025 / t.alan_km2
        grew = True
        while grew:
            grew = False
            for j in t.index[~core & (dens >= p["chain_density"])]:
                same = t.index[core & (t.il == t.at[j, "il"])]
                if any(self.dk.get((j, k), 1e9) <= p["chain_link"] for k in same):
                    core[j] = True
                    grew = True
        self.core = core
        self.by_il = {il: list(g.index) for il, g in t.groupby("il")}
        self.pop = t.nufus2025.to_dict()
        self.bolge = {i: BOLGELER.index(BOLGE_AD[b]) for i, b in t.bolge.items()} if "bolge" in t else {i: 0 for i in t.index}

    def t_to(self, j, center):
        """center: None = mevcut il merkezi, int = yeni il merkezi ilçe id"""
        if center is None:
            return 0.0 if self.core[j] else self.t.at[j, "il_merkez_dk"]
        return 0.0 if j == center else self.dk.get((j, center), 1e9)

    def assign_il(self, il, centers):
        """centers: bu ildeki yeni merkez id'leri → {ilçe: merkez(None|id)}"""
        out = {}
        for j in self.by_il[il]:
            if self.core[j]:
                out[j] = None
            elif j in centers:
                out[j] = j
            else:
                out[j] = min([None] + list(centers), key=lambda c: (self.t_to(j, c), c is not None))
        return out

    def score(self, c, hpop):
        p, t = self.p, self.t
        comp = dict(s_hinter=loglin(hpop, 80_000, 1_000_000),
                    s_own=loglin(self.pop[c], 30_000, 600_000),
                    s_dist=lin(t.at[c, "il_merkez_dk"], 30, 180),
                    s_sege=lin(t.at[c, "sege_skor"], -1.5, 2.5))
        W = p["w_hinter"] + p["w_own"] + p["w_dist"] + p["w_sege"]
        s = 100 * (p["w_hinter"] * comp["s_hinter"] + p["w_own"] * comp["s_own"]
                   + p["w_dist"] * comp["s_dist"] + p["w_sege"] * comp["s_sege"]) / W
        return s, comp

    def try_add(self, c, chosen):
        """c'yi eklemeyi dene → (kayıt, atama) ; kayıt['uygun'] koşulları gösterir"""
        il = self.t.at[c, "il"]
        centers = [x for x in chosen if self.t.at[x, "il"] == il] + [c]
        a = self.assign_il(il, centers)
        grp = {}
        for j, cc in a.items():
            grp.setdefault(cc, []).append(j)
        hpop = sum(self.pop[j] for j in grp[c])
        parent = sum(self.pop[j] for j in grp.get(None, []))
        others_ok = all(sum(self.pop[j] for j in grp.get(x, [])) >= self.p["min_hinter"]
                        for x in centers if x != c)
        s, comp = self.score(c, hpop)
        reason = []
        if hpop < self.p["min_hinter"]:
            reason.append("yeni il nüfusu yetersiz")
        if parent < self.p["min_parent"]:
            reason.append("geride kalan il çok küçülüyor")
        if not others_ok:
            reason.append("komşu yeni ili eşiğin altına düşürüyor")
        if self.p["il_max"] > 0 and len(centers) - 1 >= self.p["il_max"]:
            reason.append("ilinden zaten yeni il çıktı")
        t = self.t
        rec = dict(id=c, il=il, ilce=t.at[c, "ilce"], nufus=int(self.pop[c]),
                   il_merkez_dk=t.at[c, "il_merkez_dk"], sege=t.at[c, "sege_skor"],
                   hinter_nufus=int(hpop), hinter_ilce=len(grp[c]),
                   hinter_liste=", ".join(t.at[j, "ilce"] for j in grp[c] if j != c),
                   parent_kalan=int(parent), parent_toplam=int(sum(self.pop[j] for j in self.by_il[il])),
                   uygun=not reason, neden="; ".join(reason), puan=round(s, 1),
                   **{k: round(v, 3) for k, v in comp.items()})
        return rec, a

    def run(self):
        p, t = self.p, self.t
        cands = [i for i in t.index if not self.core[i] and self.pop[i] >= p["min_own"]]
        first = pd.DataFrame([self.try_add(c, [])[0] for c in cands]).sort_values("puan", ascending=False)
        chosen, recs = [], []

        def pick(pool):
            best = None
            for c in pool:
                if c in chosen:
                    continue
                r, a = self.try_add(c, chosen)
                if r["uygun"] and (best is None or r["puan"] > best[0]["puan"]):
                    best = (r, a)
            return best

        # bölge kotası: önce her bölgeden en iyi uygun aday (tur tur), sonra kalan koltuklar puan sırasıyla
        for _ in range(p["kota"]):
            for b in range(len(BOLGELER)):
                if len(chosen) >= p["n_new"]:
                    break
                best = pick([c for c in cands if self.bolge[c] == b])
                if best:
                    chosen.append(best[0]["id"])
                    recs.append(best[0])
        while len(chosen) < p["n_new"]:
            best = pick(cands)
            if best is None:
                break
            chosen.append(best[0]["id"])
            recs.append(best[0])
        # son durum: tüm yeni illerin nihai hinterlandını yeniden hesapla
        final = {}
        for il in self.by_il:
            final.update(self.assign_il(il, [x for x in chosen if t.at[x, "il"] == il]))
        sel = []
        for k, c in enumerate(chosen, 1):
            mem = [j for j, cc in final.items() if cc == c]
            il = t.at[c, "il"]
            hpop = sum(self.pop[j] for j in mem)
            s, comp = self.score(c, hpop)
            sel.append(dict(sira=k, id=c, il=il, ilce=t.at[c, "ilce"], nufus=int(self.pop[c]),
                            il_merkez_dk=t.at[c, "il_merkez_dk"], sege=t.at[c, "sege_skor"],
                            hinter_nufus=int(hpop), hinter_ilce=len(mem),
                            hinter_liste=", ".join(t.at[j, "ilce"] for j in mem if j != c),
                            parent_kalan=int(sum(self.pop[j] for j, cc in final.items()
                                                 if cc is None and t.at[j, "il"] == il)),
                            puan=round(s, 1), **{q: round(v, 3) for q, v in comp.items()}))
        out = t[["il", "ilce", "nufus2025"]].copy()
        out["cekirdek"] = self.core
        out["yeni_il"] = [t.at[i, "il"] if final[i] is None else t.at[final[i], "ilce"] for i in t.index]
        out["yeni_mi"] = [final[i] is not None for i in t.index]
        press = set(PRESS_LIST)
        first["basin_listesi"] = [(r.il, r.ilce) in press for r in first.itertuples()]
        sel = pd.DataFrame(sel)
        sel["basin_listesi"] = [(r.il, r.ilce) in press for r in sel.itertuples()]
        return first, sel, out.reset_index()


if __name__ == "__main__":
    t = pd.read_csv("ilce_tablo.csv")
    mat = pd.read_csv("il_ici_matris.csv")
    first, sel, out = Model(t, mat).run()
    first.to_csv("adaylar.csv", index=False)
    sel.to_csv("secim.csv", index=False)
    out.to_csv("atama.csv", index=False)
    pd.set_option("display.width", 250)
    print(sel[["sira", "il", "ilce", "nufus", "hinter_nufus", "hinter_ilce", "il_merkez_dk", "sege",
               "parent_kalan", "puan", "basin_listesi"]].to_string(index=False))
    print("basın listesiyle örtüşen:", int(sel.basin_listesi.sum()), "/ 19")
