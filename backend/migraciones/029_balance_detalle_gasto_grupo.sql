-- =========================================================
-- MIGRACION 029: la foto de balance guarda tambien el desglose de gastos
--
-- "Gastos de la semana" era un total sin abrir: se veia CUANTO salio, no EN
-- QUE. Ahora la foto guarda una fila por grupo de gasto, reusando la tabla de
-- detalle que ya existe (024) en vez de crear una tabla nueva.
--
-- Ese detalle nacio para los cuatro bloques de INVENTARIO Y ACTIVOS, que son
-- saldos a la fecha de la foto. GASTO_GRUPO es distinto: es un FLUJO de la
-- semana previa, igual que Gastos_Semana. Va igual aca porque el mecanismo es
-- exactamente el mismo -una fila por item, con la descripcion COPIADA, no por
-- relacion- y porque es justo el bloque donde esa copia mas importa: los
-- grupos de gasto se fusionan y se borran con el tiempo, y una foto tiene que
-- seguir diciendo lo que decia el dia que se tomo, aunque el grupo ya no
-- exista. Un grupo borrado dejaria la foto ilegible si se leyera por relacion.
--
-- El CHECK original solo aceptaba los cuatro bloques, asi que hay que
-- ampliarlo: sin esto, tomar una foto falla al insertar el detalle.
--
-- Las fotos anteriores a esta migracion no tienen el bloque. El frontend ya
-- distingue "sin detalle guardado" de "valia cero", asi que no hace falta
-- rellenar nada hacia atras (tampoco se podria: el desglose de una semana ya
-- pasada no se puede reconstruir si los grupos cambiaron desde entonces).
-- =========================================================

ALTER TABLE "Balance_Detalle"
  DROP CONSTRAINT IF EXISTS "Balance_Detalle_Tipo_Detalle_check";

ALTER TABLE "Balance_Detalle"
  ADD CONSTRAINT "Balance_Detalle_Tipo_Detalle_check"
  CHECK ("Tipo_Detalle" IN ('MP', 'INTERMEDIO', 'TERMINADO', 'ACTIVO', 'GASTO_GRUPO'));
