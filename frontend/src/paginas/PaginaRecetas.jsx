import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { fmtNumero } from '../formato'

// Pre-recetas (mejora 3.6). Una receta produce un producto intermedio O un
// producto terminado, a partir de un rendimiento base y sus insumos (MP e
// intermedios). Al aplicarla en Producción se escala a lo que se va a producir
// y se resuelven los lotes por FIFO. El trabajo no va en la receta.
function PaginaRecetas() {
  const [recetas, setRecetas] = useState([])
  const [intermedios, setIntermedios] = useState([])
  const [terminados, setTerminados] = useState([])
  const [materias, setMaterias] = useState([])

  // Cabecera
  const [tipo, setTipo] = useState('INTERMEDIO')     // INTERMEDIO / TERMINADO
  const [idProducto, setIdProducto] = useState('')
  const [nombre, setNombre] = useState('')
  const [rendimiento, setRendimiento] = useState('')
  // Insumos que se van armando
  const [detalles, setDetalles] = useState([])  // [{tipo, id_insumo, cantidad, nombre}]
  // Temporal para agregar un insumo
  const [tipoIns, setTipoIns] = useState('MP')
  const [idIns, setIdIns] = useState('')
  const [cantIns, setCantIns] = useState('')

  const [editandoId, setEditandoId] = useState(null)
  const [mensaje, setMensaje] = useState('')

  // Secciones plegables de la lista (ambas colapsadas al inicio)
  const [abiertoInt, setAbiertoInt] = useState(false)
  const [abiertoTerm, setAbiertoTerm] = useState(false)

  function cargar() {
    apiGet('/recetas').then(setRecetas).catch(console.error)
    apiGet('/productos-intermedios').then(setIntermedios).catch(console.error)
    apiGet('/productos-terminados').then(setTerminados).catch(console.error)
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
  }
  useEffect(() => { cargar() }, [])

  function nombreInsumo(t, id) {
    if (t === 'MP') return materias.find((m) => m.id_materia_prima === id)?.descripcion || `MP ${id}`
    return intermedios.find((p) => p.id_producto_intermedio === id)?.descripcion || `Int. ${id}`
  }

  function agregarDetalle() {
    if (idIns === '' || cantIns === '') { setMensaje('Elige insumo y cantidad'); return }
    const nuevoTipo = tipoIns
    const nuevoId = parseInt(idIns)
    const nuevaCant = parseFloat(cantIns)
    // Si el mismo insumo ya está, suma la cantidad en vez de duplicar la fila.
    const existente = detalles.find((d) => d.tipo === nuevoTipo && d.id_insumo === nuevoId)
    if (existente) {
      setDetalles(detalles.map((d) =>
        d.tipo === nuevoTipo && d.id_insumo === nuevoId ? { ...d, cantidad: d.cantidad + nuevaCant } : d))
    } else {
      setDetalles([...detalles, {
        tipo: nuevoTipo, id_insumo: nuevoId, cantidad: nuevaCant, nombre: nombreInsumo(nuevoTipo, nuevoId),
      }])
    }
    setIdIns(''); setCantIns(''); setMensaje('')
  }
  function quitarDetalle(i) { setDetalles(detalles.filter((_, idx) => idx !== i)) }

  function limpiarForm() {
    setEditandoId(null); setTipo('INTERMEDIO'); setIdProducto(''); setNombre(''); setRendimiento(''); setDetalles([])
  }

  function guardar() {
    if (idProducto === '' || rendimiento === '') { setMensaje('Elige producto y rendimiento'); return }
    if (detalles.length === 0) { setMensaje('Agrega al menos un insumo'); return }
    const cuerpo = {
      tipo,
      id_producto: parseInt(idProducto),
      nombre: nombre || null,
      rendimiento: parseFloat(rendimiento),
      detalles: detalles.map((d) => ({ tipo: d.tipo, id_insumo: d.id_insumo, cantidad: d.cantidad })),
    }
    const accion = editandoId
      ? apiPatch(`/recetas/${editandoId}`, cuerpo)
      : apiPost('/recetas', cuerpo)
    accion
      .then(() => { setMensaje(editandoId ? 'Receta actualizada' : 'Receta creada'); limpiarForm(); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicion(r) {
    setEditandoId(r.id_receta)
    setTipo(r.tipo)
    setIdProducto(String(r.id_producto))
    setNombre(r.nombre || '')
    setRendimiento(String(r.rendimiento))
    setDetalles(r.detalles.map((d) => ({ tipo: d.tipo, id_insumo: d.id_insumo, cantidad: d.cantidad, nombre: d.nombre })))
    setMensaje('')
  }

  function alternarHabilitado(r) {
    apiPatch(`/recetas/${r.id_receta}/habilitado`, { habilitado: !r.habilitado }).then(cargar).catch((e) => setMensaje(e.message))
  }
  function borrar(r) {
    if (!window.confirm(`¿Borrar la receta de «${r.producto}»?`)) return
    apiDelete(`/recetas/${r.id_receta}`).then(() => { setMensaje('Receta eliminada'); cargar() }).catch((e) => setMensaje(e.message))
  }

  // Opciones del selector de producto de salida, según el tipo elegido
  const opcionesProducto = tipo === 'TERMINADO'
    ? terminados.filter((p) => p.habilitado)
    : intermedios.filter((p) => p.habilitado)
  const obtenerIdProducto = tipo === 'TERMINADO' ? ((p) => p.id_producto_terminado) : ((p) => p.id_producto_intermedio)

  function tablaRecetas(lista) {
    return (
      <table border="1">
        <thead>
          <tr><th>Produce</th><th>Nombre</th><th>Rendimiento</th><th>Insumos</th><th>Estado</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {lista.map((r) => (
            <tr key={r.id_receta} style={r.habilitado ? {} : { opacity: 0.5 }}>
              <td>{r.producto}</td>
              <td>{r.nombre || '—'}</td>
              <td>{fmtNumero(r.rendimiento)}</td>
              <td>{r.detalles.map((d) => `${d.nombre} (${fmtNumero(d.cantidad)})`).join(', ')}</td>
              <td>
                <button onClick={() => alternarHabilitado(r)}>
                  {r.habilitado ? 'Habilitada' : 'Deshabilitada'}
                </button>
              </td>
              <td>
                <button onClick={() => empezarEdicion(r)}>Editar</button>
                {' '}<button onClick={() => borrar(r)}>Eliminar</button>
              </td>
            </tr>
          ))}
          {lista.length === 0 && <tr><td colSpan={6}>Sin recetas</td></tr>}
        </tbody>
      </table>
    )
  }

  const recetasInt = recetas.filter((r) => r.tipo === 'INTERMEDIO')
  const recetasTerm = recetas.filter((r) => r.tipo === 'TERMINADO')

  return (
    <div>
      <h2>{editandoId ? 'Editar receta' : 'Nueva receta'}</h2>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Una receta produce un producto (intermedio o terminado) a partir de un
        rendimiento base (ej. "esta receta rinde 10 L") y sus insumos. Al aplicarla
        en Producción se escala a lo que vayas a producir y resuelve los lotes por FIFO.
      </p>
      <div>
        <select value={tipo} onChange={(e) => { setTipo(e.target.value); setIdProducto('') }}>
          <option value="INTERMEDIO">Producto intermedio</option>
          <option value="TERMINADO">Producto terminado</option>
        </select>
        <SelectorBuscable
          opciones={opcionesProducto}
          valor={idProducto}
          onCambiar={setIdProducto}
          obtenerId={obtenerIdProducto}
          obtenerTexto={(p) => p.descripcion}
          placeholder={`-- Producto ${tipo === 'TERMINADO' ? 'terminado' : 'intermedio'} que produce --`}
        />
        <input type="text" placeholder="Nombre (opcional)" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <input type="number" placeholder="Rendimiento base" value={rendimiento} onChange={(e) => setRendimiento(e.target.value)} />
      </div>

      <h4>Insumos de la receta</h4>
      <div>
        <select value={tipoIns} onChange={(e) => { setTipoIns(e.target.value); setIdIns('') }}>
          <option value="MP">Materia prima</option>
          <option value="INTERMEDIO">Producto intermedio</option>
        </select>
        {tipoIns === 'MP' ? (
          <SelectorBuscable
            opciones={materias.filter((m) => m.habilitado)} valor={idIns} onCambiar={setIdIns}
            obtenerId={(m) => m.id_materia_prima} obtenerTexto={(m) => m.descripcion} placeholder="-- Materia prima --"
          />
        ) : (
          <SelectorBuscable
            opciones={intermedios.filter((p) => p.habilitado)} valor={idIns} onCambiar={setIdIns}
            obtenerId={(p) => p.id_producto_intermedio} obtenerTexto={(p) => p.descripcion} placeholder="-- Producto intermedio --"
          />
        )}
        <input type="number" placeholder="Cantidad" value={cantIns} onChange={(e) => setCantIns(e.target.value)} />
        <button onClick={agregarDetalle}>Agregar insumo</button>
      </div>
      <ul>
        {detalles.map((d, i) => (
          <li key={i}>{d.nombre} — {fmtNumero(d.cantidad)} ({d.tipo === 'MP' ? 'materia prima' : 'intermedio'})
            {' '}<button onClick={() => quitarDetalle(i)}>quitar</button></li>
        ))}
      </ul>

      <button onClick={guardar}>{editandoId ? 'Guardar cambios' : 'Crear receta'}</button>
      {editandoId && <button onClick={limpiarForm} style={{ marginLeft: '0.5rem' }}>Cancelar edición</button>}
      {mensaje && <p>{mensaje}</p>}

      <h3 style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setAbiertoInt(!abiertoInt)}>
        {abiertoInt ? '▾' : '▸'} Recetas de producto intermedio ({recetasInt.length})
      </h3>
      {abiertoInt && tablaRecetas(recetasInt)}

      <h3 style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setAbiertoTerm(!abiertoTerm)}>
        {abiertoTerm ? '▾' : '▸'} Recetas de producto terminado ({recetasTerm.length})
      </h3>
      {abiertoTerm && tablaRecetas(recetasTerm)}
    </div>
  )
}

export default PaginaRecetas
