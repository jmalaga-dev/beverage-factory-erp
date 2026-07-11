-- =========================================================
-- MIGRACION 011: proveedores (mejora 5.1 base)
-- Antes una Compra no sabia de quien se compro. Se agrega:
--   - Proveedor: el catalogo de proveedores, con contacto y ubicacion
--     (lat/long, para el futuro ruteo con Maps, mismo patron que Cliente).
--   - Proveedor_Materia_Prima: que proveedor vende que materia prima.
--     Tabla puente para poder habilitar/deshabilitar por par (ej. Juan
--     deja de vender azucar pero sigue vendiendo alcohol) sin perder el
--     historial. UNIQUE por par evita duplicar la misma relacion.
--   - Compra.Id_Proveedor: de quien se compro este lote. Nullable: las
--     compras historicas (previas a esta migracion) no tienen proveedor
--     conocido. En el flujo nuevo, el servicio de compra lo exige cuando
--     la materia prima ya tiene proveedores registrados.
-- =========================================================

CREATE TABLE "Proveedor" (
  "Id_Proveedor" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Proveedor" varchar NOT NULL,
  "Celular_Proveedor" varchar,
  "Latitud_Proveedor" numeric,
  "Longitud_Proveedor" numeric,
  "Habilitado_Proveedor" boolean NOT NULL DEFAULT TRUE
);

CREATE TABLE "Proveedor_Materia_Prima" (
  "Id_Proveedor_Materia_Prima" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Proveedor" integer NOT NULL,
  "Id_Materia_Prima" integer NOT NULL,
  "Habilitado_Proveedor_Materia_Prima" boolean NOT NULL DEFAULT TRUE,
  UNIQUE ("Id_Proveedor", "Id_Materia_Prima")
);

ALTER TABLE "Compra"
  ADD COLUMN "Id_Proveedor" integer;

ALTER TABLE "Proveedor_Materia_Prima"
  ADD FOREIGN KEY ("Id_Proveedor") REFERENCES "Proveedor" ("Id_Proveedor");
ALTER TABLE "Proveedor_Materia_Prima"
  ADD FOREIGN KEY ("Id_Materia_Prima") REFERENCES "Materia_Prima" ("Id_Materia_Prima");
ALTER TABLE "Compra"
  ADD FOREIGN KEY ("Id_Proveedor") REFERENCES "Proveedor" ("Id_Proveedor");
