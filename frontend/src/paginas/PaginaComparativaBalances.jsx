import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import { fmtMoneda } from '../formato'

// Conceptos del patrimonio (mismas filas que la pantalla de Balance, para
// que ambos reportes se lean igual). Las que empiezan con '*' son desgloses
// de la fila de arriba.
const filas = [
  ['Efectivo', 'efectivo'],
  ['Stock materia prima', 'stock_materia_prima'],
  ['Stock producto intermedio', 'stock_producto_intermedio'],
  ['Horas en stand-by', 'valor_horas_standby'],
  ['Stock producto terminado (a precio de venta)', 'stock_producto_terminado'],
  ['*Stock producto terminado (costo o mercado, el menor)', 'stock_producto_terminado_conservador'],
  ['Activos fijos', 'activos_fijos'],
  ['*Inmuebles', 'total_inmuebles'],
  ['*Equipos', 'total_equipos'],
  ['*Otros activos', 'total_otros'],
  ['Deudas', 'deudas'],
  ['Escenario C (solo efectivo)', 'escenario_c'],
  ['Escenario B (+ stock)', 'escenario_b'],
  ['Escenario A (+ activos fijos, liquidez: todo a precio de venta)', 'escenario_a'],
  ['PATRIMONIO (contable: stock terminado sin ganancia no realizada)', 'patrimonio'],
]

// Movimientos que cada foto capturó de SU semana previa. Comparar estos
// entre dos cierres muestra cómo cambió el ritmo del negocio semana a semana.
const filasMovimientos = [
  ['Ventas de la semana', 'ventas'],
  ['Compras de la semana', 'compras'],
  ['Gastos de la semana', 'gastos'],
  ['Pagos a trabajadores', 'pagos'],
]

// Etiqueta de una foto en el selector. Como varias fotos pueden compartir
// fecha, se antepone el id para poder distinguirlas.
function etiquetaFoto(b) {
  return `#${b.id_balance} — ${b.fecha}`
}

function PaginaComparativaBalances() {
  const [balances, setBalances] = useState([])
  const [idA, setIdA] = useState('')
  const [idB, setIdB] = useState('')

  useEffect(() => {
    apiGet('/balances')
      .then((lista) => {
        setBalances(lista)
        // Por defecto: A = penúltima foto, B = última. Así la diferencia
        // (B − A) muestra el cambio del último cierre respecto al anterior.
        if (lista.length >= 2) {
          setIdB(String(lista[0].id_balance))
          setIdA(String(lista[1].id_balance))
        } else if (lista.length === 1) {
          setIdB(String(lista[0].id_balance))
          setIdA(String(lista[0].id_balance))
        }
      })
      .catch(console.error)
  }, [])

  const fotoA = balances.find((b) => String(b.id_balance) === idA) || null
  const fotoB = balances.find((b) => String(b.id_balance) === idB) || null

  // Diferencia B − A con color (verde sube, rojo baja). Si a alguna de las
  // dos fotos le falta el dato (columna agregada después), no se compara.
  function diff(campo) {
    if (!fotoA || !fotoB) return null
    const a = fotoA[campo]
    const b = fotoB[campo]
    if (a == null || b == null) return <span style={{ color: 'gray' }}>—</span>
    const d = b - a
    const color = d > 0 ? 'lightgreen' : d < 0 ? 'salmon' : 'gray'
    const signo = d > 0 ? '+' : ''
    return <span style={{ color }}>{signo}{fmtMoneda(d)}</span>
  }

  function celda(foto, campo) {
    if (!foto) return '—'
    const v = foto[campo]
    return v == null ? '—' : fmtMoneda(v)
  }

  return (
    <div>
      <h2>Comparar cierres — informe entre dos fotos de balance</h2>

      <div className="no-imprimir" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '1rem' }}>
        <label>
          Foto A:{' '}
          <select value={idA} onChange={(e) => setIdA(e.target.value)}>
            {balances.map((b) => (
              <option key={b.id_balance} value={b.id_balance}>{etiquetaFoto(b)}</option>
            ))}
          </select>
        </label>
        <label>
          Foto B:{' '}
          <select value={idB} onChange={(e) => setIdB(e.target.value)}>
            {balances.map((b) => (
              <option key={b.id_balance} value={b.id_balance}>{etiquetaFoto(b)}</option>
            ))}
          </select>
        </label>
        <button onClick={() => window.print()}>Imprimir / PDF</button>
      </div>

      {balances.length < 2 && (
        <p>Se necesitan al menos dos fotos guardadas para comparar. Tomá fotos desde la pantalla de Balance.</p>
      )}

      <table border="1">
        <thead>
          <tr>
            <th>Concepto</th>
            <th>Foto A {fotoA ? `(${etiquetaFoto(fotoA)})` : ''}</th>
            <th>Foto B {fotoB ? `(${etiquetaFoto(fotoB)})` : ''}</th>
            <th>Diferencia (B − A)</th>
          </tr>
        </thead>
        <tbody>
          {filas.map(([label, campo]) => (
            <tr key={campo}>
              <td>{label}</td>
              <td>{celda(fotoA, campo)}</td>
              <td>{celda(fotoB, campo)}</td>
              <td>{diff(campo)}</td>
            </tr>
          ))}
          <tr>
            <td colSpan={4} style={{ background: '#eee', fontWeight: 'bold' }}>Movimientos de la semana previa a cada foto</td>
          </tr>
          {filasMovimientos.map(([label, campo]) => (
            <tr key={campo}>
              <td>{label}</td>
              <td>{celda(fotoA, campo)}</td>
              <td>{celda(fotoB, campo)}</td>
              <td>{diff(campo)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaComparativaBalances
