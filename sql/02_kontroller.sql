-- 100 İl — veri kontrolleri (her sorgu tek satırlık özet ya da sorunlu kayıtların listesini döndürür)

-- K1. Her ilçe merkezi kendi poligonunun içinde mi? (beklenen: 0 satır)
SELECT id, il, ilce, round(ST_Distance(merkez::geography, geom::geography)) AS poligona_uzaklik_m
FROM yuz_il.ilce
WHERE NOT ST_Covers(geom, merkez);

-- K2. Toplam nüfus TÜİK'in açıkladığı 86.092.168 ile örtüşüyor mu?
SELECT sum(nufus) AS toplam, sum(nufus) - 86092168 AS fark FROM yuz_il.ilce;

-- K3. Alan: Python'da hesaplanan alan (alan_km2), geography (elipsoit) ve ilçenin kendi 3° TM dilimi tutarlı mı?
WITH a AS (
  SELECT id, il, ilce, alan_km2,
         ST_Area(geom::geography) / 1e6               AS alan_elipsoit,
         ST_Area(ST_Transform(geom, tm_epsg)) / 1e6  AS alan_tm
  FROM yuz_il.ilce
)
SELECT round((percentile_cont(0.5) WITHIN GROUP (ORDER BY abs(alan_tm / alan_elipsoit - 1)))::numeric * 100, 3) AS tm_elipsoit_medyan_fark_yuzde,
       round(max(abs(alan_tm / alan_elipsoit - 1))::numeric * 100, 3)                                  AS tm_elipsoit_max_fark_yuzde,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY abs(alan_elipsoit / alan_km2 - 1)))::numeric * 100, 1)  AS python_alan_medyan_fark_yuzde,
       count(*) FILTER (WHERE abs(alan_elipsoit / alan_km2 - 1) > 0.25)                                 AS python_alanindan_25yuzde_sapan
FROM a;

-- K3b. Tek TM dilimi kullanılsaydı (TM30, EPSG:5254) doğudaki ilçelerin alanı ne kadar şişerdi?
SELECT ST_X(merkez)::int / 3 * 3 AS boylam_dilimi,
       round(avg(ST_Area(ST_Transform(geom, 5254)) / ST_Area(geom::geography) - 1)::numeric * 100, 2) AS tm30_alan_hatasi_yuzde,
       count(*) AS ilce
FROM yuz_il.ilce GROUP BY 1 ORDER BY 1;

-- K4. Belediye binası noktası kendi ilçesinde mi, ilçe merkezine ne kadar uzak? (kaynak türüne göre)
SELECT b.tur, count(*) AS adet,
       count(*) FILTER (WHERE NOT ST_DWithin(b.geom::geography, i.geom::geography, 1000)) AS ilce_disinda,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY ST_Distance(b.geom::geography, i.merkez::geography)))::numeric) AS merkeze_medyan_m
FROM yuz_il.belediye b JOIN yuz_il.ilce i USING (id)
GROUP BY b.tur ORDER BY adet DESC;

-- K5. Yol süresi matrisi fiziksel olarak mümkün mü? (yol mesafesi kuş uçuşunun %90'ından kısa olamaz)
SELECT count(*) AS cift,
       count(*) FILTER (WHERE y.dk IS NULL) AS rota_yok,
       count(*) FILTER (WHERE y.km < 0.9 * ST_Distance(a.merkez::geography, b.merkez::geography) / 1000) AS kus_ucusundan_kisa,
       count(*) FILTER (WHERE y.km / nullif(y.dk, 0) * 60 > 130) AS ortalama_130_kmsa_ustu
FROM yuz_il.yol_sure y
JOIN yuz_il.ilce a ON a.id = y.kaynak_id
JOIN yuz_il.ilce b ON b.id = y.hedef_id;

-- K6. Her il merkezi kendi ilinin sınırları içinde mi? (beklenen: 0 satır)
SELECT m.il FROM yuz_il.il_merkezi m
WHERE NOT EXISTS (SELECT 1 FROM yuz_il.ilce i WHERE i.il = m.il AND i.geom && ST_Expand(m.geom, 0.01)
                    AND ST_DWithin(i.geom::geography, m.geom::geography, 500));

-- K7. OSM'de her ilçe için belediye adayı: ilçe sınırına 1 km tampon içindeki townhall / "... Belediyesi" kayıtları
SELECT count(*) AS ilce,
       count(*) FILTER (WHERE n > 0) AS osm_adayi_olan,
       round(avg(n), 1)              AS ortalama_aday
FROM (
  SELECT i.id, count(o.osm) AS n
  FROM yuz_il.ilce i
  LEFT JOIN yuz_il.osm_belediye o
         ON o.geom && ST_Expand(i.geom, 0.015)                       -- GiST indeksiyle kutu ön elemesi (~1,3 km)
        AND ST_DWithin(o.geom::geography, i.geom::geography, 1000)  -- kesin mesafe elipsoit üzerinde
  GROUP BY i.id
) q;
