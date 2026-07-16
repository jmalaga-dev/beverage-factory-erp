-- =========================================================
-- MIGRACION 020: corregir el lote de producto terminado que quedo en
-- stock negativo tras la migracion del Excel (mejora 8.4)
--
-- El Excel no tenia restriccion de stock: su macro descontaba la venta de
-- un lote aunque ese lote ya estuviera agotado. Resultado: SOBAQUERA VODKA
-- STERN produjo 228 botellas el 08/07/2023 (lote A) pero se le descontaron
-- 290 ventas -> restante -62; y el lote del 12/07/2023 (lote B) quedo con
-- 112 cuando fisicamente solo hay 50. Los 62 sobrantes son los mismos: las
-- ultimas ventas salieron del lote B, no del A.
--
-- La venta es un hecho (el cliente se llevo las botellas); lo que estaba mal
-- era a que lote se le atribuian. Se reasignan cronologicamente: el acumulado
-- de ventas del lote A llega a 228 -exactamente su capacidad- en una linea, y
-- las dos siguientes (ambas del 2025-04-05, de 52 y 10 botellas) suman los 62
-- de exceso. El corte cae justo en un limite de linea, asi que no hay que
-- partir ninguna venta.
--
-- Por que importa: el balance ignora los restantes negativos (filtra
-- > UMBRAL_STOCK_MINIMO), pero SI valorizaba las 112 botellas del lote B a
-- precio de venta cuando solo existen 50. Esto corrige esa sobrevaloracion.
--
-- Idempotente: si los detalles ya apuntan al lote B, los UPDATE no encuentran
-- filas y el recalculo de restantes da el mismo resultado.
-- =========================================================

-- 1) Reasignar las ventas de exceso del lote agotado al lote que si tenia stock.
UPDATE "Detalle_Venta" dv
SET "Id_Produccion" = destino."Id_Produccion"
FROM "Produccion" origen,
     "Produccion" destino
WHERE dv."Id_Produccion" = origen."Id_Produccion"
  AND origen."Id_Producto_Terminado" = destino."Id_Producto_Terminado"
  AND origen."Fecha_Produccion" = DATE '2023-07-08'
  AND destino."Fecha_Produccion" = DATE '2023-07-12'
  AND origen."Id_Producto_Terminado" = (
      SELECT "Id_Producto_Terminado" FROM "Producto_Terminado"
      WHERE "Descripcion_Producto_Terminado" = 'SOBAQUERA VODKA STERN')
  -- solo las lineas de exceso: las que caen despues de agotar la capacidad
  -- del lote origen, en orden cronologico.
  AND dv."Id_Detalle_Venta" IN (
      SELECT d."Id_Detalle_Venta"
      FROM (
          SELECT dv2."Id_Detalle_Venta",
                 SUM(dv2."Cantidad_Venta") OVER (
                     ORDER BY v2."Fecha_Venta", dv2."Id_Detalle_Venta"
                 ) AS acumulado
          FROM "Detalle_Venta" dv2
          JOIN "Venta" v2 ON v2."Id_Venta" = dv2."Id_Venta"
          WHERE dv2."Id_Produccion" = origen."Id_Produccion"
      ) d
      WHERE d.acumulado > origen."Cantidad_Producida_Produccion"
  );

-- 2) Recalcular el restante de los dos lotes desde sus ventas reales.
--    (producido - vendido; el Excel guardaba este numero, aca se deriva)
UPDATE "Produccion" p
SET "Cantidad_Restante_Produccion" = p."Cantidad_Producida_Produccion" - COALESCE((
        SELECT SUM(dv."Cantidad_Venta") FROM "Detalle_Venta" dv
        WHERE dv."Id_Produccion" = p."Id_Produccion"
    ), 0)
WHERE p."Id_Producto_Terminado" = (
        SELECT "Id_Producto_Terminado" FROM "Producto_Terminado"
        WHERE "Descripcion_Producto_Terminado" = 'SOBAQUERA VODKA STERN')
  AND p."Fecha_Produccion" IN (DATE '2023-07-08', DATE '2023-07-12');
