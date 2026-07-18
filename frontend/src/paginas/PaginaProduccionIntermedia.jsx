import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import SelectorFifo from '../componentes/SelectorFifo'
import TablaFiltrable from '../componentes/TablaFiltrable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero } from '../formato'
import { fusionar } from '../insumos'

function PaginaProduccionIntermedia() {
  const { fechaParaEnviar } = useFechaGlobal()
  // Datos para los desplegables
  const [productos, setProductos] = useState([])
  const [materias, setMaterias] = useState([])  // catalogo de materias primas (para FIFO)
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

  // Pre-recetas (3.6)
  const [recetas, setRecetas] = useState([])
  const [recetaSel, setRecetaSel] = useState('')
  const [recetaCantidad, setRecetaCantidad] = useState('')

  function cargar() {
    apiGet('/productos-intermedios').then(setProductos).catch(console.error)   // catálogo para el desplegable "a producir"
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
    apiGet('/jornadas')
      .then((datos) => setJornadas(datos.filter((j) => j.horas_restantes > 0)))
      .catch(console.error)
    apiGet('/producciones-intermedias').then(setProducciones).catch(console.error)   // lotes producidos con stock
    apiGet('/stock-intermedio-general').then(setStockGeneral).catch(console.error)
    apiGet('/trabajadores').then(setTrabajadores).catch(console.error)
    apiGet('/recetas').then(setRecetas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Aplicar una pre-receta (3.6): escala a la cantidad y resuelve por FIFO,
  // pre-llenando producto, cantidad e insumos (MP e intermedios). Editable.
  function aplicarReceta() {
    if (recetaSel === '' || recetaCantidad === '') { setMensaje('Elige receta y cantidad a producir'); return }
    apiGet(`/recetas/${recetaSel}/aplicar?cantidad=${parseFloat(recetaCantidad)}`)
      .then((d) => {
        setIdProducto(String(d.id_producto))
        setCantidad(String(d.cantidad_producir))
        setInsumosMP(fusionar([], d.insumos_mp.map((a) => ({ id_compra: a.id_compra, cantidad: a.cantidad })), 'id_compra'))
        setInsumosIntermedio(fusionar([], d.insumos_intermedio.map((a) => ({ id_prod: a.id_prod, cantidad: a.cantidad })), 'id_prod'))
        setInsumosTrabajo([])  // el trabajo se agrega a mano
        if (d.faltantes.length > 0) {
          setMensaje('Receta aplicada. Ojo, falta stock: ' + d.faltantes.map((f) => `${f.nombre} (faltan ${f.faltante})`).join(', '))
        } else {
          setMensaje('Receta aplicada. Revisa y agrega el trabajo antes de producir.')
        }
      })
      .catch((e) => setMensaje(e.message))
  }

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
    setInsumosMP(fusionar(insumosMP, [{ id_compra: parseInt(mpLote), cantidad: parseFloat(mpCantidad) }], 'id_compra'))
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

  // FIFO (3.1): agrega a la lista de MP los lotes que el resolver sugiere.
  function agregarMPFifo(_idMateria, asignaciones) {
    setInsumosMP(fusionar(insumosMP, asignaciones.map((a) => ({ id_compra: a.id_lote, cantidad: a.cantidad })), 'id_compra'))
    setMensaje('')
  }
  // FIFO para intermedios usados como insumo
  function agregarIntermedioFifo(_idProd, asignaciones) {
    setInsumosIntermedio(fusionar(insumosIntermedio, asignaciones.map((a) => ({ id_prod: a.id_lote, cantidad: a.cantidad })), 'id_prod'))
    setMensaje('')
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
    setInsumosIntermedio(fusionar(insumosIntermedio, [{ id_prod: parseInt(intLote), cantidad: parseFloat(intCantidad) }], 'id_prod'))
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

      {/* Aplicar pre-receta (mejora 3.6): escala + resuelve FIFO y pre-llena */}
      {recetas.some((r) => r.tipo === 'INTERMEDIO' && r.habilitado) && (
        <div style={{ background: '#efe', padding: '0.4rem', margin: '0.3rem 0' }}>
          <span style={{ fontSize: '0.85em', color: '#575' }}>Aplicar receta: </span>
          <SelectorBuscable
            opciones={recetas.filter((r) => r.habilitado && r.tipo === 'INTERMEDIO')}
            valor={recetaSel}
            onCambiar={setRecetaSel}
            obtenerId={(r) => r.id_receta}
            obtenerTexto={(r) => `${r.nombre || r.producto} (rinde ${r.rendimiento})`}
            placeholder="-- Receta --"
          />
          <input type="number" placeholder="Cantidad a producir"
            value={recetaCantidad} onChange={(e) => setRecetaCantidad(e.target.value)} />
          <button onClick={aplicarReceta}>Aplicar receta</button>
        </div>
      )}

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
      <SelectorFifo
        origen="MP"
        opciones={materias.filter((m) => m.habilitado)}
        obtenerId={(m) => m.id_materia_prima}
        obtenerTexto={(m) => m.descripcion}
        placeholder="-- Materia prima --"
        onResolver={agregarMPFifo}
      />
      <div>
        <SelectorBuscable
          opciones={lotes}
          valor={mpLote}
          onCambiar={setMpLote}
          obtenerId={(l) => l.id_compra}
          obtenerTexto={(l) => `${l.nombre_materia} - Lote ${l.id_compra} (restante: ${l.cantidad_restante})`}
          placeholder="-- Lote (manual) --"
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
      <SelectorFifo
        origen="INTERMEDIO"
        opciones={productos.filter((p) => p.habilitado)}
        obtenerId={(p) => p.id_producto_intermedio}
        obtenerTexto={(p) => p.descripcion}
        placeholder="-- Producto intermedio --"
        onResolver={agregarIntermedioFifo}
      />
      <div>
        <SelectorBuscable
          opciones={producciones}
          valor={intLote}
          onCambiar={setIntLote}
          obtenerId={(p) => p.id_produccion_intermedio}
          obtenerTexto={(p) => `${p.descripcion} - Lote ${p.id_produccion_intermedio} (quedan ${p.cantidad_restante}, costo ${p.costo_unitario})`}
          placeholder="-- Producción intermedia (manual) --"
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

      <TablaFiltrable
        titulo="Stock general por producto (consolidado)"
        filas={stockGeneral}
        claveOrden="descripcion"
        abiertoInicial={true}
        columnas={[
          { key: 'descripcion', label: 'Producto' },
          { key: 'stock_total', label: 'Stock total', formato: (v) => fmtNumero(v) },
          { key: 'costo_promedio', label: 'Costo promedio', formato: (v) => fmtNumero(v, 4) },
        ]}
      />

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