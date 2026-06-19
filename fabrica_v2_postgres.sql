-- =====================================================================
-- FABRICA V2 - Script de creacion para PostgreSQL
-- =====================================================================
-- Ajustes respecto a la exportacion cruda de dbdiagram:
--   1. Ids como IDENTITY (autoincremento automatico, como autonumerico de Access)
--   2. Restricciones CHECK en campos "tipo" (rechaza valores mal escritos)
--   3. NOT NULL en campos que siempre deben tener valor
--   4. Indices en llaves foraneas mas consultadas (velocidad)
-- =====================================================================


-- =========================================================
-- CATALOGOS BASE (sin dependencias)
-- =========================================================

CREATE TABLE "Materia_Prima" (
  "Id_Materia_Prima" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Descripcion_Materia_Prima" varchar NOT NULL,
  "Unidad_Materia_Prima" varchar NOT NULL
);

CREATE TABLE "Trabajador" (
  "Id_Trabajador" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Trabajador" varchar NOT NULL,
  "Pago_Trabajador" numeric,
  "Horas_Base_Trabajador" numeric
);

CREATE TABLE "Producto_Intermedio" (
  "Id_Producto_Intermedio" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Descripcion_Producto_Intermedio" varchar NOT NULL,
  "Litros_Botella_Final" numeric
);

CREATE TABLE "Producto_Terminado" (
  "Id_Producto_Terminado" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Descripcion_Producto_Terminado" varchar NOT NULL,
  "Precio_Venta_Recomendado_Producto_Terminado" numeric
);

CREATE TABLE "Sector" (
  "Id_Sector" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Sector" varchar UNIQUE NOT NULL
);

CREATE TABLE "Cuenta" (
  "Id_Cuenta" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Cuenta" varchar UNIQUE NOT NULL,
  "Saldo_Actual_Cuenta" numeric NOT NULL DEFAULT 0
);

CREATE TABLE "Grupo_Movimiento" (
  "Id_Grupo_Movimiento" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Grupo_Movimiento" varchar UNIQUE NOT NULL
);

CREATE TABLE "Deuda" (
  "Id_Deuda" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Descripcion_Deuda" varchar UNIQUE NOT NULL,
  "Saldo_Actual_Deuda" numeric NOT NULL DEFAULT 0
);

CREATE TABLE "Tipo_Bien" (
  "Id_Tipo_Bien" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Tipo_Bien" varchar UNIQUE NOT NULL
);

CREATE TABLE "Gasto_Extra" (
  "Id_Gasto_Extra" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Descripcion_Gasto_Extra" varchar NOT NULL,
  "Precio_Mensual_Gasto_Extra" numeric
);


-- =========================================================
-- FINANZAS: libro de movimientos (antes de tablas que lo referencian)
-- =========================================================

CREATE TABLE "Movimiento" (
  "Id_Movimiento" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Fecha_Movimiento" date NOT NULL,
  "Tipo_Movimiento" varchar NOT NULL
      CHECK ("Tipo_Movimiento" IN ('ENTRADA','SALIDA','TRANSFERENCIA')),
  "Id_Cuenta_Origen" integer,
  "Id_Cuenta_Destino" integer,
  "Monto_Movimiento" numeric NOT NULL,
  "Descripcion_Movimiento" varchar,
  "Id_Grupo_Movimiento" integer
);

CREATE TABLE "Movimiento_Deuda" (
  "Id_Movimiento_Deuda" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Deuda" integer NOT NULL,
  "Fecha_Movimiento_Deuda" date NOT NULL,
  "Tipo_Movimiento_Deuda" varchar NOT NULL
      CHECK ("Tipo_Movimiento_Deuda" IN ('AUMENTO','PAGO')),
  "Monto_Movimiento_Deuda" numeric NOT NULL,
  "Id_Cuenta_Pago" integer
);


-- =========================================================
-- ACTIVOS FIJOS
-- =========================================================

CREATE TABLE "Activo" (
  "Id_Activo" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Tipo_Bien" integer NOT NULL,
  "Descripcion_Activo" varchar NOT NULL,
  "Valor_Activo" numeric NOT NULL
);


-- =========================================================
-- COMPRAS
-- =========================================================

CREATE TABLE "Compra" (
  "Id_Compra" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Materia_Prima" integer NOT NULL,
  "Fecha_Compra" date NOT NULL,
  "Cantidad_Compra" numeric NOT NULL,
  "Precio_Compra" numeric NOT NULL,
  "Cantidad_Restante_Compra" numeric NOT NULL,
  "Id_Movimiento" integer
);


-- =========================================================
-- JORNADAS DE TRABAJO
-- =========================================================

CREATE TABLE "Registro_Trabajador" (
  "Id_Registro_Trabajador" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Trabajador" integer NOT NULL,
  "Fecha_Registro_Trabajador" date NOT NULL,
  "Horas_Registro_Trabajador" numeric NOT NULL,
  "Horas_Restante_Registro_Trabajador" numeric,
  "Id_Movimiento" integer
);


-- =========================================================
-- PRODUCCION INTERMEDIA + DETALLES
-- =========================================================

CREATE TABLE "Produccion_Intermedio" (
  "Id_Produccion_Intermedio" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Producto_Intermedio" integer NOT NULL,
  "Fecha_Produccion_Intermedio" date NOT NULL,
  "Cantidad_Producida" numeric NOT NULL,
  "Cantidad_Restante_Producida" numeric NOT NULL
);

CREATE TABLE "Detalle_PI_Materia_Prima" (
  "Id_Detalle_PI_MP" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion_Intermedio" integer NOT NULL,
  "Id_Compra" integer NOT NULL,
  "Cantidad_Usada" numeric NOT NULL
);

CREATE TABLE "Detalle_PI_Trabajo" (
  "Id_Detalle_PI_Trab" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion_Intermedio" integer NOT NULL,
  "Id_Registro_Trabajador" integer NOT NULL,
  "Horas_Usadas" numeric NOT NULL
);

CREATE TABLE "Detalle_PI_Intermedio" (
  "Id_Detalle_PI_Int" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion_Intermedio" integer NOT NULL,
  "Id_Produccion_Intermedio_Origen" integer NOT NULL,
  "Cantidad_Usada" numeric NOT NULL
);


-- =========================================================
-- PRODUCCION (producto terminado) + DETALLES
-- =========================================================

CREATE TABLE "Produccion" (
  "Id_Produccion" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Producto_Terminado" integer NOT NULL,
  "Fecha_Produccion" date NOT NULL,
  "Cantidad_Producida_Produccion" numeric NOT NULL,
  "Precio_Unitario_Producto_Terminado" numeric,
  "Cantidad_Restante_Produccion" numeric NOT NULL
);

CREATE TABLE "Detalle_Prod_Intermedio" (
  "Id_Detalle_Prod_Int" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion" integer NOT NULL,
  "Id_Produccion_Intermedio" integer NOT NULL,
  "Cantidad_Usada" numeric NOT NULL
);

CREATE TABLE "Detalle_Prod_Materia_Prima" (
  "Id_Detalle_Prod_MP" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion" integer NOT NULL,
  "Id_Compra" integer NOT NULL,
  "Cantidad_Usada" numeric NOT NULL
);

CREATE TABLE "Detalle_Prod_Trabajador" (
  "Id_Detalle_Prod_Trab" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Produccion" integer NOT NULL,
  "Id_Registro_Trabajador" integer NOT NULL,
  "Horas_Usadas" numeric NOT NULL
);


-- =========================================================
-- CLIENTES Y VENTAS
-- =========================================================

CREATE TABLE "Cliente" (
  "Id_Cliente" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Nombre_Cliente" varchar NOT NULL,
  "Apellido_Cliente" varchar,
  "Celular_Cliente" varchar,
  "Licoreria_Cliente" varchar,
  "Latitud_Cliente" numeric,
  "Longitud_Cliente" numeric,
  "Id_Sector" integer
);

CREATE TABLE "Venta" (
  "Id_Venta" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Cliente" integer NOT NULL,
  "Fecha_Venta" date NOT NULL
);

CREATE TABLE "Detalle_Venta" (
  "Id_Detalle_Venta" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Venta" integer NOT NULL,
  "Id_Produccion" integer NOT NULL,
  "Cantidad_Venta" numeric NOT NULL,
  "Precio_Venta_Real" numeric NOT NULL,
  "Id_Movimiento" integer
);


-- =========================================================
-- GASTOS EXTRA: horas por producto/mes y prorrateo
-- =========================================================

CREATE TABLE "Horas_Producto_Mes" (
  "Id_Horas_Producto_Mes" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Producto_Terminado" integer NOT NULL,
  "Anio_Mes" varchar NOT NULL,
  "Horas_Producto_Mes" numeric NOT NULL
);

CREATE TABLE "Prorrateo_Mensual" (
  "Id_Prorrateo" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Horas_Producto_Mes" integer NOT NULL,
  "Id_Gasto_Extra" integer NOT NULL,
  "Gasto_Extra_Asignado" numeric NOT NULL
);


-- =========================================================
-- MOVIMIENTOS DE INVENTARIO (mermas, ajustes, devoluciones, reprocesos)
-- =========================================================

CREATE TABLE "Movimiento_Inventario" (
  "Id_Movimiento_Inventario" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Fecha_Movimiento_Inventario" date NOT NULL,
  "Tipo_Movimiento_Inventario" varchar NOT NULL
      CHECK ("Tipo_Movimiento_Inventario" IN ('MERMA','AJUSTE','DEVOLUCION','REPROCESO')),
  "Sentido_Movimiento_Inventario" varchar NOT NULL
      CHECK ("Sentido_Movimiento_Inventario" IN ('SALIDA','ENTRADA')),
  "Origen_Lote" varchar NOT NULL
      CHECK ("Origen_Lote" IN ('COMPRA','PRODUCCION','PRODUCCION_INTERMEDIO')),
  "Id_Compra" integer,
  "Id_Produccion" integer,
  "Id_Produccion_Intermedio" integer,
  "Cantidad_Movimiento_Inventario" numeric NOT NULL,
  "Motivo_Movimiento_Inventario" varchar,
  "Ref_Reproceso" integer
);


-- =========================================================
-- BALANCE (foto semanal) + detalle por producto
-- =========================================================

CREATE TABLE "Balance" (
  "Id_Balance" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Fecha_Balance" date NOT NULL,
  "Total_Efectivo" numeric,
  "Total_Inmuebles" numeric,
  "Total_Equipos" numeric,
  "Total_Otros_Activos" numeric,
  "Valor_Stock_Materia_Prima" numeric,
  "Valor_Stock_Producto_Terminado" numeric,
  "Total_Deudas" numeric,
  "Ventas_Semana" numeric,
  "Compras_Semana" numeric,
  "Gastos_Semana" numeric,
  "Escenario_A" numeric,
  "Escenario_B" numeric,
  "Escenario_C" numeric,
  "Patrimonio" numeric
);

CREATE TABLE "Balance_Detalle_Producto" (
  "Id_Balance_Detalle" integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  "Id_Balance" integer NOT NULL,
  "Id_Producto_Terminado" integer NOT NULL,
  "Cantidad_En_Stock" numeric,
  "Valor_En_Stock" numeric
);


-- =====================================================================
-- LLAVES FORANEAS (relaciones)
-- =====================================================================

ALTER TABLE "Movimiento" ADD FOREIGN KEY ("Id_Cuenta_Origen") REFERENCES "Cuenta" ("Id_Cuenta");
ALTER TABLE "Movimiento" ADD FOREIGN KEY ("Id_Cuenta_Destino") REFERENCES "Cuenta" ("Id_Cuenta");
ALTER TABLE "Movimiento" ADD FOREIGN KEY ("Id_Grupo_Movimiento") REFERENCES "Grupo_Movimiento" ("Id_Grupo_Movimiento");

ALTER TABLE "Movimiento_Deuda" ADD FOREIGN KEY ("Id_Deuda") REFERENCES "Deuda" ("Id_Deuda");
ALTER TABLE "Movimiento_Deuda" ADD FOREIGN KEY ("Id_Cuenta_Pago") REFERENCES "Cuenta" ("Id_Cuenta");

ALTER TABLE "Activo" ADD FOREIGN KEY ("Id_Tipo_Bien") REFERENCES "Tipo_Bien" ("Id_Tipo_Bien");

ALTER TABLE "Compra" ADD FOREIGN KEY ("Id_Materia_Prima") REFERENCES "Materia_Prima" ("Id_Materia_Prima");
ALTER TABLE "Compra" ADD FOREIGN KEY ("Id_Movimiento") REFERENCES "Movimiento" ("Id_Movimiento");

ALTER TABLE "Registro_Trabajador" ADD FOREIGN KEY ("Id_Trabajador") REFERENCES "Trabajador" ("Id_Trabajador");
ALTER TABLE "Registro_Trabajador" ADD FOREIGN KEY ("Id_Movimiento") REFERENCES "Movimiento" ("Id_Movimiento");

ALTER TABLE "Produccion_Intermedio" ADD FOREIGN KEY ("Id_Producto_Intermedio") REFERENCES "Producto_Intermedio" ("Id_Producto_Intermedio");

ALTER TABLE "Detalle_PI_Materia_Prima" ADD FOREIGN KEY ("Id_Produccion_Intermedio") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");
ALTER TABLE "Detalle_PI_Materia_Prima" ADD FOREIGN KEY ("Id_Compra") REFERENCES "Compra" ("Id_Compra");

ALTER TABLE "Detalle_PI_Trabajo" ADD FOREIGN KEY ("Id_Produccion_Intermedio") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");
ALTER TABLE "Detalle_PI_Trabajo" ADD FOREIGN KEY ("Id_Registro_Trabajador") REFERENCES "Registro_Trabajador" ("Id_Registro_Trabajador");

ALTER TABLE "Detalle_PI_Intermedio" ADD FOREIGN KEY ("Id_Produccion_Intermedio") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");
ALTER TABLE "Detalle_PI_Intermedio" ADD FOREIGN KEY ("Id_Produccion_Intermedio_Origen") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");

ALTER TABLE "Produccion" ADD FOREIGN KEY ("Id_Producto_Terminado") REFERENCES "Producto_Terminado" ("Id_Producto_Terminado");

ALTER TABLE "Detalle_Prod_Intermedio" ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
ALTER TABLE "Detalle_Prod_Intermedio" ADD FOREIGN KEY ("Id_Produccion_Intermedio") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");

ALTER TABLE "Detalle_Prod_Materia_Prima" ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
ALTER TABLE "Detalle_Prod_Materia_Prima" ADD FOREIGN KEY ("Id_Compra") REFERENCES "Compra" ("Id_Compra");

ALTER TABLE "Detalle_Prod_Trabajador" ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
ALTER TABLE "Detalle_Prod_Trabajador" ADD FOREIGN KEY ("Id_Registro_Trabajador") REFERENCES "Registro_Trabajador" ("Id_Registro_Trabajador");

ALTER TABLE "Cliente" ADD FOREIGN KEY ("Id_Sector") REFERENCES "Sector" ("Id_Sector");

ALTER TABLE "Venta" ADD FOREIGN KEY ("Id_Cliente") REFERENCES "Cliente" ("Id_Cliente");

ALTER TABLE "Detalle_Venta" ADD FOREIGN KEY ("Id_Venta") REFERENCES "Venta" ("Id_Venta");
ALTER TABLE "Detalle_Venta" ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
ALTER TABLE "Detalle_Venta" ADD FOREIGN KEY ("Id_Movimiento") REFERENCES "Movimiento" ("Id_Movimiento");

ALTER TABLE "Horas_Producto_Mes" ADD FOREIGN KEY ("Id_Producto_Terminado") REFERENCES "Producto_Terminado" ("Id_Producto_Terminado");

ALTER TABLE "Prorrateo_Mensual" ADD FOREIGN KEY ("Id_Horas_Producto_Mes") REFERENCES "Horas_Producto_Mes" ("Id_Horas_Producto_Mes");
ALTER TABLE "Prorrateo_Mensual" ADD FOREIGN KEY ("Id_Gasto_Extra") REFERENCES "Gasto_Extra" ("Id_Gasto_Extra");

ALTER TABLE "Movimiento_Inventario" ADD FOREIGN KEY ("Id_Compra") REFERENCES "Compra" ("Id_Compra");
ALTER TABLE "Movimiento_Inventario" ADD FOREIGN KEY ("Id_Produccion") REFERENCES "Produccion" ("Id_Produccion");
ALTER TABLE "Movimiento_Inventario" ADD FOREIGN KEY ("Id_Produccion_Intermedio") REFERENCES "Produccion_Intermedio" ("Id_Produccion_Intermedio");

ALTER TABLE "Balance_Detalle_Producto" ADD FOREIGN KEY ("Id_Balance") REFERENCES "Balance" ("Id_Balance");
ALTER TABLE "Balance_Detalle_Producto" ADD FOREIGN KEY ("Id_Producto_Terminado") REFERENCES "Producto_Terminado" ("Id_Producto_Terminado");


-- =====================================================================
-- INDICES en llaves foraneas (aceleran JOINs y filtros por lote)
-- =====================================================================

CREATE INDEX ON "Compra" ("Id_Materia_Prima");
CREATE INDEX ON "Registro_Trabajador" ("Id_Trabajador");
CREATE INDEX ON "Produccion_Intermedio" ("Id_Producto_Intermedio");
CREATE INDEX ON "Detalle_PI_Materia_Prima" ("Id_Produccion_Intermedio");
CREATE INDEX ON "Detalle_PI_Materia_Prima" ("Id_Compra");
CREATE INDEX ON "Detalle_PI_Trabajo" ("Id_Produccion_Intermedio");
CREATE INDEX ON "Detalle_PI_Trabajo" ("Id_Registro_Trabajador");
CREATE INDEX ON "Detalle_PI_Intermedio" ("Id_Produccion_Intermedio");
CREATE INDEX ON "Produccion" ("Id_Producto_Terminado");
CREATE INDEX ON "Detalle_Prod_Intermedio" ("Id_Produccion");
CREATE INDEX ON "Detalle_Prod_Materia_Prima" ("Id_Produccion");
CREATE INDEX ON "Detalle_Prod_Materia_Prima" ("Id_Compra");
CREATE INDEX ON "Detalle_Prod_Trabajador" ("Id_Produccion");
CREATE INDEX ON "Cliente" ("Id_Sector");
CREATE INDEX ON "Venta" ("Id_Cliente");
CREATE INDEX ON "Detalle_Venta" ("Id_Venta");
CREATE INDEX ON "Detalle_Venta" ("Id_Produccion");
CREATE INDEX ON "Movimiento" ("Id_Cuenta_Origen");
CREATE INDEX ON "Movimiento" ("Id_Cuenta_Destino");
CREATE INDEX ON "Movimiento_Deuda" ("Id_Deuda");
CREATE INDEX ON "Prorrateo_Mensual" ("Id_Horas_Producto_Mes");
CREATE INDEX ON "Movimiento_Inventario" ("Id_Compra");
CREATE INDEX ON "Movimiento_Inventario" ("Id_Produccion");
CREATE INDEX ON "Balance_Detalle_Producto" ("Id_Balance");
