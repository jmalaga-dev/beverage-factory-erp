-- =========================================================
-- MIGRACION 023: unidad de medida en Producto_Intermedio (mejora 6.14)
-- Un producto intermedio no decia en que unidad estaba medido: en las tablas
-- se veia un "30" sin saber si eran litros, unidades o kilos. La columna es
-- SOLO una etiqueta descriptiva: el sistema nunca convierte unidades de
-- intermedios (se produce X y se consume X en la misma unidad, siempre), asi
-- que esto no toca costeo ni stock.
--
-- No confundir con Litros_Botella_Final, que ya existia y es otra cosa (un
-- dato de la botella final, no la unidad en que se mide el intermedio).
--
-- Default LITRO: es la unidad de la mayoria de los intermedios (liquidos).
-- Los que no lo sean se corrigen a mano desde el catalogo, uno por uno; no
-- hay forma de adivinarlo por el nombre sin arriesgar clasificar mal, y a
-- diferencia de la migracion 006 aca no hay un criterio previo que replicar.
-- =========================================================

ALTER TABLE "Producto_Intermedio"
  ADD COLUMN "Unidad_Producto_Intermedio" varchar NOT NULL DEFAULT 'LITRO'
  CHECK ("Unidad_Producto_Intermedio" IN ('LITRO', 'UNIDAD', 'KG'));
