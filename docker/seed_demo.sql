-- =====================================================================
-- DATOS FICTICIOS DE DEMOSTRACION (mejora 8.6)
-- =====================================================================
-- TODO lo que hay aca es INVENTADO. Ningun nombre, precio, cliente,
-- proveedor ni monto sale del negocio real: este archivo se versiona en un
-- repositorio publico (ver la regla en DECISIONES_DISENO.md, seccion 8).
--
-- Objetivo: que quien levante el contenedor abra la app y vea las pantallas
-- CON CONTENIDO (stock, costos, balance) en vez de tablas vacias, sin tener
-- que cargar nada a mano.
--
-- Se carga solo en MODO_DATOS=demo. Los ids son GENERATED ALWAYS AS
-- IDENTITY, asi que se dejan que los asigne PostgreSQL y despues se
-- referencian por su descripcion, no por un numero fijo.
-- =====================================================================

-- ---------- CUENTAS ----------
INSERT INTO "Cuenta" ("Nombre_Cuenta", "Saldo_Actual_Cuenta", "Rol_Cuenta") VALUES
  ('Billetera Fabrica', 12000, 'FABRICA'),
  ('Billetera Casa',     4500, 'CASA'),
  ('Banco Demo',        20000, 'OTRA');

-- ---------- GRUPOS DE MOVIMIENTO ----------
INSERT INTO "Grupo_Movimiento" ("Nombre_Grupo_Movimiento") VALUES
  ('Familiar'), ('Fabrica'), ('Impuestos');

-- ---------- TRABAJADORES ----------
-- Pago semanal sobre horas base: la tarifa/hora se deriva de ahi.
INSERT INTO "Trabajador" ("Nombre_Trabajador", "Pago_Trabajador", "Horas_Base_Trabajador") VALUES
  ('Ana Demo',    1200, 48),
  ('Bruno Demo',  1000, 48),
  ('Carla Demo',   900, 40);

-- ---------- MATERIA PRIMA ----------
INSERT INTO "Materia_Prima" ("Descripcion_Materia_Prima", "Unidad_Materia_Prima") VALUES
  ('Azucar demo',          'Kg'),
  ('Alcohol demo',         'L'),
  ('Esencia de limon demo','L'),
  ('Botella 750 demo',     'Unidad'),
  ('Tapa demo',            'Unidad'),
  ('Etiqueta demo',        'Unidad');

-- ---------- PROVEEDORES ----------
-- Con proveedor cargado desde el inicio: sin al menos uno por materia, la
-- pantalla de Compras bloquea el registro a proposito (ver mejora 5.1).
INSERT INTO "Proveedor" ("Nombre_Proveedor", "Celular_Proveedor") VALUES
  ('Distribuidora Norte (demo)', '70000001'),
  ('Insumos del Valle (demo)',   '70000002');

INSERT INTO "Proveedor_Materia_Prima" ("Id_Proveedor", "Id_Materia_Prima")
SELECT p."Id_Proveedor", m."Id_Materia_Prima"
FROM "Proveedor" p CROSS JOIN "Materia_Prima" m
WHERE p."Nombre_Proveedor" = 'Distribuidora Norte (demo)';

-- ---------- PRODUCTOS ----------
INSERT INTO "Producto_Intermedio"
  ("Descripcion_Producto_Intermedio", "Litros_Botella_Final", "Unidad_Producto_Intermedio") VALUES
  ('Jarabe base demo',       0.75, 'LITRO'),
  ('Licor de limon demo',    0.75, 'LITRO'),
  ('Botella lavada demo',    NULL, 'UNIDAD');

INSERT INTO "Producto_Terminado"
  ("Descripcion_Producto_Terminado", "Precio_Venta_Recomendado_Producto_Terminado", "Botellas_Por_Paquete") VALUES
  ('Licor Limon 750 demo',  35, 6),
  ('Licor Naranja 750 demo',35, 6),
  ('Licor Suelto demo',     28, 1),
  ('Pack Especial demo',    40, 12);

-- ---------- SECTORES Y CLIENTES ----------
INSERT INTO "Sector" ("Nombre_Sector") VALUES ('Centro demo'), ('Sur demo');

INSERT INTO "Cliente" ("Nombre_Cliente", "Apellido_Cliente", "Celular_Cliente", "Id_Sector")
SELECT 'Cliente Uno', 'Demo', '71000001', s."Id_Sector" FROM "Sector" s WHERE s."Nombre_Sector"='Centro demo';
INSERT INTO "Cliente" ("Nombre_Cliente", "Apellido_Cliente", "Celular_Cliente", "Id_Sector")
SELECT 'Cliente Dos', 'Demo', '71000002', s."Id_Sector" FROM "Sector" s WHERE s."Nombre_Sector"='Sur demo';

-- ---------- GASTOS EXTRA RECURRENTES ----------
INSERT INTO "Gasto_Extra" ("Descripcion_Gasto_Extra", "Precio_Mensual_Gasto_Extra") VALUES
  ('Luz demo', 300), ('Agua demo', 120), ('Internet demo', 250);

-- ---------- TIPOS DE BIEN Y ACTIVOS ----------
INSERT INTO "Tipo_Bien" ("Nombre_Tipo_Bien", "Categoria_Tipo_Bien") VALUES
  ('Inmueble demo', 'INMUEBLE'),
  ('Equipo demo',   'EQUIPO');

INSERT INTO "Activo" ("Id_Tipo_Bien", "Descripcion_Activo", "Valor_Activo")
SELECT t."Id_Tipo_Bien", 'Galpon demo', 150000 FROM "Tipo_Bien" t WHERE t."Nombre_Tipo_Bien"='Inmueble demo';
INSERT INTO "Activo" ("Id_Tipo_Bien", "Descripcion_Activo", "Valor_Activo")
SELECT t."Id_Tipo_Bien", 'Embotelladora demo', 18000 FROM "Tipo_Bien" t WHERE t."Nombre_Tipo_Bien"='Equipo demo';

-- ---------- COMPRAS (con su movimiento de dinero) ----------
-- Cada compra descuenta de una cuenta: se crea el Movimiento y se enlaza,
-- igual que hace el servicio de compras en la app.
DO $$
DECLARE
  v_cuenta int;
  v_prov   int;
  v_mp     int;
  v_mov    int;
  r        record;
BEGIN
  SELECT "Id_Cuenta"    INTO v_cuenta FROM "Cuenta"    WHERE "Nombre_Cuenta"='Billetera Fabrica';
  SELECT "Id_Proveedor" INTO v_prov   FROM "Proveedor" WHERE "Nombre_Proveedor"='Distribuidora Norte (demo)';

  FOR r IN
    SELECT * FROM (VALUES
      ('Azucar demo',           50.0,  400.0),
      ('Alcohol demo',          80.0, 1600.0),
      ('Esencia de limon demo',  5.0,  350.0),
      ('Botella 750 demo',     600.0, 1800.0),
      ('Tapa demo',            600.0,  300.0),
      ('Etiqueta demo',        600.0,  240.0)
    ) AS t(materia, cantidad, precio)
  LOOP
    SELECT "Id_Materia_Prima" INTO v_mp FROM "Materia_Prima"
      WHERE "Descripcion_Materia_Prima" = r.materia;

    INSERT INTO "Movimiento"
      ("Fecha_Movimiento","Tipo_Movimiento","Id_Cuenta_Origen","Monto_Movimiento","Descripcion_Movimiento")
    VALUES (CURRENT_DATE - 30, 'SALIDA', v_cuenta, r.precio, 'Compra demo: ' || r.materia)
    RETURNING "Id_Movimiento" INTO v_mov;

    INSERT INTO "Compra"
      ("Id_Materia_Prima","Fecha_Compra","Cantidad_Compra","Precio_Compra",
       "Cantidad_Restante_Compra","Id_Movimiento","Id_Proveedor")
    VALUES (v_mp, CURRENT_DATE - 30, r.cantidad, r.precio, r.cantidad, v_mov, v_prov);
  END LOOP;
END $$;

-- ---------- JORNADAS DE TRABAJO ----------
INSERT INTO "Registro_Trabajador"
  ("Id_Trabajador","Fecha_Registro_Trabajador","Horas_Registro_Trabajador","Horas_Restante_Registro_Trabajador")
SELECT "Id_Trabajador", CURRENT_DATE - 20, 8, 8 FROM "Trabajador";
INSERT INTO "Registro_Trabajador"
  ("Id_Trabajador","Fecha_Registro_Trabajador","Horas_Registro_Trabajador","Horas_Restante_Registro_Trabajador")
SELECT "Id_Trabajador", CURRENT_DATE - 19, 6, 6 FROM "Trabajador";

-- ---------- PRODUCCION INTERMEDIA ----------
-- Consume azucar y alcohol, y deja un lote de jarabe con su costo unitario.
DO $$
DECLARE
  v_pi int; v_prod int; v_compra int; v_usar numeric; v_costo numeric := 0;
BEGIN
  SELECT "Id_Producto_Intermedio" INTO v_pi FROM "Producto_Intermedio"
    WHERE "Descripcion_Producto_Intermedio"='Jarabe base demo';

  INSERT INTO "Produccion_Intermedio"
    ("Id_Producto_Intermedio","Fecha_Produccion_Intermedio","Cantidad_Producida",
     "Cantidad_Restante_Producida","Costo_Unitario_Produccion_Intermedio","Horas_Acumuladas")
  VALUES (v_pi, CURRENT_DATE - 15, 100, 100, 0, 0)
  RETURNING "Id_Produccion_Intermedio" INTO v_prod;

  -- Azucar: 20 Kg
  SELECT "Id_Compra" INTO v_compra FROM "Compra" c
    JOIN "Materia_Prima" m USING ("Id_Materia_Prima")
    WHERE m."Descripcion_Materia_Prima"='Azucar demo' LIMIT 1;
  v_usar := 20;
  INSERT INTO "Detalle_PI_Materia_Prima" ("Id_Produccion_Intermedio","Id_Compra","Cantidad_Usada")
    VALUES (v_prod, v_compra, v_usar);
  UPDATE "Compra" SET "Cantidad_Restante_Compra" = "Cantidad_Restante_Compra" - v_usar
    WHERE "Id_Compra" = v_compra;
  SELECT v_costo + v_usar * ("Precio_Compra"/"Cantidad_Compra") INTO v_costo
    FROM "Compra" WHERE "Id_Compra"=v_compra;

  -- Alcohol: 30 L
  SELECT "Id_Compra" INTO v_compra FROM "Compra" c
    JOIN "Materia_Prima" m USING ("Id_Materia_Prima")
    WHERE m."Descripcion_Materia_Prima"='Alcohol demo' LIMIT 1;
  v_usar := 30;
  INSERT INTO "Detalle_PI_Materia_Prima" ("Id_Produccion_Intermedio","Id_Compra","Cantidad_Usada")
    VALUES (v_prod, v_compra, v_usar);
  UPDATE "Compra" SET "Cantidad_Restante_Compra" = "Cantidad_Restante_Compra" - v_usar
    WHERE "Id_Compra" = v_compra;
  SELECT v_costo + v_usar * ("Precio_Compra"/"Cantidad_Compra") INTO v_costo
    FROM "Compra" WHERE "Id_Compra"=v_compra;

  UPDATE "Produccion_Intermedio"
    SET "Costo_Unitario_Produccion_Intermedio" = v_costo / 100
    WHERE "Id_Produccion_Intermedio" = v_prod;
END $$;

-- ---------- PRODUCCION TERMINADA ----------
-- Consume el jarabe + botellas/tapas/etiquetas y deja lotes vendibles.
DO $$
DECLARE
  v_pt int; v_prod int; v_pi_lote int; v_compra int; v_costo numeric := 0;
  v_botellas numeric := 120;
BEGIN
  SELECT "Id_Producto_Terminado" INTO v_pt FROM "Producto_Terminado"
    WHERE "Descripcion_Producto_Terminado"='Licor Limon 750 demo';

  INSERT INTO "Produccion"
    ("Id_Producto_Terminado","Fecha_Produccion","Cantidad_Producida_Produccion",
     "Cantidad_Restante_Produccion","Precio_Unitario_Producto_Terminado","Horas_Acumuladas")
  VALUES (v_pt, CURRENT_DATE - 10, v_botellas, v_botellas, 0, 0)
  RETURNING "Id_Produccion" INTO v_prod;

  -- Jarabe: 90 L del lote intermedio
  SELECT "Id_Produccion_Intermedio" INTO v_pi_lote FROM "Produccion_Intermedio" LIMIT 1;
  INSERT INTO "Detalle_Prod_Intermedio"
    ("Id_Produccion","Id_Produccion_Intermedio","Cantidad_Usada")
    VALUES (v_prod, v_pi_lote, 90);
  UPDATE "Produccion_Intermedio"
    SET "Cantidad_Restante_Producida" = "Cantidad_Restante_Producida" - 90
    WHERE "Id_Produccion_Intermedio" = v_pi_lote;
  SELECT v_costo + 90 * "Costo_Unitario_Produccion_Intermedio" INTO v_costo
    FROM "Produccion_Intermedio" WHERE "Id_Produccion_Intermedio"=v_pi_lote;

  -- Envases: una botella, una tapa y una etiqueta por unidad producida
  FOR v_compra IN
    SELECT c."Id_Compra" FROM "Compra" c JOIN "Materia_Prima" m USING ("Id_Materia_Prima")
    WHERE m."Descripcion_Materia_Prima" IN ('Botella 750 demo','Tapa demo','Etiqueta demo')
  LOOP
    INSERT INTO "Detalle_Prod_Materia_Prima" ("Id_Produccion","Id_Compra","Cantidad_Usada")
      VALUES (v_prod, v_compra, v_botellas);
    UPDATE "Compra" SET "Cantidad_Restante_Compra" = "Cantidad_Restante_Compra" - v_botellas
      WHERE "Id_Compra" = v_compra;
    SELECT v_costo + v_botellas * ("Precio_Compra"/"Cantidad_Compra") INTO v_costo
      FROM "Compra" WHERE "Id_Compra"=v_compra;
  END LOOP;

  UPDATE "Produccion"
    SET "Precio_Unitario_Producto_Terminado" = v_costo / v_botellas
    WHERE "Id_Produccion" = v_prod;
END $$;

-- ---------- UNA VENTA ----------
DO $$
DECLARE
  v_cli int; v_venta int; v_lote int; v_cuenta int; v_mov int;
  v_cant numeric := 24; v_precio numeric := 35;
BEGIN
  SELECT "Id_Cliente" INTO v_cli FROM "Cliente" LIMIT 1;
  SELECT "Id_Cuenta"  INTO v_cuenta FROM "Cuenta" WHERE "Nombre_Cuenta"='Billetera Fabrica';
  SELECT "Id_Produccion" INTO v_lote FROM "Produccion" LIMIT 1;

  INSERT INTO "Venta" ("Id_Cliente","Fecha_Venta") VALUES (v_cli, CURRENT_DATE - 5)
    RETURNING "Id_Venta" INTO v_venta;

  INSERT INTO "Movimiento"
    ("Fecha_Movimiento","Tipo_Movimiento","Id_Cuenta_Destino","Monto_Movimiento","Descripcion_Movimiento")
  VALUES (CURRENT_DATE - 5, 'ENTRADA', v_cuenta, v_cant * v_precio, 'Venta demo')
  RETURNING "Id_Movimiento" INTO v_mov;

  INSERT INTO "Detalle_Venta"
    ("Id_Venta","Id_Produccion","Cantidad_Venta","Precio_Venta_Real","Id_Movimiento")
  VALUES (v_venta, v_lote, v_cant, v_precio, v_mov);

  UPDATE "Produccion" SET "Cantidad_Restante_Produccion" = "Cantidad_Restante_Produccion" - v_cant
    WHERE "Id_Produccion" = v_lote;
  UPDATE "Cuenta" SET "Saldo_Actual_Cuenta" = "Saldo_Actual_Cuenta" + v_cant * v_precio
    WHERE "Id_Cuenta" = v_cuenta;
END $$;

-- ---------- UNA RECETA DE EJEMPLO ----------
DO $$
DECLARE v_receta int; v_pi int;
BEGIN
  SELECT "Id_Producto_Intermedio" INTO v_pi FROM "Producto_Intermedio"
    WHERE "Descripcion_Producto_Intermedio"='Jarabe base demo';

  INSERT INTO "Receta" ("Tipo_Receta","Id_Producto_Intermedio","Nombre_Receta","Rendimiento_Receta")
  VALUES ('INTERMEDIO', v_pi, 'Jarabe base demo (100 L)', 100)
  RETURNING "Id_Receta" INTO v_receta;

  INSERT INTO "Receta_Detalle" ("Id_Receta","Tipo_Insumo_Receta","Id_Materia_Prima","Cantidad_Receta")
  SELECT v_receta, 'MP', "Id_Materia_Prima", 20 FROM "Materia_Prima"
    WHERE "Descripcion_Materia_Prima"='Azucar demo';
  INSERT INTO "Receta_Detalle" ("Id_Receta","Tipo_Insumo_Receta","Id_Materia_Prima","Cantidad_Receta")
  SELECT v_receta, 'MP', "Id_Materia_Prima", 30 FROM "Materia_Prima"
    WHERE "Descripcion_Materia_Prima"='Alcohol demo';
END $$;
