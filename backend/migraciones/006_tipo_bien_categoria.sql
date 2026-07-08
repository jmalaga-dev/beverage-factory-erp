-- =========================================================
-- MIGRACION 006: categoria explicita en Tipo_Bien (mejora 4.2)
-- Antes, el balance clasificaba Inmueble/Equipo/Otro adivinando por texto
-- en el nombre del tipo de bien (ilike '%INMUEBLE%' / '%EQUIPO%'), fragil
-- si el nombre no contenia esa palabra literal (ej. "Casa", "Terreno").
-- Ahora se elige explicitamente al crear/editar el tipo de bien.
--
-- Backfill: reproduce el comportamiento anterior para los tipos ya
-- existentes (mismo criterio ilike, una sola vez), para no cambiarles la
-- clasificacion de golpe. Los que no matcheen quedan en OTRO (default) y
-- se pueden corregir a mano desde la pantalla de Activos.
-- =========================================================

ALTER TABLE "Tipo_Bien"
  ADD COLUMN "Categoria_Tipo_Bien" varchar NOT NULL DEFAULT 'OTRO'
  CHECK ("Categoria_Tipo_Bien" IN ('INMUEBLE', 'EQUIPO', 'OTRO'));

UPDATE "Tipo_Bien" SET "Categoria_Tipo_Bien" = 'INMUEBLE'
  WHERE "Nombre_Tipo_Bien" ILIKE '%INMUEBLE%';

UPDATE "Tipo_Bien" SET "Categoria_Tipo_Bien" = 'EQUIPO'
  WHERE "Nombre_Tipo_Bien" ILIKE '%EQUIPO%';
