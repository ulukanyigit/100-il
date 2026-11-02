# 100 İl — Vikipedi tablosunda hatalı olan 8 ilçe merkezi koordinatının düzeltilmesi sonrası
# etkilenen illerin OSRM sürelerini (il merkezine + il içi matris) yeniden hesaplar.
# Kontrol: 973 ilçe merkezinin kendi ilçe poligonunda olup olmadığı test edildi; dışarıda kalan 8 ilçe:
# Çaldıran, Selendi, Kale (Denizli), Kartepe, Defne, Yüksekova, Bağcılar, Gerede — hepsi tablo kaynaklı.
import json, time, urllib.request, os
import pandas as pd

D = r"C:\Users\yigit\Desktop\100-il\data\processed"
ILLER = ["Van", "Manisa", "Denizli", "Kocaeli", "Hatay", "Hakkâri", "İstanbul", "Bolu"]
UA = {"User-Agent": "100-il-research/0.1"}


def table(coords):
    s = ";".join(f"{lo:.5f},{la:.5f}" for la, lo in coords)
    u = f"https://router.project-osrm.org/table/v1/driving/{s}?annotations=duration,distance"
    for k in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read())
        except Exception as e:
            err = e
            time.sleep(3 * (k + 1))
    raise err


t = pd.read_csv(os.path.join(D, "ilce_tablo.csv"))
mc = pd.read_csv(os.path.join(D, "il_merkezleri.csv")).set_index("il")
mat = pd.read_csv(os.path.join(D, "il_ici_matris.csv"))
ids_all = set()
new_rows = []
for il in ILLER:
    g = t[t.il == il]
    ids = g.id.tolist()
    ids_all |= set(ids)
    coords = list(zip(g.lat, g.lon)) + [(mc.at[il, "merkez_lat"], mc.at[il, "merkez_lon"])]
    j = table(coords)
    n = len(ids)
    for k, idx in enumerate(g.index):
        if not (il == "İstanbul" and t.at[idx, "ilce"] == "Adalar"):
            t.at[idx, "il_merkez_dk"] = round(j["durations"][k][n] / 60, 1)
            t.at[idx, "il_merkez_km"] = round(j["distances"][k][n] / 1000, 1)
        for q, b in enumerate(ids):
            if ids[k] != b:
                du, di = j["durations"][k][q], j["distances"][k][q]
                new_rows.append((ids[k], b, None if du is None else round(du / 60, 1),
                                 None if di is None else round(di / 1000, 1)))
    time.sleep(1.2)
mat = mat[~mat.kaynak_id.isin(ids_all)]
mat = pd.concat([mat, pd.DataFrame(new_rows, columns=mat.columns)]).sort_values(["kaynak_id", "hedef_id"])
mat.to_csv(os.path.join(D, "il_ici_matris.csv"), index=False)
t.to_csv(os.path.join(D, "ilce_tablo.csv"), index=False)
print("güncellendi:", len(ids_all), "ilçe")
