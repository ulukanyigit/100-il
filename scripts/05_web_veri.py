"""100 İl — web uygulamasının veri paketini (web/data/veri.json) ve sonuç katmanlarını üretir."""
import json
import pandas as pd
import geopandas as gpd
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # model.py aynı klasörde
from model import PRESS_LIST

t = pd.read_csv("ilce_tablo.csv").sort_values("id")
m = pd.read_csv("il_ici_matris.csv")
press = set(PRESS_LIST)
assert all(((t.il == a) & (t.ilce == b)).any() for a, b in press)
tr_key = lambda s: s.replace("Ç", "Cz").replace("İ", "Iz").replace("Ş", "Sz").replace("Ö", "Oz").replace("Ü", "Uz")
il_list = sorted(t.il.unique(), key=tr_key)
il_idx = {il: i for i, il in enumerate(il_list)}
ilce = [[int(r.id), il_idx[r.il], r.ilce, int(r.nufus2025), round(float(r.il_merkez_dk), 1),
         round(float(r.il_merkez_km), 1), round(float(r.sege_skor), 3), int(r.sege_sira),
         round(float(r.alan_km2), 1), round(float(r.lat), 4), round(float(r.lon), 4),
         1 if (r.il, r.ilce) in press else 0] for r in t.itertuples()]
dk = {(a, b): d for a, b, d in m[["kaynak_id", "hedef_id", "dk"]].itertuples(index=False)}
mat = {}
for il, g in t.groupby("il"):
    ids = g.id.tolist()
    mat[il_idx[il]] = {"ids": ids, "dk": [[0 if a == b else (None if pd.isna(dk.get((a, b))) else dk[(a, b)])
                                          for b in ids] for a in ids]}
# yeni il merkezi adayları: ilçe belediye binası (07_belediye_eslestir.py); mevcut il merkezleri
TUR = {"ad": 1, "hizmet-binasi": 1, "genel-ad": 2, "isimsiz": 2, "ek-bina": 2, "nominatim": 1, "yok": 0}
bel = pd.read_csv("belediye_eslesme.csv").set_index("id").reindex(t.id)
belediye = [[round(float(r.bel_lat), 6), round(float(r.bel_lon), 6), (r.bel_ad if isinstance(r.bel_ad, str) else None),
             (r.bel_osm if isinstance(r.bel_osm, str) else None), TUR[r.bel_tur]] for r in bel.itertuples()]
mc = pd.read_csv("il_merkezleri.csv").set_index("il")
il_merkez = [[round(float(mc.at[il, "merkez_lat"]), 5), round(float(mc.at[il, "merkez_lon"]), 5)] for il in il_list]
out = {"meta": {"olusturma": "2026-11-02", "nufus": "TÜİK ADNKS 2025", "sege": "SEGE-2022", "yol": "OSRM (trafiksiz)"},
       "iller": il_list,
       "alanlar": ["id", "il", "ilce", "nufus", "merkez_dk", "merkez_km", "sege", "sege_sira", "alan", "lat", "lon", "basin"],
       "ilceler": ilce, "matris": mat,
       "belediye_alanlar": ["lat", "lon", "ad", "osm", "kesinlik(1=OSM belediye binası, 2=OSM yakın kayıt, 0=yok: ilçe merkezi)"],
       "belediye": belediye, "il_merkez": il_merkez}
open("../../docs/data/veri.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))


def katmanlar():
    g = gpd.read_file("ilceler.gpkg")[["id", "geometry"]].merge(t, on="id")
    a = pd.read_csv("atama.csv")
    s = pd.read_csv("secim.csv")
    sag = json.load(open("../../docs/data/saglamlik.json"))["oran"]
    plaka = {n: 82 + i for i, n in enumerate(sorted(s.ilce.tolist(), key=tr_key))}
    g = g.merge(a[["id", "cekirdek", "yeni_il", "yeni_mi"]], on="id")
    g["plaka_yeni"] = g.yeni_il.map(plaka)
    g["saglamlik"] = g.id.astype(str).map(sag).fillna(0)
    g.to_file("ilceler.gpkg", layer="ilceler", driver="GPKG")
    d = g.dissolve(by="yeni_il", aggfunc={"nufus2025": "sum", "yeni_mi": "max", "il": "first", "id": "count"}) \
        .reset_index().rename(columns={"id": "ilce_sayisi", "il": "ana_il"})
    d["plaka"] = d.yeni_il.map(plaka)
    d["durum"] = d.yeni_mi.map({True: "yeni il", False: "mevcut il"})
    d.drop(columns=["yeni_mi"]).to_file("iller_100.gpkg", layer="iller_100", driver="GPKG")
    s["plaka"] = s.ilce.map(plaka)
    s["saglamlik"] = s.id.astype(str).map(sag)
    s.to_csv("secim.csv", index=False)
    assert len(d) == 100 and d.nufus2025.sum() == t.nufus2025.sum()


if __name__ == "__main__":
    import sys
    if "katman" in sys.argv:
        katmanlar()
    print("ok")
