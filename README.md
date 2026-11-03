# 100 İl Haritası

**Türkiye 100 il olsaydı, veri hangi 19 ilçeyi seçerdi?**

“100 il, 1000 ilçe” önerisinde il olacak ilçelerin kesin listesi açıklanmadı. Bu proje Türkiye'nin 973 ilçesini nüfus, il merkezine yol süresi ve gelişmişlik verisiyle tartıp 19 yeni ili kendisi seçer. Web uygulamasında ağırlıkları değiştirdiğinizde model tarayıcıda yeniden çalışır ve harita yeniden çizilir.

*What if Türkiye had 100 provinces? A data-driven model that scores all 973 districts on population, drive time to the provincial capital (OSRM) and socio-economic development (SEGE-2022), then picks 19 new provinces. Interactive web map with live re-weighting.*

## Varsayılan senaryonun sonucu

| Plaka | İlçe | Ayrıldığı il | Yeni ilin nüfusu | İl merkezine | 1000 senaryoda | Basın listesi |
|---|---|---|---|---|---|---|
| 82 | Akhisar | Manisa | 369.619 | 51 dk | %78 |  |
| 83 | Alanya | Antalya | 427.397 | 105 dk | %98 | ✓ |
| 84 | Bandırma | Balıkesir | 306.763 | 74 dk | %87 | ✓ |
| 85 | Bodrum | Muğla | 359.471 | 99 dk | %100 |  |
| 86 | Çerkezköy | Tekirdağ | 427.952 | 56 dk | %99 |  |
| 87 | Çorlu | Tekirdağ | 409.210 | 37 dk | %89 | ✓ |
| 88 | Edremit | Balıkesir | 367.608 | 61 dk | %70 | ✓ |
| 89 | Elbistan | Kahramanmaraş | 282.876 | 116 dk | %59 | ✓ |
| 90 | Ereğli | Konya | 221.360 | 107 dk | %64 |  |
| 91 | Fethiye | Muğla | 365.011 | 108 dk | %100 | ✓ |
| 92 | Gebze | Kocaeli | 927.697 | 38 dk | %99 |  |
| 93 | İnegöl | Bursa | 413.212 | 46 dk | %91 |  |
| 94 | İskenderun | Hatay | 601.722 | 47 dk | %87 | ✓ |
| 95 | Kuşadası | Aydın | 368.415 | 50 dk | %68 |  |
| 96 | Manavgat | Antalya | 434.360 | 61 dk | %100 | ✓ |
| 97 | Menemen | İzmir | 554.404 | 36 dk | %44 |  |
| 98 | Salihli | Manisa | 431.399 | 61 dk | %60 |  |
| 99 | Silivri | İstanbul | 321.172 | 55 dk | %92 |  |
| 100 | Torbalı | İzmir | 578.045 | 39 dk | %72 |  |

**Sağlamlık:** 1000 rastgele ağırlık seti (Dirichlet(2,2,2,2)) denendi. Manavgat, Bodrum, Fethiye, Gebze, Çerkezköy ve Alanya senaryoların en az %98'inde seçiliyor. Varsayılan senaryoda basın listesiyle örtüşme 8/19. Basında yer alan 19 ilçelik listeden 10'u (Cizre, Erciş, Ergani, Kâhta, Lüleburgaz, Midyat, Nazilli, Polatlı, Ünye, Yüksekova) senaryoların en fazla %6'sında çıkıyor.

## Yöntem

1. **Kent çekirdeği:** İl merkezine yol mesafesi ≤30 km olan ilçeler, ayrıca yoğunluğu ≥500 kişi/km² olup çekirdekteki bir ilçeye ≤20 dk uzaklıktaki ilçeler (Pendik, Esenyurt gibi kesintisiz kent dokusu) aday olamaz.
2. **Hinterland:** Bir aday il olursa, kendisine eski il merkezinden daha kısa sürede ulaşılan ilçeler ona bağlanır. Model ilçeleri yalnızca kendi ili içinde dağıtır.
3. **Koşullar:** Yeni il ≥150 bin nüfus, geride kalan il ≥250 bin nüfus, aday ilçe ≥40 bin nüfus.
4. **Puan (0–100):** yeni ilin toplam nüfusu (%35, log), ilçenin kendi nüfusu (%20, log), il merkezine sürüş süresi (%25, 30–180 dk), SEGE-2022 skoru (%20).
5. **Seçim:** Her turda koşulları sağlayan en yüksek puanlı aday il olur, ilçeler en yakın merkeze yeniden dağıtılır, 19 il seçilene kadar sürer.
6. **Yeni il merkezi:** İl olan ilçenin belediye binası yeni il merkezi olarak gösterilir. Konum önce OpenStreetMap'ten alınır; OSM'de kaydı olmayan belediyeler için belediyenin resmî sitesindeki (*.bel.tr) harita ya da adres kullanılır (adres, Nominatim ile koordinata çevrilir). Varsayılan 19 ilin 18'inde ana belediye binası, İnegöl'de ek hizmet binası kullanılıyor. 1000 senaryoda en az bir kez seçilen 55 ilçenin 41'i OSM'de tam eşleşti, 8'i resmî siteden bulundu (Payas, Arsuz, Tire haritadan; Dörtyol sokak, Gönen, Finike, Erzin, Kiraz mahalle düzeyinde). Kırıkhan, Urla ve Ceylanpınar'da güvenilir konum bulunamadığı için ilçe merkezi gösteriliyor. Google Maps verisi kullanılmadı: kullanım koşulları otomatik çekmeye ve açık bir depoda yeniden yayına izin vermiyor (`scripts/07_belediye_eslestir.py`, `scripts/08_belediye_resmi_site.py`, `data/processed/belediye_eslesme.csv`).


**Bölgesel denge (isteğe bağlı):** Varsayılan model 19 ili ülke genelinde tek puan sıralamasıyla seçer; sonuçta 19 ilin 18'i Marmara, Ege ve Akdeniz'den çıkar (7/7/4, İç Anadolu 1, Karadeniz, Doğu ve Güneydoğu 0). Sitedeki "Bölgesel denge" kutusunda iki kural açılabilir: *her ilden en fazla 1 yeni il* (`il_max`) ve *her bölgeden en az 1–2 il* (`kota`; önce 7 bölgenin her birinden en yüksek puanlı uygun aday seçilir, kalan koltuklar puan sırasıyla dolar). Yalnızca il başı sınır açıldığında dağılım 5/4/4/1/2/1/2 olur ve 7 bölgenin hepsi listeye girer; il başı sınır ve 2'lik kota birlikte 5/4/3/2/2/1/2 verir. Doğu Anadolu'da koşulları sağlayan aday az olduğundan kota orada 1'de kalır. Kurallar URL'e yazılır (`#k=çekirdek,min_hinter,min_parent,il_max,kota`). 1000 senaryoluk sağlamlık kareleri varsayılan model içindir.
**Sınırlar:** Yol süreleri trafiksiz OSRM tahminidir. İl sınırını aşan düzenlemeler, bölgesel denge, güvenlik, tarih ve kimlik gibi ölçütler modele girmez. Basındaki liste resmî değildir, yalnızca karşılaştırma için kullanılır.

## Veri

| Veri | Kaynak |
|---|---|
| İlçe nüfusu 2025 | TÜİK ADNKS 2025 (tr.wikipedia “Türkiye'nin ilçeleri” tablosu üzerinden) |
| Gelişmişlik | Sanayi ve Teknoloji Bakanlığı, SEGE-2022 ilçe skorları |
| Sınırlar | geoBoundaries gbOpen TUR ADM1/ADM2 (CC BY 4.0) |
| Yol süreleri | OSRM public demo, © OpenStreetMap katkıcıları; demo tablo servisinin hatalı snap ettiği 368 çift tek tek rota sorgusuyla düzeltildi |
| Belediye binaları | OpenStreetMap (Overpass, Nominatim), belediyelerin resmî siteleri (*.bel.tr) |
| İl merkezleri | Wikidata (P36) / il ile aynı adlı merkez ilçe |
| Koordinat düzeltmeleri | Tablodaki 10 hatalı ilçe merkezi (Çamlıyayla, Adilcevaz, Çaldıran, Selendi, Kale, Kartepe, Defne, Yüksekova, Bağcılar, Gerede) elle düzeltildi; 973 merkezin tamamı kendi poligonunda |
| Basın listesi | gzt.com, 2 Kasım 2026 |

## Teknik yapı

| Katman | Araç |
|---|---|
| Veri hazırlama | Python (pandas, GeoPandas, Shapely), PyQGIS |
| Mekânsal veritabanı | PostgreSQL 13 + PostGIS 3.5 (`yuz_il` şeması) |
| Yol süreleri | OSRM (OpenStreetMap), doğrulamalı yeniden hesap |
| Model | Üç eş uygulama: Python (`scripts/model.py`), PL/pgSQL (`sql/04_model.sql`), JavaScript (`docs/model.js`, tarayıcıda) |
| Web | MapLibre GL, TopoJSON, GitHub Pages |
| Sağlamlık | 1000 senaryoluk Monte Carlo (Node) |

### PostGIS

`scripts/10_postgis_yukle.py` QGIS'te kayıtlı PostgreSQL bağlantısıyla `yuz_il` şemasını kurar ve 973 ilçe poligonunu, 13.980 il içi yol süresini, il merkezlerini, belediye binalarını ve 2.607 OSM belediye kaydını yükler (yaklaşık 1 sn).

- `sql/02_kontroller.sql`: Veri kontrolleri. Her ilçe merkezi kendi poligonunda mı (`ST_Covers`, 0 hata), toplam nüfus (TÜİK'le 9 kişi fark), yol matrisinin fiziksel tutarlılığı (kuş uçuşundan kısa yol: 0), belediye noktalarının ilçeye uzaklığı, il merkezlerinin kendi ilinde olup olmadığı. OSM eşleştirmesinde GiST indeksiyle kutu ön elemesi (`&&`) ve ardından elipsoit üzerinde kesin mesafe (`ST_DWithin` geography) kullanılır.
- Alan hesabı ülke ölçeğinde elipsoit (geography), ilçe ölçeğinde ilçenin kendi 3° TM diliminde (TUREF/TM27–TM45, EPSG:5253–5259) yapılır. İki yöntem arasındaki fark medyanda %0,009, en fazla %0,05. Tüm ülke tek dilimde (TM30) hesaplansaydı 45° boylamındaki ilçelerin alanı %4 büyük çıkardı.
- `sql/03_cekirdek.sql`: Kent çekirdeği `WITH RECURSIVE` ile. İl merkezine 30 km'den yakın ilçelere, çekirdeğe 20 dakikadan yakın ve km²'de 500 kişiden yoğun ilçeler zincirle eklenir (Pendik, Esenyurt, Tuzla, Narlıdere…).
- `sql/04_model.sql`: Seçim modeli PL/pgSQL fonksiyonu olarak. `SELECT * FROM yuz_il.calistir();` ya da `yuz_il.calistir(il_max => 1, kota => 2)`. Sonuçlar `yuz_il.secim`, `yuz_il.atama`, `yuz_il.adaylar` tablolarına yazılır; bir çalıştırma 1,5–3 sn sürer.
- `sql/05_iller_100.sql`: 100 ilin sınırları (`ST_Union`), yeni il merkezleri (belediye binası, plaka 82–100) ve QGIS için `v_ilce_sonuc` görünümü.
- `scripts/11_sql_test.py`: PL/pgSQL modelini Python modeliyle 6 ayarda (varsayılan, il başı sınır, bölge kotası, düşük eşik, erişim ağırlıklı, dar çekirdek) karşılaştırır. Altısında da 19 ilin sırası, nüfusları ve puanları birebir aynı.

## Klasör yapısı

```
scripts/01_veri_toplama.py   sınırlar, nüfus, koordinatlar, il merkezine OSRM süresi
scripts/02_osrm_matris.py    il içi ilçe→ilçe sürüş süresi matrisi (QGIS konsolunda arka planda)
scripts/03_birlestir.py      SEGE eşleştirme, poligon bağlama, alan
scripts/04_koordinat_duzelt.py hatalı koordinatlar sonrası OSRM yeniden hesap (06 ile değiştirildi)
scripts/07_belediye_eslestir.py belediye binası konumları (OSM Overpass + Nominatim)
scripts/08_belediye_resmi_site.py OSM'de olmayan belediyeler için resmî site haritası/adresi
scripts/06_osrm_dogrulamali.py doğrulamalı OSRM: snap > 2 km ve imkânsız çiftler 2 noktalı rota ile yeniden (368 çift)
scripts/05_web_veri.py       web veri paketi ve sonuç katmanları
scripts/model.py             referans model (Python) → adaylar.csv, secim.csv, atama.csv
scripts/mc.js                1000 senaryoluk sağlamlık analizi (Node)
scripts/10_postgis_yukle.py   PostGIS şeması + veri yükleme (QGIS konsolu)
scripts/11_sql_test.py       PL/pgSQL modeli ile Python modelini karşılaştırır
sql/                         01 şema · 02 veri kontrolleri · 03 kent çekirdeği · 04 seçim modeli · 05 100 il
data/processed/              ilceler.gpkg, iller_100.gpkg, tablolar
docs/                        statik site (GitHub Pages) (MapLibre GL + TopoJSON); model.js Python modeliyle birebir aynı sonucu verir
100il.qgz                    QGIS projesi
```

Web sürümünü yerelde açmak için: `cd docs && python -m http.server` ve tarayıcıda `localhost:8000`.

Hazırlayan: Hamza Yiğit Ulukan, Harita Mühendisi
