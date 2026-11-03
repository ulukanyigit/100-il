-- 100 İl — PostGIS şeması
-- Çalıştırma: scripts/10_postgis_yukle.py bu dosyayı çalıştırır ve verileri yükler.
-- Koordinatlar EPSG:4326 (WGS84). Ülke ölçeğindeki uzunluk/alan hesapları geography ile,
-- ilçe ölçeğindekiler ilçenin kendi 3° TM diliminde (TUREF/TM27–TM45, EPSG:5253–5259) yapılır.

CREATE EXTENSION IF NOT EXISTS postgis;
DROP SCHEMA IF EXISTS yuz_il CASCADE;
CREATE SCHEMA yuz_il;
COMMENT ON SCHEMA yuz_il IS '100 İl: Türkiye 100 il olsaydı veri hangi 19 ilçeyi seçerdi? (github.com/ulukanyigit/100-il)';

-- 973 ilçe: TÜİK ADNKS 2025 nüfusu, SEGE-2022, il merkezine OSRM sürüş süresi, geoBoundaries poligonu
CREATE TABLE yuz_il.ilce (
  id            integer PRIMARY KEY,
  il            text    NOT NULL,
  ilce          text    NOT NULL,
  bolge         text    NOT NULL,          -- MB, EB, AB, İAB, KB, DAB, GAB
  nufus         integer NOT NULL,          -- TÜİK ADNKS 2025
  alan_km2      double precision,          -- poligondan hesaplanan alan (scripts/03_birlestir.py; yoğunluk ve kent çekirdeği için)
  il_merkez_dk  double precision NOT NULL, -- il merkezine OSRM sürüş süresi (dk, trafiksiz)
  il_merkez_km  double precision NOT NULL, -- il merkezine yol mesafesi (km)
  sege_skor     double precision,          -- SEGE-2022 skoru
  sege_sira     integer,                   -- SEGE-2022 sırası (1 = en gelişmiş)
  gbid          text,                      -- geoBoundaries kimliği
  merkez        geometry(Point, 4326) NOT NULL,        -- ilçe merkezi
  geom          geometry(MultiPolygon, 4326) NOT NULL, -- ilçe sınırı
  tm_epsg       integer GENERATED ALWAYS AS (5253 + greatest(0, least(6, round((ST_X(merkez) - 27) / 3)::int))) STORED
);
CREATE INDEX ON yuz_il.ilce USING gist (geom);
CREATE INDEX ON yuz_il.ilce USING gist (merkez);
CREATE INDEX ON yuz_il.ilce (il);
COMMENT ON COLUMN yuz_il.ilce.tm_epsg IS 'İlçe merkezinin düştüğü TUREF 3° TM dilimi (5253 = TM27 … 5259 = TM45)';

-- il içi ilçe→ilçe sürüş süresi matrisi (OSRM, doğrulamalı yeniden hesap: scripts/06_osrm_dogrulamali.py)
CREATE TABLE yuz_il.yol_sure (
  kaynak_id integer REFERENCES yuz_il.ilce(id),
  hedef_id  integer REFERENCES yuz_il.ilce(id),
  dk        double precision,  -- NULL = rota bulunamadı
  km        double precision,
  PRIMARY KEY (kaynak_id, hedef_id)
);

-- mevcut 81 il merkezi (Wikidata P36)
CREATE TABLE yuz_il.il_merkezi (
  il     text PRIMARY KEY,
  kaynak text,
  geom   geometry(Point, 4326) NOT NULL
);

-- ilçe belediye binaları (yeni il merkezi olarak gösterilir): OSM + belediyelerin resmî siteleri
CREATE TABLE yuz_il.belediye (
  id      integer PRIMARY KEY REFERENCES yuz_il.ilce(id),
  ad      text,
  tur     text NOT NULL,   -- ad, hizmet-binasi, genel-ad, isimsiz, ek-bina, site-harita, adres-sokak, adres-mahalle, yok
  kaynak  text,            -- OSM ya da belediye sitesi URL
  geom    geometry(Point, 4326) NOT NULL
);

-- OpenStreetMap ham belediye kayıtları (Overpass; varsa yüklenir)
CREATE TABLE yuz_il.osm_belediye (
  osm      text PRIMARY KEY,  -- node/123, way/456
  ad       text,
  townhall boolean,           -- amenity=townhall etiketi var mı
  tip      text,              -- townhall:type
  geom     geometry(Point, 4326) NOT NULL
);
CREATE INDEX ON yuz_il.osm_belediye USING gist (geom);

-- basında yer alan 19 ilçelik aday listesi (gzt.com, 2 Kasım 2026) — resmî değil
CREATE TABLE yuz_il.basin_listesi (il text, ilce text, PRIMARY KEY (il, ilce));
INSERT INTO yuz_il.basin_listesi VALUES
 ('Antalya','Alanya'),('Antalya','Manavgat'),('Balıkesir','Bandırma'),('Balıkesir','Edremit'),('Muğla','Fethiye'),
 ('Aydın','Nazilli'),('Ankara','Polatlı'),('Tekirdağ','Çorlu'),('Kırklareli','Lüleburgaz'),('Hatay','İskenderun'),
 ('Ordu','Ünye'),('Kahramanmaraş','Elbistan'),('Şanlıurfa','Siverek'),('Adıyaman','Kâhta'),('Diyarbakır','Ergani'),
 ('Mardin','Midyat'),('Şırnak','Cizre'),('Van','Erciş'),('Hakkâri','Yüksekova');

-- coğrafi bölge sırası (bölge kotasında bu sırayla dolaşılır; web ve Python sürümüyle aynı)
CREATE TABLE yuz_il.bolge (kod text PRIMARY KEY, sira smallint UNIQUE NOT NULL, ad text NOT NULL);
INSERT INTO yuz_il.bolge VALUES ('MB',0,'Marmara'),('EB',1,'Ege'),('AB',2,'Akdeniz'),('İAB',3,'İç Anadolu'),
 ('KB',4,'Karadeniz'),('DAB',5,'Doğu Anadolu'),('GAB',6,'Güneydoğu Anadolu');
