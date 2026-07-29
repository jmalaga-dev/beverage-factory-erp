import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import { fmtNumero } from '../formato'

// Catalogo generico: crear + listar + editar + habilitar/deshabilitar + borrar.
// Reutilizado por todos los catalogos simples (mejora 6.1). El backend expone,
// por cada catalogo, el mismo juego de rutas:
//   GET    /endpoint                  (cada fila trae habilitado + en_uso)
//   POST   /endpoint                  (crear)
//   PATCH  /endpoint/{id}             (editar campos descriptivos)
//   PATCH  /endpoint/{id}/habilitado  (dar de baja / alta sin borrar)
//   DELETE /endpoint/{id}             (borrado real, solo si en_uso == false)
//
// Props:
//   titulo, endpoint          identifican el catalogo
//   idKey                     nombre del campo Id que devuelve el GET (ej. 'id_materia_prima')
//   campos                    campos del formulario de crear/editar [{nombre,label,tipo,obligatorio}]
//   camposTabla               columnas de la tabla [{key,label}]
//   abiertoInicial            si la seccion arranca desplegada
//   permitirCrear             si se muestra el formulario de alta (default true)
//   soportaDestacado          si el catalogo tiene el marcador "destacado" (item 14):
//                             agrega una columna con una estrella para marcar/desmarcar.
//                             El backend expone PATCH /endpoint/{id}/destacado.
//   marcador                  columna de toggle booleano generica (bloque E), para
//                             banderas propias de un catalogo:
//                             {campo, ruta, label, ayuda, tituloSi, tituloNo}
//                             El backend expone PATCH /endpoint/{id}/{ruta}
//                             recibiendo {[campo]: bool}.
function Catalogo({ titulo, endpoint, idKey, campos, camposTabla, abiertoInicial, permitirCrear = true, soportaDestacado = false, marcador = null }) {
  const [items, setItems] = useState([])
  const [valores, setValores] = useState({})
  const [mensaje, setMensaje] = useState('')
  const [abierto, setAbierto] = useState(abiertoInicial)
  const [filtro, setFiltro] = useState('')

  // Edicion in-line: id de la fila en edicion y sus valores en curso
  const [editandoId, setEditandoId] = useState(null)
  const [editValores, setEditValores] = useState({})

  function cargar() {
    apiGet(`/${endpoint}`).then(setItems).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Arma el body convirtiendo los campos numericos (comun a crear y editar)
  function armarBody(origen) {
    const body = {}
    for (const campo of campos) {
      let v = origen[campo.nombre]
      if (campo.tipo === 'number' && v !== '' && v != null) v = parseFloat(v)
      body[campo.nombre] = v === '' ? null : v
    }
    return body
  }

  function crear() {
    for (const campo of campos) {
      if (campo.obligatorio && !valores[campo.nombre]) {
        setMensaje(`${campo.label} es obligatorio`)
        return
      }
    }
    apiPost(`/${endpoint}`, armarBody(valores))
      .then(() => { setMensaje(`${titulo} creado`); setValores({}); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicion(item) {
    setEditandoId(item[idKey])
    const iniciales = {}
    for (const campo of campos) iniciales[campo.nombre] = item[campo.nombre] ?? ''
    setEditValores(iniciales)
  }

  function guardarEdicion(id) {
    for (const campo of campos) {
      if (campo.obligatorio && !editValores[campo.nombre]) {
        setMensaje(`${campo.label} es obligatorio`)
        return
      }
    }
    apiPatch(`/${endpoint}/${id}`, armarBody(editValores))
      .then(() => { setMensaje(`${titulo} actualizado`); setEditandoId(null); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function alternarHabilitado(item) {
    apiPatch(`/${endpoint}/${item[idKey]}/habilitado`, { habilitado: !item.habilitado })
      .then(cargar)
      .catch((e) => setMensaje(e.message))
  }

  function alternarDestacado(item) {
    apiPatch(`/${endpoint}/${item[idKey]}/destacado`, { destacado: !item.destacado })
      .then(cargar)
      .catch((e) => setMensaje(e.message))
  }

  function alternarMarcador(item) {
    apiPatch(`/${endpoint}/${item[idKey]}/${marcador.ruta}`,
      { [marcador.campo]: !item[marcador.campo] })
      .then((r) => { setMensaje(r.mensaje || ''); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function borrar(item) {
    if (!window.confirm(`¿Borrar «${item[camposTabla[0].key]}»? No se puede deshacer.`)) return
    apiDelete(`/${endpoint}/${item[idKey]}`)
      .then(() => { setMensaje(`${titulo} eliminado`); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  const filtrados = items.filter((item) =>
    camposTabla.some((c) => String(item[c.key] ?? '').toLowerCase().includes(filtro.toLowerCase()))
  )

  return (
    <div style={{ marginBottom: '1rem' }}>
      <h3 style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setAbierto(!abierto)}>
        {abierto ? '▾' : '▸'} {titulo} ({items.length})
      </h3>
      {abierto && (
        <>
          {permitirCrear && (
            <div>
              {campos.map((campo) => (
                campo.tipo === 'select' ? (
                  <select
                    key={campo.nombre}
                    value={valores[campo.nombre] || ''}
                    onChange={(e) => setValores({ ...valores, [campo.nombre]: e.target.value })}
                  >
                    <option value="">-- {campo.label} --</option>
                    {campo.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    key={campo.nombre}
                    type={campo.tipo === 'number' ? 'number' : 'text'}
                    placeholder={campo.label}
                    value={valores[campo.nombre] || ''}
                    onChange={(e) => setValores({ ...valores, [campo.nombre]: e.target.value })}
                  />
                )
              ))}
              <button onClick={crear}>Agregar</button>
            </div>
          )}
          {mensaje && <p>{mensaje}</p>}
          <input
            type="text"
            placeholder="Buscar..."
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            style={{ display: 'block', marginBottom: '0.5rem' }}
          />
          <table border="1">
            <thead>
              <tr>
                {camposTabla.map((c) => <th key={c.key}>{c.label}</th>)}
                {soportaDestacado && <th>Destacado</th>}
                {marcador && <th title={marcador.ayuda}>{marcador.label}</th>}
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((item) => {
                const id = item[idKey]
                const enEdicion = editandoId === id
                // Fila deshabilitada: atenuada, para distinguirla de un vistazo
                const estilo = item.habilitado ? {} : { opacity: 0.5 }
                return (
                  <tr key={id} style={estilo}>
                    {camposTabla.map((c) => {
                      const campoEditable = campos.find((ca) => ca.nombre === c.key)
                      return (
                        <td key={c.key}>
                          {enEdicion && campoEditable ? (
                            campoEditable.tipo === 'select' ? (
                              <select
                                value={editValores[c.key] ?? ''}
                                onChange={(e) => setEditValores({ ...editValores, [c.key]: e.target.value })}
                              >
                                {campoEditable.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                              </select>
                            ) : (
                              <input
                                type={campoEditable.tipo === 'number' ? 'number' : 'text'}
                                style={{ width: campoEditable.tipo === 'number' ? '90px' : 'auto' }}
                                value={editValores[c.key] ?? ''}
                                onChange={(e) => setEditValores({ ...editValores, [c.key]: e.target.value })}
                              />
                            )
                          ) : (
                            campoEditable && campoEditable.tipo === 'number'
                              ? fmtNumero(item[c.key])
                              : item[c.key]
                          )}
                        </td>
                      )
                    })}
                    {soportaDestacado && (
                      <td style={{ textAlign: 'center' }}>
                        <button onClick={() => alternarDestacado(item)}
                          title={item.destacado ? 'Destacado (clic para quitar)' : 'No destacado (clic para destacar)'}
                          style={{ fontSize: '1.1em', lineHeight: 1 }}>
                          {item.destacado ? '★' : '☆'}
                        </button>
                      </td>
                    )}
                    {marcador && (
                      <td style={{ textAlign: 'center' }}>
                        <button onClick={() => alternarMarcador(item)}
                          title={item[marcador.campo] ? marcador.tituloSi : marcador.tituloNo}
                          style={{ fontSize: '1.1em', lineHeight: 1 }}>
                          {item[marcador.campo] ? '☑' : '☐'}
                        </button>
                      </td>
                    )}
                    <td>
                      <button onClick={() => alternarHabilitado(item)}>
                        {item.habilitado ? 'Habilitado (clic para deshabilitar)' : 'Deshabilitado (clic para habilitar)'}
                      </button>
                    </td>
                    <td>
                      {enEdicion ? (
                        <>
                          <button onClick={() => guardarEdicion(id)}>Guardar</button>
                          {' '}<button onClick={() => setEditandoId(null)}>Cancelar</button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => empezarEdicion(item)}>Editar</button>
                          {' '}
                          {item.en_uso ? (
                            <button disabled title="Tiene historial: deshabilítalo en vez de borrarlo">Eliminar</button>
                          ) : (
                            <button onClick={() => borrar(item)}>Eliminar</button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default Catalogo
