import { useState, useEffect } from 'react'

function PaginaJornadas() {
  const [trabajadores, setTrabajadores] = useState([])
  const [jornadas, setJornadas] = useState([])

  const [idTrabajador, setIdTrabajador] = useState('')
  const [horas, setHoras] = useState('')
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    fetch('http://127.0.0.1:8000/trabajadores')
      .then((r) => r.json()).then(setTrabajadores).catch(console.error)
    fetch('http://127.0.0.1:8000/jornadas')
      .then((r) => r.json()).then(setJornadas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrar() {
    if (idTrabajador === '' || horas === '') {
      setMensaje('Elige trabajador y horas')
      return
    }
    fetch('http://127.0.0.1:8000/jornadas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_trabajador: parseInt(idTrabajador),
        horas: parseFloat(horas),
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
      })
      .then(() => {
        setMensaje('Jornada registrada')
        setHoras('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Registrar jornada</h2>
      <div>
        <select value={idTrabajador} onChange={(e) => setIdTrabajador(e.target.value)}>
          <option value="">-- Trabajador --</option>
          {trabajadores.map((t) => (
            <option key={t.id_trabajador} value={t.id_trabajador}>
              {t.nombre} ({t.pago} Bs/hora)
            </option>
          ))}
        </select>
        <input type="number" placeholder="Horas trabajadas"
          value={horas} onChange={(e) => setHoras(e.target.value)} />
        <button onClick={registrar}>Registrar jornada</button>
      </div>
      {mensaje && <p>{mensaje}</p>}

      <h2>Jornadas registradas</h2>
      <table border="1">
        <thead>
          <tr><th>Trabajador</th><th>Fecha</th><th>Horas</th><th>Pagada</th></tr>
        </thead>
        <tbody>
          {jornadas.map((j) => (
            <tr key={j.id_jornada}>
              <td>{j.nombre_trabajador}</td>
              <td>{j.fecha}</td>
              <td>{j.horas}</td>
              <td>{j.pagada ? 'Sí' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaJornadas