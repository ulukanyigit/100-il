-- 100 İl — kent çekirdeği
-- İl merkezine yol mesafesi core_km'den az olan ilçeler çekirdektir. Buna ek olarak yoğunluğu chain_density'den
-- yüksek olup çekirdekteki bir ilçeye chain_link dakikadan yakın ilçeler de, zincir uzadıkça, çekirdeğe katılır
-- (Pendik, Esenyurt gibi kesintisiz kent dokusu). Çekirdek ilçeler il adayı olamaz, ana ilde kalır.

CREATE OR REPLACE FUNCTION yuz_il.cekirdek(
  core_km       double precision DEFAULT 30,
  chain_density double precision DEFAULT 500,
  chain_link    double precision DEFAULT 20
) RETURNS TABLE (id integer)
LANGUAGE sql STABLE AS $$
  WITH RECURSIVE c(id) AS (
    SELECT i.id FROM yuz_il.ilce i WHERE i.il_merkez_km <= core_km
    UNION
    SELECT j.id
    FROM c
    JOIN yuz_il.yol_sure y ON y.hedef_id = c.id AND y.dk <= chain_link   -- j'den çekirdekteki ilçeye süre
    JOIN yuz_il.ilce j     ON j.id = y.kaynak_id
    WHERE j.nufus / j.alan_km2 >= chain_density
  )
  SELECT c.id FROM c;
$$;
COMMENT ON FUNCTION yuz_il.cekirdek IS 'Kent çekirdeği: il merkezine ≤ core_km + yoğun ve çekirdeğe ≤ chain_link dk bitişik ilçeler (özyinelemeli)';

-- örnek: zincirle çekirdeğe katılan ilçeler (mesafe ölçütünü geçemeyip yoğunluk zinciriyle eklenenler)
-- SELECT i.il, i.ilce, i.il_merkez_km FROM yuz_il.cekirdek() c JOIN yuz_il.ilce i USING (id)
-- WHERE i.il_merkez_km > 30 ORDER BY i.il, i.ilce;
