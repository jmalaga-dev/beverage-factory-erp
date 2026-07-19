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
  // De qué jornada salió la sugerencia de horas (6.7). null = sin historial.
  const [horasSugeridas, setHorasSugeridas] = useState(null)
  // Filtro de la tabla: 'no_pagadas' (default, como antes), 'standby' (horas
  // registradas que aun no se consumieron en una produccion — las que el
  // cierre de produccion va a repartir) o 'todas'. Mutuamente excluyentes.
  const [filtro, setFiltro] = useState('no_pagadas')

  // Fila sobre la que esta el mouse (para mostrar sus botones) y fila en edicion
  const [filaHover, setFilaHover] = useState(null)
  const [editando, setEditando] = useState(null)
  const [editTrabajador, setEditTrabajador] = useState('')
  const [editHoras, setEditHoras] = useState('')

  // Pase de lista (mejora 10.9): una fila por trabajador habilitado, con sus
  // horas del dia. Mapa id_trabajador -> texto de horas (string, para poder
  // dejarlo vacio). 0 o vacio = esa persona no vino ese dia y se omite.
  const [horasLote, setHorasLote] = useState({})
  const [loteMensaje, setLoteMensaje] = useState('')

  function cargar() {
    apiGet('/trabajadores').then(setTrabajadores).catch(console.error)
    apiGet('/jornadas').then(setJornadas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Al elegir trabajador, proponer las horas de su última jornada (6.7): la
  // mayoría trabaja la misma cantidad de horas casi todos los días, así que
  // es el valor que más se repite. Se calcula sobre las jornadas ya cargadas,
  // sin pedirle nada al backend.
  function elegirTrabajador(id) {
    setIdTrabajador(id)
    const suyas = jornadas.filter((j) => String(j.id_trabajador) === String(id))
    if (suyas.length === 0) { setHorasSugeridas(null); return }
    // La lista puede venir en cualquier orden: buscar la de fecha más reciente
    // y, a igual fecha, la de id más alto (la última registrada ese día).
    const ultima = suyas.reduce((a, b) => {
      if (a.fecha !== b.fecha) return a.fecha > b.fecha ? a : b
      return a.id_jornada > b.id_jornada ? a : b
    })
    setHoras(String(ultima.horas))
    setHorasSugeridas(ultima)
  }

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
        setHorasSugeridas(null)
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

  function cambiarHorasLote(idTrabajador, valor) {
    setHorasLote({ ...horasLote, [idTrabajador]: valor })
  }

  function registrarLote() {
    const trabajadoresHabilitados = trabajadores.filter((t) => t.habilitado)
    const lineas = trabajadoresHabilitados.map((t) => ({
      id_trabajador: t.id_trabajador,
      horas: horasLote[t.id_trabajador] ? parseFloat(horasLote[t.id_trabajador]) : null,
    }))
    if (!lineas.some((l) => l.horas > 0)) {
      setLoteMensaje('Ingresa horas para al menos un trabajador')
      return
    }
    apiPost('/jornadas-lote', { lineas, fecha: fechaParaEnviar })
      .then((r) => {
        setLoteMensaje(r.mensaje || 'Jornadas registradas')
        setHorasLote({})
        cargar()
      })
      .catch((e) => setLoteMensaje(e.message))
  }

  return (
    <div>
      <h2>Registrar jornada</h2>
      <div>
        <SelectorBuscable
          opciones={trabajadores.filter((t) => t.habilitado)}
          valor={idTrabajador}
          onCambiar={elegirTrabajador}
          obtenerId={(t) => t.id_trabajador}
          obtenerTexto={(t) => `${t.nombre} (${t.tarifa} Bs/hora)`}
          placeholder="-- Trabajador --"
        />
        <input type="number" placeholder="Horas trabajadas"
          value={horas} onChange={(e) => setHoras(e.target.value)} />
        {horasSugeridas && (
          <span style={{ marginLeft: '0.4rem', color: '#557', fontSize: '0.85em' }}>
            sugerido: su última jornada ({horasSugeridas.fecha}) — editable
          </span>
        )}
        <button onClick={registrar}>Registrar jornada</button>
      </div>
      {mensaje && <p>{mensaje}</p>}

      {/* Pase de lista del dia (mejora 10.9): una fila por trabajador
          habilitado, para no tener que repetir el formulario de arriba una
          vez por persona. Una fila en 0 o vacia se omite: esa persona no
          vino ese dia. */}
      <h2>Registrar jornadas del día (tabla)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Pon las horas de hoy para cada trabajador habilitado. Deja en blanco
        (o 0) a quien no vino ese día — no se le registra jornada.
      </p>
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        <table border="1" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr><th>Trabajador</th><th>Bs/hora</th><th>Horas de hoy</th></tr>
          </thead>
          <tbody>
            {trabajadores.filter((t) => t.habilitado).map((t) => (
              <tr key={t.id_trabajador}>
                <td>{t.nombre}</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(t.tarifa)}</td>
                <td>
                  <input type="number" placeholder="0" style={{ width: '70px' }}
                    value={horasLote[t.id_trabajador] ?? ''}
                    onChange={(e) => cambiarHorasLote(t.id_trabajador, e.target.value)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button onClick={registrarLote} style={{ marginTop: '0.5rem' }}>Registrar jornadas</button>
        {loteMensaje && <p>{loteMensaje}</p>}
      </div>

      <h2>Jornadas registradas</h2>
      <div style={{ marginBottom: '0.5rem' }}>
        <label>
          <input type="radio" name="filtroJornadas" checked={filtro === 'no_pagadas'}
            onChange={() => setFiltro('no_pagadas')} />
          {' '}Solo no pagadas
        </label>
        {' '}
        <label style={{ marginLeft: '1rem' }}>
          <input type="radio" name="filtroJornadas" checked={filtro === 'standby'}
            onChange={() => setFiltro('standby')} />
          {' '}Solo standby (horas sin consumir)
        </label>
        {' '}
        <label style={{ marginLeft: '1rem' }}>
          <input type="radio" name="filtroJornadas" checked={filtro === 'todas'}
            onChange={() => setFiltro('todas')} />
          {' '}Todas
        </label>
      </div>
      <table border="1">
        <thead>
          <tr><th>Trabajador</th><th>Fecha</th><th>Horas</th><th>Horas restantes</th><th>Pagada</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {jornadas
            .filter((j) => {
              if (filtro === 'no_pagadas') return !j.pagada
              if (filtro === 'standby') return j.horas_restantes > 0
              return true
            })
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