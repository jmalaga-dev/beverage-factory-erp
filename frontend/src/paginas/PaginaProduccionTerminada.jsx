import { useState, useEffect } from 'react'
import { apiGet, apiPost, apiDelete } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import SelectorFifo from '../componentes/SelectorFifo'
import TablaFiltrable from '../componentes/TablaFiltrable'
import CantidadPaquetes, { totalBotellas } from '../componentes/CantidadPaquetes'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import ResumenProduccion from '../componentes/ResumenProduccion'
import InputCalculo from '../componentes/InputCalculo'
import { fmtNumero, fmtBotellasYPaquetes } from '../formato'
import { fusionar } from '../insumos'
import { resumenMateriaPrima, resumenIntermedios, resumenTrabajo } from '../resumenProduccion'
import { evaluar } from '../calculo'

function PaginaProduccionTerminada() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [productos, setProductos] = useState([])
  const [materias, setMaterias] = useState([])         // catalogo de materias primas (para FIFO)
  const [productosIntermedios, setProductosIntermedios] = useState([])  // catalogo intermedio (para FIFO)
  const [intermedios, setIntermedios] = useState([])   // producciones intermedias con stock
  const [lotes, setLotes] = useState([])               // lotes de materia prima
  const [jornadas, setJornadas] = useState([])
  const [porLote, setPorLote] = useState([])           // stock terminado por lote
  const [stockGeneral, setStockGeneral] = useState([]) // stock terminado consolidado
  const [trabajadores, setTrabajadores] = useState([]) // para la tarifa (indicadores en vivo, 6.11)

  const [idProducto, setIdProducto] = useState('')
  // Cantidad a producir en paquetes + botellas sueltas (6.13). El total en
  // botellas se deriva con totalBotellas(), nunca se guarda como estado.
  const [cantidadPaquetes, setCantidadPaquetes] = useState('')
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

  // Pre-recetas (3.6) de tipo TERMINADO
  const [recetas, setRecetas] = useState([])
  const [recetaSel, setRecetaSel] = useState('')
  const [recetaCantidad, setRecetaCantidad] = useState('')

  function cargar() {
    apiGet('/productos-terminados').then(setProductos).catch(console.error)
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
    apiGet('/productos-intermedios').then(setProductosIntermedios).catch(console.error)
    apiGet('/producciones-intermedias').then(setIntermedios).catch(console.error)
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
    apiGet('/jornadas')
      .then((d) => setJornadas(d.filter((j) => j.horas_restantes > 0))).catch(console.error)
    apiGet('/producciones-terminadas').then(setPorLote).catch(console.error)
    apiGet('/stock-terminado-general').then(setStockGeneral).catch(console.error)
    apiGet('/trabajadores').then(setTrabajadores).catch(console.error)
    apiGet('/recetas').then(setRecetas).catch(console.error)
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
    const cant = evaluar(intCantidad)
    if (Number.isNaN(cant)) { setMensaje('La cantidad no es una operación válida'); return }
    const prod = intermedios.find((p) => p.id_produccion_intermedio === parseInt(intLote))
    const yaUsado = insumosIntermedio
      .filter((x) => x.id_prod === parseInt(intLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (prod && yaUsado + cant > prod.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${prod.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
      return
    }
    setInsumosIntermedio(fusionar(insumosIntermedio, [{ id_prod: parseInt(intLote), cantidad: cant }], 'id_prod'))
    setIntLote(''); setIntCantidad(''); setMensaje('')
  }
  function quitarIntermedio(i) { setInsumosIntermedio(insumosIntermedio.filter((_, idx) => idx !== i)) }
  // FIFO (3.1)
  function agregarIntermedioFifo(_id, asignaciones) {
    setInsumosIntermedio(fusionar(insumosIntermedio, asignaciones.map((a) => ({ id_prod: a.id_lote, cantidad: a.cantidad })), 'id_prod'))
    setMensaje('')
  }

  // Agregar/quitar materia prima
  function agregarMP() {
    if (mpLote === '' || mpCantidad === '') { setMensaje('Elige lote y cantidad'); return }
    const cant = evaluar(mpCantidad)
    if (Number.isNaN(cant)) { setMensaje('La cantidad no es una operación válida'); return }
    const lote = lotes.find((l) => l.id_compra === parseInt(mpLote))
    const yaUsado = insumosMP
      .filter((x) => x.id_compra === parseInt(mpLote))
      .reduce((s, x) => s + x.cantidad, 0)
    if (lote && yaUsado + cant > lote.cantidad_restante) {
      setMensaje(`Ese lote solo tiene ${lote.cantidad_restante} disponible${yaUsado > 0 ? ` (ya usaste ${yaUsado})` : ''}`)
      return
    }
    setInsumosMP(fusionar(insumosMP, [{ id_compra: parseInt(mpLote), cantidad: cant }], 'id_compra'))
    setMpLote(''); setMpCantidad(''); setMensaje('')
  }
  function quitarMP(i) { setInsumosMP(insumosMP.filter((_, idx) => idx !== i)) }
  // FIFO (3.1)
  function agregarMPFifo(_id, asignaciones) {
    setInsumosMP(fusionar(insumosMP, asignaciones.map((a) => ({ id_compra: a.id_lote, cantidad: a.cantidad })), 'id_compra'))
    setMensaje('')
  }

  // Agregar/quitar trabajo
  function agregarTrabajo() {
    if (trabJornada === '' || trabHoras === '') { setMensaje('Elige jornada y horas'); return }
    const hs = evaluar(trabHoras)
    if (Number.isNaN(hs)) { setMensaje('Las horas no son una operación válida'); return }
    const jornada = jornadas.find((j) => j.id_jornada === parseInt(trabJornada))
    const yaUsado = insumosTrabajo
      .filter((x) => x.id_registro === parseInt(trabJornada))
      .reduce((s, x) => s + x.horas, 0)
    if (jornada && yaUsado + hs > jornada.horas_restantes) {
      setMensaje(`Esa jornada solo tiene ${jornada.horas_restantes}h disponibles${yaUsado > 0 ? ` (ya usaste ${yaUsado}h)` : ''}`)
      return
    }
    setInsumosTrabajo([...insumosTrabajo, { id_registro: parseInt(trabJornada), horas: hs }])
    setTrabJornada(''); setTrabHoras(''); setMensaje('')
  }
  function quitarTrabajo(i) { setInsumosTrabajo(insumosTrabajo.filter((_, idx) => idx !== i)) }

  // Aplicar pre-receta de terminado (3.6): escala + FIFO y pre-llena
  function aplicarReceta() {
    if (recetaSel === '' || recetaCantidad === '') { setMensaje('Elige receta y cantidad a producir'); return }
    const cantReceta = evaluar(recetaCantidad)
    if (Number.isNaN(cantReceta) || cantReceta <= 0) { setMensaje('La cantidad a producir no es válida'); return }
    apiGet(`/recetas/${recetaSel}/aplicar?cantidad=${cantReceta}`)
      .then((d) => {
        setIdProducto(String(d.id_producto))
        // La receta escala en botellas: se vuelca al campo de botellas y se
        // limpian los paquetes, para no sumar un resto de la carga anterior.
        setCantidad(String(d.cantidad_producir))
        setCantidadPaquetes('')
        setInsumosMP(fusionar([], d.insumos_mp.map((a) => ({ id_compra: a.id_compra, cantidad: a.cantidad })), 'id_compra'))
        setInsumosIntermedio(fusionar([], d.insumos_intermedio.map((a) => ({ id_prod: a.id_prod, cantidad: a.cantidad })), 'id_prod'))
        setInsumosTrabajo([])
        setMensaje(d.faltantes.length > 0
          ? 'Receta aplicada. Ojo, falta stock: ' + d.faltantes.map((f) => `${f.nombre} (faltan ${f.faltante})`).join(', ')
          : 'Receta aplicada. Revisa y agrega el trabajo antes de producir.')
      })
      .catch((e) => setMensaje(e.message))
  }

  // Cambiar de producto limpia la cantidad: un valor en paquetes pertenece al
  // tamaño de paquete del producto anterior, y arrastrarlo daria un total
  // distinto del que se tecleo (o quedaria oculto si el nuevo es suelto).
  function elegirProducto(id) {
    setIdProducto(id)
    setCantidadPaquetes(''); setCantidad('')
  }

  function producir() {
    if (idProducto === '' || cantidadTotal <= 0) { setMensaje('Elige producto y cantidad'); return }
    if (insumosIntermedio.length === 0 && insumosMP.length === 0 && insumosTrabajo.length === 0) {
      setMensaje('Agrega al menos un insumo'); return
    }

    apiPost('/producciones-terminadas', {
      id_producto_terminado: parseInt(idProducto),
      cantidad_producida: cantidadTotal,
      insumos_intermedio: insumosIntermedio.map((x) => [x.id_prod, x.cantidad]),
      insumos_mp: insumosMP.map((x) => [x.id_compra, x.cantidad]),
      insumos_trabajo: insumosTrabajo.map((x) => [x.id_registro, x.horas]),
      fecha: fechaParaEnviar,
    })
      .then((data) => {
        setMensaje(`Producción creada. Costo unitario: ${data.costo_unitario} Bs`)
        setIdProducto(''); setCantidad(''); setCantidadPaquetes('')
        setInsumosIntermedio([]); setInsumosMP([]); setInsumosTrabajo([])
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  // Eliminar una producción recién creada, solo si está intacta (item 6a): el
  // backend devuelve el stock de los insumos y revierte la absorción. Para
  // "editar", se elimina y se vuelve a crear con los datos corregidos.
  function eliminarProduccion(id) {
    if (!window.confirm(`¿Eliminar la producción (lote ${id})? Se devolverán los insumos consumidos. Solo se puede si el lote está intacto.`)) return
    apiDelete(`/producciones-terminadas/${id}`)
      .then(() => { setMensaje(`Producción ${id} eliminada, insumos devueltos.`); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  // Producto elegido y su tamaño de paquete: manda cuantos campos de cantidad
  // se muestran (6.13). El total en botellas es lo unico que se envia y lo
  // que divide el costo unitario parcial de abajo.
  const productoElegido = idProducto !== ''
    ? productos.find((p) => p.id_producto_terminado === parseInt(idProducto))
    : null
  const bppElegido = productoElegido ? productoElegido.botellas_por_paquete : 1
  const cantidadTotal = totalBotellas(cantidadPaquetes, cantidad, bppElegido)

  // Indicadores en vivo (mejora 6.11): costo unitario parcial y horas
  // invertidas hasta el momento, recalculados al agregar/quitar insumos.
  // No incluye la absorcion por botella (1.4, se decide solo al confirmar)
  // ni horas heredadas de intermedios (depende de 1.1, no construido aun).
  const costoIntermedio = insumosIntermedio.reduce((suma, x) => {
    const prod = intermedios.find((p) => p.id_produccion_intermedio === x.id_prod)
    return suma + x.cantidad * (prod ? prod.costo_unitario : 0)
  }, 0)
  const costoMP = insumosMP.reduce((suma, x) => {
    const lote = lotes.find((l) => l.id_compra === x.id_compra)
    const unit = lote && lote.cantidad_compra ? lote.precio_compra / lote.cantidad_compra : 0
    return suma + x.cantidad * unit
  }, 0)
  const costoTrabajo = insumosTrabajo.reduce((suma, x) => {
    const jornada = jornadas.find((j) => j.id_jornada === x.id_registro)
    const trabajador = jornada ? trabajadores.find((t) => t.id_trabajador === jornada.id_trabajador) : null
    // `pago` es el SUELDO del periodo, no Bs/hora. La tarifa/hora la deriva el
    // backend (sueldo / horas_base) y la expone como `tarifa`; usarla acá para
    // que el indicador visual coincida con el costo real que calcula el backend.
    return suma + x.horas * (trabajador ? trabajador.tarifa || 0 : 0)
  }, 0)
  const costoTotalParcial = costoIntermedio + costoMP + costoTrabajo
  const horasInvertidas = insumosTrabajo.reduce((suma, x) => suma + x.horas, 0)
  const costoUnitarioParcial = cantidadTotal > 0
    ? costoTotalParcial / cantidadTotal
    : null

  // Resumen consolidado pre-producción (item 6b), armado con helpers
  // compartidos con Producción Intermedia. El encabezado se muestra solo cuando
  // ya hay producto y cantidad; las líneas de insumos, apenas hay algo cargado
  // (por eso aparece también en producción manual, no solo al aplicar receta).
  const resumenMP = resumenMateriaPrima(insumosMP, lotes)
  const resumenIntermedio = resumenIntermedios(insumosIntermedio, intermedios)
  const resumenTrab = resumenTrabajo(insumosTrabajo, jornadas)
  const encabezadoResumen = idProducto !== '' && cantidadTotal > 0
    ? <><strong>{fmtBotellasYPaquetes(cantidadTotal, bppElegido)}</strong>{productoElegido ? <> de <strong>{productoElegido.descripcion}</strong></> : null}</>
    : null

  return (
    <div>
      <h2>Producir producto terminado</h2>

      {/* Aplicar pre-receta de terminado (mejora 3.6) */}
      {recetas.some((r) => r.tipo === 'TERMINADO' && r.habilitado) && (
        <div style={{ background: '#efe', padding: '0.4rem', margin: '0.3rem 0' }}>
          <span style={{ fontSize: '0.85em', color: '#575' }}>Aplicar receta: </span>
          <SelectorBuscable
            opciones={recetas.filter((r) => r.habilitado && r.tipo === 'TERMINADO')}
            valor={recetaSel}
            onCambiar={setRecetaSel}
            obtenerId={(r) => r.id_receta}
            obtenerTexto={(r) =>
              `${r.nombre || r.producto} (rinde ${fmtBotellasYPaquetes(r.rendimiento, r.botellas_por_paquete)})`
            }
            placeholder="-- Receta --"
          />
          <InputCalculo value={recetaCantidad} onChange={setRecetaCantidad} placeholder="Cantidad a producir" />
          <button onClick={aplicarReceta}>Aplicar receta</button>
        </div>
      )}

      <div>
        <SelectorBuscable
          opciones={productos.filter((p) => p.habilitado)}
          valor={idProducto}
          onCambiar={elegirProducto}
          obtenerId={(p) => p.id_producto_terminado}
          obtenerTexto={(p) => p.descripcion}
          placeholder="-- Producto terminado a producir --"
        />
        <CantidadPaquetes
          botellasPorPaquete={bppElegido}
          paquetes={cantidadPaquetes}
          botellas={cantidad}
          onCambiarPaquetes={setCantidadPaquetes}
          onCambiarBotellas={setCantidad}
          etiquetaBotellas="Botellas sueltas"
        />
      </div>

      {/* Producto intermedio (insumo principal) */}
      <h3>Producto intermedio</h3>
      <SelectorFifo
        origen="INTERMEDIO"
        opciones={productosIntermedios.filter((p) => p.habilitado)}
        obtenerId={(p) => p.id_producto_intermedio}
        obtenerTexto={(p) => p.descripcion}
        placeholder="-- Producto intermedio --"
        onResolver={agregarIntermedioFifo}
      />
      <div>
        <SelectorBuscable
          opciones={intermedios}
          valor={intLote}
          onCambiar={setIntLote}
          obtenerId={(p) => p.id_produccion_intermedio}
          obtenerTexto={(p) => `${p.descripcion} - Lote ${p.id_produccion_intermedio} (quedan ${p.cantidad_restante}${p.unidad ? ' ' + p.unidad : ''}, costo ${p.costo_unitario})`}
          placeholder="-- Producción intermedia (manual) --"
        />
        <InputCalculo value={intCantidad} onChange={setIntCantidad} placeholder="Cantidad" />
        <button onClick={agregarIntermedio}>Agregar intermedio</button>
      </div>
      <ul>
        {insumosIntermedio.map((x, i) => (
          <li key={i}>{nombreIntermedio(x.id_prod)} — cantidad: {x.cantidad}{' '}<button onClick={() => quitarIntermedio(i)}>quitar</button></li>
        ))}
      </ul>

      {/* Materia prima directa */}
      <h3>Materia prima directa</h3>
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
        <InputCalculo value={mpCantidad} onChange={setMpCantidad} placeholder="Cantidad" />
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
        <InputCalculo value={trabHoras} onChange={setTrabHoras} placeholder="Horas a usar" />
        <button onClick={agregarTrabajo}>Agregar trabajo</button>
      </div>
      <ul>
        {insumosTrabajo.map((x, i) => (
          <li key={i}>{nombreJornada(x.id_registro)} — horas: {x.horas}{' '}<button onClick={() => quitarTrabajo(i)}>quitar</button></li>
        ))}
      </ul>

      {/* Indicadores en vivo (mejora 6.11) */}
      {(insumosIntermedio.length > 0 || insumosMP.length > 0 || insumosTrabajo.length > 0) && (
        <p style={{ background: '#f0f0f0', padding: '0.4rem' }}>
          <strong>Costo unitario parcial:</strong>{' '}
          {costoUnitarioParcial !== null ? `${costoUnitarioParcial.toFixed(4)} Bs` : `(ingresa la cantidad — costo insumos: ${costoTotalParcial.toFixed(2)} Bs)`}
          {' | '}
          <strong>Horas hombre invertidas:</strong> {horasInvertidas.toFixed(2)} h
        </p>
      )}

      <button onClick={producir}>PRODUCIR</button>
      {mensaje && <p>{mensaje}</p>}

      <ResumenProduccion
        encabezado={encabezadoResumen}
        mp={resumenMP}
        intermedio={resumenIntermedio}
        trabajo={resumenTrab}
      />

      <TablaFiltrable
        titulo="Stock general por producto (consolidado)"
        filas={stockGeneral}
        claveOrden="descripcion"
        totales={['stock_total', 'paquetes_equivalentes']}
        columnas={[
          { key: 'descripcion', label: 'Producto' },
          { key: 'stock_total', label: 'Stock total', formato: (v) => fmtNumero(v) },
          { key: 'paquetes_equivalentes', label: 'Paquetes eq.', formato: (v) => fmtNumero(v) },
          { key: 'costo_promedio', label: 'Costo promedio', formato: (v) => fmtNumero(v, 4) },
        ]}
      />

      <TablaFiltrable
        titulo="Stock por lote"
        filas={porLote}
        claveOrden="descripcion"
        columnas={[
          { key: 'id_produccion', label: 'Lote' },
          { key: 'descripcion', label: 'Producto' },
          { key: 'cantidad_restante', label: 'Stock restante', formato: (v) => fmtNumero(v) },
          { key: 'costo_unitario', label: 'Costo unitario', formato: (v) => fmtNumero(v, 4) },
          { key: 'horas_acumuladas', label: 'Horas acum.', formato: (v) => fmtNumero(v, 2) },
        ]}
        acciones={(f) => (
          f.eliminable
            ? <button onClick={() => eliminarProduccion(f.id_produccion)}>Eliminar</button>
            : <span style={{ color: '#999', fontSize: '0.85em' }} title="Ya se usó (venta/merma/etc): corrígelo con devolución, merma o reproceso">— usado</span>
        )}
      />
    </div>
  )
}

export default PaginaProduccionTerminada