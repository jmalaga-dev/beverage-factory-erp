// filasBalance.js
// Estructura de la tabla de balance, compartida por la pantalla de Balance y
// por la Comparativa de fotos, para que las dos muestren SIEMPRE los mismos
// conceptos en el mismo orden (antes estaba duplicada en las dos paginas y
// habia que acordarse de tocar las dos).
//
// El orden sigue la convencion contable: primero los componentes, despues la
// linea, despues el subtotal que sale de sumarlos. Asi se lee de donde viene
// cada escenario sin tener que buscar las filas por la tabla:
//
//   Efectivo − Deudas ................... = Escenario C
//   C + los cuatro stocks ............... = Escenario B
//   B + activos fijos (suma de los *) ... = Escenario A
//
// Tipos de fila:
//   componente     un sumando; `signo` dice como entra al subtotal siguiente
//   subtotal       resultado de los componentes de arriba (C, B, A)
//   subcomponente  desglose informativo (los *): NO se suma aparte, ya esta
//                  dentro de la fila que lo agrupa
//   grupo          total de los subcomponentes de arriba (Activos fijos)
//   separador      aire entre bloques
//   nota           aclaracion de la fila que sigue (el stock conservador)

export const filasBalance = [
  { tipo: 'componente', signo: '+', label: 'Efectivo', campo: 'efectivo' },
  { tipo: 'componente', signo: '−', label: 'Deudas', campo: 'deudas' },
  { tipo: 'subtotal', label: 'Escenario C (solo efectivo)', campo: 'escenario_c' },

  { tipo: 'componente', signo: '+', label: 'Stock materia prima', campo: 'stock_materia_prima' },
  { tipo: 'componente', signo: '+', label: 'Stock producto intermedio', campo: 'stock_producto_intermedio' },
  { tipo: 'componente', signo: '+', label: 'Horas en stand-by', campo: 'valor_horas_standby' },
  { tipo: 'componente', signo: '+', label: 'Utensilios sin absorber', campo: 'utensilios_sin_absorber' },
  { tipo: 'componente', signo: '+', label: 'Stock producto terminado (a precio de venta)', campo: 'stock_producto_terminado' },
  { tipo: 'subtotal', label: 'Escenario B (+ stock)', campo: 'escenario_b' },

  { tipo: 'subcomponente', label: 'Inmuebles', campo: 'total_inmuebles' },
  { tipo: 'subcomponente', label: 'Equipos', campo: 'total_equipos' },
  { tipo: 'subcomponente', label: 'Otros activos', campo: 'total_otros' },
  { tipo: 'grupo', signo: '+', label: 'Activos fijos', campo: 'activos_fijos' },
  { tipo: 'subtotal', label: 'Escenario A (+ activos fijos, liquidez: todo a precio de venta)', campo: 'escenario_a' },

  { tipo: 'separador' },
  { tipo: 'nota', label: 'Stock producto terminado (costo o mercado, el menor)', campo: 'stock_producto_terminado_conservador' },
  { tipo: 'subtotal', label: 'PATRIMONIO (contable: stock terminado sin ganancia no realizada)', campo: 'patrimonio', destacado: true },
]

// Movimientos del periodo. Van aparte porque en la pantalla de Balance su
// columna "actual" no sale del balance en vivo sino del resumen desde la
// ultima foto (son flujos del periodo, no saldos a hoy).
// Las cuatro salidas van desglosadas, no sumadas: cada una tiene su propia
// tabla y su propio vinculo con el movimiento (decision 4.1). "Gastos" es el
// residuo -lo que sale y no es ninguna de las otras tres-, asi que solo se
// entiende viendo las cuatro juntas.
export const filasMovimientos = [
  { label: 'Ventas de la semana', campo: 'ventas' },
  { label: 'Compras de la semana', campo: 'compras' },
  { label: 'Gastos de la semana', campo: 'gastos' },
  { label: 'Servicios de la semana (luz, agua, internet…)', campo: 'servicios' },
  { label: 'Pagos a trabajadores', campo: 'pagos' },
]
