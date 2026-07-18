import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import SelectorFifo from '../componentes/SelectorFifo'
import CantidadPaquetes, { totalBotellas } from '../componentes/CantidadPaquetes'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtMoneda, fmtNumero } from '../formato'

function PaginaVentas() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [clientes, setClientes] = useState([])
  const [lotes, setLotes] = useState([])       // lotes de producto terminado con stock
  const [ventas, setVentas] = useState([])     // ventas registradas

  const [idCliente, setIdCliente] = useState('')

  // La lista de líneas de la venta. El dinero NO se asigna a una cuenta a mano:
  // se reparte 70/30 entre Fábrica y Casa según recuperación de inversión (2.C).
  const [lineas, setLineas] = useState([])   // [{id_produccion, cantidad, precio_real}]

  // Campos temporales para agregar una línea. La cantidad se carga en
  // paquetes + botellas sueltas (6.13); el total en botellas es derivado.
  const [linProd, setLinProd] = useState('')
  const [linCantidadPaquetes, setLinCantidadPaquetes] = useState('')
  const [linCantidad, setLinCantidad] = useState('')
  const [linPrecio, setLinPrecio] = useState('')

  // Margen mínimo de ganancia (% sobre el precio de venta), editable acá (6.12).
  const [margen, setMargen] = useState('35')

  // Taxi/delivery: SOLO cálculo en pantalla (6.12). No mueve caja.
  const [taxi, setTaxi] = useState('')

  // Vista previa del reparto 70/30 Fábrica/Casa (2.C), recalculada por el backend.
  const [reparto, setReparto] = useState(null)

  // Último precio al que ESTE cliente compró cada producto (mejora 10.4). Mapa
  // { id_producto: precio }. Es el precio por defecto de la línea; si el
  // producto no está en el mapa (nunca se lo vendimos a este cliente), se cae
  // al precio sugerido.
  const [ultimosPrecios, setUltimosPrecios] = useState({})

  const [mensaje, setMensaje] = useState('')

  function precioSugerido(lote) {
    const m = (parseFloat(margen) || 0) / 100
    const porMargen = m < 1 ? Math.round((lote.costo_unitario / (1 - m)) * 100) / 100 : lote.costo_unitario
    return Math.round(Math.max(lote.precio_recomendado, porMargen) * 100) / 100
  }

  // Precio por defecto de una línea: el último que le vendimos a este cliente
  // de ese producto; si no hay, el sugerido (mejora 10.4).
  function precioDefault(lote) {
    const ultimo = ultimosPrecios[lote.id_producto]
    return ultimo != null ? ultimo : precioSugerido(lote)
  }

  // Texto de un cliente en el selector: nombre + apellido, y licorería/celular
  // entre paréntesis si los tiene, para poder buscarlo y distinguirlo de otro
  // cliente con el mismo nombre (mejora 10.9). SelectorBuscable filtra sobre
  // este mismo texto, así que basta con incluir los campos para que también
  // se pueda buscar por celular o licorería.
  function textoCliente(c) {
    const nombreCompleto = `${c.nombre}${c.apellido ? ' ' + c.apellido : ''}`
    const extra = [c.licoreria, c.celular].filter(Boolean).join(' · ')
    return extra ? `${nombreCompleto} (${extra})` : nombreCompleto
  }

  function cargar() {
    apiGet('/clientes').then(setClientes).catch(console.error)
    apiGet('/lotes-producto-terminado').then(setLotes).catch(console.error)
    apiGet('/ventas').then(setVentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Cargar los últimos precios de este cliente al elegirlo (mejora 10.4).
  useEffect(() => {
    if (idCliente === '') { setUltimosPrecios({}); return }
    apiGet(`/ultimo-precio-cliente/${idCliente}`).then(setUltimosPrecios).catch(() => setUltimosPrecios({}))
  }, [idCliente])

  // Recalcular el reparto 70/30 cada vez que cambian las líneas (lo resuelve el
  // backend, misma lógica que al registrar: acumula el saldo línea por línea).
  useEffect(() => {
    if (lineas.length === 0) { setReparto(null); return }
    apiPost('/ventas/preview-reparto', lineas.map((l) => ({
      id_produccion: l.id_produccion, cantidad: l.cantidad, precio_real: l.precio_real,
    }))).then(setReparto).catch(() => setReparto(null))
  }, [lineas])

  const productos = []
  const vistos = new Set()
  for (const l of lotes) {
    if (!vistos.has(l.id_producto)) {
      vistos.add(l.id_producto)
      productos.push({
        id_producto: l.id_producto,
        nombre_producto: l.nombre_producto,
        botellas_por_paquete: l.botellas_por_paquete,
      })
    }
  }

  function yaUsadoDeLote(idLote) {
    return lineas.filter((l) => l.id_produccion === idLote).reduce((s, l) => s + l.cantidad, 0)
  }

  function agregarLinea() {
    if (linProd === '' || linCantidadTotal <= 0 || linPrecio === '') {
      setMensaje('Completa lote, cantidad y precio')
      return
    }
    const lote = lotes.find((l) => l.id_produccion === parseInt(linProd))
    const yaUsado = yaUsadoDeLote(parseInt(linProd))
    if (lote && yaUsado + linCantidadTotal > lote.stock) {
      setMensaje(`Ese lote solo tiene ${lote.stock} en stock${yaUsado > 0 ? ` (ya agregaste ${yaUsado})` : ''}`)
      return
    }
    setLineas([...lineas, {
      id_produccion: parseInt(linProd),
      cantidad: linCantidadTotal,
      precio_real: parseFloat(linPrecio),
    }])
    setLinProd(''); setLinCantidadPaquetes(''); setLinCantidad(''); setLinPrecio('')
    setMensaje('')
  }

  // Resolver por FIFO: agrega una línea por cada lote sugerido, con su precio
  // sugerido. Descuenta lo ya comprometido en las líneas actuales.
  function agregarPorFifo(idProducto, asignaciones) {
    let pendiente = asignaciones.reduce((s, a) => s + a.cantidad, 0)
    const nuevas = []
    for (const a of asignaciones) {
      if (pendiente <= 0) break
      const lote = lotes.find((l) => l.id_produccion === a.id_lote)
      if (!lote) continue
      const disponible = lote.stock - yaUsadoDeLote(a.id_lote)
      const usar = Math.round(Math.min(pendiente, disponible) * 1e6) / 1e6
      if (usar <= 0) continue
      nuevas.push({ id_produccion: a.id_lote, cantidad: usar, precio_real: precioDefault(lote) })
      pendiente -= usar
    }
    if (nuevas.length === 0) {
      setMensaje('Ese producto ya está todo comprometido en las líneas actuales (sin stock libre)')
      return
    }
    setLineas([...lineas, ...nuevas])
    setMensaje(pendiente > 0.0001
      ? `Se agregó lo disponible; faltan ${fmtNumero(pendiente, 2)} (ya comprometidos en otras líneas o sin stock)`
      : '')
  }

  function quitarLinea(i) { setLineas(lineas.filter((_, idx) => idx !== i)) }

  function cambiarPrecioLinea(i, valor) {
    setLineas(lineas.map((l, idx) => (idx === i ? { ...l, precio_real: parseFloat(valor) || 0 } : l)))
  }

  function elegirProducto(id) {
    setLinProd(id)
    // Limpiar la cantidad: un valor en paquetes pertenece al tamaño de paquete
    // del lote anterior, y arrastrarlo daría un total distinto del tecleado.
    setLinCantidadPaquetes(''); setLinCantidad('')
    const lote = lotes.find((x) => x.id_produccion === parseInt(id))
    if (lote) setLinPrecio(precioDefault(lote))
  }

  function registrarVenta() {
    if (idCliente === '') { setMensaje('Elige un cliente'); return }
    if (lineas.length === 0) { setMensaje('Agrega al menos una línea'); return }

    apiPost('/ventas', {
      id_cliente: parseInt(idCliente),
      lineas: lineas,   // el taxi NO se envía; reparto 70/30 = default en el backend
      fecha: fechaParaEnviar,
    })
      .then(() => {
        setMensaje('Venta registrada correctamente')
        setIdCliente('')
        setLineas([])
        setTaxi('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function nombreLote(id) {
    const l = lotes.find((x) => x.id_produccion === id)
    return l ? `${l.nombre_producto} - Lote ${id}` : `Lote ${id}`
  }
  function costoDeLote(id) {
    const l = lotes.find((x) => x.id_produccion === id)
    return l ? l.costo_unitario : null
  }

  const loteEnCurso = linProd !== '' ? lotes.find((x) => x.id_produccion === parseInt(linProd)) : null
  const precioBajoCosto = loteEnCurso && linPrecio !== '' && parseFloat(linPrecio) < loteEnCurso.costo_unitario
  // Total en botellas de la línea en curso (6.13): derivado, nunca estado.
  const bppEnCurso = loteEnCurso ? loteEnCurso.botellas_por_paquete : 1
  const linCantidadTotal = totalBotellas(linCantidadPaquetes, linCantidad, bppEnCurso)

  // ----- Cálculos de la venta (ganancia + prorrateo de taxi) -----
  const taxiNum = parseFloat(taxi) || 0
  // Botellas de TODA la venta (para prorratear el taxi). Nombre explicito
  // para no chocar con el helper importado totalBotellas() de 6.13.
  const totalBotellasVenta = lineas.reduce((s, l) => s + l.cantidad, 0)
  const taxiPorBotella = totalBotellasVenta > 0 ? taxiNum / totalBotellasVenta : 0
  const hayTaxi = taxiNum > 0

  const filas = lineas.map((l) => {
    const lote = lotes.find((x) => x.id_produccion === l.id_produccion)
    const costo = costoDeLote(l.id_produccion) ?? 0
    const sugerido = lote ? precioSugerido(lote) : costo
    const ingreso = l.cantidad * l.precio_real
    const gananciaBruta = (l.precio_real - costo) * l.cantidad
    const taxiLinea = l.cantidad * taxiPorBotella
    const gananciaNeta = gananciaBruta - taxiLinea
    const pct = ingreso > 0 ? (gananciaBruta / ingreso) * 100 : 0
    return {
      ...l, costo, sugerido, ingreso, gananciaBruta, taxiLinea, gananciaNeta, pct,
      bpp: lote ? lote.botellas_por_paquete : 1,
      bajoCosto: l.precio_real < costo,
    }
  })

  const totIngreso = filas.reduce((s, f) => s + f.ingreso, 0)
  const totCosto = filas.reduce((s, f) => s + f.costo * f.cantidad, 0)
  const totBruta = filas.reduce((s, f) => s + f.gananciaBruta, 0)
  const totNeta = totBruta - taxiNum
  const gananciaFinal = hayTaxi ? totNeta : totBruta
  const pctPonderado = totIngreso > 0 ? (gananciaFinal / totIngreso) * 100 : 0

  return (
    <div>
      <h2>Registrar venta</h2>

      <div>
        <SelectorBuscable
          opciones={clientes.filter((c) => c.habilitado)}
          valor={idCliente}
          onCambiar={setIdCliente}
          obtenerId={(c) => c.id_cliente}
          obtenerTexto={textoCliente}
          placeholder="-- Cliente (nombre, celular o licorería) --"
        />
      </div>

      <div style={{ margin: '0.5rem 0' }}>
        <label>
          Margen sugerido:{' '}
          <input type="number" value={margen} onChange={(e) => setMargen(e.target.value)}
            style={{ width: '4rem' }} /> %
        </label>
        <span style={{ marginLeft: '0.5rem', color: '#557', fontSize: '0.85em' }}>
          (precio sugerido = mayor entre el recomendado y costo/(1−margen))
        </span>
      </div>

      {/* Agregar línea de venta */}
      <h3>Agregar producto a la venta</h3>
      <div>
        <SelectorBuscable
          opciones={lotes}
          valor={linProd}
          onCambiar={elegirProducto}
          obtenerId={(l) => l.id_produccion}
          obtenerTexto={(l) => `${l.nombre_producto} - Lote ${l.id_produccion} (stock: ${l.stock} | costo: ${l.costo_unitario} | sugerido: ${precioSugerido(l)} Bs)`}
          placeholder="-- Lote de producto --"
        />
        <CantidadPaquetes
          botellasPorPaquete={bppEnCurso}
          paquetes={linCantidadPaquetes}
          botellas={linCantidad}
          onCambiarPaquetes={setLinCantidadPaquetes}
          onCambiarBotellas={setLinCantidad}
        />
        <input type="number" placeholder="Precio de venta"
          value={linPrecio} onChange={(e) => setLinPrecio(e.target.value)} />
        <button onClick={agregarLinea}>Agregar línea</button>
      </div>

      {precioBajoCosto && (
        <p style={{ color: 'red' }}>
          ⚠ El precio ({linPrecio} Bs) es menor al costo del lote ({loteEnCurso.costo_unitario} Bs)
        </p>
      )}

      {/* Resolver por FIFO: llena varias líneas de golpe */}
      <SelectorFifo
        origen="TERMINADO"
        opciones={productos}
        obtenerId={(p) => p.id_producto}
        obtenerTexto={(p) => p.nombre_producto}
        placeholder="-- Producto (FIFO) --"
        onResolver={agregarPorFifo}
        obtenerBotellasPorPaquete={(p) => p.botellas_por_paquete}
      />

      {/* Líneas de la venta como tabla */}
      {lineas.length > 0 && (
        <table border="1" style={{ marginTop: '0.5rem', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>Producto - Lote</th>
              <th>Cant.</th>
              <th>Costo u.</th>
              <th>Precio sugerido</th>
              <th>Precio</th>
              <th>Ganancia línea</th>
              <th>%</th>
              {hayTaxi && <th>Taxi</th>}
              {hayTaxi && <th>Neto</th>}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={i} style={f.bajoCosto ? { color: 'red' } : undefined}>
                <td>{nombreLote(f.id_produccion)}{f.bajoCosto && ' ⚠'}</td>
                <td style={{ textAlign: 'right' }}>
                  {fmtNumero(f.cantidad, 2)}
                  {f.bpp > 1 && (
                    <span style={{ color: '#557', fontSize: '0.85em' }}>
                      {' '}({fmtNumero(f.cantidad / f.bpp)} paq)
                    </span>
                  )}
                </td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(f.costo)}</td>
                <td style={{ textAlign: 'right', color: '#557' }}>{fmtMoneda(f.sugerido)}</td>
                <td style={{ textAlign: 'right' }}>
                  <input type="number" value={f.precio_real}
                    onChange={(e) => cambiarPrecioLinea(i, e.target.value)}
                    style={{ width: '5.5rem', textAlign: 'right' }} />
                </td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(f.gananciaBruta)}</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(f.pct, 1)}%</td>
                {hayTaxi && <td style={{ textAlign: 'right' }}>{fmtMoneda(f.taxiLinea)}</td>}
                {hayTaxi && <td style={{ textAlign: 'right', color: f.gananciaNeta < 0 ? 'red' : undefined }}>{fmtMoneda(f.gananciaNeta)}</td>}
                <td><button onClick={() => quitarLinea(i)}>quitar</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Taxi/delivery: solo cálculo en pantalla */}
      {lineas.length > 0 && (
        <div style={{ margin: '0.5rem 0' }}>
          <label>
            Taxi/delivery (solo cálculo, no mueve caja):{' '}
            <input type="number" placeholder="0.00"
              value={taxi} onChange={(e) => setTaxi(e.target.value)} style={{ width: '7rem' }} />
          </label>
          {hayTaxi && (
            <span style={{ marginLeft: '0.5rem', color: '#557' }}>
              = {fmtMoneda(taxiPorBotella)} Bs por botella ({fmtNumero(totalBotellasVenta, 2)} botellas)
            </span>
          )}
        </div>
      )}

      {/* Totales de la venta */}
      {lineas.length > 0 && (
        <div style={{ margin: '0.5rem 0', lineHeight: 1.6 }}>
          <div>Ingreso: <strong>{fmtMoneda(totIngreso)} Bs</strong>{'  ·  '}
            Costo: {fmtMoneda(totCosto)} Bs{'  ·  '}
            Ganancia bruta: {fmtMoneda(totBruta)} Bs</div>
          {hayTaxi && <div>Taxi total: {fmtMoneda(taxiNum)} Bs</div>}
          <div>
            <strong>Ganancia {hayTaxi ? 'neta' : ''}: {fmtMoneda(gananciaFinal)} Bs</strong>
            {'  ·  '}% ganancia ponderado: <strong>{fmtNumero(pctPonderado, 1)}%</strong>
          </div>
        </div>
      )}

      {/* Reparto 70/30 del ingreso entre Fábrica y Casa (2.C) */}
      {reparto && (
        <div style={{ margin: '0.5rem 0', padding: '0.4rem', background: '#eef7ee' }}>
          <strong>Reparto del ingreso</strong> (100% a Fábrica hasta recuperar la inversión de cada producto; después 70/30):{' '}
          Fábrica <strong>{fmtMoneda(reparto.total_fabrica)} Bs</strong>{'  ·  '}
          Casa <strong>{fmtMoneda(reparto.total_casa)} Bs</strong>
        </div>
      )}

      <button onClick={registrarVenta}>REGISTRAR VENTA</button>
      {mensaje && <p>{mensaje}</p>}

      <h2>Ventas registradas</h2>
      <table border="1">
        <thead>
          <tr><th>Venta</th><th>Cliente</th><th>Fecha</th><th>Líneas</th><th>Total</th></tr>
        </thead>
        <tbody>
          {ventas.map((v) => (
            <tr key={v.id_venta}>
              <td>{v.id_venta}</td><td>{v.cliente}</td><td>{v.fecha}</td><td>{v.lineas}</td><td>{fmtMoneda(v.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaVentas
