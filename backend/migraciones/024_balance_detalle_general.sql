-- =========================================================
-- MIGRACION 024: detalle historico completo en la foto de balance (mejora 4.6)
--
-- Antes: `Balance_Detalle_Producto` guardaba, por cada foto, el detalle de
-- stock SOLO de producto terminado. Ni intermedio, ni materia prima, ni el
-- detalle de activos (de los activos la foto guardaba unicamente los tres
-- totales). Y ningun endpoint lo leia, asi que ese detalle nunca se veia.
--
-- Ahora: una sola tabla `Balance_Detalle` con un campo `Tipo_Detalle`, que
-- cubre los cuatro bloques. Asi agregar un bloque nuevo no pide otra tabla.
--
-- POR QUE SE GUARDA LA DESCRIPCION Y NO SOLO EL ID: una foto tiene que ser
-- autocontenida. Si dentro de un anio se renombra un producto (o se borra uno
-- que nunca se uso), la foto de hoy debe seguir diciendo como se llamaba
-- cuando se tomo. Por eso `Descripcion_Balance_Detalle` es una copia del
-- nombre en ese momento, no un JOIN al catalogo actual. Por lo mismo
-- `Id_Item_Balance_Detalle` NO lleva foreign key: apunta al catalogo que
-- corresponda segun el tipo, y no debe impedir que un item se borre despues.
--
-- Los datos existentes se copian antes del DROP: no se pierde nada.
-- =========================================================

CREATE TABLE "Balance_Detalle" (
  "Id_Balance_Detalle" serial PRIMARY KEY,
  "Id_Balance" integer NOT NULL REFERENCES "Balance"("Id_Balance"),
  "Tipo_Detalle" varchar NOT NULL
    CHECK ("Tipo_Detalle" IN ('MP', 'INTERMEDIO', 'TERMINADO', 'ACTIVO')),
  "Id_Item_Balance_Detalle" integer NOT NULL,
  "Descripcion_Balance_Detalle" varchar NOT NULL,
  "Cantidad_Balance_Detalle" numeric,
  "Valor_Balance_Detalle" numeric NOT NULL
);

CREATE INDEX "idx_balance_detalle_balance"
  ON "Balance_Detalle" ("Id_Balance", "Tipo_Detalle");

-- Copiar el detalle ya guardado (solo habia de producto terminado). La
-- descripcion se toma del catalogo actual: es lo mas fiel disponible hoy,
-- porque el nombre historico no se guardaba.
INSERT INTO "Balance_Detalle" (
  "Id_Balance", "Tipo_Detalle", "Id_Item_Balance_Detalle",
  "Descripcion_Balance_Detalle", "Cantidad_Balance_Detalle", "Valor_Balance_Detalle"
)
SELECT
  d."Id_Balance",
  'TERMINADO',
  d."Id_Producto_Terminado",
  COALESCE(pt."Descripcion_Producto_Terminado", '(producto ' || d."Id_Producto_Terminado" || ')'),
  d."Cantidad_En_Stock",
  d."Valor_En_Stock"
FROM "Balance_Detalle_Producto" d
LEFT JOIN "Producto_Terminado" pt
  ON pt."Id_Producto_Terminado" = d."Id_Producto_Terminado";

DROP TABLE "Balance_Detalle_Producto";
