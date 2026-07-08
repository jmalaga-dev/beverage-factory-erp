import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

function PaginaVentas() {
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

  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/clientes').then(setClientes).catch(console.error)
    apiGet('/lotes-producto-terminado').then(setLotes).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/ventas').then(setVentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function agregarLinea() {
    if (linProd === '' || linCantidad === '' || linPrecio === '' || linCuenta === '') {
      setMensaje('Completa todos los campos de la línea')
      return
    }
    const lote = lotes.find((l) => l.id_produccion === parseInt(linProd))
    const yaUsado = lineas
      .filter((l) => l.id_produccion === parseInt(linProd))
      .reduce((s, l) => s + l.cantidad, 0)
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

  function quitarLinea(i) { setLineas(lineas.filter((_, idx) => idx !== i)) }

  // Al elegir un lote, autocompletar el precio con el recomendado
  function elegirProducto(id) {
    setLinProd(id)
    const lote = lotes.find((x) => x.id_produccion === parseInt(id))
    if (lote) setLinPrecio(lote.precio_recomendado)
  }

  function registrarVenta() {
    if (idCliente === '') { setMensaje('Elige un cliente'); return }
    if (lineas.length === 0) { setMensaje('Agrega al menos una línea'); return }

    apiPost('/ventas', {
      id_cliente: parseInt(idCliente),
      lineas: lineas,
    })
      .then(() => {
        setMensaje('Venta registrada correctamente')
        setIdCliente('')
        setLineas([])
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

  // Total de la venta que se está armando
  const totalVenta = lineas.reduce((suma, l) => suma + l.cantidad * l.precio_real, 0)

  return (
    <div>
      <h2>Registrar venta</h2>

      <div>
        <SelectorBuscable
          opciones={clientes}
          valor={idCliente}
          onCambiar={setIdCliente}
          obtenerId={(c) => c.id_cliente}
          obtenerTexto={(c) => c.nombre}
          placeholder="-- Cliente --"
        />
      </div>

      {/* Agregar línea de venta */}
      <h3>Agregar producto a la venta</h3>
      <div>
        <SelectorBuscable
          opciones={lotes}
          valor={linProd}
          onCambiar={elegirProducto}
          obtenerId={(l) => l.id_produccion}
          obtenerTexto={(l) => `${l.nombre_producto} - Lote ${l.id_produccion} (stock: ${l.stock} | costo: ${l.costo_unitario} | recomendado: ${l.precio_recomendado} Bs)`}
          placeholder="-- Lote de producto --"
        />
        <input type="number" placeholder="Cantidad"
          value={linCantidad} onChange={(e) => setLinCantidad(e.target.value)} />
        <input type="number" placeholder="Precio de venta"
          value={linPrecio} onChange={(e) => setLinPrecio(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas}
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

      {/* Líneas de la venta */}
      <ul>
        {lineas.map((l, i) => {
          const costo = costoDeLote(l.id_produccion)
          const bajoCosto = costo !== null && l.precio_real < costo
          return (
            <li key={i} style={bajoCosto ? { color: 'red' } : undefined}>
              {nombreLote(l.id_produccion)} — {l.cantidad} × {l.precio_real} Bs = {(l.cantidad * l.precio_real).toFixed(2)} Bs
              → {nombreCuenta(l.id_cuenta)}
              {bajoCosto && ' ⚠ bajo costo'}
              {' '}<button onClick={() => quitarLinea(i)}>quitar</button>
            </li>
          )
        })}
      </ul>

      {lineas.length > 0 && <p><strong>Total venta: {totalVenta.toFixed(2)} Bs</strong></p>}

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
              <td>{v.id_venta}</td><td>{v.cliente}</td><td>{v.fecha}</td><td>{v.lineas}</td><td>{v.total}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaVentas