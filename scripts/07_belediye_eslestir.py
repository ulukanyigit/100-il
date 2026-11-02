"""100 İl — ilçe belediye binası konumları (yeni il merkezi olarak gösterilir).

Kaynak: OpenStreetMap (Overpass)
  osm_townhall.json   : amenity=townhall kayıtları
  osm_belediye_ad.json: adı "...Belediyesi / Belediye Başkanlığı / Binası / Sarayı / Hizmet Binası" olan tüm kayıtlar
Eşleştirme (her ilçe için, ilçe poligonu + 1 km tampon içinde):
  1) ad "<ilçe> belediye..." ile başlamalı, "büyükşehir" içermemeli
  2) öncelik: tam ana ad (Belediyesi / Belediye Başkanlığı / Belediye Binası / Belediye Sarayı)
     > ana hizmet binası > merkeze ≤2 km genel ad ("Belediye Binası") > merkeze ≤3 km "ek hizmet binası";
     spor salonu, barınak, nikah salonu gibi ek tesisler elenir
  2b) Nominatim ile eksik adaylar için ikinci arama (nominatim_belediye.json; bu sürümde ek kayıt bulamadı)
  3) eşitlikte amenity=townhall etiketi, sonra ilçe merkezine yakınlık
  4) hiçbiri yoksa: ilçe merkezine ≤3 km, adsız ve townhall:type belediye türünde kayıt
  5) o da yoksa ilçe merkezi koordinatı (bel_tur = "yok")
Çıktı: belediye_eslesme.csv
"""
import json
import unicodedata
import pandas as pd
import geopandas as gpd


def norm(x):
    x = str(x).replace("İ", "i").replace("I", "ı").lower()
    x = x.replace("ı", "i").replace("â", "a").replace("î", "i").replace("û", "u")
    x = "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))
    return "".join(ch for ch in x if ch.isalnum())


def load(path, kaynak):
    rows = []
    for e in json.load(open(path, encoding="utf-8"))["elements"]:
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if c["lat"] is None:
            continue
        t = e.get("tags", {})
        rows.append(dict(osm=f"{e['type']}/{e['id']}", lat=c["lat"], lon=c["lon"], name=t.get("name", ""),
                         ttype=t.get("townhall:type", ""), townhall=t.get("amenity") == "townhall", kaynak=kaynak))
    return rows


rows = load("osm_townhall.json", "townhall") + load("osm_belediye_ad.json", "ad")
th = pd.DataFrame(rows).sort_values("townhall", ascending=False).drop_duplicates("osm")
th = gpd.GeoDataFrame(th, geometry=gpd.points_from_xy(th.lon, th.lat), crs=4326).to_crs(5254)
th["nn"] = th.name.map(norm)

g = gpd.read_file("ilceler.gpkg")[["id", "il", "ilce", "geometry"]]
t = pd.read_csv("ilce_tablo.csv")[["id", "lat", "lon"]]
g = g.merge(t, on="id").to_crs(5254)
ALIAS = {"Karadeniz Ereğli": ["karadenizeregli", "eregli"], "19 Mayıs": ["ondokuzmayis", "19mayis"]}
MAIN = ["belediyesi", "belediyebaskanligi", "belediyebinasi", "belediyesarayi", "belediyesibaskanligi",
        "belediyesibinasi", "belediyesianahizmetbinasi", "belediyesihizmetbinasi", "belediyehizmetbinasi"]
GENERIC = {"belediye", "belediyebinasi", "belediyebaskanligi", "belediyesarayi", "belediyehizmetbinasi"}


def rank(nn, keys, d):
    """0 = ana bina adı, 1 = ana hizmet binası, 2 = merkeze ≤2 km genel ad; ek tesisler elenir (None)"""
    if "buyuksehir" in nn or "belediye" not in nn:
        return None
    if nn.startswith("tc"):
        nn = nn[2:]
    k = next((k for k in keys if nn.startswith(k)), None)
    if k is not None:
        rest = nn[len(k):]
        if rest in MAIN[:6]:
            return 0
        if rest in MAIN[6:]:
            return 1
        if rest.endswith("hizmetbinasi") and d <= 3000:
            return 3  # ana bina OSM'de yoksa: merkeze ≤3 km "ek hizmet binası" (idari bina)
        return None  # spor salonu, barınak, nikah salonu vb.
    if nn in GENERIC and d <= 2000:
        return 2
    return None


out = []
for r in g.itertuples():
    keys = ALIAS.get(r.ilce, [norm(r.ilce)])
    cpt = gpd.GeoSeries(gpd.points_from_xy([r.lon], [r.lat]), crs=4326).to_crs(5254).iloc[0]
    inside = th[th.within(r.geometry.buffer(1000))].copy()
    inside["d"] = inside.distance(cpt)
    inside["rk"] = [rank(n, keys, d) for n, d in zip(inside.nn, inside.d)]
    m = inside[inside.rk.notna()].sort_values(["rk", "townhall", "d"], ascending=[True, False, True])
    tur = "ad"
    if not len(m):
        m = inside[(inside.d < 3000) & inside.townhall & ~inside.nn.str.contains("muhtar|koy|mahalle|buyuksehir")]
        m = m[(m.name == "") | m.ttype.isin(["city", "town", "municipality", "district"])].sort_values("d")
        tur = "isimsiz"
    if len(m):
        b = m.iloc[0]
        ll = gpd.GeoSeries([b.geometry], crs=5254).to_crs(4326).iloc[0]
        out.append(dict(id=r.id, il=r.il, ilce=r.ilce, bel_lat=round(ll.y, 6), bel_lon=round(ll.x, 6),
                        bel_ad=b["name"] or f"{r.ilce} Belediyesi", bel_osm=b.osm,
                        bel_tur=tur if tur == "isimsiz" else {0: "ad", 1: "hizmet-binasi", 2: "genel-ad", 3: "ek-bina"}[int(b.rk)], mesafe_m=int(b.d)))
    else:
        out.append(dict(id=r.id, il=r.il, ilce=r.ilce, bel_lat=r.lat, bel_lon=r.lon, bel_ad=None, bel_osm=None,
                        bel_tur="yok", mesafe_m=0))
o = pd.DataFrame(out)
o.to_csv("belediye_eslesme.csv", index=False)
print(o.bel_tur.value_counts().to_dict())

# --- 2. tur: Nominatim (OSM arama servisi; büyük-küçük harf duyarsız) ile eksik adaylar ---------------
# nominatim_belediye.json: {ilce_id: [sonuçlar]} ; yalnızca ilçe poligonu içinde ve adı ana bina olan kayıtlar
import os
if os.path.exists("nominatim_belediye.json"):
    nres = json.load(open("nominatim_belediye.json", encoding="utf-8"))
    polys = g.set_index("id").geometry
    o = o.set_index("id")
    eklenen = 0
    for sid, lst in nres.items():
        i = int(sid)
        if o.at[i, "bel_tur"] == "ad":
            continue
        keys = ALIAS.get(o.at[i, "ilce"], [norm(o.at[i, "ilce"])])
        cpt = gpd.GeoSeries(gpd.points_from_xy([t.set_index("id").at[i, "lon"]], [t.set_index("id").at[i, "lat"]]), crs=4326).to_crs(5254).iloc[0]
        best = None
        for r in lst:
            nm = r.get("name") or r.get("display_name", "").split(",")[0]
            p = gpd.GeoSeries(gpd.points_from_xy([float(r["lon"])], [float(r["lat"])]), crs=4326).to_crs(5254).iloc[0]
            if not polys[i].buffer(1000).contains(p):
                continue
            d = p.distance(cpt)
            rk = rank(norm(nm), keys, d)
            if rk is None or rk >= 2:
                continue
            cand = (rk, d, nm, float(r["lat"]), float(r["lon"]), f"{r['osm_type']}/{r['osm_id']}")
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best:
            o.loc[i, ["bel_lat", "bel_lon", "bel_ad", "bel_osm", "bel_tur", "mesafe_m"]] = [round(best[3], 6), round(best[4], 6), best[2], best[5], "nominatim", int(best[1])]
            eklenen += 1
    o = o.reset_index()
    o.to_csv("belediye_eslesme.csv", index=False)
    print("Nominatim ile eklenen:", eklenen, o.bel_tur.value_counts().to_dict())
