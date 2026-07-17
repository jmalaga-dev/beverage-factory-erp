-- =========================================================
-- MIGRACION 022: marcar como pagadas las jornadas migradas del Excel
--
-- El Excel no tenia una tabla de pagos a trabajadores (el catalogo de
-- trabajadores solo guardaba el sueldo pactado), pero en la realidad todas
-- esas jornadas YA fueron pagadas -se paga cada sabado, por la semana
-- trabajada-. La migracion original (020...021) dejo las 4374 jornadas con
-- Id_Pago_Trabajador NULL, que en V2 significa "pendiente de pago": el
-- endpoint /trabajadores/{id}/pago-sugerido las suma todas y ofrece pagar
-- de nuevo un sueldo que ya se pago hace anios (ej. 119.772 Bs "sugeridos"
-- para un solo trabajador antes de este fix).
--
-- Se crea UN Pago_Trabajador por (trabajador, semana) agrupando sus
-- jornadas de esa semana, con Fecha_Pago_Trabajador = el sabado de esa
-- semana (Mon-Sun, ISODOW: sabado=6). Monto = horas de la semana x tarifa
-- pactada (sueldo/horas base, misma formula que tarifa_hora() en
-- servicios/trabajadores.py); no hay dato de "monto real" distinto del
-- sugerido en el Excel, asi que se guardan iguales.
--
-- Id_Movimiento = NULL a proposito, igual que las Compra/Venta migradas:
-- ese dinero salio de la caja hace anios y el saldo actual de las cuentas
-- (ultimo snapshot del Excel) ya esta descontado. Crear un Movimiento SALIDA
-- ahora restaria esa plata una segunda vez.
--
-- Alcance: solo toca jornadas con Id_Pago_Trabajador IS NULL (hoy son
-- exactamente las 4374 migradas; si alguna vez se corre de nuevo con
-- jornadas reales sin pagar mezcladas, tambien las agruparia y pagaria -por
-- eso es admin, no automatico, y se corre una sola vez a proposito).
-- =========================================================

WITH jornadas_semana AS (
    SELECT
        rt."Id_Registro_Trabajador",
        rt."Id_Trabajador",
        rt."Horas_Registro_Trabajador",
        -- Sabado que cierra la semana de esta fecha (ISODOW: lunes=1..domingo=7, sabado=6)
        (rt."Fecha_Registro_Trabajador"
            + (((6 - EXTRACT(ISODOW FROM rt."Fecha_Registro_Trabajador")::int) + 7) % 7) * INTERVAL '1 day'
        )::date AS fecha_pago
    FROM "Registro_Trabajador" rt
    WHERE rt."Id_Pago_Trabajador" IS NULL
),
resumen AS (
    SELECT "Id_Trabajador", fecha_pago, SUM("Horas_Registro_Trabajador") AS horas_semana
    FROM jornadas_semana
    GROUP BY "Id_Trabajador", fecha_pago
),
pagos_creados AS (
    INSERT INTO "Pago_Trabajador"
        ("Id_Trabajador", "Fecha_Pago_Trabajador", "Monto_Sugerido_Pago", "Monto_Real_Pago", "Id_Movimiento")
    SELECT
        r."Id_Trabajador",
        r.fecha_pago,
        r.horas_semana * (t."Pago_Trabajador" / NULLIF(t."Horas_Base_Trabajador", 0)),
        r.horas_semana * (t."Pago_Trabajador" / NULLIF(t."Horas_Base_Trabajador", 0)),
        NULL
    FROM resumen r
    JOIN "Trabajador" t ON t."Id_Trabajador" = r."Id_Trabajador"
    RETURNING "Id_Pago_Trabajador", "Id_Trabajador", "Fecha_Pago_Trabajador"
)
UPDATE "Registro_Trabajador" rt
SET "Id_Pago_Trabajador" = pc."Id_Pago_Trabajador"
FROM pagos_creados pc
JOIN jornadas_semana js
    ON js."Id_Trabajador" = pc."Id_Trabajador" AND js.fecha_pago = pc."Fecha_Pago_Trabajador"
WHERE rt."Id_Registro_Trabajador" = js."Id_Registro_Trabajador";
