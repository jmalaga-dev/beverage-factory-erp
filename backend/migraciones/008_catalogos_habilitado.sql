-- =========================================================
-- MIGRACION 008: campo "habilitado" en los catalogos (mejora 6.1)
-- Extiende a todos los catalogos el patron que Trabajador ya tenia
-- (migracion 004): poder DESHABILITAR en vez de borrar cuando ya hay
-- historial encima (compras, producciones, ventas...). Un item
-- deshabilitado deja de ofrecerse para operaciones nuevas (desaparece de
-- los desplegables) pero sigue existiendo, y su historial queda intacto
-- (principio de inmutabilidad del historico, ver DECISIONES_DISENO.md).
--
-- Por defecto TRUE: todos los registros existentes quedan habilitados sin
-- necesidad de tocarlos uno por uno.
-- Trabajador NO se toca aqui: ya tiene Habilitado_Trabajador desde la 004.
-- =========================================================

ALTER TABLE "Materia_Prima"
  ADD COLUMN "Habilitado_Materia_Prima" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Producto_Terminado"
  ADD COLUMN "Habilitado_Producto_Terminado" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Producto_Intermedio"
  ADD COLUMN "Habilitado_Producto_Intermedio" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Grupo_Movimiento"
  ADD COLUMN "Habilitado_Grupo_Movimiento" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Gasto_Extra"
  ADD COLUMN "Habilitado_Gasto_Extra" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Cuenta"
  ADD COLUMN "Habilitado_Cuenta" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Cliente"
  ADD COLUMN "Habilitado_Cliente" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Sector"
  ADD COLUMN "Habilitado_Sector" boolean NOT NULL DEFAULT TRUE;
