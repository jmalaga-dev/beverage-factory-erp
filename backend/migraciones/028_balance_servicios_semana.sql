-- =========================================================
-- MIGRACION 028: los servicios pasan a ser su propia linea del balance
--
-- Los gastos extra recurrentes (los servicios: el catalogo Gasto_Extra y su
-- monto real de cada mes en Gasto_Extra_Mes) se sumaban dentro de "Gastos de
-- la semana", mezclados con el gasto suelto del dia a dia. Pasan a tener linea
-- propia, igual que las compras y los pagos a trabajadores: son otra forma en
-- que sale la plata, con su tabla propia y su vinculo propio con Movimiento.
--
-- Con esto "Gastos" queda definido como el RESIDUO: la salida que no es
-- compra, ni pago a trabajador, ni servicio. Mismo criterio de la decision
-- "categorizar sin adivinar" (DECISIONES_DISENO 4): se separa por el vinculo
-- real de cada tabla con Movimiento, no adivinando por el texto.
--
-- El monto de la linea sale de Gasto_Extra_Mes, no del libro de movimientos:
-- hay meses pagados que nunca generaron un Movimiento (los que vinieron de la
-- migracion del sistema anterior), asi que contarlos desde Movimiento perderia
-- esa parte de la historia. Es lo mismo que ya hacen las compras, que se suman
-- desde Compra y cuentan aunque no tengan Id_Movimiento.
--
-- NULL, no 0: las fotos de balance anteriores a esta columna no tienen el
-- dato. Con 0 la comparativa mostraria una caida inventada; con NULL muestra
-- "—". Misma convencion que Pagos_Semana y Valor_Utensilios_Sin_Absorber.
-- =========================================================

ALTER TABLE "Balance"
  ADD COLUMN IF NOT EXISTS "Servicios_Semana" numeric;
