-- 100 İl — sonuç katmanları (yuz_il.calistir() çalıştırıldıktan sonra)

-- 100 ilin sınırları: ilçeler bağlandıkları ile göre birleştirilir
DROP TABLE IF EXISTS yuz_il.iller_100;
CREATE TABLE yuz_il.iller_100 AS
SELECT a.yeni_il,
       min(i.il)                          AS ana_il,
       bool_or(a.yeni_mi)                 AS yeni_mi,
       count(*)::int                      AS ilce_sayisi,
       sum(i.nufus)::bigint               AS nufus,
       round((sum(ST_Area(i.geom::geography)) / 1e6)::numeric) AS alan_km2,
       ST_Multi(ST_Union(i.geom))::geometry(MultiPolygon, 4326) AS geom
FROM yuz_il.atama a JOIN yuz_il.ilce i USING (id)
GROUP BY a.yeni_il;
ALTER TABLE yuz_il.iller_100 ADD PRIMARY KEY (yeni_il);
CREATE INDEX ON yuz_il.iller_100 USING gist (geom);

-- yeni il merkezleri: ilçenin belediye binası (yoksa ilçe merkezi) + plaka (82–100, ada göre)
CREATE OR REPLACE VIEW yuz_il.yeni_il_merkezi AS
SELECT 81 + row_number() OVER (ORDER BY s.ilce COLLATE "tr-TR-x-icu")::int AS plaka,
       s.ilce, s.il AS ana_il, s.hinter_nufus, s.puan,
       coalesce(b.ad, s.ilce || ' ilçe merkezi') AS merkez_ad, coalesce(b.tur, 'yok') AS konum_turu,
       coalesce(b.geom, i.merkez)::geometry(Point, 4326) AS geom
FROM yuz_il.secim s JOIN yuz_il.ilce i ON i.id = s.id LEFT JOIN yuz_il.belediye b ON b.id = s.id;

-- QGIS için ilçe katmanı: hangi ile bağlandığı ve çekirdek bilgisi
CREATE OR REPLACE VIEW yuz_il.v_ilce_sonuc AS
SELECT i.id, i.il, i.ilce, i.nufus, a.cekirdek, a.yeni_il, a.yeni_mi, i.geom
FROM yuz_il.ilce i JOIN yuz_il.atama a USING (id);

-- özet: il sayısı, nüfus korunumu, bölgelere dağılım
SELECT count(*) AS il_sayisi, sum(nufus) AS toplam_nufus,
       sum(nufus) = (SELECT sum(nufus) FROM yuz_il.ilce) AS nufus_korundu
FROM yuz_il.iller_100;

SELECT bo.ad AS bolge, count(s.id) AS yeni_il
FROM yuz_il.bolge bo
LEFT JOIN yuz_il.ilce i ON i.bolge = bo.kod
LEFT JOIN yuz_il.secim s ON s.id = i.id
GROUP BY bo.ad, bo.sira ORDER BY bo.sira;
