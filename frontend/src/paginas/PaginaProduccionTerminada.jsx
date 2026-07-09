import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

function PaginaProduccionTerminada() {
  const [productos, setProductos] = useState([])
  const [intermedios, setIntermedios] = useState([])   // producciones intermedias con stock
  const [lotes, setLotes] = useState([])               // lotes de materia prima
  const [jornadas, setJornadas] = useState([])
  const [porLote, setPorLote] = useState([])           // stock terminado por lote
  const [stockGeneral, setStockGeneral] = useState([]) // stock terminado consolidado

  const [idProducto, setIdProducto] = useState('')
  const [cantidad, setCantidad] = useState('')

  // Listas de insumos
  const [insumosIntermedio, setInsumosIntermedio] = useState([])
  const [insumosMP, setInsumosMP] = useState([])
  const [insumosTrabajo, setInsumosTrabajo] = useState([])

  // Campos temporales
  const [intLote, setIntLote] = useState('')
  const [intCantidad, setIntCantidad] = useState('')
  const [mpLote, setMpLote] = useState('')
  const [mpCantidad, setMpCantidad] = useState('')
  const [trabJornada, setTrabJornada] = useState('')
  const [trabHoras, setTrabHoras] = useState('')

  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/productos-terminados').then(setProductos).catch(console.error)
    apiGet('/producciones-intermedias').then(setIntermedios).catch(console.error)
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
    apiGet('/jornadas')
      .then((d) => setJornadas(d.filter((j) => j.horas_restantes > 0))).catch(console.error)
    apiGet('/producciones-terminadas').then(setPorLote).catch(console.error)
    apiGet('/stock-terminado-general').then(setStockGeneral).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Helpers para mostrar nombres en las listas de insumos agregados
  function nombreIntermedio(id) {
    const p = intermedios.find((x) => x.id_produccion_intermedio === id)
    return p ? `${p.descripcion} - Lote ${id}` : `Lote ${id}`
  }
  function nombreLote(id) {
    const l = lotes.find((x) => x.id_compra === id)
    return l ? `${l.nombre_materia} - Lote ${id}` : `Lote ${id}`
  }
  function nombreJornada(id) {
    const j = jornadas.find((x) => x.id_jornada === id)
    return j ? `${j.nombre_trabajador} (${j.fecha})` : `Jornada ${id}`
  }

  // Agregar/quitar intermedio
  function agregarIntermedio() {
    if (intLote === '' || intCantidad === '') { setMensaje('Elige intermedio y cantidad'); return }
    const prod = intermedios.find((p) => p.id_produccion_intermedio === parseInt(intLote))
    const yaUsado = insumosIntermedio
      .filter((x) => x.id_prod === parseInt(intLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (prod && yaUsado + parseFloat(intCantidad) > prod.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${prod.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
      return
    }
    setInsumosIntermedio([...insumosIntermedio, { id_prod: parseInt(intLote), cantidad: parseFloat(intCantidad) }])
    setIntLote(''); setIntCantidad(''); setMensaje('')
  }
  function quitarIntermedio(i) { setInsumosIntermedio(insumosIntermedio.filter((_, idx) => idx !== i)) }

  // Agregar/quitar materia prima
  function agregarMP() {
    if (mpLote === '' || mpCantidad === '') { setMensaje('Elige lote y cantidad'); return }
    const lote = lotes.find((l) => l.id_compra === parseInt(mpLote))
    const yaUsado = insumosMP
      .filter((x) => x.id_compra === parseInt(mpLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (lote && yaUsado + parseFloat(mpCantidad) > lote.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${lote.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
      return
    }
    setInsumosMP([...insumosMP, { id_compra: parseInt(mpLote), cantidad: parseFloat(mpCantidad) }])
    setMpLote(''); setMpCantidad(''); setMensaje('')
  }
  function quitarMP(i) { setInsumosMP(insumosMP.filter((_, idx) => idx !== i)) }

  // Agregar/quitar trabajo
  function agregarTrabajo() {
    if (trabJornada === '' || trabHoras === '') { setMensaje('Elige jornada y horas'); return }
    const jornada = jornadas.find((j) => j.id_jornada === parseInt(trabJornada))
    const yaUsado = insumosTrabajo
      .filter((x) => x.id_registro === parseInt(trabJornada))
      .reduce((s, x) => s + x.horas, 0)
    if (jornada && yaUsado + parseFloat(trabHoras) > jornada.horas_restantes) {
      setMensaje(`Esa jornada solo tiene ${jornada.horas_restantes}h disponibles${yaUsado > 0 ? ` (ya usaste ${yaUsado}h)` : ''}`)
      return
    }
    setInsumosTrabajo([...insumosTrabajo, { id_registro: parseInt(trabJornada), horas: parseFloat(trabHoras) }])
    setTrabJornada(''); setTrabHoras(''); setMensaje('')
  }
  function quitarTrabajo(i) { setInsumosTrabajo(insumosTrabajo.filter((_, idx) => idx !== i)) }

  function producir() {
    if (idProducto === '' || cantidad === '') { setMensaje('Elige producto y cantidad'); return }
    if (insumosIntermedio.length === 0 && insumosMP.length === 0 && insumosTrabajo.length === 0) {
      setMensaje('Agrega al menos un insumo'); return
    }

    apiPost('/producciones-terminadas', {
      id_producto_terminado: parseInt(idProducto),
      cantidad_producida: parseFloat(cantidad),
      insumos_intermedio: insumosIntermedio.map((x) => [x.id_prod, x.cantidad]),
      insumos_mp: insumosMP.map((x) => [x.id_compra, x.cantidad]),
      insumos_trabajo: insumosTrabajo.map((x) => [x.id_registro, x.horas]),
    })
      .then((data) => {
        setMensaje(`Producción creada. Costo unitario: ${data.costo_unitario} Bs`)
        setIdProducto(''); setCantidad('')
        setInsumosIntermedio([]); setInsumosMP([]); setInsumosTrabajo([])
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Producir producto terminado</h2>
      <div>
        <SelectorBuscable
          opciones={productos.filter((p) => p.habilitado)}
          valor={idProducto}
          onCambiar={setIdProducto}
          obtenerId={(p) => p.id_producto_terminado}
          obtenerTexto={(p) => p.descripcion}
          placeholder="-- Producto terminado a producir --"
        />
        <input type="number" placeholder="Cantidad a producir"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
      </div>

      {/* Producto intermedio (insumo principal) */}
      <h3>Producto intermedio</h3>
      <div>
        <SelectorBuscable
          opciones={intermedios}
          valor={intLote}
          onCambiar={setIntLote}
          obtenerId={(p) => p.id_produccion_intermedio}
          obtenerTexto={(p) => `${p.descripcion} - Lote ${p.id_produccion_intermedio} (quedan ${p.cantidad_restante}, costo ${p.costo_unitario})`}
          placeholder="-- Producción intermedia --"
        />
        <input type="number" placeholder="Cantidad"
          value={intCantidad} onChange={(e) => setIntCantidad(e.target.value)} />
        <button onClick={agregarIntermedio}>Agregar intermedio</button>
      </div>
      <ul>
        {insumosIntermedio.map((x, i) => (
          <li key={i}>{nombreIntermedio(x.id_prod)} — cantidad: {x.cantidad}{' '}<button onClick={() => quitarIntermedio(i)}>quitar</button></li>
        ))}
      </ul>

      {/* Materia prima directa */}
      <h3>Materia prima directa</h3>
      <div>
        <SelectorBuscable
          opciones={lotes}
          valor={mpLote}
          onCambiar={setMpLote}
          obtenerId={(l) => l.id_compra}
          obtenerTexto={(l) => `${l.nombre_materia} - Lote ${l.id_compra} (restante: ${l.cantidad_restante})`}
          placeholder="-- Lote --"
        />
        <input type="number" placeholder="Cantidad"
          value={mpCantidad} onChange={(e) => setMpCantidad(e.target.value)} />
        <button onClick={agregarMP}>Agregar MP</button>
      </div>
      <ul>
        {insumosMP.map((x, i) => (
          <li key={i}>{nombreLote(x.id_compra)} — cantidad: {x.cantidad}{' '}<button onClick={() => quitarMP(i)}>quitar</button></li>
        ))}
      </ul>

      {/* Trabajo */}
      <h3>Trabajo</h3>
      <div>
        <SelectorBuscable
          opciones={jornadas}
          valor={trabJornada}
          onCambiar={setTrabJornada}
          obtenerId={(j) => j.id_jornada}
          obtenerTexto={(j) => `${j.nombre_trabajador} - ${j.fecha} (quedan ${j.horas_restantes}h)`}
          placeholder="-- Jornada --"
        />
        <input type="number" placeholder="Horas a usar"
          value={trabHoras} onChange={(e) => setTrabHoras(e.target.value)} />
        <button onClick={agregarTrabajo}>Agregar trabajo</button>
      </div>
      <ul>
        {insumosTrabajo.map((x, i) => (
          <li key={i}>{nombreJornada(x.id_registro)} — horas: {x.horas}{' '}<button onClick={() => quitarTrabajo(i)}>quitar</button></li>
        ))}
      </ul>

      <button onClick={producir}>PRODUCIR</button>
      {mensaje && <p>{mensaje}</p>}

      <h2>Stock general por producto (consolidado)</h2>
      <table border="1">
        <thead><tr><th>Producto</th><th>Stock total</th><th>Costo promedio</th></tr></thead>
        <tbody>
          {stockGeneral.map((s) => (
            <tr key={s.id_producto_terminado}>
              <td>{s.descripcion}</td><td>{s.stock_total}</td><td>{s.costo_promedio}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Stock por lote</h2>
      <table border="1">
        <thead><tr><th>Lote</th><th>Producto</th><th>Stock restante</th><th>Costo unitario</th></tr></thead>
        <tbody>
          {porLote.map((p) => (
            <tr key={p.id_produccion}>
              <td>{p.id_produccion}</td><td>{p.descripcion}</td><td>{p.cantidad_restante}</td><td>{p.costo_unitario}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaProduccionTerminada