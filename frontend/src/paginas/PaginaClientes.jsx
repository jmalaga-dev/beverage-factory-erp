import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import Catalogo from '../componentes/Catalogo'

function PaginaClientes() {
  const [clientes, setClientes] = useState([])
  const [sectores, setSectores] = useState([])

  const [nombre, setNombre] = useState('')
  const [apellido, setApellido] = useState('')
  const [celular, setCelular] = useState('')
  const [licoreria, setLicoreria] = useState('')
  const [idSector, setIdSector] = useState('')
  const [linkMaps, setLinkMaps] = useState('')
  const [latitud, setLatitud] = useState('')
  const [longitud, setLongitud] = useState('')

  // Edicion in-line de un cliente
  const [editando, setEditando] = useState(null)
  const [edit, setEdit] = useState({})

  const [mensaje, setMensaje] = useState('')

  function cargarClientes() {
    apiGet('/clientes')
      .then((datos) => setClientes(datos))
      .catch((e) => console.error('Error al cargar clientes:', e))
  }

  function cargarSectores() {
    apiGet('/sectores')
      .then((datos) => setSectores(datos))
      .catch((e) => console.error('Error al cargar sectores:', e))
  }

  useEffect(() => {
    cargarClientes()
    cargarSectores()
  }, [])

  function extraerCoordenadas() {
    if (linkMaps.trim() === '') {
      setMensaje('Pega un link de Maps primero')
      return
    }

    let lat = null
    let lng = null

    const patronArroba = linkMaps.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/)
    const patron3d4d = linkMaps.match(/!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)/)

    if (patron3d4d) {
      lat = patron3d4d[1]
      lng = patron3d4d[2]
    } else if (patronArroba) {
      lat = patronArroba[1]
      lng = patronArroba[2]
    }

    if (lat && lng) {
      setLatitud(lat)
      setLongitud(lng)
      setMensaje('Coordenadas extraidas del link')
    } else {
      setMensaje('No se pudo extraer del link. Pega lat/long a mano.')
    }
  }

  function crearCliente() {
    if (nombre.trim() === '') {
      setMensaje('El nombre es obligatorio')
      return
    }

    apiPost('/clientes', {
      nombre: nombre,
      apellido: apellido || null,
      celular: celular || null,
      licoreria: licoreria || null,
      latitud: latitud ? parseFloat(latitud) : null,
      longitud: longitud ? parseFloat(longitud) : null,
      id_sector: idSector ? parseInt(idSector) : null,
    })
      .then(() => {
        setMensaje('Cliente creado correctamente')
        setNombre('')
        setApellido('')
        setCelular('')
        setLicoreria('')
        setIdSector('')
        setLinkMaps('')
        setLatitud('')
        setLongitud('')
        cargarClientes()
      })
      .catch((e) => setMensaje(e.message))
  }

  function nombreSector(id) {
    const s = sectores.find((x) => x.id_sector === id)
    return s ? s.nombre : (id ? `Sector ${id}` : '—')
  }

  function empezarEdicion(c) {
    setEditando(c.id_cliente)
    setEdit({
      nombre: c.nombre ?? '',
      apellido: c.apellido ?? '',
      celular: c.celular ?? '',
      licoreria: c.licoreria ?? '',
      id_sector: c.id_sector ?? '',
    })
  }

  function guardarEdicion(id) {
    apiPatch(`/clientes/${id}`, {
      nombre: edit.nombre,
      apellido: edit.apellido || null,
      celular: edit.celular || null,
      licoreria: edit.licoreria || null,
      // id_sector = 0 desvincula el sector (lo entiende el backend)
      id_sector: edit.id_sector === '' ? 0 : parseInt(edit.id_sector),
    })
      .then(() => { setMensaje('Cliente actualizado'); setEditando(null); cargarClientes() })
      .catch((e) => setMensaje(e.message))
  }

  function alternarHabilitado(c) {
    apiPatch(`/clientes/${c.id_cliente}/habilitado`, { habilitado: !c.habilitado })
      .then(cargarClientes)
      .catch((e) => setMensaje(e.message))
  }

  function eliminarCliente(c) {
    if (!window.confirm(`¿Borrar a «${c.nombre}»? No se puede deshacer.`)) return
    apiDelete(`/clientes/${c.id_cliente}`)
      .then(() => { setMensaje('Cliente eliminado'); cargarClientes() })
      .catch((e) => setMensaje(e.message))
  }

  const sectoresHabilitados = sectores.filter((s) => s.habilitado)

  return (
    <div>
      <h2>Nuevo cliente</h2>

      <div>
        <input type="text" placeholder="Nombre"
          value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <input type="text" placeholder="Apellido"
          value={apellido} onChange={(e) => setApellido(e.target.value)} />
        <input type="text" placeholder="Celular"
          value={celular} onChange={(e) => setCelular(e.target.value)} />
        <input type="text" placeholder="Licorería"
          value={licoreria} onChange={(e) => setLicoreria(e.target.value)} />

        <SelectorBuscable
          opciones={sectoresHabilitados}
          valor={idSector}
          onCambiar={setIdSector}
          obtenerId={(s) => s.id_sector}
          obtenerTexto={(s) => s.nombre}
          placeholder="-- Sin sector --"
        />

        <div>
          <input type="text" placeholder="Link de Google Maps"
            value={linkMaps} onChange={(e) => setLinkMaps(e.target.value)} />
          <button onClick={extraerCoordenadas}>Extraer coordenadas</button>
        </div>
        <div>
          <input type="text" placeholder="Latitud"
            value={latitud} onChange={(e) => setLatitud(e.target.value)} />
          <input type="text" placeholder="Longitud"
            value={longitud} onChange={(e) => setLongitud(e.target.value)} />
        </div>

        <button onClick={crearCliente}>Agregar cliente</button>
      </div>

      {mensaje && <p>{mensaje}</p>}

      <h2>Clientes</h2>
      <table border="1">
        <thead>
          <tr>
            <th>Nombre</th><th>Apellido</th><th>Celular</th><th>Licorería</th>
            <th>Sector</th><th>Estado</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {clientes.map((c) => {
            const enEdicion = editando === c.id_cliente
            const estilo = c.habilitado ? {} : { opacity: 0.5 }
            return (
              <tr key={c.id_cliente} style={estilo}>
                {enEdicion ? (
                  <>
                    <td><input value={edit.nombre} onChange={(e) => setEdit({ ...edit, nombre: e.target.value })} /></td>
                    <td><input value={edit.apellido} onChange={(e) => setEdit({ ...edit, apellido: e.target.value })} /></td>
                    <td><input value={edit.celular} onChange={(e) => setEdit({ ...edit, celular: e.target.value })} /></td>
                    <td><input value={edit.licoreria} onChange={(e) => setEdit({ ...edit, licoreria: e.target.value })} /></td>
                    <td>
                      <SelectorBuscable
                        opciones={sectoresHabilitados}
                        valor={edit.id_sector}
                        onCambiar={(v) => setEdit({ ...edit, id_sector: v })}
                        obtenerId={(s) => s.id_sector}
                        obtenerTexto={(s) => s.nombre}
                        placeholder="-- Sin sector --"
                      />
                    </td>
                    <td>{c.habilitado ? 'Habilitado' : 'Deshabilitado'}</td>
                    <td>
                      <button onClick={() => guardarEdicion(c.id_cliente)}>Guardar</button>
                      {' '}<button onClick={() => setEditando(null)}>Cancelar</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{c.nombre}</td>
                    <td>{c.apellido || '—'}</td>
                    <td>{c.celular || '—'}</td>
                    <td>{c.licoreria || '—'}</td>
                    <td>{nombreSector(c.id_sector)}</td>
                    <td>
                      <button onClick={() => alternarHabilitado(c)}>
                        {c.habilitado ? 'Habilitado (clic para deshabilitar)' : 'Deshabilitado (clic para habilitar)'}
                      </button>
                    </td>
                    <td>
                      <button onClick={() => empezarEdicion(c)}>Editar</button>
                      {' '}
                      {c.en_uso ? (
                        <button disabled title="Tiene ventas: deshabilítalo en vez de borrarlo">Eliminar</button>
                      ) : (
                        <button onClick={() => eliminarCliente(c)}>Eliminar</button>
                      )}
                    </td>
                  </>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>

      <h2>Sectores (zonas de reparto)</h2>
      <Catalogo
        titulo="Sectores"
        abiertoInicial={true}
        endpoint="sectores"
        idKey="id_sector"
        campos={[{ nombre: 'nombre', label: 'Nombre', tipo: 'text', obligatorio: true }]}
        camposTabla={[{ key: 'nombre', label: 'Nombre' }]}
      />
    </div>
  )
}

export default PaginaClientes
