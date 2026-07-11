import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero } from '../formato'

function PaginaJornadas() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [trabajadores, setTrabajadores] = useState([])
  const [jornadas, setJornadas] = useState([])

  const [idTrabajador, setIdTrabajador] = useState('')
  const [horas, setHoras] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [soloNoPagadas, setSoloNoPagadas] = useState(true)

  // Fila sobre la que esta el mouse (para mostrar sus botones) y fila en edicion
  const [filaHover, setFilaHover] = useState(null)
  const [editando, setEditando] = useState(null)
  const [editTrabajador, setEditTrabajador] = useState('')
  const [editHoras, setEditHoras] = useState('')

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
      fecha: fechaParaEnviar,
    })
      .then(() => {
        setMensaje('Jornada registrada')
        setHoras('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicion(j) {
    setEditando(j.id_jornada)
    setEditTrabajador(String(j.id_trabajador))
    setEditHoras(String(j.horas))
  }

  function cancelarEdicion() {
    setEditando(null)
  }

  function guardarEdicion(id) {
    if (editTrabajador === '' || editHoras === '') {
      setMensaje('Elige trabajador y horas')
      return
    }
    apiPatch(`/jornadas/${id}`, {
      id_trabajador: parseInt(editTrabajador),
      horas: parseFloat(editHoras),
    })
      .then(() => {
        setMensaje('Jornada actualizada')
        setEditando(null)
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function eliminarJornada(id) {
    if (!window.confirm('¿Eliminar esta jornada? No se puede deshacer.')) return
    apiDelete(`/jornadas/${id}`)
      .then(() => {
        setMensaje('Jornada eliminada')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Registrar jornada</h2>
      <div>
        <SelectorBuscable
          opciones={trabajadores.filter((t) => t.habilitado)}
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
      <label style={{ display: 'block', marginBottom: '0.5rem' }}>
        <input type="checkbox" checked={soloNoPagadas}
          onChange={(e) => setSoloNoPagadas(e.target.checked)} />
        {' '}Mostrar solo no pagadas
      </label>
      <table border="1">
        <thead>
          <tr><th>Trabajador</th><th>Fecha</th><th>Horas</th><th>Horas restantes</th><th>Pagada</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {jornadas
            .filter((j) => !soloNoPagadas || !j.pagada)
            .map((j) => (
              <tr key={j.id_jornada}
                onMouseEnter={() => setFilaHover(j.id_jornada)}
                onMouseLeave={() => setFilaHover(null)}>
                {editando === j.id_jornada ? (
                  <>
                    <td>
                      <SelectorBuscable
                        opciones={trabajadores.filter((t) => t.habilitado)}
                        valor={editTrabajador}
                        onCambiar={setEditTrabajador}
                        obtenerId={(t) => t.id_trabajador}
                        obtenerTexto={(t) => t.nombre}
                        placeholder="-- Trabajador --"
                      />
                    </td>
                    <td>{j.fecha}</td>
                    <td>
                      <input type="number" style={{ width: '70px' }}
                        value={editHoras} onChange={(e) => setEditHoras(e.target.value)} />
                    </td>
                    <td>{fmtNumero(j.horas_restantes)}</td>
                    <td>{j.pagada ? 'Sí' : 'No'}</td>
                    <td>
                      <button onClick={() => guardarEdicion(j.id_jornada)}>Guardar</button>
                      {' '}<button onClick={cancelarEdicion}>Cancelar</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{j.nombre_trabajador}</td>
                    <td>{j.fecha}</td>
                    <td>{fmtNumero(j.horas)}</td>
                    <td>{fmtNumero(j.horas_restantes)}</td>
                    <td>{j.pagada ? 'Sí' : 'No'}</td>
                    <td>
                      {filaHover === j.id_jornada && j.intacta && (
                        <>
                          <button onClick={() => empezarEdicion(j)}>Editar</button>
                          {' '}<button onClick={() => eliminarJornada(j.id_jornada)}>Eliminar</button>
                        </>
                      )}
                    </td>
                  </>
                )}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaJornadas