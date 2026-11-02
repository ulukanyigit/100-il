"""100 İl — OSM'de belediye binası olmayan adaylar için belediyelerin resmî sitelerinden konum (3. tur).

Yöntem (2 Kasım 2026):
  - Her belediyenin *.bel.tr iletişim sayfası okundu; sayfadaki gömülü harita koordinatı ve resmî adres çıkarıldı.
  - Harita koordinatı varsa ve ilçe poligonunun içinde, adresle tutarlıysa kullanıldı ("site-harita").
  - Yalnızca adres varsa OSM Nominatim ile sokak ya da mahalle düzeyinde koordinata çevrildi.
  - Tutarsız işaretler elendi: Ceylanpınar sitesindeki işaret ilçe merkezine 29 km (ilçe dışı),
    Kiraz sitesindeki işaret adresteki caddeye 1,6 km uzak çıktı.
  - Google Maps verisi kullanılmadı (kullanım koşulları otomatik çekmeyi ve yeniden yayını yasaklıyor).
Kırıkhan, Urla ve Ceylanpınar için güvenilir koordinat bulunamadı: ilçe merkezi kalır (bel_tur = "yok").
Girdi/çıktı: belediye_eslesme.csv (07_belediye_eslestir.py çıktısının üzerine yazar)
"""
import pandas as pd

RESMI = {  # (il, ilçe): (lat, lon, ad, kaynak, tür)
    ("Hatay", "Payas"): (36.7577, 36.213911, "Payas Belediyesi", "https://payas.bel.tr/", "site-harita"),
    ("Hatay", "Arsuz"): (36.446178, 35.939924, "Arsuz Belediyesi (Akçalı Mh. 856. Sk. No:3)", "https://arsuz.bel.tr/iletisim", "site-harita"),
    ("İzmir", "Tire"): (38.086851, 27.732003, "Tire Belediyesi", "https://tire.bel.tr/tr/iletisim", "site-harita"),
    ("Hatay", "Dörtyol"): (36.8298482, 36.2177234, "Dörtyol Belediyesi (İstasyon Caddesi No:2)", "https://dortyol.bel.tr/iletisim", "adres-sokak"),
    ("Balıkesir", "Gönen"): (40.1028264, 27.6528561, "Gönen Belediyesi (Malkoç Mh. Atatürk Cd. No:2)", "https://balikesirgonen.bel.tr/iletisim", "adres-mahalle"),
    ("Antalya", "Finike"): (36.2975312, 30.1440424, "Finike Belediyesi (Eski Mahalle 109. Sokak No:1)", "https://finike.bel.tr/", "adres-mahalle"),
    ("Hatay", "Erzin"): (36.9549432, 36.1937143, "Erzin Belediyesi (Cumhuriyet Mh. Demokrasi Cd. No:3)", "https://www.erzin.bel.tr/iletisim", "adres-mahalle"),
    ("İzmir", "Kiraz"): (38.2332587, 28.2046508, "Kiraz Belediyesi (İstiklal Mh. Sabit Arlı Cd. No:51)", "https://kiraz.bel.tr/iletisim", "adres-mahalle"),
}

if __name__ == "__main__":
    o = pd.read_csv("belediye_eslesme.csv")
    if "bel_kaynak" not in o:
        o["bel_kaynak"] = None
    o["bel_kaynak"] = [k if isinstance(k, str) else (f"https://www.openstreetmap.org/{x}" if isinstance(x, str) else None)
                       for k, x in zip(o.bel_kaynak, o.bel_osm)]
    for (il, ilce), (la, lo, ad, url, tur) in RESMI.items():
        m = (o.il == il) & (o.ilce == ilce)
        assert m.sum() == 1, (il, ilce)
        o.loc[m, ["bel_lat", "bel_lon", "bel_ad", "bel_osm", "bel_tur", "bel_kaynak"]] = [la, lo, ad, None, tur, url]
    o.to_csv("belediye_eslesme.csv", index=False)
    print(o.bel_tur.value_counts().to_dict())
