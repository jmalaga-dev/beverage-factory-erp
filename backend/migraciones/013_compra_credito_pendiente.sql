-- =========================================================
-- MIGRACION 013: compras a credito y pedidos pendientes (mejora 5.1 ampliacion)
--
--   - Compra.Recibida_Compra: FALSE = pedido hecho pero la mercaderia aun no
--     llego. Un pedido pendiente nace con Cantidad_Restante_Compra = 0, asi
--     que no cuenta como stock (las consultas ya filtran por restante > 0);
--     al "recibir" se pone Restante = Cantidad y aparece el stock. Las
--     compras existentes quedan TRUE (ya recibidas).
--
--   - Deuda.Id_Proveedor: la deuda nacida de una compra a credito se agrupa
--     por proveedor (una deuda por proveedor, acumula). Nullable: las deudas
--     manuales (banco, interes) no tienen proveedor. El costo del lote es el
--     precio COMPLETO (pagado + adeudado); lo adeudado se vuelve esta deuda.
-- =========================================================

ALTER TABLE "Compra"
  ADD COLUMN "Recibida_Compra" boolean NOT NULL DEFAULT TRUE;

ALTER TABLE "Deuda"
  ADD COLUMN "Id_Proveedor" integer;

ALTER TABLE "Deuda"
  ADD FOREIGN KEY ("Id_Proveedor") REFERENCES "Proveedor" ("Id_Proveedor");
