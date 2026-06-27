# Decisiones de diseño y mejoras futuras — Fábrica V2

Este documento registra decisiones de diseño tomadas durante el desarrollo,
especialmente aquellas donde se eligió una solución más simple para el MVP
y se dejó anotada una versión más completa para el futuro.

---

## Costeo del trabajo en producción

**Decisión actual (MVP) — "Camino 1":**
El costo del trabajo en una producción se calcula con la **tarifa pactada**
del trabajador (`Pago_Trabajador` de la tabla `Trabajador`), no con el pago
real semanal.

Razones:
- La tarifa pactada existe y es conocida en el momento de producir.
- El pago real ocurre *después* (semanalmente) y puede diferir del estimado.
- Esto da un costo unitario inmediato y completo al producir, sin esperar al pago.
- Las diferencias entre pago estimado y real (ej. pagar 850 en vez de 820, o
  redondear 800.02 a 800) se tratan como un ajuste a nivel de flujo de caja
  general, NO se reparten producto por producto.

Consecuencia: el costo de producción es un **estimado estable**, suficiente
para decidir rentabilidad entre productos, que es el objetivo principal.

**Mejora futura — "Camino 2" (recálculo fiel):**
Cuando se registra el pago real semanal, recalcular el costo unitario de todas
las producciones de esa semana que usaron las horas de ese trabajador,
repartiendo la diferencia (pago real vs. tarifa pactada) proporcionalmente
entre las producciones según las horas que cada una consumió.

Complejidad: alta. Las horas de una jornada pueden repartirse entre varias
producciones, lo que obliga a un reparto proporcional fino. Por eso se pospone.

Nota: esto NO afecta el costeo de la materia prima, que sí usa el costo real
del lote (Filosofía B) porque ahí el dato es directo y conocido al producir.

---

## Otras notas pendientes (de conversaciones previas)

- **Base de datos de proveedores:** agregar una tabla `Proveedor` y un
  `Id_Proveedor` en `Compra`, para comparar precios de la misma materia prima
  entre proveedores y decidir cuál conviene.

- **Unir las islas (productivo / financiero):** los vínculos `Id_Movimiento`
  en Compra, Detalle_Venta y Registro_Trabajador ya existen como FK opcionales.
  El backend debe llenarlos consistentemente al registrar cada operación.

- **Informe comparativo entre balances:** generar automáticamente un reporte
  que compare dos fotos de Balance semanales y resalte qué cambió (costos,
  patrimonio, stock). Clave dado que se eligió Filosofía B para el costo de
  materia prima.


## Reparto de pagos por prioridad de cuentas (pendiente — capa de orquestación)

Los gastos, compras y pagos pueden cubrirse con dinero de varias fuentes, siguiendo
una logica de aportes + prioridad que se construira como una capa POR ENCIMA de las
operaciones base (probablemente en el frontend o en una capa de orquestacion). Las
operaciones base (registrar un gasto/compra/pago desde UNA cuenta) ya existen y son
el ladrillo que esta capa invocara varias veces.

Logica a implementar:
1. Aportes explicitos primero: montos fijos que alguien (conyuge, banco) pone para
   cubrir parte del total. Son input manual del momento.
2. El faltante (total - aportes) se cubre desde las cuentas siguiendo un ORDEN DE
   PRIORIDAD que depende del tipo de operacion:
   - Gastos familiares: primero Billetera Casa, luego Billetera Fabrica.
   - Compras de materia prima y pagos a trabajadores: primero Billetera Fabrica,
     luego Billetera Casa.
   - Ventas (ingreso): reparto 70/30 (70% Fabrica, 30% Casa) una vez recuperado
     lo invertido.
3. La capa calcula cuanto sacar de cada cuenta y luego llama a la operacion base
   correspondiente una vez por cada fuente.

Ejemplo (gasto familiar): gastos suman 40 Bs. Conyuge aporta 15, banco aporta 5
(= 20 puestos). Faltan 20: se sacan de Billetera Casa (prioridad), y solo si no
alcanza, de Billetera Fabrica.

Razon de separarlo: la operacion base (sacar dinero de UNA cuenta) es reutilizable
entre gastos, compras y pagos; la logica de prioridad cambia segun el caso pero
todas terminan llamando a esa misma base. Mantenerlas separadas facilita pruebas
y evita duplicar codigo.