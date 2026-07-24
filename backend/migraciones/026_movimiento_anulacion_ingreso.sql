-- =========================================================
-- MIGRACION 026: anulacion de ingreso externo (item 10a)
-- Poder deshacer un ingreso externo mal cargado (ej. cargado dos veces) SIN
-- borrar el movimiento original (inmutabilidad del libro de movimientos): se
-- registra un movimiento INVERSO que devuelve el dinero (baja el saldo de la
-- cuenta) y queda enlazado al original. Quedan las dos filas: el ingreso y su
-- anulacion, con rastro completo.
--
-- 1) Nuevo Tipo_Movimiento 'ANULACION_INGRESO_EXTERNO'. Necesita su propio
--    valor (no 'SALIDA') para que el balance no lo cuente como gasto de la
--    semana -- mismo criterio que INGRESO_EXTERNO (migracion 010) y PAGO_DEUDA
--    (012): los gastos son las SALIDA sin vinculo a compra/pago.
-- 2) Columna Id_Movimiento_Anulado: enlaza la anulacion con el ingreso que
--    cancela. Permite marcar un ingreso como "ya anulado" (no volver a
--    anularlo) y leer el par en el historial.
-- =========================================================

ALTER TABLE "Movimiento"
  DROP CONSTRAINT "Movimiento_Tipo_Movimiento_check";

ALTER TABLE "Movimiento"
  ADD CONSTRAINT "Movimiento_Tipo_Movimiento_check"
  CHECK ("Tipo_Movimiento" IN (
    'ENTRADA', 'SALIDA', 'TRANSFERENCIA', 'INGRESO_EXTERNO', 'PAGO_DEUDA',
    'ANULACION_INGRESO_EXTERNO'
  ));

ALTER TABLE "Movimiento"
  ADD COLUMN "Id_Movimiento_Anulado" integer REFERENCES "Movimiento"("Id_Movimiento");
