-- =========================================================
-- MIGRACION 027: taxi/delivery persistido en la venta (item 8)
-- Antes el taxi era solo cálculo en pantalla (decisión 3.9): se veía el neto
-- por botella pero la venta entraba entera (ej. 900) y el taxi (ej. 50) había
-- que registrarlo aparte como gasto. Decisión de negocio revisada: el taxi
-- NO es una salida extra — sale de esas mismas botellas, así que lo que entra
-- (y se reparte 70/30) es el NETO (850). Se prorratea uniforme por botella.
--
-- Se guarda a nivel de VENTA (un taxi por venta/reparto). El precio por línea
-- (Detalle_Venta.Precio_Venta_Real) sigue siendo el BRUTO que pagó el cliente
-- (para analizar margen real: precio cobrado vs taxi vs neto, y para que una
-- devolución reembolse lo que el cliente pagó). El neto se deriva restando la
-- parte de taxi de cada botella.
--
-- Default 0: todas las ventas históricas quedan sin taxi (neto = bruto), sin
-- cambiar ningún cálculo pasado.
-- =========================================================

ALTER TABLE "Venta"
  ADD COLUMN "Taxi_Venta" numeric NOT NULL DEFAULT 0;
