import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import FilaBalance from '../componentes/FilaBalance'
import TablaFiltrable from '../componentes/TablaFiltrable'
import { filasBalance, filasMovimientos } from '../filasBalance'
import { fmtMoneda, fmtNumero } from '../formato'
import { useFechaGlobal } from '../componentes/FechaGlobal'

// Columnas comunes a los tres detalles: un marcador de destacado (item 14),
// descripcion, cantidad y costo promedio ponderado (los endpoints "general"
// ya lo calculan por producto).
const columnasDetalle = [
  { key: 'descripcion', label: 'Producto' },
  { key: 'destacado', label: '★', formato: (v) => (v ? '★' : '') },
  { key: 'stock_total', label: 'Cantidad', formato: (v) => fmtNumero(v, 2) },
  { key: 'costo_promedio', label: 'Costo ponderado promedio', formato: (v) => fmtNumero(v, 4) },
]

// Producto Terminado suma una columna de paquetes equivalentes (mejora 4.7):
// solo esa tabla tiene Botellas_Por_Paquete (3.9), intermedio y materia
// prima no se venden por paquete.
const columnasDetalleTerminado = [
  ...columnasDetalle,
  { key: 'paquetes_equivalentes', label: 'Paquetes equiv.', formato: (v) => fmtNumero(v, 2) },
]

// Columnas de la lista de activos fijos (resumen en el balance).
const columnasActivos = [
  { key: 'descripcion', label: 'Descripción' },
  { key: 'tipo_bien', label: 'Tipo' },
  { key: 'valor', label: 'Valor', formato: (v) => fmtMoneda(v) },
]

function PaginaBalance() {
  const { fechaParaEnviar } = useFechaGlobal()
  // Filtro del detalle por producto: mostrar solo los marcados como destacados
  // (item 14). Las tablas de MP/intermedio/terminado son largas; esto las
  // acota a los que mas se usan, marcados a mano en Catalogos.
  const [soloDestacados, setSoloDestacados] = useState(false)
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
    // Prioridad: la fecha global fijada (mejora 6.10). Si no hay, "hoy" LOCAL:
    // `toISOString()` a secas devuelve UTC, y a las 11pm de Bolivia (UTC-4) eso
    // ya es el día siguiente. Se compensa el offset como en Cierre/Prorrateo.
    const d = new Date()
    const hoyLocal = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
    const fecha = fechaParaEnviar || hoyLocal
    apiPost('/balances', { fecha_balance: fecha, dias_semana: 7 })
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
    const a = ultimo[campo]
    const b = columnaActual[campo]
    // Una foto vieja no tiene los campos agregados después (pagos, utensilios
    // sin absorber): vienen en null. Restar contra null da el valor entero,
    // porque en JS null se convierte en 0 — y se mostraría un alza inventada
    // de algo que en realidad nunca se midió. No se compara.
    if (a == null || b == null) return <span style={{ color: 'gray' }}>—</span>
    const d = b - a
    const color = d > 0 ? 'lightgreen' : d < 0 ? 'salmon' : 'gray'
    const signo = d > 0 ? '+' : ''
    return <span style={{ color }}>{signo}{fmtMoneda(d)}</span>
  }

  // Un importe: alineado a la derecha y en rojo si es negativo.
  function celdaImporte(valor) {
    if (valor === null || valor === undefined) return <td className="num">—</td>
    return <td className={`num${valor < 0 ? ' negativo' : ''}`}>{fmtMoneda(valor)}</td>
  }

  return (
    <div>
      <h2>Balance — comparación</h2>

      <table className="tabla-balance">
        <thead>
          <tr>
            <th>Concepto</th>
            <th className="num">Última foto{ultimo ? ` (${ultimo.fecha})` : ''}</th>
            <th className="num">Estado actual</th>
            <th className="num">Diferencia</th>
          </tr>
        </thead>
        <tbody>
          {filasBalance.map((fila, i) => (
            <FilaBalance key={fila.campo || `sep${i}`} fila={fila}>
              {celdaImporte(ultimo ? ultimo[fila.campo] : null)}
              {celdaImporte(actual ? actual[fila.campo] : null)}
              <td className="num">{diff(fila.campo, 'actual')}</td>
            </FilaBalance>
          ))}

          <FilaBalance fila={{ tipo: 'separador' }} />

          {/* Movimientos desde la ultima foto: "Ultima foto" = lo que esa foto
              capturo de SU semana anterior; "Estado actual" = lo que paso desde
              esa foto hasta hoy (resumen en vivo, sin tomar otra foto). */}
          {filasMovimientos.map((fila) => (
            <FilaBalance key={fila.campo} fila={{ ...fila, tipo: 'componente' }}>
              {celdaImporte(ultimo ? ultimo[fila.campo] : null)}
              {celdaImporte(resumen ? resumen[fila.campo] : null)}
              <td className="num">{diff(fila.campo, 'resumen')}</td>
            </FilaBalance>
          ))}
        </tbody>
      </table>

      {!ultimo && <p>Aún no hay ninguna foto guardada. Toma la primera para empezar a comparar.</p>}

      <div className="no-imprimir" style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
        <button onClick={tomarBalance}>Tomar foto ahora</button>
        <button onClick={() => window.print()}>Imprimir / PDF</button>
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
      <label className="no-imprimir" style={{ display: 'block', marginBottom: '0.5rem' }}>
        <input type="checkbox" checked={soloDestacados}
          onChange={(e) => setSoloDestacados(e.target.checked)} />
        {' '}Mostrar solo los destacados (★, se marcan en Catálogos)
      </label>
      <TablaFiltrable
        titulo="Producto Terminado"
        filas={soloDestacados ? detalleTerminado.filter((f) => f.destacado) : detalleTerminado}
        columnas={columnasDetalleTerminado}
        claveOrden="descripcion"
        totales={['stock_total', 'paquetes_equivalentes']}
      />
      <TablaFiltrable
        titulo="Producto Intermedio"
        filas={soloDestacados ? detalleIntermedio.filter((f) => f.destacado) : detalleIntermedio}
        columnas={columnasDetalle}
        claveOrden="descripcion"
      />
      <TablaFiltrable
        titulo="Materia Prima"
        filas={soloDestacados ? detalleMateriaPrima.filter((f) => f.destacado) : detalleMateriaPrima}
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