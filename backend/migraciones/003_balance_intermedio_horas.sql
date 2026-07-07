-- =========================================================
-- MIGRACION 003: agregar stock intermedio y horas standby al balance
-- =========================================================

ALTER TABLE "Balance"
  ADD COLUMN "Valor_Stock_Intermedio" numeric,
  ADD COLUMN "Valor_Horas_Standby" numeric;