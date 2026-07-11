-- =========================================================
-- MIGRACION 010: tipo INGRESO_EXTERNO en Movimiento (mejora 7.5)
-- El esquema base ya preveia TRANSFERENCIA (mover dinero entre cuentas
-- propias) en el CHECK de Tipo_Movimiento, pero faltaba un tipo para
-- dinero que entra desde fuera de la fabrica (aporte externo) sin ser
-- una venta. Usar "ENTRADA" para esto lo mezclaria con las ventas de la
-- semana en el balance (suma_movimientos("ENTRADA", ...) en balance.py),
-- por eso necesita su propio valor.
-- =========================================================

ALTER TABLE "Movimiento"
  DROP CONSTRAINT "Movimiento_Tipo_Movimiento_check";

ALTER TABLE "Movimiento"
  ADD CONSTRAINT "Movimiento_Tipo_Movimiento_check"
  CHECK ("Tipo_Movimiento" IN ('ENTRADA', 'SALIDA', 'TRANSFERENCIA', 'INGRESO_EXTERNO'));
