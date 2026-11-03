-- 100 İl — il adayı seçim modeli (PL/pgSQL)
-- scripts/model.py ve docs/model.js ile aynı mantık; üç uygulama aynı girdiyle aynı 19 ili seçer (sql/06_test.sql).
--
--   SELECT * FROM yuz_il.calistir();                          -- varsayılan ağırlıklar
--   SELECT * FROM yuz_il.calistir(il_max => 1, kota => 2);    -- bölgesel denge kurallarıyla
--
-- Sonuçlar yuz_il.secim (seçilen iller), yuz_il.atama (973 ilçenin 100 ildeki yeri) ve
-- yuz_il.adaylar (ilk tur: her aday tek başına il olsaydı) tablolarına yazılır.

CREATE TABLE IF NOT EXISTS yuz_il.secim (
  sira integer PRIMARY KEY, id integer REFERENCES yuz_il.ilce(id), il text, ilce text, nufus integer,
  hinter_nufus bigint, hinter_ilce integer, hinter_liste text, parent_kalan bigint,
  puan numeric, kota_ile boolean, basin_listesi boolean);
CREATE TABLE IF NOT EXISTS yuz_il.atama (
  id integer PRIMARY KEY REFERENCES yuz_il.ilce(id), cekirdek boolean, merkez_id integer,  -- NULL = ana ilde kalır
  yeni_il text, yeni_mi boolean);
CREATE TABLE IF NOT EXISTS yuz_il.adaylar (
  id integer PRIMARY KEY, il text, ilce text, nufus integer, hinter_nufus bigint, parent_kalan bigint,
  uygun boolean, neden text, puan numeric);

-- 0–1 ölçekleme
CREATE OR REPLACE FUNCTION yuz_il._lin(x double precision, a double precision, b double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$ SELECT greatest(0, least(1, (x - a) / (b - a))) $$;
CREATE OR REPLACE FUNCTION yuz_il._loglin(x double precision, a double precision, b double precision)
RETURNS double precision LANGUAGE sql IMMUTABLE AS $$ SELECT yuz_il._lin(log(greatest(x, 1)), log(a), log(b)) $$;

-- puan (0–100): yeni ilin nüfusu (log), ilçenin nüfusu (log), il merkezine süre, SEGE-2022
CREATE OR REPLACE FUNCTION yuz_il._puan(hpop double precision, own double precision, mdk double precision, sege double precision,
  w_hinter double precision, w_own double precision, w_dist double precision, w_sege double precision)
RETURNS numeric LANGUAGE sql IMMUTABLE AS $$
  SELECT round((100 * (w_hinter * yuz_il._loglin(hpop, 80000, 1000000)
                     + w_own    * yuz_il._loglin(own, 30000, 600000)
                     + w_dist   * yuz_il._lin(mdk, 30, 180)
                     + w_sege   * yuz_il._lin(sege, -1.5, 2.5))
                / coalesce(nullif(w_hinter + w_own + w_dist + w_sege, 0), 1))::numeric, 1)
$$;

-- bir ilin ilçelerini merkezlere dağıt: çekirdek → ana il; merkezin kendisi → kendisi;
-- diğerleri en kısa sürede ulaşılan merkeze (eşitlikte ana il, sonra seçilme sırası)
CREATE OR REPLACE FUNCTION yuz_il._ata(p_il text, p_centers integer[])
RETURNS TABLE (id integer, merkez integer) LANGUAGE plpgsql STABLE AS $$
BEGIN
  RETURN QUERY
  WITH ce AS (SELECT u.x, u.o FROM unnest(p_centers) WITH ORDINALITY AS u(x, o)),
  secenek AS (
    SELECT m.id, NULL::integer AS c, 0::bigint AS o, CASE WHEN m.core THEN 0 ELSE m.mdk END AS tt
    FROM _m m WHERE m.il = p_il
    UNION ALL
    SELECT m.id, ce.x, ce.o, CASE WHEN m.id = ce.x THEN 0 ELSE coalesce(y.dk, 1e9) END
    FROM _m m CROSS JOIN ce
    LEFT JOIN yuz_il.yol_sure y ON y.kaynak_id = m.id AND y.hedef_id = ce.x
    WHERE m.il = p_il AND NOT m.core
  )
  SELECT DISTINCT ON (s.id) s.id,
         CASE WHEN m.core THEN NULL WHEN m.id = ANY (p_centers) THEN m.id ELSE s.c END
  FROM secenek s JOIN _m m ON m.id = s.id
  ORDER BY s.id, s.tt, s.o;
END $$;

-- c ilçesini mevcut seçime eklemeyi dene → koşullar ve puan
CREATE OR REPLACE FUNCTION yuz_il._dene(p_c integer, p_chosen integer[], p jsonb,
  OUT uygun boolean, OUT neden text, OUT puan numeric, OUT hpop bigint, OUT parent bigint)
LANGUAGE plpgsql STABLE AS $$
DECLARE v_il text; v_centers integer[]; v_others_ok boolean; r text[] := '{}';
BEGIN
  SELECT m.il INTO v_il FROM _m m WHERE m.id = p_c;
  SELECT coalesce(array_agg(u.x ORDER BY u.o), '{}') INTO v_centers
  FROM unnest(p_chosen) WITH ORDINALITY AS u(x, o) JOIN _m m ON m.id = u.x WHERE m.il = v_il;
  v_centers := v_centers || p_c;
  WITH a AS (SELECT t.id, t.merkez, m.nufus FROM yuz_il._ata(v_il, v_centers) t JOIN _m m ON m.id = t.id)
  SELECT coalesce(sum(a.nufus) FILTER (WHERE a.merkez = p_c), 0),
         coalesce(sum(a.nufus) FILTER (WHERE a.merkez IS NULL), 0),
         coalesce((SELECT bool_and(g.n >= (p->>'min_hinter')::int)
                   FROM (SELECT sum(a2.nufus) AS n FROM a a2 WHERE a2.merkez IS NOT NULL AND a2.merkez <> p_c GROUP BY a2.merkez) g), true)
  INTO hpop, parent, v_others_ok FROM a;
  IF hpop < (p->>'min_hinter')::int THEN r := r || 'yeni il nüfusu yetersiz'::text; END IF;
  IF parent < (p->>'min_parent')::int THEN r := r || 'geride kalan il çok küçülüyor'::text; END IF;
  IF NOT v_others_ok THEN r := r || 'komşu yeni ili eşiğin altına düşürüyor'::text; END IF;
  IF (p->>'il_max')::int > 0 AND cardinality(v_centers) - 1 >= (p->>'il_max')::int THEN r := r || 'ilinden zaten yeni il çıktı'::text; END IF;
  SELECT yuz_il._puan(hpop, m.nufus, m.mdk, m.sege, (p->>'w_hinter')::float8, (p->>'w_own')::float8, (p->>'w_dist')::float8, (p->>'w_sege')::float8)
  INTO puan FROM _m m WHERE m.id = p_c;
  uygun := cardinality(r) = 0;
  neden := array_to_string(r, '; ');
END $$;

-- ana fonksiyon
CREATE OR REPLACE FUNCTION yuz_il.calistir(
  w_hinter double precision DEFAULT 35, w_own double precision DEFAULT 20,
  w_dist   double precision DEFAULT 25, w_sege double precision DEFAULT 20,
  core_km double precision DEFAULT 30, chain_density double precision DEFAULT 500, chain_link double precision DEFAULT 20,
  min_own integer DEFAULT 40000, min_hinter integer DEFAULT 150000, min_parent integer DEFAULT 250000,
  il_max integer DEFAULT 0, kota integer DEFAULT 0, n_new integer DEFAULT 19
) RETURNS SETOF yuz_il.secim LANGUAGE plpgsql AS $$
DECLARE
  p jsonb := jsonb_build_object('w_hinter', w_hinter, 'w_own', w_own, 'w_dist', w_dist, 'w_sege', w_sege,
                                'min_hinter', min_hinter, 'min_parent', min_parent, 'il_max', il_max);
  v_chosen integer[] := '{}'; v_kota integer[] := '{}';
  v_cands integer[]; best_id integer; best_puan numeric; c integer; d record; q integer; b record;
BEGIN
  -- çalışma tablosu: ilçe öznitelikleri + bu ayarlarla kent çekirdeği
  DROP TABLE IF EXISTS _m;
  CREATE TEMP TABLE _m AS
  SELECT i.id, i.il, i.bolge, i.nufus, i.il_merkez_dk AS mdk, i.sege_skor AS sege,
         (i.id IN (SELECT k.id FROM yuz_il.cekirdek(core_km, chain_density, chain_link) k)) AS core
  FROM yuz_il.ilce i;
  CREATE INDEX ON _m (il); ANALYZE _m;

  SELECT array_agg(m.id ORDER BY m.id) INTO v_cands FROM _m m WHERE NOT m.core AND m.nufus >= min_own;

  -- ilk tur: her aday tek başına il olsaydı
  TRUNCATE yuz_il.adaylar;
  INSERT INTO yuz_il.adaylar
  SELECT x, i.il, i.ilce, i.nufus, r.hpop, r.parent, r.uygun, nullif(r.neden, ''), r.puan
  FROM unnest(v_cands) x JOIN yuz_il.ilce i ON i.id = x, LATERAL yuz_il._dene(x, '{}', p) r;

  -- bölge kotası: önce her bölgeden en iyi uygun aday (tur tur)
  FOR q IN 1..kota LOOP
    FOR b IN SELECT kod FROM yuz_il.bolge ORDER BY sira LOOP
      EXIT WHEN cardinality(v_chosen) >= n_new;
      best_id := NULL;
      FOREACH c IN ARRAY v_cands LOOP
        CONTINUE WHEN c = ANY (v_chosen) OR (SELECT m.bolge FROM _m m WHERE m.id = c) <> b.kod;
        SELECT * INTO d FROM yuz_il._dene(c, v_chosen, p);
        IF d.uygun AND (best_id IS NULL OR d.puan > best_puan) THEN best_id := c; best_puan := d.puan; END IF;
      END LOOP;
      IF best_id IS NOT NULL THEN v_chosen := v_chosen || best_id; v_kota := v_kota || best_id; END IF;
    END LOOP;
  END LOOP;

  -- kalan koltuklar: her turda koşulları sağlayan en yüksek puanlı aday
  WHILE cardinality(v_chosen) < n_new LOOP
    best_id := NULL;
    FOREACH c IN ARRAY v_cands LOOP
      CONTINUE WHEN c = ANY (v_chosen);
      SELECT * INTO d FROM yuz_il._dene(c, v_chosen, p);
      IF d.uygun AND (best_id IS NULL OR d.puan > best_puan) THEN best_id := c; best_puan := d.puan; END IF;
    END LOOP;
    EXIT WHEN best_id IS NULL;
    v_chosen := v_chosen || best_id;
  END LOOP;

  -- nihai atama: her ilin ilçeleri o ilden seçilen merkezlere (seçilme sırasıyla)
  TRUNCATE yuz_il.atama;
  INSERT INTO yuz_il.atama
  SELECT a.id, m.core, a.merkez, coalesce(ci.ilce, i.il), a.merkez IS NOT NULL
  FROM (SELECT DISTINCT il FROM _m) l,
       LATERAL yuz_il._ata(l.il, coalesce((SELECT array_agg(u.x ORDER BY u.o) FROM unnest(v_chosen) WITH ORDINALITY u(x, o)
                                           JOIN _m mm ON mm.id = u.x WHERE mm.il = l.il), '{}')) a
  JOIN _m m ON m.id = a.id JOIN yuz_il.ilce i ON i.id = a.id
  LEFT JOIN yuz_il.ilce ci ON ci.id = a.merkez;

  TRUNCATE yuz_il.secim;
  INSERT INTO yuz_il.secim
  SELECT u.o, i.id, i.il, i.ilce, i.nufus, h.n, h.k, h.liste,
         (SELECT sum(ii.nufus) FROM yuz_il.atama aa JOIN yuz_il.ilce ii ON ii.id = aa.id WHERE ii.il = i.il AND aa.merkez_id IS NULL),
         yuz_il._puan(h.n, i.nufus, i.il_merkez_dk, i.sege_skor, w_hinter, w_own, w_dist, w_sege),
         i.id = ANY (v_kota),
         EXISTS (SELECT 1 FROM yuz_il.basin_listesi bl WHERE bl.il = i.il AND bl.ilce = i.ilce)
  FROM unnest(v_chosen) WITH ORDINALITY u(x, o)
  JOIN yuz_il.ilce i ON i.id = u.x,
  LATERAL (SELECT sum(ii.nufus) AS n, count(*)::int AS k,
                  string_agg(ii.ilce, ', ' ORDER BY ii.ilce) FILTER (WHERE ii.id <> i.id) AS liste
           FROM yuz_il.atama aa JOIN yuz_il.ilce ii ON ii.id = aa.id WHERE aa.merkez_id = i.id) h;

  RETURN QUERY SELECT * FROM yuz_il.secim ORDER BY sira;
END $$;
COMMENT ON FUNCTION yuz_il.calistir IS '100 İl seçim modeli: 19 yeni il seçer; sonuçları yuz_il.secim / atama / adaylar tablolarına yazar';
