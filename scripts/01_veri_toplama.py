"""100 İl — veri toplama (QGIS Python konsolunda ya da geopandas yüklü bir ortamda çalışır).

Kaynaklar
- İlçe sınırları : geoBoundaries gbOpen TUR ADM1/ADM2 (CC BY 4.0)
- Nüfus 2025     : TÜİK ADNKS 2025 — tr.wikipedia "Türkiye'nin ilçeleri" tablosu (kaynak: TÜİK)
- İlçe merkezleri: aynı tablodaki geohack koordinatları (Çamlıyayla ve Adilcevaz elle düzeltildi)
- İl merkezleri  : il ile aynı adlı ilçenin merkezi; büyükşehirlerde Wikidata P36 başkent koordinatı
- Gelişmişlik    : Sanayi ve Teknoloji Bakanlığı SEGE-2022 ilçe skorları (rapor PDF'inden ayrıştırıldı)
- Yol süreleri   : OSRM public demo (router.project-osrm.org), trafiksiz sürüş süresi
"""
import io, re, json, time, urllib.request, urllib.parse, os
import pandas as pd

D = r"C:\Users\yigit\Desktop\100-il"
RAW, PRO = os.path.join(D, "data", "raw"), os.path.join(D, "data", "processed")
UA = {"User-Agent": "100-il-research/0.1"}


def get(u, binary=False, timeout=60):
    b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout).read()
    return b if binary else b.decode("utf-8", "replace")


def sinirlar():
    base = "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/TUR/"
    for lvl in ["ADM1", "ADM2"]:
        open(os.path.join(RAW, f"gb_{lvl}.geojson"), "wb").write(
            get(base + f"{lvl}/geoBoundaries-TUR-{lvl}.geojson", binary=True))


def nufus_ve_koordinat():
    from lxml import html as LH
    html = get("https://tr.wikipedia.org/wiki/" + urllib.parse.quote("Türkiye'nin_ilçeleri"))
    open(os.path.join(RAW, "wiki_turkiye_ilceleri.html"), "w", encoding="utf-8").write(html)
    t = pd.read_html(io.StringIO(html), thousands=".", decimal=",")[1]
    t.columns = ["il", "ilce", "bolge", "kurulus", "alan_km2", "nufus2025", "yogunluk", "rakim",
                 "posta", "mahalle", "koy", "konum", "gorsel"]
    t["nufus2025"] = pd.to_numeric(t["nufus2025"].astype(str).str.replace(r"[^\d]", "", regex=True))
    doc = LH.fromstring(html)
    tb = max(doc.xpath("//table[contains(@class,'wikitable')]"), key=lambda x: len(x.xpath(".//tr")))
    lat, lon = [], []
    for tr in tb.xpath(".//tr")[1:]:
        p = re.search(r"params=([^&]+)", tr.xpath(".//a[contains(@href,'geohack')]/@href")[0]).group(1)
        g = re.match(r"([\d.]+)_([\d.]+)?_?([\d.]+)?_?[NS]_([\d.]+)_([\d.]+)?_?([\d.]+)?_?[EW]", p).groups()
        lat.append(float(g[0]) + float(g[1] or 0) / 60 + float(g[2] or 0) / 3600)
        lon.append(float(g[3]) + float(g[4] or 0) / 60 + float(g[5] or 0) / 3600)
    t["lat"], t["lon"] = lat, lon
    fix = {("Mersin", "Çamlıyayla"): (37.1697, 34.6050), ("Bitlis", "Adilcevaz"): (38.8008, 42.7322)}
    for (il, ilce), (la, lo) in fix.items():
        t.loc[(t.il == il) & (t.ilce == ilce), ["lat", "lon"]] = [la, lo]
    return t.drop(columns=["konum", "gorsel", "posta"])


def il_merkezleri(t):
    q = """SELECT ?pLabel ?coord WHERE { ?p wdt:P31 wd:Q48336; wdt:P36 ?cap. ?cap wdt:P625 ?coord.
           SERVICE wikibase:label { bd:serviceParam wikibase:language "tr,en". } }"""
    r = json.loads(get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q)))
    cap = {}
    for b in r["results"]["bindings"]:
        lo, la = map(float, re.findall(r"[\d.\-]+", b["coord"]["value"]))
        cap.setdefault(b["pLabel"]["value"].replace("Hakkari", "Hakkâri"), (la, lo))
    out = {}
    for il in t.il.unique():
        same = t[(t.il == il) & (t.ilce == il)]
        out[il] = (same.lat.iloc[0], same.lon.iloc[0]) if len(same) else cap[il]
    return out


def il_merkezine_sure(t, cen):
    t["il_merkez_dk"] = None
    for il, g in t.groupby("il"):
        la, lo = cen[il]
        coords = list(zip(g.lat, g.lon)) + [(la, lo)]
        s = ";".join(f"{x:.5f},{y:.5f}" for y, x in coords)
        u = (f"https://router.project-osrm.org/table/v1/driving/{s}?sources="
             f"{';'.join(map(str, range(len(g))))}&destinations={len(g)}&annotations=duration,distance")
        j = json.loads(get(u))
        t.loc[g.index, "il_merkez_dk"] = [round(d[0] / 60, 1) for d in j["durations"]]
        t.loc[g.index, "il_merkez_km"] = [round(d[0] / 1000, 1) for d in j["distances"]]
        time.sleep(1.1)
    t.loc[(t.il == "İstanbul") & (t.ilce == "Adalar"), ["il_merkez_dk", "il_merkez_km"]] = [45, 20]
    return t


def sege_ayristir(pdf_path):
    """SEGE-2022 raporundaki 'Sıra İl Adı İlçe Adı Skor' tablolarını okur (pdfplumber gerekir)."""
    import pdfplumber
    pat = re.compile(r"(\d{1,3}) ([A-ZÇĞİÖŞÜ][a-zçğıöşüâ]+) (.+?) (-?\d,\d{3})")
    rows = {}
    for pg in pdfplumber.open(pdf_path).pages:
        txt = pg.extract_text() or ""
        if "Sıra İl Adı İlçe Adı Skor" in txt:
            for m in pat.finditer(txt):
                rows[int(m.group(1))] = (int(m.group(1)), m.group(2), m.group(3).strip(),
                                         float(m.group(4).replace(",", ".")))
    return pd.DataFrame(sorted(rows.values()), columns=["sira", "il", "ilce", "skor"])


if __name__ == "__main__":
    sinirlar()
    t = nufus_ve_koordinat()
    t = il_merkezine_sure(t, il_merkezleri(t))
    t.to_csv(os.path.join(PRO, "ilce_nufus_2025.csv"), index=False, encoding="utf-8")
    # SEGE eşleştirme + poligon bağlama adımları: 03_birlestir.py
