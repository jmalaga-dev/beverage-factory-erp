import { useState, useEffect } from 'react'

function PaginaProduccionIntermedia() {
  // Datos para los desplegables
  const [productos, setProductos] = useState([])
  const [lotes, setLotes] = useState([])
  const [jornadas, setJornadas] = useState([])
  const [producciones, setProducciones] = useState([])

  // Cabecera de la producción
  const [idProducto, setIdProducto] = useState('')
  const [cantidad, setCantidad] = useState('')

  // Las LISTAS de insumos que el usuario va armando
  const [insumosMP, setInsumosMP] = useState([])         // [{id_compra, cantidad}]
  const [insumosTrabajo, setInsumosTrabajo] = useState([]) // [{id_registro, horas}]

  // Campos temporales para agregar un insumo
  const [mpLote, setMpLote] = useState('')
  const [mpCantidad, setMpCantidad] = useState('')
  const [trabJornada, setTrabJornada] = useState('')
  const [trabHoras, setTrabHoras] = useState('')

  const [mensaje, setMensaje] = useState('')

  // Campos para intermedios lo coloque aqui
  const [insumosIntermedio, setInsumosIntermedio] = useState([])  // [{id_prod, cantidad}]
  const [intLote, setIntLote] = useState('')
  const [intCantidad, setIntCantidad] = useState('')

  // Para resumen produccion intermedio tabla resumen
  const [stockGeneral, setStockGeneral] = useState([])

  

  function cargar() {
    fetch('http://127.0.0.1:8000/productos-intermedios')
      .then((r) => r.json()).then(setProductos).catch(console.error)   // catálogo para el desplegable "a producir"
    fetch('http://127.0.0.1:8000/lotes-compra')
      .then((r) => r.json()).then(setLotes).catch(console.error)
    fetch('http://127.0.0.1:8000/jornadas')
      .then((r) => r.json()).then((datos) => setJornadas(datos.filter((j) => j.horas_restantes > 0)))
      .catch(console.error)
    fetch('http://127.0.0.1:8000/producciones-intermedias')
      .then((r) => r.json()).then(setProducciones).catch(console.error)   // lotes producidos con stock
    fetch('http://127.0.0.1:8000/stock-intermedio-general')
      .then((r) => r.json()).then(setStockGeneral).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Agregar una materia prima a la lista
  function agregarMP() {
    if (mpLote === '' || mpCantidad === '') {
      setMensaje('Elige lote y cantidad de materia prima')
      return
    }
    setInsumosMP([...insumosMP, { id_compra: parseInt(mpLote), cantidad: parseFloat(mpCantidad) }])
    setMpLote('')
    setMpCantidad('')
    setMensaje('')
  }

  function nombreIntermedio(id) {
    const p = producciones.find((x) => x.id_produccion_intermedio === id)
    return p ? `${p.descripcion} - Lote ${id}` : `Lote ${id}`
  }

  // Quitar una materia prima de la lista (por su posición)
  function quitarMP(indice) {
    setInsumosMP(insumosMP.filter((_, i) => i !== indice))
  }

  // Agregar trabajo a la lista
  function agregarTrabajo() {
    if (trabJornada === '' || trabHoras === '') {
      setMensaje('Elige jornada y horas')
      return
    }
    setInsumosTrabajo([...insumosTrabajo, { id_registro: parseInt(trabJornada), horas: parseFloat(trabHoras) }])
    setTrabJornada('')
    setTrabHoras('')
    setMensaje('')
  }

  function quitarTrabajo(indice) {
    setInsumosTrabajo(insumosTrabajo.filter((_, i) => i !== indice))
  }

  function agregarIntermedio() {
    if (intLote === '' || intCantidad === '') {
      setMensaje('Elige producción intermedia y cantidad')
      return
    }
    setInsumosIntermedio([...insumosIntermedio, { id_prod: parseInt(intLote), cantidad: parseFloat(intCantidad) }])
    setIntLote('')
    setIntCantidad('')
    setMensaje('')
  }

  function quitarIntermedio(indice) {
    setInsumosIntermedio(insumosIntermedio.filter((_, i) => i !== indice))
  }

  // Producir: enviar todo al backend
  function producir() {
    if (idProducto === '' || cantidad === '') {
      setMensaje('Elige el producto y la cantidad a producir')
      return
    }
    if (insumosMP.length === 0 && insumosTrabajo.length === 0) {
      setMensaje('Agrega al menos un insumo')
      return
    }

    // Convertir las listas al formato que el backend espera: [[id, cantidad], ...]
    const mp = insumosMP.map((x) => [x.id_compra, x.cantidad])
    const trabajo = insumosTrabajo.map((x) => [x.id_registro, x.horas])
    const intermedio = insumosIntermedio.map((x) => [x.id_prod, x.cantidad])

    fetch('http://127.0.0.1:8000/producciones-intermedias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_producto_intermedio: parseInt(idProducto),
        cantidad_producida: parseFloat(cantidad),
        insumos_mp: mp,
        insumos_trabajo: trabajo,
        insumos_intermedio: intermedio,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
      })
      .then((data) => {
        setMensaje(`Producción creada. Costo unitario: ${data.costo_unitario} Bs`)
        // limpiar todo
        setIdProducto('')
        setCantidad('')
        setInsumosMP([])
        setInsumosTrabajo([])
        setInsumosIntermedio([])
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  // Helpers para mostrar nombres en las listas
  function nombreLote(id) {
    const l = lotes.find((x) => x.id_compra === id)
    return l ? `${l.nombre_materia} - Lote ${id}` : `Lote ${id}`
  }
  function nombreJornada(id) {
    const j = jornadas.find((x) => x.id_jornada === id)
    return j ? `${j.nombre_trabajador} (${j.fecha})` : `Jornada ${id}`
  }

  return (
    <div>
      <h2>Producir producto intermedio</h2>

      {/* Cabecera */}
      <div>
        <select value={idProducto} onChange={(e) => setIdProducto(e.target.value)}>
          <option value="">-- Producto intermedio a producir --</option>
          {productos.map((p) => (
            <option key={p.id_producto_intermedio} value={p.id_producto_intermedio}>
              {p.descripcion}
            </option>
          ))}
        </select>
        <input type="number" placeholder="Cantidad a producir"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
      </div>

      {/* Agregar materia prima */}
      <h3>Materia prima</h3>
      <div>
        <select value={mpLote} onChange={(e) => setMpLote(e.target.value)}>
          <option value="">-- Lote --</option>
          {lotes.map((l) => (
            <option key={l.id_compra} value={l.id_compra}>
              {l.nombre_materia} - Lote {l.id_compra} (restante: {l.cantidad_restante})
            </option>
          ))}
        </select>
        <input type="number" placeholder="Cantidad"
          value={mpCantidad} onChange={(e) => setMpCantidad(e.target.value)} />
        <button onClick={agregarMP}>Agregar MP</button>
      </div>
      <ul>
        {insumosMP.map((x, i) => (
          <li key={i}>
            {nombreLote(x.id_compra)} — cantidad: {x.cantidad}
            {' '}<button onClick={() => quitarMP(i)}>quitar</button>
          </li>
        ))}
      </ul>

      {/* Agregar trabajo */}
      <h3>Trabajo</h3>
      <div>
        <select value={trabJornada} onChange={(e) => setTrabJornada(e.target.value)}>
          <option value="">-- Jornada --</option>
          {jornadas.map((j) => (
            <option key={j.id_jornada} value={j.id_jornada}>
              {j.nombre_trabajador} - {j.fecha} (quedan {j.horas_restantes}h)
            </option>
          ))}
        </select>
        <input type="number" placeholder="Horas a usar"
          value={trabHoras} onChange={(e) => setTrabHoras(e.target.value)} />
        <button onClick={agregarTrabajo}>Agregar trabajo</button>
      </div>
      <ul>
        {insumosTrabajo.map((x, i) => (
          <li key={i}>
            {nombreJornada(x.id_registro)} — horas: {x.horas}
            {' '}<button onClick={() => quitarTrabajo(i)}>quitar</button>
          </li>
        ))}
      </ul>

      {/* Agregar producto intermedio como insumo */}
      <h3>Producto intermedio (usar uno ya producido)</h3>
      <div>
        <select value={intLote} onChange={(e) => setIntLote(e.target.value)}>
          <option value="">-- Producción intermedia --</option>
          {producciones.map((p) => (
            <option key={p.id_produccion_intermedio} value={p.id_produccion_intermedio}>
              {p.descripcion} - Lote {p.id_produccion_intermedio} (quedan {p.cantidad_restante}, costo {p.costo_unitario})
            </option>
          ))}
        </select>
        <input type="number" placeholder="Cantidad"
          value={intCantidad} onChange={(e) => setIntCantidad(e.target.value)} />
        <button onClick={agregarIntermedio}>Agregar intermedio</button>
      </div>
      <ul>
        {insumosIntermedio.map((x, i) => (
          <li key={i}>
            {nombreIntermedio(x.id_prod)} — cantidad: {x.cantidad}
            {' '}<button onClick={() => quitarIntermedio(i)}>quitar</button>
          </li>
        ))}
      </ul>

      <button onClick={producir}>PRODUCIR</button>
      {mensaje && <p>{mensaje}</p>}

      <h2>Stock general por producto (consolidado)</h2>
      <table border="1">
        <thead>
          <tr><th>Producto</th><th>Stock total</th><th>Costo promedio</th></tr>
        </thead>
        <tbody>
          {stockGeneral.map((s) => (
            <tr key={s.id_producto_intermedio}>
              <td>{s.descripcion}</td>
              <td>{s.stock_total}</td>
              <td>{s.costo_promedio}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Stock de producciones intermedias</h2>
      <table border="1">
        <thead>
          <tr><th>Lote</th><th>Producto</th><th>Stock restante</th><th>Costo unitario</th></tr>
        </thead>
        <tbody>
          {producciones.map((p) => (
            <tr key={p.id_produccion_intermedio}>
              <td>{p.id_produccion_intermedio}</td>
              <td>{p.descripcion}</td>
              <td>{p.cantidad_restante}</td>
              <td>{p.costo_unitario}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    
  )
}

export default PaginaProduccionIntermedia