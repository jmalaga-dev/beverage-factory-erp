-- =========================================================
-- MIGRACION 005: columna Pagos_Semana en Balance (mejora 4.1)
-- Antes los pagos a trabajadores se mezclaban con Compras_Semana (bug).
-- Ahora se separan y se guardan aparte, igual que Ventas/Compras/Gastos.
-- =========================================================

ALTER TABLE "Balance"
  ADD COLUMN "Pagos_Semana" numeric;
