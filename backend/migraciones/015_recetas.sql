-- =========================================================
-- MIGRACION 015: pre-recetas de produccion intermedia (mejora 3.6)
--
-- Una Receta es una plantilla para producir un producto intermedio: define
-- que insumos lleva (materia prima y/o intermedios) y en que cantidad, para
-- un RENDIMIENTO base. Al aplicarla para producir X, se escala por
-- X / rendimiento y se resuelven los lotes por FIFO (mejora 3.1) para
-- pre-llenar el formulario de produccion (editable, no restrictivo).
--
-- El trabajo NO va en la receta: las horas cambian cada dia y se agregan a
-- mano en cada produccion.
-- =========================================================

CREATE TABLE "Receta" (
  "Id_Receta" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Producto_Intermedio" integer NOT NULL,
  "Nombre_Receta" varchar,
  "Rendimiento_Receta" numeric NOT NULL CHECK ("Rendimiento_Receta" > 0),
  "Habilitado_Receta" boolean NOT NULL DEFAULT TRUE
);

CREATE TABLE "Receta_Detalle" (
  "Id_Receta_Detalle" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Receta" integer NOT NULL,
  "Tipo_Insumo_Receta" varchar NOT NULL
      CHECK ("Tipo_Insumo_Receta" IN ('MP', 'INTERMEDIO')),
  "Id_Materia_Prima" integer,
  "Id_Producto_Intermedio" integer,
  "Cantidad_Receta" numeric NOT NULL CHECK ("Cantidad_Receta" > 0)
);

ALTER TABLE "Receta"
  ADD FOREIGN KEY ("Id_Producto_Intermedio") REFERENCES "Producto_Intermedio" ("Id_Producto_Intermedio");
ALTER TABLE "Receta_Detalle"
  ADD FOREIGN KEY ("Id_Receta") REFERENCES "Receta" ("Id_Receta");
ALTER TABLE "Receta_Detalle"
  ADD FOREIGN KEY ("Id_Materia_Prima") REFERENCES "Materia_Prima" ("Id_Materia_Prima");
ALTER TABLE "Receta_Detalle"
  ADD FOREIGN KEY ("Id_Producto_Intermedio") REFERENCES "Producto_Intermedio" ("Id_Producto_Intermedio");
