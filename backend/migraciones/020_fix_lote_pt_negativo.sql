-- =========================================================
-- MIGRACION 020: corregir lotes de producto terminado que quedaron en stock
-- negativo tras la migracion del Excel (mejora 8.4)
--
-- El Excel no tenia restriccion de stock: su macro podia descontar la venta
-- de un lote aunque ese lote ya estuviera agotado, dejandolo con restante
-- negativo, y no descontarla del lote que si tenia las botellas (que queda
-- inflado). La venta es un hecho (el cliente se llevo las botellas); lo que
-- estaba mal era a que lote se le atribuia.
--
-- Se reasignan las ventas de exceso -las que caen despues de agotar la
-- capacidad del lote, en orden cronologico- al siguiente lote del MISMO
-- producto que tenga stock. Luego se recalcula el restante de cada lote
-- tocado desde sus ventas reales (producido - vendido).
--
-- Por que importa: el balance ignora los restantes negativos (filtra
-- > UMBRAL_STOCK_MINIMO), pero SI valorizaba las botellas del lote inflado
-- que no existen. Esto corrige esa sobrevaloracion.
--
-- Generico e idempotente: opera sobre cualquier lote negativo (no sobre uno
-- fijo); si no hay ninguno, no hace nada. Es la misma logica que el bloque 5b
-- de migrar_excel_v2.py, que ya la aplica en la corrida; esta migracion la
-- deja tambien como paso reproducible aparte.
-- =========================================================

DO $$
DECLARE
    r RECORD;
    id_destino integer;
BEGIN
    -- Un lote negativo por vez, del mas antiguo al mas nuevo.
    FOR r IN
        SELECT "Id_Produccion", "Id_Producto_Terminado", "Fecha_Produccion",
               "Cantidad_Producida_Produccion" AS producido
        FROM "Produccion"
        WHERE "Cantidad_Restante_Produccion" < 0
        ORDER BY "Fecha_Produccion"
    LOOP
        -- Siguiente lote del mismo producto, con stock, no anterior al negativo.
        SELECT "Id_Produccion" INTO id_destino
        FROM "Produccion"
        WHERE "Id_Producto_Terminado" = r."Id_Producto_Terminado"
          AND "Fecha_Produccion" >= r."Fecha_Produccion"
          AND "Id_Produccion" <> r."Id_Produccion"
          AND "Cantidad_Restante_Produccion" > 0
        ORDER BY "Fecha_Produccion"
        LIMIT 1;

        IF id_destino IS NULL THEN
            CONTINUE;  -- no hay a donde mover; se deja como esta
        END IF;

        -- Mover las lineas de venta de exceso al lote destino.
        UPDATE "Detalle_Venta" dv
        SET "Id_Produccion" = id_destino
        WHERE dv."Id_Detalle_Venta" IN (
            SELECT d."Id_Detalle_Venta"
            FROM (
                SELECT dv2."Id_Detalle_Venta",
                       SUM(dv2."Cantidad_Venta") OVER (
                           ORDER BY v2."Fecha_Venta", dv2."Id_Detalle_Venta"
                       ) AS acumulado
                FROM "Detalle_Venta" dv2
                JOIN "Venta" v2 ON v2."Id_Venta" = dv2."Id_Venta"
                WHERE dv2."Id_Produccion" = r."Id_Produccion"
            ) d
            WHERE d.acumulado > r.producido
        );

        -- Recalcular el restante de origen y destino desde sus ventas reales.
        UPDATE "Produccion" p
        SET "Cantidad_Restante_Produccion" = p."Cantidad_Producida_Produccion" - COALESCE((
                SELECT SUM(dv."Cantidad_Venta") FROM "Detalle_Venta" dv
                WHERE dv."Id_Produccion" = p."Id_Produccion"
            ), 0)
        WHERE p."Id_Produccion" IN (r."Id_Produccion", id_destino);
    END LOOP;
END $$;
