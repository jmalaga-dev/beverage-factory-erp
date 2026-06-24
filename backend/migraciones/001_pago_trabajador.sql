-- =========================================================
-- MIGRACION: agregar pago semanal a trabajadores
-- =========================================================

-- 1. Nueva tabla de pagos semanales
CREATE TABLE "Pago_Trabajador" (
  "Id_Pago_Trabajador" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Trabajador" integer NOT NULL,
  "Fecha_Pago_Trabajador" date NOT NULL,
  "Monto_Sugerido_Pago" numeric,
  "Monto_Real_Pago" numeric NOT NULL,
  "Id_Movimiento" integer,
  FOREIGN KEY ("Id_Trabajador") REFERENCES "Trabajador" ("Id_Trabajador"),
  FOREIGN KEY ("Id_Movimiento") REFERENCES "Movimiento" ("Id_Movimiento")
);

-- 2. Nuevo campo en Registro_Trabajador para marcar que jornada fue pagada
ALTER TABLE "Registro_Trabajador"
  ADD COLUMN "Id_Pago_Trabajador" integer;

ALTER TABLE "Registro_Trabajador"
  ADD FOREIGN KEY ("Id_Pago_Trabajador") REFERENCES "Pago_Trabajador" ("Id_Pago_Trabajador");

-- 3. Indices para las nuevas llaves foraneas
CREATE INDEX ON "Pago_Trabajador" ("Id_Trabajador");
CREATE INDEX ON "Registro_Trabajador" ("Id_Pago_Trabajador");