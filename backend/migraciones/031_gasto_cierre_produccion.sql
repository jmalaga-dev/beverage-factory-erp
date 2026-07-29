-- =========================================================
-- MIGRACION 031: gastos de fabrica prorrateados en el cierre de produccion
--
-- Caso que la motiva: hay un grupo de gastos que son extras que se le dan al
-- trabajador ademas del sueldo, sin ser insumo de produccion. Hoy son una
-- SALIDA como cualquier otra: salen de la caja y cuentan como gasto de la
-- semana, pero NO tocan el costo de ninguna botella. Lo que se busca es que
-- los absorba el producto que se produjo esa semana -- exactamente lo que ya
-- hace el cierre de produccion (mejora 3.7) con las horas standby.
--
-- 1) Prorratea_Cierre_Produccion en Grupo_Movimiento
--    Marca que los gastos de ese grupo entran al cierre de produccion.
--
--    Es una COLUMNA y no un match por nombre a proposito. El mismo movimiento
--    que hizo la mejora 4.2, cuando reemplazo el 'ilike' sobre el nombre del
--    tipo de bien por una categoria explicita: la logica no puede depender de
--    como este escrita una etiqueta. Asi el grupo se puede renombrar (a lo
--    que sea) desde el catalogo sin tocar codigo
--    -- las relaciones son por Id, renombrar no corrompe el historial (6.1) --
--    y se puede marcar mas de un grupo si aparecen otros gastos con la misma
--    naturaleza.
--
--    Default FALSE: ningun grupo cambia de comportamiento por esta migracion.
--    El usuario marca el que corresponda desde Catalogos.
--
-- 2) Gasto_Cierre_Produccion: el LIBRO de que gasto se repartio, a que lote y
--    por cuanto. Calcado de Absorcion_Produccion (migracion 014), y por los
--    mismos dos motivos:
--      a) EVITA EL DOBLE CONTEO, que es el riesgo central de esta mejora. Un
--         movimiento que ya figura en el libro no se vuelve a repartir, asi
--         que re-correr el cierre es seguro -- igual que ya lo es con las
--         horas standby, que al consumirse dejan su saldo en cero.
--      b) Deja la trazabilidad: a que lotes fue a parar cada gasto.
--
-- NOTA CONTABLE (la misma de la absorcion 1.4): el gasto YA bajo el efectivo
-- cuando se registro; al sumarlo al costo del lote, sube el valor del stock.
-- El neto en patrimonio es ~0 mientras no se venda, y recien al vender se
-- vuelve costo real. Es el comportamiento buscado y NO es doble conteo del
-- gasto: en el libro de movimientos sigue habiendo uno solo. Tampoco se cruza
-- con el prorrateo mensual (que lee Gasto_Extra_Mes) ni con la absorcion (que
-- lee Item_Absorcion): ninguno de los dos mira Movimiento.
-- =========================================================

ALTER TABLE "Grupo_Movimiento"
  ADD COLUMN "Prorratea_Cierre_Produccion" boolean NOT NULL DEFAULT FALSE;

CREATE TABLE "Gasto_Cierre_Produccion" (
  "Id_Gasto_Cierre_Produccion" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Movimiento" integer NOT NULL REFERENCES "Movimiento"("Id_Movimiento"),
  "Id_Produccion" integer NOT NULL REFERENCES "Produccion"("Id_Produccion"),
  "Monto_Asignado" numeric NOT NULL,
  "Fecha_Cierre" date NOT NULL
);

-- El filtro caliente del motor es "¿este movimiento ya se repartio?".
CREATE INDEX "idx_gasto_cierre_movimiento"
  ON "Gasto_Cierre_Produccion" ("Id_Movimiento");
