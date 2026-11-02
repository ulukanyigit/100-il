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
data/processed/              ilceler.gpkg, iller_100.gpkg, tablolar
web/                         statik site (MapLibre GL + TopoJSON); model.js Python modeliyle birebir aynı sonucu verir
100il.qgz                    QGIS projesi
```

Web sürümünü yerelde açmak için: `cd web && python -m http.server` ve tarayıcıda `localhost:8000`.

Hazırlayan: Hamza Yiğit Ulukan, Harita Mühendisi
