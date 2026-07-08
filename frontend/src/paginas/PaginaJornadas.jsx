import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

function PaginaJornadas() {
  const [trabajadores, setTrabajadores] = useState([])
  const [jornadas, setJornadas] = useState([])

  const [idTrabajador, setIdTrabajador] = useState('')
  const [horas, setHoras] = useState('')
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/trabajadores').then(setTrabajadores).catch(console.error)
    apiGet('/jornadas').then(setJornadas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrar() {
    if (idTrabajador === '' || horas === '') {
      setMensaje('Elige trabajador y horas')
      return
    }
    apiPost('/jornadas', {
      id_trabajador: parseInt(idTrabajador),
      horas: parseFloat(horas),
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
        <SelectorBuscable
          opciones={trabajadores}
          valor={idTrabajador}
          onCambiar={setIdTrabajador}
          obtenerId={(t) => t.id_trabajador}
          obtenerTexto={(t) => `${t.nombre} (${t.pago} Bs/hora)`}
          placeholder="-- Trabajador --"
        />
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