-- =========================================================
-- MIGRACION 017: fusionar insumos duplicados en las recetas (mejora 3.6)
--
-- Recetas creadas antes del fix guardaban el mismo insumo (ej. Azucar) en
-- varias filas de Receta_Detalle. Ahora el guardado los fusiona, pero los
-- ya guardados quedaron duplicados. Esta limpieza suma las cantidades en una
-- sola fila por (receta, tipo, insumo) y borra las repetidas. Es segura:
-- aplicar_receta ya sumaba estos duplicados al resolver FIFO, asi que el
-- comportamiento no cambia; solo queda mas limpio el almacenamiento y la
-- vista. Idempotente: si no hay duplicados, no hace nada.
-- =========================================================

-- 1) En la fila que se conserva (la de menor id por grupo), poner la suma.
UPDATE "Receta_Detalle" rd
SET "Cantidad_Receta" = sub.total
FROM (
  SELECT MIN("Id_Receta_Detalle") AS keep_id,
         SUM("Cantidad_Receta") AS total
  FROM "Receta_Detalle"
  GROUP BY "Id_Receta", "Tipo_Insumo_Receta",
           COALESCE("Id_Materia_Prima", -1), COALESCE("Id_Producto_Intermedio", -1)
) sub
WHERE rd."Id_Receta_Detalle" = sub.keep_id;

-- 2) Borrar las filas duplicadas (todas menos la conservada de cada grupo).
DELETE FROM "Receta_Detalle"
WHERE "Id_Receta_Detalle" NOT IN (
  SELECT MIN("Id_Receta_Detalle")
  FROM "Receta_Detalle"
  GROUP BY "Id_Receta", "Tipo_Insumo_Receta",
           COALESCE("Id_Materia_Prima", -1), COALESCE("Id_Producto_Intermedio", -1)
);
