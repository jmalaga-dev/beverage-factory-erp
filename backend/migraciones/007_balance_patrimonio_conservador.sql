-- =========================================================
-- MIGRACION 007: patrimonio contable puro (mejora 4.3)
-- Antes, "Patrimonio" era simplemente un alias de Escenario A (efectivo +
-- stocks valorizados + activos fijos - deudas), y el stock de producto
-- terminado ahi se valoraba a Precio_Venta_Recomendado, es decir, incluyendo
-- la ganancia todavia no realizada de lo que no se vendio.
--
-- Ahora se distinguen dos cosas:
--  - Escenario A/B/C: vistas de liquidez ("cuanto tendria si liquido"),
--    sin cambios, stock terminado sigue a precio de venta.
--  - Patrimonio: cifra contable conservadora, stock terminado valorado al
--    MENOR entre costo de produccion y precio de venta (criterio "costo o
--    mercado, el menor"). Ya no es un alias de Escenario A.
--
-- Esta columna nueva guarda esa valorizacion conservadora para que la foto
-- historica deje ver por que Patrimonio difiere de Escenario A (mismo
-- criterio de transparencia que 006 con Inmuebles/Equipos/Otros).
-- =========================================================

ALTER TABLE "Balance"
  ADD COLUMN "Valor_Stock_Producto_Terminado_Conservador" numeric;
