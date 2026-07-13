-- =========================================================
-- MIGRACION 019: rol de cada cuenta (mejora 2.A, sección 2)
--
-- Para el reparto por prioridad de cuentas hace falta distinguir el ROL de
-- cada cuenta (Billetera Fábrica vs Billetera Casa) sin depender del nombre.
--   FABRICA / CASA / OTRA (otras cuentas, ej. un banco).
-- Las reglas de prioridad y el reparto de ventas (70/30, sección 2.C) se
-- apoyan en este rol, no en el texto del nombre.
-- Las cuentas existentes quedan como 'OTRA' hasta que se les asigne el rol
-- en el catálogo.
-- =========================================================

ALTER TABLE "Cuenta"
  ADD COLUMN "Rol_Cuenta" varchar NOT NULL DEFAULT 'OTRA'
  CHECK ("Rol_Cuenta" IN ('FABRICA', 'CASA', 'OTRA'));
