-- =========================================================
-- MIGRACION 030: anular una SALIDA con movimiento inverso (bloque B)
--
-- Caso que la motiva: un gasto del mes (luz, telefono...) se pago por un monto
-- equivocado -- "pague 10 y eran 20", o eran 5 y sobran 5. Hasta ahora no habia
-- salida: registrar_monto_mes rechaza cambiar el monto de un gasto ya pagado, y
-- no existia forma de deshacer el pago. La unica alternativa era inventar un
-- gasto o un ingreso falso para compensar, ensuciando el historial.
--
-- Se resuelve con el MISMO criterio que la anulacion de ingreso externo
-- (migracion 026, item 10a): no se borra nada, se registra un movimiento
-- INVERSO que devuelve el dinero a la cuenta y queda enlazado al original por
-- Id_Movimiento_Anulado (columna que ya existe desde la 026). Quedan las dos
-- filas -- el pago y su anulacion -- con rastro completo. Despues se corrige el
-- monto y se vuelve a pagar.
--
-- 1) Nuevo Tipo_Movimiento 'ANULACION_SALIDA'. Necesita su propio valor y no
--    'ENTRADA': si fuera ENTRADA, el balance lo contaria como VENTA de la
--    semana (ventas_semana = suma de las ENTRADA). Mismo criterio que
--    INGRESO_EXTERNO (010), PAGO_DEUDA (012) y ANULACION_INGRESO_EXTERNO (026):
--    cada concepto tiene su tipo, el balance no adivina.
--
--    El nombre es generico (ANULACION_SALIDA, no ANULACION_PAGO_GASTO_MES)
--    porque el mecanismo es identico para cualquier SALIDA. Hoy el unico punto
--    de entrada es el controlado -- anular_pago_gasto_mes(), que valida que el
--    movimiento pertenezca a un Gasto_Extra_Mes -- pero la regla del balance de
--    abajo ya queda escrita para cualquier SALIDA anulada.
--
-- 2) IMPORTANTE, el efecto que casi se escapa: al anular, el Gasto_Extra_Mes
--    deja de estar pagado y se le limpia el Id_Movimiento. Eso deja la SALIDA
--    original SIN VINCULO, y la definicion de "gasto" del balance es
--    justamente "SALIDA que no es compra, ni pago, ni servicio" (4.1 + 10.25).
--    Sin tratamiento, un pago de servicio anulado se convertiria por descarte
--    en un GASTO de la semana: el dinero vuelve a la cuenta y ademas aparece
--    una linea de gasto que nunca existio.
--
--    Por eso balance.py (las dos rutas: resumen en vivo y foto congelada) ahora
--    excluye de "gastos" toda SALIDA que tenga una anulacion apuntandole. Una
--    salida cancelada no es un gasto. No hace falta excluir la anulacion en si:
--    no es SALIDA ni ENTRADA, su tipo propio la deja fuera de las dos sumas.
--
--    Las fotos de Balance ya tomadas NO cambian (inmutabilidad del historico):
--    si una foto se tomo cuando el gasto estaba pagado, ese dia estaba pagado.
--
-- Sin cambios de columnas: Id_Movimiento_Anulado ya existe (026). Esta
-- migracion solo amplia el CHECK de tipos.
-- =========================================================

ALTER TABLE "Movimiento"
  DROP CONSTRAINT IF EXISTS "Movimiento_Tipo_Movimiento_check";

ALTER TABLE "Movimiento"
  ADD CONSTRAINT "Movimiento_Tipo_Movimiento_check"
  CHECK ("Tipo_Movimiento" IN (
    'ENTRADA', 'SALIDA', 'TRANSFERENCIA', 'INGRESO_EXTERNO', 'PAGO_DEUDA',
    'ANULACION_INGRESO_EXTERNO', 'ANULACION_SALIDA'
  ));
