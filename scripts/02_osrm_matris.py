# 100 İl — il içi ilçe-ilçe sürüş süresi matrisi (OSRM public demo)
# QGIS Python konsolunda arka plan iş parçacığında çalışır; çıktı: data/processed/il_ici_matris.csv
import json, time, threading, urllib.request, csv, os
import pandas as pd

D = r"C:\Users\yigit\Desktop\100-il"
OUT = os.path.join(D, "data", "processed", "il_ici_matris.csv")
LOG = os.path.join(D, "data", "processed", "osrm_log.txt")


def _table(coords):
    s = ";".join(f"{lo:.5f},{la:.5f}" for la, lo in coords)
    u = f"https://router.project-osrm.org/table/v1/driving/{s}?annotations=duration,distance"
    err = None
    for k in range(5):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "100-il-research/0.1"})
            return json.loads(urllib.request.urlopen(req, timeout=90).read())
        except Exception as e:
            err = e
            time.sleep(4 * (k + 1))
    raise err


def run():
    t = pd.read_csv(os.path.join(D, "data", "processed", "ilce_tablo.csv"))
    rows = []
    with open(LOG, "w", encoding="utf-8") as log:
        for il, g in t.groupby("il"):
            ids = g["id"].tolist()
            coords = list(zip(g.lat, g.lon))
            try:
                j = _table(coords)
                for a, ra, rb in zip(ids, j["durations"], j["distances"]):
                    for b, du, di in zip(ids, ra, rb):
                        if a != b:
                            rows.append((a, b, None if du is None else round(du / 60, 1),
                                         None if di is None else round(di / 1000, 1)))
                log.write(f"OK {il} {len(ids)}\n")
            except Exception as e:
                log.write(f"FAIL {il} {e}\n")
            log.flush()
            time.sleep(1.2)
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["kaynak_id", "hedef_id", "dk", "km"])
            w.writerows(rows)
        log.write("DONE\n")


threading.Thread(target=run, daemon=True).start()
print("OSRM matrisi arka planda başladı ->", OUT)
