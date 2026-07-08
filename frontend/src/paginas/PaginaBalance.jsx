import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import TablaFiltrable from '../componentes/TablaFiltrable'
import { fmtMoneda, fmtNumero } from '../formato'

// Columnas comunes a los tres detalles: descripcion, cantidad y costo
// promedio ponderado (los endpoints "general" ya lo calculan por producto).
const columnasDetalle = [
  { key: 'descripcion', label: 'Producto' },
  { key: 'stock_total', label: 'Cantidad', formato: (v) => fmtNumero(v, 2) },
  { key: 'costo_promedio', label: 'Costo ponderado promedio', formato: (v) => fmtNumero(v, 4) },
]

// Columnas de la lista de activos fijos (resumen en el balance).
const columnasActivos = [
  { key: 'descripcion', label: 'Descripción' },
  { key: 'tipo_bien', label: 'Tipo' },
  { key: 'valor', label: 'Valor', formato: (v) => fmtMoneda(v) },
]

function PaginaBalance() {
  const [actual, setActual] = useState(null)
  const [ultimo, setUltimo] = useState(null)
  const [resumen, setResumen] = useState(null)
  const [mensaje, setMensaje] = useState('')
  const [diasAbierto, setDiasAbierto] = useState(false)

  const [detalleTerminado, setDetalleTerminado] = useState([])
  const [detalleIntermedio, setDetalleIntermedio] = useState([])
  const [detalleMateriaPrima, setDetalleMateriaPrima] = useState([])
  const [activos, setActivos] = useState([])

  function cargar() {
    apiGet('/balance-actual').then(setActual).catch(console.error)
    apiGet('/balance-ultimo').then(setUltimo).catch(console.error)
    apiGet('/balance-resumen-semana').then(setResumen).catch(console.error)
    apiGet('/stock-terminado-general').then(setDetalleTerminado).catch(console.error)
    apiGet('/stock-intermedio-general').then(setDetalleIntermedio).catch(console.error)
    apiGet('/stock-materia-prima').then(setDetalleMateriaPrima).catch(console.error)
    apiGet('/activos').then(setActivos).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function tomarBalance() {
    const hoy = new Date().toISOString().slice(0, 10)
    apiPost('/balances', { fecha_balance: hoy, dias_semana: 7 })
      .then(() => {
        setMensaje('Foto tomada. Ahora esta es la última foto.')
        cargar()   // recargar para que la nueva foto sea la "última"
      })
      .catch((e) => setMensaje(e.message))
  }

  // Helper: muestra la diferencia con color (verde sube, rojo baja).
  // `fuente` indica de donde sale el valor "actual": del balance en vivo,
  // o del resumen de movimientos desde la ultima foto (ventas/compras/etc).
  function diff(campo, fuente) {
    const columnaActual = fuente === 'resumen' ? resumen : actual
    if (!columnaActual || !ultimo) return null
    const d = columnaActual[campo] - ultimo[campo]
    const color = d > 0 ? 'lightgreen' : d < 0 ? 'salmon' : 'gray'
    const signo = d > 0 ? '+' : ''
    return <span style={{ color }}>{signo}{fmtMoneda(d)}</span>
  }

  const filas = [
    ['Efectivo', 'efectivo'],
    ['Stock materia prima', 'stock_materia_prima'],
    ['Stock producto intermedio', 'stock_producto_intermedio'],
    ['Horas en stand-by', 'valor_horas_standby'],
    ['Stock producto terminado', 'stock_producto_terminado'],
    ['Activos fijos', 'activos_fijos'],
    ['Deudas', 'deudas'],
    ['Escenario C (solo efectivo)', 'escenario_c'],
    ['Escenario B (+ stock)', 'escenario_b'],
    ['Escenario A (+ activos fijos)', 'escenario_a'],
    ['PATRIMONIO', 'patrimonio'],
  ]

  // Movimientos desde la ultima foto: "Ultima foto" = lo que esa foto
  // capturo de SU semana anterior; "Estado actual" = lo que paso desde
  // esa foto hasta hoy (resumen en vivo, sin necesidad de tomar otra foto).
  const filasMovimientos = [
    ['Ventas de la semana', 'ventas'],
    ['Compras de la semana', 'compras'],
    ['Gastos de la semana', 'gastos'],
    ['Pagos a trabajadores', 'pagos'],
  ]

  return (
    <div>
      <h2>Balance — comparación</h2>

      <table border="1">
        <thead>
          <tr>
            <th>Concepto</th>
            <th>Última foto{ultimo ? ` (${ultimo.fecha})` : ''}</th>
            <th>Estado actual</th>
            <th>Diferencia</th>
          </tr>
        </thead>
        <tbody>
          {filas.map(([label, campo]) => (
            <tr key={campo}>
              <td>{label}</td>
              <td>{ultimo ? fmtMoneda(ultimo[campo]) : '—'}</td>
              <td>{actual ? fmtMoneda(actual[campo]) : '—'}</td>
              <td>{diff(campo, 'actual')}</td>
            </tr>
          ))}
          {filasMovimientos.map(([label, campo]) => (
            <tr key={campo}>
              <td>{label}</td>
              <td>{ultimo ? fmtMoneda(ultimo[campo]) : '—'}</td>
              <td>{resumen ? fmtMoneda(resumen[campo]) : '—'}</td>
              <td>{diff(campo, 'resumen')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!ultimo && <p>Aún no hay ninguna foto guardada. Toma la primera para empezar a comparar.</p>}

      <div style={{ marginTop: '1rem' }}>
        <button onClick={tomarBalance}>Tomar foto ahora</button>
      </div>
      {mensaje && <p>{mensaje}</p>}

      <h3 style={{ cursor: 'pointer', userSelect: 'none', marginTop: '1.5rem' }}
        onClick={() => setDiasAbierto(!diasAbierto)}>
        {diasAbierto ? '▾' : '▸'} Detalle día a día desde la última foto
        {resumen && ` (${resumen.desde || 'inicio'} → ${resumen.hasta})`}
      </h3>
      {diasAbierto && (
        resumen && resumen.dias.length > 0 ? (
          resumen.dias.map((dia) => (
            <div key={dia.fecha} style={{ marginBottom: '1rem' }}>
              <strong>Fecha: {dia.fecha}</strong>
              <ul>
                {dia.eventos.map((ev, i) => <li key={i}>{ev}</li>)}
              </ul>
            </div>
          ))
        ) : (
          <p>Sin movimientos registrados en este período.</p>
        )
      )}

      <h2 style={{ marginTop: '2rem' }}>Detalle por producto (estado actual)</h2>
      <TablaFiltrable
        titulo="Producto Terminado"
        filas={detalleTerminado}
        columnas={columnasDetalle}
        claveOrden="descripcion"
      />
      <TablaFiltrable
        titulo="Producto Intermedio"
        filas={detalleIntermedio}
        columnas={columnasDetalle}
        claveOrden="descripcion"
      />
      <TablaFiltrable
        titulo="Materia Prima"
        filas={detalleMateriaPrima}
        columnas={columnasDetalle}
        claveOrden="descripcion"
      />

      <h2 style={{ marginTop: '2rem' }}>Activos fijos</h2>
      <TablaFiltrable
        titulo="Activos"
        filas={activos}
        columnas={columnasActivos}
        claveOrden="descripcion"
      />
    </div>
  )
}

export default PaginaBalance