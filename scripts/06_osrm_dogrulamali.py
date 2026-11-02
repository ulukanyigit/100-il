# 100 İl — doğrulamalı OSRM hesabı (02 ve 04'ün yerini alır)
# Sorun: OSRM demo tablo servisi bazı çok noktalı isteklerde bir noktayı yoldan km'lerce uzağa "snap" ediyor
# (ör. Hatay tablosunda Arsuz 18,5 km kaydı; 2 noktalı istekte 21 m). Bu yüzden:
#  1) her il için tablo (ilçeler + il merkezi) istenir, her noktanın snap mesafesi kontrol edilir;
#  2) snap > 2 km olan noktaların tüm çiftleri ve fiziksel olarak imkânsız çiftler
#     (yol km < 0,9 × kuş uçuşu, ya da 5 km üstünde ortalama hız < 25 km/sa) 2 noktalı route isteğiyle yeniden hesaplanır.
# QGIS Python konsolunda arka plan iş parçacığında çalışır.
import json, time, math, threading, urllib.request, urllib.error, os, csv
import pandas as pd

D = r"C:\Users\yigit\Desktop\100-il\data\processed"
LOG = os.path.join(D, "osrm_dogrula_log.txt")
UA = {"User-Agent": "100-il-research/0.1"}
FERIBOT = {("Çanakkale", "Eceabat"), ("Çanakkale", "Gökçeada"), ("Çanakkale", "Bozcaada"),
           ("Balıkesir", "Marmara"), ("İstanbul", "Adalar")}


def get(u):
    err = None
    for k in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read())
        except urllib.error.HTTPError as e:
            if e.code == 400:  # OSRM "NoRoute" (ör. ada) → rota yok
                return {"code": "NoRoute"}
            err = e
            time.sleep(3 * (k + 1))
        except Exception as e:
            err = e
            time.sleep(3 * (k + 1))
    raise err


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))


def route(a, b):
    j = get(f"https://router.project-osrm.org/route/v1/driving/{a[1]:.5f},{a[0]:.5f};{b[1]:.5f},{b[0]:.5f}?overview=false")
    time.sleep(0.6)
    if j.get("code") != "Ok":
        return None, None
    r = j["routes"][0]
    return r["duration"] / 60, r["distance"] / 1000


def suspicious(dk, km, h):
    if dk is None or km is None:
        return True
    return km < 0.9 * h - 0.5 or (km > 5 and km / (dk / 60) < 25) or (h > 15 and km / h > 3)


def run():
    t = pd.read_csv(os.path.join(D, "ilce_tablo.csv"))
    mc = pd.read_csv(os.path.join(D, "il_merkezleri.csv")).set_index("il")
    rows, fixed = [], 0
    CACHE = os.path.join(D, "osrm_onbellek.json")  # biten iller; yeniden başlatınca atlanır
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    with open(LOG, "a", encoding="utf-8") as log:
        for il, g in t.groupby("il"):
            ids = g.id.tolist()
            if il in cache:
                dur, dis = cache[il]["dur"], cache[il]["dis"]
                n = len(ids)
                for k, idx in enumerate(g.index):
                    if (il, g.ilce.iloc[k]) == ("İstanbul", "Adalar"):
                        t.at[idx, "il_merkez_dk"], t.at[idx, "il_merkez_km"] = 45.0, 20.0
                    else:
                        t.at[idx, "il_merkez_dk"], t.at[idx, "il_merkez_km"] = round(dur[k][n], 1), round(dis[k][n], 1)
                    for q in range(n):
                        if q != k:
                            rows.append((ids[k], ids[q], None if dur[k][q] is None else round(dur[k][q], 1),
                                         None if dis[k][q] is None else round(dis[k][q], 1)))
                continue
            pts = list(zip(g.lat, g.lon)) + [(mc.at[il, "merkez_lat"], mc.at[il, "merkez_lon"])]
            n = len(ids)
            s = ";".join(f"{lo:.5f},{la:.5f}" for la, lo in pts)
            j = get(f"https://router.project-osrm.org/table/v1/driving/{s}?annotations=duration,distance")
            snap_bad = {k for k, w in enumerate(j["sources"]) if w["distance"] > 2000}
            dur = [[None if x is None else x / 60 for x in r] for r in j["durations"]]
            dis = [[None if x is None else x / 1000 for x in r] for r in j["distances"]]
            nfix = 0
            for a in range(n + 1):
                for b in range(n + 1):
                    if a == b or (a == n and b != n):
                        continue  # merkez→ilçe gerekmiyor
                    ad = lambda x: g.ilce.iloc[x] if x < n else None
                    feri = (il, ad(a)) in FERIBOT or (il, ad(b)) in FERIBOT  # vapur hatları yavaştır, normal
                    h = hav(pts[a], pts[b])
                    if a in snap_bad or b in snap_bad or (not feri and suspicious(dur[a][b], dis[a][b], h)):
                        d2, k2 = route(pts[a], pts[b])
                        if d2 is not None:
                            dur[a][b], dis[a][b] = d2, k2
                            nfix += 1
            fixed += nfix
            for k, idx in enumerate(g.index):
                if (il, g.ilce.iloc[k]) == ("İstanbul", "Adalar"):
                    t.at[idx, "il_merkez_dk"], t.at[idx, "il_merkez_km"] = 45.0, 20.0
                else:
                    t.at[idx, "il_merkez_dk"] = round(dur[k][n], 1)
                    t.at[idx, "il_merkez_km"] = round(dis[k][n], 1)
                for q in range(n):
                    if q != k:
                        rows.append((ids[k], ids[q], None if dur[k][q] is None else round(dur[k][q], 1),
                                     None if dis[k][q] is None else round(dis[k][q], 1)))
            cache[il] = {"dur": dur, "dis": dis}
            json.dump(cache, open(CACHE, "w", encoding="utf-8"))
            log.write(f"OK {il} n={n} snap_bad={sorted(snap_bad)} duzeltilen={nfix}\n")
            log.flush()
            time.sleep(1.2)
        with open(os.path.join(D, "il_ici_matris.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["kaynak_id", "hedef_id", "dk", "km"])
            w.writerows(rows)
        t.to_csv(os.path.join(D, "ilce_tablo.csv"), index=False)
        log.write(f"DONE toplam_duzeltilen={fixed}\n")


if __name__ == "__main__":
    threading.Thread(target=run, daemon=True).start()
    print("doğrulamalı OSRM hesabı arka planda başladı ->", LOG)
