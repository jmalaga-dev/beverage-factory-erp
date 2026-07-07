import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'

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

        <select value={idSector} onChange={(e) => setIdSector(e.target.value)}>
          <option value="">-- Sin sector --</option>
          {sectores.map((s) => (
            <option key={s.id_sector} value={s.id_sector}>
              {s.nombre}
            </option>
          ))}
        </select>

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
      <ul>
        {clientes.map((cliente) => (
          <li key={cliente.id_cliente}>
            {cliente.nombre} — celular: {cliente.celular || 'sin dato'}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default PaginaClientes