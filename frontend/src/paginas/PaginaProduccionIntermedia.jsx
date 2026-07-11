import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero } from '../formato'

function PaginaProduccionIntermedia() {
  const { fechaParaEnviar } = useFechaGlobal()
  // Datos para los desplegables
  const [productos, setProductos] = useState([])
  const [lotes, setLotes] = useState([])
  const [jornadas, setJornadas] = useState([])
  const [producciones, setProducciones] = useState([])
  const [trabajadores, setTrabajadores] = useState([])  // para la tarifa (indicadores en vivo, 6.11)

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
    apiGet('/productos-intermedios').then(setProductos).catch(console.error)   // catálogo para el desplegable "a producir"
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
    apiGet('/jornadas')
      .then((datos) => setJornadas(datos.filter((j) => j.horas_restantes > 0)))
      .catch(console.error)
    apiGet('/producciones-intermedias').then(setProducciones).catch(console.error)   // lotes producidos con stock
    apiGet('/stock-intermedio-general').then(setStockGeneral).catch(console.error)
    apiGet('/trabajadores').then(setTrabajadores).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Agregar una materia prima a la lista
  function agregarMP() {
    if (mpLote === '' || mpCantidad === '') {
      setMensaje('Elige lote y cantidad de materia prima')
      return
    }
    const lote = lotes.find((l) => l.id_compra === parseInt(mpLote))
    const yaUsado = insumosMP
      .filter((x) => x.id_compra === parseInt(mpLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (lote && yaUsado + parseFloat(mpCantidad) > lote.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${lote.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
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
    const jornada = jornadas.find((j) => j.id_jornada === parseInt(trabJornada))
    const yaUsado = insumosTrabajo
      .filter((x) => x.id_registro === parseInt(trabJornada))
      .reduce((s, x) => s + x.horas, 0)
    if (jornada && yaUsado + parseFloat(trabHoras) > jornada.horas_restantes) {
      setMensaje(`Esa jornada solo tiene ${jornada.horas_restantes}h disponibles${yaUsado > 0 ? ` (ya usaste ${yaUsado}h)` : ''}`)
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
    const prod = producciones.find((p) => p.id_produccion_intermedio === parseInt(intLote))
    const yaUsado = insumosIntermedio
      .filter((x) => x.id_prod === parseInt(intLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (prod && yaUsado + parseFloat(intCantidad) > prod.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${prod.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
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

    apiPost('/producciones-intermedias', {
      id_producto_intermedio: parseInt(idProducto),
      cantidad_producida: parseFloat(cantidad),
      insumos_mp: mp,
      insumos_trabajo: trabajo,
      insumos_intermedio: intermedio,
      fecha: fechaParaEnviar,
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

  // Indicadores en vivo (mejora 6.11): costo unitario parcial y horas
  // invertidas hasta el momento, recalculados al agregar/quitar insumos.
  // Solo suman lo agregado en ESTA producción (no heredan horas de
  // intermedios consumidos: eso depende de 1.1, no construido aun).
  const costoMP = insumosMP.reduce((suma, x) => {
    const lote = lotes.find((l) => l.id_compra === x.id_compra)
    const unit = lote && lote.cantidad_compra ? lote.precio_compra / lote.cantidad_compra : 0
    return suma + x.cantidad * unit
  }, 0)
  const costoIntermedio = insumosIntermedio.reduce((suma, x) => {
    const prod = producciones.find((p) => p.id_produccion_intermedio === x.id_prod)
    return suma + x.cantidad * (prod ? prod.costo_unitario : 0)
  }, 0)
  const costoTrabajo = insumosTrabajo.reduce((suma, x) => {
    const jornada = jornadas.find((j) => j.id_jornada === x.id_registro)
    const trabajador = jornada ? trabajadores.find((t) => t.id_trabajador === jornada.id_trabajador) : null
    return suma + x.horas * (trabajador ? trabajador.pago : 0)
  }, 0)
  const costoTotalParcial = costoMP + costoIntermedio + costoTrabajo
  const horasInvertidas = insumosTrabajo.reduce((suma, x) => suma + x.horas, 0)
  const costoUnitarioParcial = cantidad !== '' && parseFloat(cantidad) > 0
    ? costoTotalParcial / parseFloat(cantidad)
    : null

  return (
    <div>
      <h2>Producir producto intermedio</h2>

      {/* Cabecera */}
      <div>
        <SelectorBuscable
          opciones={productos.filter((p) => p.habilitado)}
          valor={idProducto}
          onCambiar={setIdProducto}
          obtenerId={(p) => p.id_producto_intermedio}
          obtenerTexto={(p) => p.descripcion}
          placeholder="-- Producto intermedio a producir --"
        />
        <input type="number" placeholder="Cantidad a producir"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
      </div>

      {/* Agregar materia prima */}
      <h3>Materia prima</h3>
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
          <li key={i}>
            {nombreLote(x.id_compra)} — cantidad: {x.cantidad}
            {' '}<button onClick={() => quitarMP(i)}>quitar</button>
          </li>
        ))}
      </ul>

      {/* Agregar trabajo */}
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
          <li key={i}>
            {nombreJornada(x.id_registro)} — horas: {x.horas}
            {' '}<button onClick={() => quitarTrabajo(i)}>quitar</button>
          </li>
        ))}
      </ul>

      {/* Agregar producto intermedio como insumo */}
      <h3>Producto intermedio (usar uno ya producido)</h3>
      <div>
        <SelectorBuscable
          opciones={producciones}
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
          <li key={i}>
            {nombreIntermedio(x.id_prod)} — cantidad: {x.cantidad}
            {' '}<button onClick={() => quitarIntermedio(i)}>quitar</button>
          </li>
        ))}
      </ul>

      {/* Indicadores en vivo (mejora 6.11) */}
      {(insumosMP.length > 0 || insumosIntermedio.length > 0 || insumosTrabajo.length > 0) && (
        <p style={{ background: '#f0f0f0', padding: '0.4rem' }}>
          <strong>Costo unitario parcial:</strong>{' '}
          {costoUnitarioParcial !== null ? `${costoUnitarioParcial.toFixed(4)} Bs` : `(ingresa la cantidad — costo insumos: ${costoTotalParcial.toFixed(2)} Bs)`}
          {' | '}
          <strong>Horas hombre invertidas:</strong> {horasInvertidas.toFixed(2)} h
        </p>
      )}

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
              <td>{fmtNumero(s.stock_total)}</td>
              <td>{fmtNumero(s.costo_promedio, 4)}</td>
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
              <td>{fmtNumero(p.cantidad_restante)}</td>
              <td>{fmtNumero(p.costo_unitario, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    
  )
}

export default PaginaProduccionIntermedia