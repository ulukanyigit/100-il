"""100 İl — SEGE eşleştirme, ilçe poligonlarına bağlama, alan hesabı.
Girdi : ilce_nufus_2025.csv (01), sege2022.csv (01.sege_ayristir), gb_ADM1/ADM2.geojson
Çıktı : ilce_tablo.csv, ilceler.gpkg
"""
import unicodedata
import pandas as pd
import geopandas as gpd


def norm(x):
    x = str(x).replace("İ", "i").replace("I", "ı").lower()
    x = x.replace("ı", "i").replace("â", "a").replace("î", "i").replace("û", "u")
    x = "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    return x.replace(" ", "").replace("-", "").replace("'", "")


n = pd.read_csv("ilce_nufus_2025.csv")
s = pd.read_csv("sege2022.csv")
s["il_k"] = s.il.map(norm)
s["ilce_k"] = s.apply(lambda r: norm(r.il) if r.ilce == "Merkez" else norm(r.ilce), axis=1)
s.loc[(s.ilce_k == "eregli") & (s.il_k == "zonguldak"), "ilce_k"] = "karadenizeregli"
s.loc[s.ilce_k == "ondokuzmayis", "ilce_k"] = "19mayis"
n["il_k"], n["ilce_k"] = n.il.map(norm), n.ilce.map(norm)
n = n.merge(s[["il_k", "ilce_k", "sira", "skor"]].rename(columns={"sira": "sege_sira", "skor": "sege_skor"}),
            on=["il_k", "ilce_k"], how="left")
assert n.sege_skor.notna().all()

a2 = gpd.read_file("gb_ADM2.geojson")[["shapeName", "geometry"]]
a1 = gpd.read_file("gb_ADM1.geojson")[["shapeName", "geometry"]].rename(columns={"shapeName": "il_gb"})
rp = a2.copy()
rp["geometry"] = a2.geometry.representative_point()
a2["il_gb"] = gpd.sjoin(rp, a1, predicate="within", how="left")["il_gb"].values
a2["il_k"], a2["ilce_k"], a2["gbid"] = a2.il_gb.map(norm), a2.shapeName.map(norm), range(len(a2))

m = n.merge(a2[["il_k", "ilce_k", "gbid"]], on=["il_k", "ilce_k"], how="left")
um = m.gbid.isna()  # "X merkez", "Imbros", "Prince Islands" vb. → ilçe merkezi noktası hangi poligondaysa
pts = gpd.GeoDataFrame(m[um], geometry=gpd.points_from_xy(m[um].lon, m[um].lat), crs=4326)
m.loc[um, "gbid"] = gpd.sjoin(pts, a2[["gbid", "geometry"]].rename(columns={"gbid": "g2"}),
                              predicate="within", how="left")["g2"].values
assert m.gbid.notna().all() and not m.gbid.duplicated().any()
m["gbid"] = m.gbid.astype(int)
m["id"] = range(len(m))
g = a2[["gbid", "geometry"]].merge(m.drop(columns=["il_k", "ilce_k"]), on="gbid")
g["alan_km2"] = (g.to_crs(6933).area / 1e6).round(1)
g.to_file("ilceler.gpkg", layer="ilceler", driver="GPKG")
m.drop(columns=["il_k", "ilce_k"]).assign(alan_km2=g.set_index("id").alan_km2.reindex(m.id).values) \
    .to_csv("ilce_tablo.csv", index=False)
