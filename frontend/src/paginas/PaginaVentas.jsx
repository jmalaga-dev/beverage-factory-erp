import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import SelectorFifo from '../componentes/SelectorFifo'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtMoneda, fmtNumero } from '../formato'

function PaginaVentas() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [clientes, setClientes] = useState([])
  const [lotes, setLotes] = useState([])       // lotes de producto terminado con stock
  const [cuentas, setCuentas] = useState([])
  const [ventas, setVentas] = useState([])     // ventas registradas

  const [idCliente, setIdCliente] = useState('')

  // La lista de líneas de la venta
  const [lineas, setLineas] = useState([])   // [{id_produccion, cantidad, precio_real, id_cuenta}]

  // Campos temporales para agregar una línea
  const [linProd, setLinProd] = useState('')
  const [linCantidad, setLinCantidad] = useState('')
  const [linPrecio, setLinPrecio] = useState('')
  const [linCuenta, setLinCuenta] = useState('')

  // Margen mínimo de ganancia (% sobre el precio de venta), editable acá en la
  // pantalla porque puede cambiar seguido (6.12). Manda sobre el precio
  // sugerido: al autocompletar una línea o resolver por FIFO se usa el margen
  // actual. Default 35%.
  const [margen, setMargen] = useState('35')

  // Taxi/delivery: SOLO cálculo en pantalla (6.12). Prorratea su costo entre
  // todas las botellas de la venta para ver el neto real por línea. NO mueve
  // caja ni se envía al backend; si el taxi se pagó de verdad, va aparte como
  // un Gasto normal.
  const [taxi, setTaxi] = useState('')

  const [mensaje, setMensaje] = useState('')

  // Precio sugerido de un lote: el mayor entre el recomendado del catálogo y
  // costo/(1−margen), redondeado a 2 decimales. El margen (sobre el precio de
  // venta) sale de la caja editable de arriba.
  function precioSugerido(lote) {
    const m = (parseFloat(margen) || 0) / 100
    const porMargen = m < 1 ? Math.round((lote.costo_unitario / (1 - m)) * 100) / 100 : lote.costo_unitario
    return Math.round(Math.max(lote.precio_recomendado, porMargen) * 100) / 100
  }

  function cargar() {
    apiGet('/clientes').then(setClientes).catch(console.error)
    apiGet('/lotes-producto-terminado').then(setLotes).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/ventas').then(setVentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Productos distintos (para el resolver FIFO, que pide producto + cantidad
  // total y devuelve los lotes del más antiguo al más nuevo).
  const productos = []
  const vistos = new Set()
  for (const l of lotes) {
    if (!vistos.has(l.id_producto)) {
      vistos.add(l.id_producto)
      productos.push({ id_producto: l.id_producto, nombre_producto: l.nombre_producto })
    }
  }

  // Cuánto de un lote ya está comprometido en las líneas actuales
  function yaUsadoDeLote(idLote) {
    return lineas.filter((l) => l.id_produccion === idLote).reduce((s, l) => s + l.cantidad, 0)
  }

  function agregarLinea() {
    if (linProd === '' || linCantidad === '' || linPrecio === '' || linCuenta === '') {
      setMensaje('Completa todos los campos de la línea')
      return
    }
    const lote = lotes.find((l) => l.id_produccion === parseInt(linProd))
    const yaUsado = yaUsadoDeLote(parseInt(linProd))
    if (lote && yaUsado + parseFloat(linCantidad) > lote.stock) {
      setMensaje(`Ese lote solo tiene ${lote.stock} en stock${yaUsado > 0 ? ` (ya agregaste ${yaUsado})` : ''}`)
      return
    }
    setLineas([...lineas, {
      id_produccion: parseInt(linProd),
      cantidad: parseFloat(linCantidad),
      precio_real: parseFloat(linPrecio),
      id_cuenta: parseInt(linCuenta),
    }])
    setLinProd(''); setLinCantidad(''); setLinPrecio(''); setLinCuenta('')
    setMensaje('')
  }

  // Resolver por FIFO: agrega una línea por cada lote sugerido, con su precio
  // sugerido y la cuenta destino elegida arriba (la comparten todas).
  // Descuenta lo que YA está comprometido en las líneas actuales, así resolver
  // el mismo producto dos veces no vuelve a meter lotes agotados ni pasa del
  // stock (el backend igual lo validaría al registrar, pero mejor evitarlo acá).
  function agregarPorFifo(idProducto, asignaciones) {
    if (linCuenta === '') { setMensaje('Elige primero la cuenta destino (la usan las líneas del FIFO)'); return }
    let pendiente = asignaciones.reduce((s, a) => s + a.cantidad, 0)
    const nuevas = []
    for (const a of asignaciones) {
      if (pendiente <= 0) break
      const lote = lotes.find((l) => l.id_produccion === a.id_lote)
      if (!lote) continue
      const disponible = lote.stock - yaUsadoDeLote(a.id_lote)
      const usar = Math.round(Math.min(pendiente, disponible) * 1e6) / 1e6
      if (usar <= 0) continue
      nuevas.push({
        id_produccion: a.id_lote,
        cantidad: usar,
        precio_real: precioSugerido(lote),
        id_cuenta: parseInt(linCuenta),
      })
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

  // Editar el precio de una línea ya cargada, sin quitar y re-agregar.
  function cambiarPrecioLinea(i, valor) {
    setLineas(lineas.map((l, idx) => (idx === i ? { ...l, precio_real: parseFloat(valor) || 0 } : l)))
  }

  // Al elegir un lote, autocompletar el precio con el SUGERIDO
  function elegirProducto(id) {
    setLinProd(id)
    const lote = lotes.find((x) => x.id_produccion === parseInt(id))
    if (lote) setLinPrecio(precioSugerido(lote))
  }

  function registrarVenta() {
    if (idCliente === '') { setMensaje('Elige un cliente'); return }
    if (lineas.length === 0) { setMensaje('Agrega al menos una línea'); return }

    apiPost('/ventas', {
      id_cliente: parseInt(idCliente),
      lineas: lineas,   // el taxi NO se envía: es solo cálculo en pantalla
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

  // Helpers para mostrar nombres en las líneas
  function nombreLote(id) {
    const l = lotes.find((x) => x.id_produccion === id)
    return l ? `${l.nombre_producto} - Lote ${id}` : `Lote ${id}`
  }
  function nombreCuenta(id) {
    const c = cuentas.find((x) => x.id_cuenta === id)
    return c ? c.nombre : `Cuenta ${id}`
  }
  function costoDeLote(id) {
    const l = lotes.find((x) => x.id_produccion === id)
    return l ? l.costo_unitario : null
  }

  // Precio bajo costo del lote que se está armando (solo aviso, no bloquea)
  const loteEnCurso = linProd !== '' ? lotes.find((x) => x.id_produccion === parseInt(linProd)) : null
  const precioBajoCosto = loteEnCurso && linPrecio !== '' && parseFloat(linPrecio) < loteEnCurso.costo_unitario

  // ----- Cálculos de la venta (con prorrateo de taxi) -----
  const taxiNum = parseFloat(taxi) || 0
  const totalBotellas = lineas.reduce((s, l) => s + l.cantidad, 0)
  const taxiPorBotella = totalBotellas > 0 ? taxiNum / totalBotellas : 0
  const hayTaxi = taxiNum > 0

  // Métricas por línea
  const filas = lineas.map((l) => {
    const costo = costoDeLote(l.id_produccion) ?? 0
    const ingreso = l.cantidad * l.precio_real
    const gananciaBruta = (l.precio_real - costo) * l.cantidad
    const taxiLinea = l.cantidad * taxiPorBotella
    const gananciaNeta = gananciaBruta - taxiLinea
    const pct = ingreso > 0 ? (gananciaBruta / ingreso) * 100 : 0
    return { ...l, costo, ingreso, gananciaBruta, taxiLinea, gananciaNeta, pct, bajoCosto: l.precio_real < costo }
  })

  // Totales de la venta
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
          obtenerTexto={(c) => c.nombre}
          placeholder="-- Cliente --"
        />
      </div>

      {/* Margen sugerido, editable acá (no en el backend) */}
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
        <input type="number" placeholder="Cantidad"
          value={linCantidad} onChange={(e) => setLinCantidad(e.target.value)} />
        <input type="number" placeholder="Precio de venta"
          value={linPrecio} onChange={(e) => setLinPrecio(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={linCuenta}
          onCambiar={setLinCuenta}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => c.nombre}
          placeholder="-- Cuenta destino --"
        />
        <button onClick={agregarLinea}>Agregar línea</button>
      </div>

      {precioBajoCosto && (
        <p style={{ color: 'red' }}>
          ⚠ El precio ({linPrecio} Bs) es menor al costo del lote ({loteEnCurso.costo_unitario} Bs)
        </p>
      )}

      {/* Resolver por FIFO: llena varias líneas de golpe (usa la cuenta destino de arriba) */}
      <SelectorFifo
        origen="TERMINADO"
        opciones={productos}
        obtenerId={(p) => p.id_producto}
        obtenerTexto={(p) => p.nombre_producto}
        placeholder="-- Producto (FIFO) --"
        onResolver={agregarPorFifo}
      />

      {/* Líneas de la venta como tabla */}
      {lineas.length > 0 && (
        <table border="1" style={{ marginTop: '0.5rem', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>Producto - Lote</th>
              <th>Cant.</th>
              <th>Costo u.</th>
              <th>Precio</th>
              <th>Ganancia línea</th>
              <th>%</th>
              {hayTaxi && <th>Taxi</th>}
              {hayTaxi && <th>Neto</th>}
              <th>Cuenta</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={i} style={f.bajoCosto ? { color: 'red' } : undefined}>
                <td>{nombreLote(f.id_produccion)}{f.bajoCosto && ' ⚠'}</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(f.cantidad, 2)}</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(f.costo)}</td>
                <td style={{ textAlign: 'right' }}>
                  <input type="number" value={f.precio_real}
                    onChange={(e) => cambiarPrecioLinea(i, e.target.value)}
                    style={{ width: '5.5rem', textAlign: 'right' }} />
                </td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(f.gananciaBruta)}</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(f.pct, 1)}%</td>
                {hayTaxi && <td style={{ textAlign: 'right' }}>{fmtMoneda(f.taxiLinea)}</td>}
                {hayTaxi && <td style={{ textAlign: 'right', color: f.gananciaNeta < 0 ? 'red' : undefined }}>{fmtMoneda(f.gananciaNeta)}</td>}
                <td>{nombreCuenta(f.id_cuenta)}</td>
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
              = {fmtMoneda(taxiPorBotella)} Bs por botella ({fmtNumero(totalBotellas, 2)} botellas)
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
