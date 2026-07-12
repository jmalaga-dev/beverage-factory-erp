-- =========================================================
-- MIGRACION 016: recetas tambien para producto terminado (mejora 3.6, ampliada)
--
-- Una Receta ahora puede producir un producto INTERMEDIO o un producto
-- TERMINADO (antes solo intermedio). Se agrega el tipo y la FK al terminado;
-- Id_Producto_Intermedio pasa a nullable (se usa solo cuando el tipo es
-- INTERMEDIO). Las recetas existentes quedan como INTERMEDIO (default).
-- =========================================================

ALTER TABLE "Receta"
  ADD COLUMN "Tipo_Receta" varchar NOT NULL DEFAULT 'INTERMEDIO'
  CHECK ("Tipo_Receta" IN ('INTERMEDIO', 'TERMINADO'));

ALTER TABLE "Receta"
  ADD COLUMN "Id_Producto_Terminado" integer;

ALTER TABLE "Receta"
  ALTER COLUMN "Id_Producto_Intermedio" DROP NOT NULL;

ALTER TABLE "Receta"
  ADD FOREIGN KEY ("Id_Producto_Terminado") REFERENCES "Producto_Terminado" ("Id_Producto_Terminado");
