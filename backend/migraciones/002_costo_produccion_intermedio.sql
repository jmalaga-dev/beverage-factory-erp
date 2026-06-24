-- =========================================================
-- MIGRACION 002: agregar costo unitario a produccion intermedia
-- =========================================================

ALTER TABLE "Produccion_Intermedio"
  ADD COLUMN "Costo_Unitario_Produccion_Intermedio" numeric;