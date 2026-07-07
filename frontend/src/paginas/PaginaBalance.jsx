import { useState, useEffect } from 'react'

function PaginaBalance() {
  const [actual, setActual] = useState(null)
  const [ultimo, setUltimo] = useState(null)
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    fetch('http://127.0.0.1:8000/balance-actual')
      .then((r) => r.json()).then(setActual).catch(console.error)
    fetch('http://127.0.0.1:8000/balance-ultimo')
      .then((r) => r.json()).then(setUltimo).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function tomarBalance() {
    const hoy = new Date().toISOString().slice(0, 10)
    fetch('http://127.0.0.1:8000/balances', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fecha_balance: hoy, dias_semana: 7 }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
      })
      .then(() => {
        setMensaje('Foto tomada. Ahora esta es la última foto.')
        cargar()   // recargar para que la nueva foto sea la "última"
      })
      .catch((e) => setMensaje(e.message))
  }

  // Helper: muestra la diferencia con color (verde sube, rojo baja)
  function diff(campo) {
    if (!actual || !ultimo) return null
    const d = actual[campo] - ultimo[campo]
    const color = d > 0 ? 'lightgreen' : d < 0 ? 'salmon' : 'gray'
    const signo = d > 0 ? '+' : ''
    return <span style={{ color }}>{signo}{d.toFixed(2)}</span>
  }

  const filas = [
    ['Efectivo', 'efectivo'],
    ['Stock materia prima', 'stock_materia_prima'],
    ['Stock producto intermedio', 'stock_producto_intermedio'],
    ['Horas en stand-by', 'valor_horas_standby'],
    ['Stock producto terminado', 'stock_producto_terminado'],
    ['Deudas', 'deudas'],
    ['Escenario C (solo efectivo)', 'escenario_c'],
    ['Escenario B (+ stock)', 'escenario_b'],
    ['Escenario A (todo)', 'escenario_a'],
    ['PATRIMONIO', 'patrimonio'],
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
              <td>{ultimo ? ultimo[campo] : '—'}</td>
              <td>{actual ? actual[campo] : '—'}</td>
              <td>{diff(campo)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!ultimo && <p>Aún no hay ninguna foto guardada. Toma la primera para empezar a comparar.</p>}

      <div style={{ marginTop: '1rem' }}>
        <button onClick={tomarBalance}>Tomar foto ahora</button>
      </div>
      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaBalance