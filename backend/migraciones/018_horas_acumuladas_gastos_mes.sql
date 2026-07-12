-- =========================================================
-- MIGRACION 018: horas acumuladas en cadena + gastos extra variables por mes
-- (mejora 1.1)
--
-- 1) HORAS ACUMULADAS (motor de horas heredadas):
--    Cada produccion "recuerda" cuantas horas-hombre lleva embebidas:
--      horas directas (jornadas) + horas heredadas de los intermedios que
--      consumio. Al consumir q unidades de un lote, se hereda
--      q * (Horas_Acumuladas / Cantidad_Producida) del lote origen (tasa por
--      unidad constante). Asi un terminado sabe directo cuantas horas-hombre le
--      corresponden, y el prorrateo mensual es una suma en vez de una recursion.
--    - En Produccion_Intermedio se llena al producir (directas + heredadas).
--    - En Produccion (terminado) se llena con las heredadas al producir, y el
--      cierre semanal (3.7) le suma las horas directas que asigna.
--
-- 2) GASTOS EXTRA VARIABLES POR MES (Gasto_Extra_Mes):
--    La factura de luz/agua/internet cambia cada mes y se paga (normalmente a
--    fin de mes). Gasto_Extra guarda el gasto recurrente (y su monto tipico);
--    Gasto_Extra_Mes guarda el MONTO REAL de un mes concreto y su pago (fecha,
--    cuenta y el Movimiento de SALIDA). El prorrateo mensual reparte esos
--    montos entre los terminados segun sus horas, y solo se puede correr cuando
--    todos los gastos del mes estan pagados.
-- =========================================================

ALTER TABLE "Produccion_Intermedio"
  ADD COLUMN "Horas_Acumuladas" numeric;

ALTER TABLE "Produccion"
  ADD COLUMN "Horas_Acumuladas" numeric;

CREATE TABLE "Gasto_Extra_Mes" (
  "Id_Gasto_Extra_Mes" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Gasto_Extra" integer NOT NULL,
  "Anio_Mes" varchar NOT NULL,
  "Monto_Gasto_Extra_Mes" numeric NOT NULL,
  "Fecha_Pago_Gasto_Extra_Mes" date,
  "Id_Cuenta_Pago" integer,
  "Id_Movimiento" integer,
  UNIQUE ("Id_Gasto_Extra", "Anio_Mes")
);

ALTER TABLE "Gasto_Extra_Mes"
  ADD FOREIGN KEY ("Id_Gasto_Extra") REFERENCES "Gasto_Extra" ("Id_Gasto_Extra");
ALTER TABLE "Gasto_Extra_Mes"
  ADD FOREIGN KEY ("Id_Cuenta_Pago") REFERENCES "Cuenta" ("Id_Cuenta");
ALTER TABLE "Gasto_Extra_Mes"
  ADD FOREIGN KEY ("Id_Movimiento") REFERENCES "Movimiento" ("Id_Movimiento");
