-- =========================================================
-- MIGRACION 009: botellas por paquete en Producto_Terminado (mejora 3.9)
-- Los productos pueden venderse en paquetes de distinto tamano (6, 8...) o
-- sueltos. Guardar cuantas botellas trae el paquete de cada producto
-- habilita resumenes en paquetes equivalentes (4.7), el costo por paquete
-- en la simulacion de nuevo producto (1.5) y registrar producciones/ventas
-- por paquete con conversion automatica a botellas.
--
-- Default 1: un producto sin configurar se vende suelto (una botella =
-- un paquete), compatible con todos los productos existentes.
-- =========================================================

ALTER TABLE "Producto_Terminado"
  ADD COLUMN "Botellas_Por_Paquete" integer NOT NULL DEFAULT 1
  CHECK ("Botellas_Por_Paquete" >= 1);
