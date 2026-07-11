-- =========================================================
-- MIGRACION 012: tipo PAGO_DEUDA en Movimiento (mejoras 7.0/7.3)
-- Pagar (amortizar) una deuda saca dinero de una cuenta. Ese egreso debe
-- quedar en el libro de movimientos (auditoria de caja), pero NO debe
-- contarse como "gasto de la semana" en el balance: el balance calcula los
-- gastos como las SALIDA que no son compra ni pago a trabajador (mejora
-- 4.1), asi que una SALIDA por pago de deuda se colaria como gasto. Por eso
-- el pago de deuda usa su propio tipo, excluido de esos calculos.
--
-- El desembolso de un prestamo (dinero que ENTRA a una cuenta al tomar la
-- deuda) reutiliza INGRESO_EXTERNO (migracion 010), que ya esta excluido de
-- las ventas de la semana. La deuda simple (interes, o un gasto que alguien
-- pago por nosotros) no genera Movimiento de caja: solo sube el pasivo.
-- =========================================================

ALTER TABLE "Movimiento"
  DROP CONSTRAINT "Movimiento_Tipo_Movimiento_check";

ALTER TABLE "Movimiento"
  ADD CONSTRAINT "Movimiento_Tipo_Movimiento_check"
  CHECK ("Tipo_Movimiento" IN ('ENTRADA', 'SALIDA', 'TRANSFERENCIA', 'INGRESO_EXTERNO', 'PAGO_DEUDA'));
