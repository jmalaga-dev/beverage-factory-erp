import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { fmtNumero } from '../formato'

// Proveedores (mejora 5.1): registrar una vez a cada proveedor (nombre,
// celular, ubicacion para el futuro ruteo con Maps) y declarar que materias
// primas vende. Al comprar, Compras consulta esas relaciones para ofrecer el
// proveedor correcto. Mismo patron de acciones que Clientes.
function PaginaProveedores() {
  const [proveedores, setProveedores] = useState([])
  const [materias, setMaterias] = useState([])
  const [comparacion, setComparacion] = useState([])

  // Alta de proveedor
  const [nombre, setNombre] = useState('')
  const [celular, setCelular] = useState('')
  const [linkMaps, setLinkMaps] = useState('')
  const [latitud, setLatitud] = useState('')
  const [longitud, setLongitud] = useState('')

  // Edicion in-line
  const [editando, setEditando] = useState(null)
  const [edit, setEdit] = useState({})

  // Selector de "agregar materia" por proveedor (id_proveedor -> id_materia elegido)
  const [materiaAAgregar, setMateriaAAgregar] = useState({})

  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/proveedores').then(setProveedores).catch((e) => console.error(e))
    apiGet('/materias-primas').then(setMaterias).catch((e) => console.error(e))
    apiGet('/comparacion-precios-proveedor').then(setComparacion).catch((e) => console.error(e))
  }

  useEffect(() => { cargar() }, [])

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
      lat = patron3d4d[1]; lng = patron3d4d[2]
    } else if (patronArroba) {
      lat = patronArroba[1]; lng = patronArroba[2]
    }
    if (lat && lng) {
      setLatitud(lat); setLongitud(lng)
      setMensaje('Coordenadas extraídas del link')
    } else {
      setMensaje('No se pudo extraer del link. Pega lat/long a mano.')
    }
  }

  function crearProveedor() {
    if (nombre.trim() === '') {
      setMensaje('El nombre es obligatorio')
      return
    }
    apiPost('/proveedores', {
      nombre: nombre,
      celular: celular || null,
      latitud: latitud ? parseFloat(latitud) : null,
      longitud: longitud ? parseFloat(longitud) : null,
    })
      .then(() => {
        setMensaje('Proveedor creado')
        setNombre(''); setCelular(''); setLinkMaps(''); setLatitud(''); setLongitud('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicion(p) {
    setEditando(p.id_proveedor)
    setEdit({ nombre: p.nombre ?? '', celular: p.celular ?? '' })
  }

  function guardarEdicion(id) {
    apiPatch(`/proveedores/${id}`, { nombre: edit.nombre, celular: edit.celular || null })
      .then(() => { setMensaje('Proveedor actualizado'); setEditando(null); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function alternarHabilitado(p) {
    apiPatch(`/proveedores/${p.id_proveedor}/habilitado`, { habilitado: !p.habilitado })
      .then(cargar)
      .catch((e) => setMensaje(e.message))
  }

  function eliminarProveedor(p) {
    if (!window.confirm(`¿Borrar a «${p.nombre}»? No se puede deshacer.`)) return
    apiDelete(`/proveedores/${p.id_proveedor}`)
      .then(() => { setMensaje('Proveedor eliminado'); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function agregarMateria(idProveedor) {
    const idMateria = materiaAAgregar[idProveedor]
    if (!idMateria) {
      setMensaje('Elige una materia prima para agregar')
      return
    }
    apiPost(`/proveedores/${idProveedor}/materias`, { id_materia_prima: parseInt(idMateria) })
      .then(() => {
        setMateriaAAgregar({ ...materiaAAgregar, [idProveedor]: '' })
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function alternarMateria(idProveedor, m) {
    apiPatch(`/proveedores/${idProveedor}/materias/${m.id_materia_prima}/habilitado`, { habilitado: !m.habilitado })
      .then(cargar)
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Nuevo proveedor</h2>
      <div>
        <input type="text" placeholder="Nombre"
          value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <input type="text" placeholder="Celular"
          value={celular} onChange={(e) => setCelular(e.target.value)} />
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
        <button onClick={crearProveedor}>Agregar proveedor</button>
      </div>

      {mensaje && <p>{mensaje}</p>}

      <h2>Proveedores</h2>
      <table border="1">
        <thead>
          <tr>
            <th>Nombre</th><th>Celular</th><th>Materias que vende</th>
            <th>Estado</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {proveedores.map((p) => {
            const enEdicion = editando === p.id_proveedor
            const estilo = p.habilitado ? {} : { opacity: 0.5 }
            // Materias que este proveedor aun no vende (para el selector de agregar)
            const yaVende = new Set(p.materias.map((m) => m.id_materia_prima))
            const disponibles = materias.filter((m) => m.habilitado && !yaVende.has(m.id_materia_prima))
            return (
              <tr key={p.id_proveedor} style={estilo}>
                {enEdicion ? (
                  <>
                    <td><input value={edit.nombre} onChange={(e) => setEdit({ ...edit, nombre: e.target.value })} /></td>
                    <td><input value={edit.celular} onChange={(e) => setEdit({ ...edit, celular: e.target.value })} /></td>
                  </>
                ) : (
                  <>
                    <td>{p.nombre}</td>
                    <td>{p.celular || '—'}</td>
                  </>
                )}
                <td>
                  {p.materias.length === 0 && <span style={{ color: '#a00' }}>— sin materias —</span>}
                  {p.materias.map((m) => (
                    <div key={m.id_materia_prima} style={{ opacity: m.habilitado ? 1 : 0.45 }}>
                      {m.nombre_materia}{' '}
                      <button onClick={() => alternarMateria(p.id_proveedor, m)}>
                        {m.habilitado ? 'quitar' : 'reactivar'}
                      </button>
                    </div>
                  ))}
                  <div style={{ marginTop: '0.3rem' }}>
                    <SelectorBuscable
                      opciones={disponibles}
                      valor={materiaAAgregar[p.id_proveedor] || ''}
                      onCambiar={(v) => setMateriaAAgregar({ ...materiaAAgregar, [p.id_proveedor]: v })}
                      obtenerId={(m) => m.id_materia_prima}
                      obtenerTexto={(m) => m.descripcion}
                      placeholder="-- Agregar materia --"
                    />
                    <button onClick={() => agregarMateria(p.id_proveedor)}>Agregar</button>
                  </div>
                </td>
                <td>
                  <button onClick={() => alternarHabilitado(p)}>
                    {p.habilitado ? 'Habilitado (clic para deshabilitar)' : 'Deshabilitado (clic para habilitar)'}
                  </button>
                </td>
                <td>
                  {enEdicion ? (
                    <>
                      <button onClick={() => guardarEdicion(p.id_proveedor)}>Guardar</button>
                      {' '}<button onClick={() => setEditando(null)}>Cancelar</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => empezarEdicion(p)}>Editar</button>
                      {' '}
                      {p.en_uso ? (
                        <button disabled title="Tiene compras: deshabilítalo en vez de borrarlo">Eliminar</button>
                      ) : (
                        <button onClick={() => eliminarProveedor(p)}>Eliminar</button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <h2>Comparación de precios por proveedor</h2>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Precio unitario según el historial de compras. Ordenado por materia y del
        promedio más barato al más caro.
      </p>
      <table border="1">
        <thead>
          <tr>
            <th>Materia prima</th><th>Proveedor</th><th># compras</th>
            <th>Mín</th><th>Promedio</th><th>Máx</th><th>Último</th>
          </tr>
        </thead>
        <tbody>
          {comparacion.map((r) => (
            <tr key={`${r.id_materia_prima}-${r.id_proveedor}`}>
              <td>{r.nombre_materia} ({r.unidad})</td>
              <td>{r.nombre_proveedor}</td>
              <td>{r.compras}</td>
              <td>{fmtNumero(r.precio_min, 4)}</td>
              <td>{fmtNumero(r.precio_promedio, 4)}</td>
              <td>{fmtNumero(r.precio_max, 4)}</td>
              <td>{fmtNumero(r.precio_ultimo, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaProveedores
