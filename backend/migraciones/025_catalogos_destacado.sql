-- =========================================================
-- MIGRACION 025: campo "destacado" en los catalogos de productos (item 14)
-- Un marcador por producto (materia prima, intermedio, terminado) para poder
-- filtrar el detalle del Balance a solo los que mas se usan. Es independiente
-- de "habilitado": un producto destacado sigue siendo un producto normal, solo
-- se resalta/filtra; deshabilitarlo lo saca de los desplegables, destacarlo no
-- cambia nada de su operacion.
--
-- Por defecto FALSE: nada queda destacado hasta que se marca a mano en el
-- catalogo. Solo los tres catalogos de productos lo llevan (son los que
-- aparecen en el detalle por producto del Balance); el resto no.
-- =========================================================

ALTER TABLE "Materia_Prima"
  ADD COLUMN "Destacado_Materia_Prima" boolean NOT NULL DEFAULT FALSE;

ALTER TABLE "Producto_Terminado"
  ADD COLUMN "Destacado_Producto_Terminado" boolean NOT NULL DEFAULT FALSE;

ALTER TABLE "Producto_Intermedio"
  ADD COLUMN "Destacado_Producto_Intermedio" boolean NOT NULL DEFAULT FALSE;
