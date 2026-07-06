import { useState, useEffect } from 'react'

function PaginaProrrateo() {
  const [anioMes, setAnioMes] = useState('')
  const [horas, setHoras] = useState(null)
  const [gastos, setGastos] = useState(null)
  const [mensaje, setMensaje] = useState('')

  // Cargar los gastos extra (no dependen del mes)
  useEffect(() => {
    fetch('http://127.0.0.1:8000/gastos-extra-total')
      .then((r) => r.json()).then(setGastos).catch(console.error)
  }, [])

  // Cuando cambia el mes, cargar las horas de ese mes
  function verMes(mes) {
    setAnioMes(mes)
    if (mes.trim() === '') { setHoras(null); return }
    fetch(`http://127.0.0.1:8000/horas-producto-mes/${mes}`)
      .then((r) => r.json()).then(setHoras).catch(console.error)
  }

  function calcular() {
    if (anioMes.trim() === '') { setMensaje('Indica el mes'); return }
    fetch('http://127.0.0.1:8000/prorrateos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anio_mes: anioMes }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
      })
      .then((data) => setMensaje(`Prorrateo calculado: ${data.asignaciones} asignaciones`))
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Prorrateo mensual de gastos extra</h2>
      <p>Reparte los gastos extra del mes entre los productos según las horas trabajadas.</p>

      {/* Gastos extra a repartir */}
      {gastos && (
        <div>
          <h3>Gastos extra mensuales (total: {gastos.total} Bs)</h3>
          <table border="1">
            <thead><tr><th>Gasto</th><th>Precio/mes</th></tr></thead>
            <tbody>
              {gastos.detalle.map((g, i) => (
                <tr key={i}><td>{g.descripcion}</td><td>{g.precio}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginTop: '1rem' }}>
        <input type="text" placeholder="Mes (ej: 2026-06)"
          value={anioMes} onChange={(e) => verMes(e.target.value)} />
        <button onClick={calcular}>Calcular prorrateo</button>
      </div>

      {/* Horas por producto ese mes */}
      {horas && (
        <div>
          <h3>Productos que usaron la fábrica en {anioMes} (total: {horas.total_horas} horas)</h3>
          {horas.detalle.length === 0 ? (
            <p>No hay horas registradas para este mes.</p>
          ) : (
            <table border="1">
              <thead><tr><th>Producto</th><th>Horas</th><th>% del mes</th></tr></thead>
              <tbody>
                {horas.detalle.map((h, i) => (
                  <tr key={i}>
                    <td>{h.producto}</td>
                    <td>{h.horas}</td>
                    <td>{horas.total_horas > 0 ? ((h.horas / horas.total_horas) * 100).toFixed(1) : 0}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaProrrateo