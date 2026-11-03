"""100 İl — PostGIS modeli ile Python modelini karşılaştırır (QGIS Python konsolunda çalışır).

sql/beklenen_python.json: scripts/model.py'nin 6 ayardaki çıktısı (id, yeni il nüfusu, geride kalan il nüfusu, puan).
Her ayar için yuz_il.calistir(...) çalıştırılır ve 19 ilin sırası, nüfusları ve puanları birebir karşılaştırılır.
"""
import json
import os
import time
from qgis.core import QgsProviderRegistry

BAGLANTI = globals().get("BAGLANTI", "postgres_local ")
KOK = globals().get("KOK") or os.path.dirname(os.path.dirname(os.path.abspath(globals().get("__file__", "."))))
conn = QgsProviderRegistry.instance().providerMetadata("postgres").connections()[BAGLANTI]

beklenen = json.load(open(os.path.join(KOK, "sql", "beklenen_python.json"), encoding="utf-8"))
hata = 0
for b in beklenen:
    args = ", ".join(f"{k} => {v}" for k, v in b["cfg"].items())
    t0 = time.time()
    r = conn.executeSql(f"SELECT id, hinter_nufus, parent_kalan, puan FROM yuz_il.calistir({args}) ORDER BY sira")
    sql = [[int(a), int(h), int(p), float(s)] for a, h, p, s in r]
    ok = sql == b["sel"]
    hata += not ok
    print(f"{'AYNI  ' if ok else 'FARKLI'} {time.time() - t0:4.1f} sn  {b['cfg'] or 'varsayılan'}")
n = conn.executeSql("SELECT count(*) FROM yuz_il.cekirdek()")[0][0]
print(f"kent çekirdeği: {n} ilçe (Python: {beklenen[0]['cekirdek']})")
conn.executeSql("SELECT count(*) FROM yuz_il.calistir()")  # tabloları varsayılan sonuçla bırak
print("sonuç:", "tüm ayarlar aynı" if hata == 0 else f"{hata} ayarda fark var")
