"""100 İl — verileri PostGIS'e yükler ve SQL fonksiyonlarını kurar (QGIS Python konsolunda çalışır).

Kullanım (QGIS > Eklentiler > Python Konsolu):
    exec(open(r"C:/.../100-il/scripts/10_postgis_yukle.py", encoding="utf-8").read())

QGIS'te kayıtlı PostgreSQL bağlantısını kullanır (şifre QGIS'te saklı kalır, betik görmez).
Sıra: sql/01_sema.sql → ilçe poligonları + tablolar → sql/03_cekirdek.sql → sql/04_model.sql
"""
import csv
import json
import os
from qgis.core import QgsProviderRegistry, QgsVectorLayer

BAGLANTI = globals().get("BAGLANTI", "postgres_local ")   # QGIS'teki bağlantı adı
KOK = globals().get("KOK") or os.path.dirname(os.path.dirname(os.path.abspath(globals().get("__file__", "."))))
P = os.path.join(KOK, "data", "processed")
RAW = os.path.join(KOK, "data", "raw")
SQL = os.path.join(KOK, "sql")

conn = QgsProviderRegistry.instance().providerMetadata("postgres").connections()[BAGLANTI]
run = conn.executeSql


def q(v):
    """SQL değişmezi"""
    if v is None or v == "" or (isinstance(v, float) and v != v):
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def toplu(tablo, kolonlar, satirlar, n=500):
    for k in range(0, len(satirlar), n):
        run(f"INSERT INTO {tablo} ({', '.join(kolonlar)}) VALUES " + ",".join(satirlar[k:k + n]))


def oku(ad):
    with open(os.path.join(P, ad), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def yukle(log=print):
    run(open(os.path.join(SQL, "01_sema.sql"), encoding="utf-8").read())
    log("şema kuruldu")

    # ilçeler: geoBoundaries poligonları + öznitelikler (data/processed/ilceler.gpkg)
    lyr = QgsVectorLayer(os.path.join(P, "ilceler.gpkg"), "ilceler", "ogr")
    rows = []
    for f in lyr.getFeatures():
        a = f.attributes(); g = {fl.name(): a[i] for i, fl in enumerate(lyr.fields())}
        wkb = bytes(f.geometry().asWkb()).hex()
        rows.append("(" + ",".join([
            q(int(g["id"])), q(g["il"]), q(g["ilce"]), q(g["bolge"]), q(int(g["nufus2025"])), q(float(g["alan_km2"])),
            q(float(g["il_merkez_dk"])), q(float(g["il_merkez_km"])), q(float(g["sege_skor"])), q(int(g["sege_sira"])), q(g["gbid"]),
            f"ST_SetSRID(ST_MakePoint({float(g['lon'])},{float(g['lat'])}),4326)",
            f"ST_Multi(ST_SetSRID(ST_GeomFromWKB(decode('{wkb}','hex')),4326))"]) + ")")
    toplu("yuz_il.ilce", ["id", "il", "ilce", "bolge", "nufus", "alan_km2", "il_merkez_dk", "il_merkez_km",
                          "sege_skor", "sege_sira", "gbid", "merkez", "geom"], rows, 40)
    log(f"ilçe: {len(rows)}")

    m = oku("il_ici_matris.csv")
    toplu("yuz_il.yol_sure", ["kaynak_id", "hedef_id", "dk", "km"],
          [f"({int(r['kaynak_id'])},{int(r['hedef_id'])},{r['dk'] or 'NULL'},{r['km'] or 'NULL'})" for r in m])
    log(f"yol süresi: {len(m)} çift")

    mc = oku("il_merkezleri.csv")
    toplu("yuz_il.il_merkezi", ["il", "kaynak", "geom"],
          [f"({q(r['il'])},{q(r['kaynak'])},ST_SetSRID(ST_MakePoint({r['merkez_lon']},{r['merkez_lat']}),4326))" for r in mc])
    log(f"il merkezi: {len(mc)}")

    bel = oku("belediye_eslesme.csv")
    toplu("yuz_il.belediye", ["id", "ad", "tur", "kaynak", "geom"],
          [f"({int(r['id'])},{q(r['bel_ad'])},{q(r['bel_tur'])},{q(r.get('bel_kaynak'))},"
           f"ST_SetSRID(ST_MakePoint({r['bel_lon']},{r['bel_lat']}),4326))" for r in bel])
    log(f"belediye: {len(bel)}")

    # OSM ham kayıtları (data/raw gitignore'da; yoksa atlanır)
    osm = {}
    for ad in ["osm_townhall.json", "osm_belediye_ad.json"]:
        p = os.path.join(RAW, ad)
        if not os.path.exists(p):
            continue
        for e in json.load(open(p, encoding="utf-8"))["elements"]:
            c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
            if c.get("lat") is None:
                continue
            t = e.get("tags", {}); k = f"{e['type']}/{e['id']}"
            if k not in osm or t.get("amenity") == "townhall":
                osm[k] = f"({q(k)},{q(t.get('name'))},{str(t.get('amenity') == 'townhall').lower()},{q(t.get('townhall:type'))}," \
                         f"ST_SetSRID(ST_MakePoint({c['lon']},{c['lat']}),4326))"
    if osm:
        toplu("yuz_il.osm_belediye", ["osm", "ad", "townhall", "tip", "geom"], list(osm.values()))
    log(f"OSM belediye kaydı: {len(osm)}")

    for ad in ["03_cekirdek.sql", "04_model.sql"]:
        run(open(os.path.join(SQL, ad), encoding="utf-8").read())
    run("ANALYZE yuz_il.ilce; ANALYZE yuz_il.yol_sure;")
    log("fonksiyonlar kuruldu")


if __name__ in ("__main__", "__console__", "builtins"):
    yukle()
