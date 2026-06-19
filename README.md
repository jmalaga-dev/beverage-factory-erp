# Fábrica V2 — Sistema de Gestión para Fábrica de Bebidas

Sistema de gestión integral para una fábrica de bebidas, en evolución desde una
herramienta original construida en Excel/VBA hacia una arquitectura moderna por
capas (base de datos relacional + backend + frontend web).

## Qué resuelve

Controla de extremo a extremo la operación de la fábrica, manteniendo
**trazabilidad por lote** en toda la cadena: desde la compra de materia prima
hasta la venta al cliente final.

- **Inventario y compras** de materia prima con control de stock por lote.
- **Personal y jornadas**, con registro de horas trabajadas.
- **Producción en dos etapas**: producto intermedio y producto terminado,
  cada uno consumiendo materia prima, mano de obra y/o productos intermedios
  previos, con trazabilidad del lote exacto consumido.
- **Clientes y ventas** con geolocalización por sector (para análisis de zonas
  vía Google Maps) y registro del precio real de venta por producto.
- **Flujo de caja**: libro único de movimientos sobre múltiples cuentas
  (billeteras, cajas, banco), deudas con su historial, y activos fijos.
- **Costeo y rentabilidad**: costo unitario por lote y prorrateo mensual de
  gastos fijos por producto según horas de uso de las instalaciones.
- **Balance semanal** como foto congelada, con tres escenarios de valorización
  y patrimonio.
- **Movimientos de inventario** (mermas, ajustes, devoluciones, reprocesos)
  bajo el principio de *nunca borrar, siempre registrar el evento*.

## Diseño de datos

El modelo relacional consta de 31 tablas con integridad referencial completa.
Principios de diseño aplicados:

- **Identificadores** autogenerados como clave primaria; relaciones por Id.
- **Sin datos duplicados**: la información derivada (totales, descripciones)
  se obtiene mediante JOIN, no se almacena.
- **Trazabilidad por lote** en compras, producción y ventas.
- **Libro de movimientos** como fuente de verdad para los saldos.
- **Validación a nivel de base de datos** (restricciones CHECK y NOT NULL).

El diagrama entidad-relación está en `fabrica_v2_modelo.dbml`
(editable en [dbdiagram.io](https://dbdiagram.io)) y la imagen en
`Fabrica_Diagrama_ER.png`.

## Stack tecnológico

| Capa        | Tecnología            | Estado        |
|-------------|-----------------------|---------------|
| Base de datos | PostgreSQL          | Implementado  |
| Backend     | Python + FastAPI      | Planificado   |
| Frontend    | React                 | Planificado   |
| Reportería  | Power BI              | Planificado   |
| Mapas       | Google Maps API       | Planificado   |

## Estructura del repositorio

```
Fabrica_V2/
├── fabrica_v2_postgres.sql     # Script de creación del esquema (PostgreSQL)
├── fabrica_v2_modelo.dbml      # Modelo de datos editable (dbdiagram.io)
├── Fabrica_Diagrama_ER.png     # Diagrama entidad-relación
├── .gitignore
└── README.md
```

## Cómo crear la base de datos

1. Instalar PostgreSQL.
2. Crear una base de datos vacía (ej. `fabrica_v2`).
3. Ejecutar el contenido de `fabrica_v2_postgres.sql` en esa base.

El script crea todas las tablas, relaciones, restricciones e índices.
No incluye datos reales.
