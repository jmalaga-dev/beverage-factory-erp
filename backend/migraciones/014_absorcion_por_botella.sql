-- =========================================================
-- MIGRACION 014: absorcion de costos indirectos por botella (mejora 1.4)
--
-- Ciertos costos que no son insumos directos deben ser "absorbidos" de a poco
-- por las botellas producidas, para que nada quede sin que alguien lo pague
-- (replica la logica del Excel):
--   - UTENSILIO: un equipo/utensilio menor (ej. un barril de roble). Se
--     compra (sale dinero) y su costo se reparte entre las botellas que se
--     produzcan despues. Decision de negocio (jul 2026): un utensilio va SOLO
--     a absorcion, no a Activo fijo — asi no se cuenta dos veces (un solo
--     camino por compra).
--   - FERIADO: horas pagadas al trabajador sin produccion a cambio; su costo
--     lo absorben las botellas siguientes.
--   - MERMA: el costo del stock perdido en una merma tambien se absorbe.
--
-- Item_Absorcion: cada costo a absorber. Botellas_Estimadas es cuantas
-- botellas se estima que lo cubriran (costo/botellas_estimadas = Bs por
-- botella); Botellas_Restantes baja con cada produccion hasta 0 (ahi el item
-- queda saldado y deja de cargar a la produccion).
--
-- Absorcion_Produccion: el libro de que produccion absorbio cuanto de cada
-- item (historico inmutable, para trazar el costo de cada lote producido).
-- =========================================================

CREATE TABLE "Item_Absorcion" (
  "Id_Item_Absorcion" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Tipo_Item_Absorcion" varchar NOT NULL
      CHECK ("Tipo_Item_Absorcion" IN ('UTENSILIO', 'FERIADO', 'MERMA')),
  "Descripcion_Item_Absorcion" varchar NOT NULL,
  "Costo_Item_Absorcion" numeric NOT NULL,
  "Botellas_Estimadas_Item_Absorcion" numeric NOT NULL,
  "Botellas_Restantes_Item_Absorcion" numeric NOT NULL,
  "Fecha_Item_Absorcion" date NOT NULL
);

CREATE TABLE "Absorcion_Produccion" (
  "Id_Absorcion_Produccion" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Item_Absorcion" integer NOT NULL,
  "Id_Produccion" integer NOT NULL,
  "Botellas_Absorbidas" numeric NOT NULL,
  "Monto_Absorbido" numeric NOT NULL
);

ALTER TABLE "Absorcion_Produccion"
  ADD FOREIGN KEY ("Id_Item_Absorcion") REFERENCES "Item_Absorcion" ("Id_Item_Absorcion");
ALTER TABLE "Absorcion_Produccion"
  ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
