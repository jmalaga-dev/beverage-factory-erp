-- =========================================================
-- MIGRACION 021: columna para el valor de utensilios/feriados comprados
-- pero todavia NO absorbidos (mejora 4.8)
--
-- Un item de absorcion (utensilio, feriado) se compra por un costo y se
-- reparte entre N botellas estimadas. Mientras queden botellas por absorber,
-- una parte de esos Bs ya se pago pero todavia no se traslado al costo de
-- ninguna botella: es valor que la fabrica tiene y el balance no contaba en
-- ninguna linea (ni efectivo, ni stock, ni activo fijo). Se perdia.
--
-- La parte sin absorber es proporcional:
--     costo * botellas_restantes / botellas_estimadas
--
-- Suma al Escenario B (junto a los otros stocks) y, por arrastre, al A y al
-- patrimonio. Se guarda en la foto para que las fotos viejas se puedan
-- comparar con las nuevas.
--
-- Las fotos anteriores a esta columna quedan en NULL (no en 0): no es que
-- valieran cero, es que no se media. El serializador las muestra como 0 para
-- no romper la comparativa, igual que se hizo con Pagos_Semana (5).
-- =========================================================

ALTER TABLE "Balance"
  ADD COLUMN "Valor_Utensilios_Sin_Absorber" numeric;
