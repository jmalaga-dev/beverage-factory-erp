-- =========================================================
-- MIGRACION 004: campo "habilitado" en Trabajador (mejora 6.5)
-- Por defecto TRUE: los trabajadores existentes quedan activos sin
-- necesidad de tocarlos uno por uno.
-- =========================================================

ALTER TABLE "Trabajador"
  ADD COLUMN "Habilitado_Trabajador" boolean NOT NULL DEFAULT TRUE;
