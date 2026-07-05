import { useState, useEffect } from 'react'

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
    fetch('http://127.0.0.1:8000/clientes')
      .then((r) => r.json()).then(setClientes).catch(console.error)
    fetch('http://127.0.0.1:8000/lotes-producto-terminado')
      .then((r) => r.json()).then(setLotes).catch(console.error)
    fetch('http://127.0.0.1:8000/cuentas')
      .then((r) => r.json()).then(setCuentas).catch(console.error)
    fetch('http://127.0.0.1:8000/ventas')
      .then((r) => r.json()).then(setVentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function agregarLinea() {
    if (linProd === '' || linCantidad === '' || linPrecio === '' || linCuenta === '') {
      setMensaje('Completa todos los campos de la línea')
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

  function registrarVenta() {
    if (idCliente === '') { setMensaje('Elige un cliente'); return }
    if (lineas.length === 0) { setMensaje('Agrega al menos una línea'); return }

    fetch('http://127.0.0.1:8000/ventas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_cliente: parseInt(idCliente),
        lineas: lineas,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
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

  // Total de la venta que se está armando
  const totalVenta = lineas.reduce((suma, l) => suma + l.cantidad * l.precio_real, 0)

  return (
    <div>
      <h2>Registrar venta</h2>

      <div>
        <select value={idCliente} onChange={(e) => setIdCliente(e.target.value)}>
          <option value="">-- Cliente --</option>
          {clientes.map((c) => (
            <option key={c.id_cliente} value={c.id_cliente}>{c.nombre}</option>
          ))}
        </select>
      </div>

      {/* Agregar línea de venta */}
      <h3>Agregar producto a la venta</h3>
      <div>
        <select value={linProd} onChange={(e) => {
          setLinProd(e.target.value)
          // autocompletar el precio con el recomendado del lote elegido
          const lote = lotes.find((x) => x.id_produccion === parseInt(e.target.value))
          if (lote) setLinPrecio(lote.precio_recomendado)
        }}>
          <option value="">-- Lote de producto --</option>
          {lotes.map((l) => (
            <option key={l.id_produccion} value={l.id_produccion}>
              {l.nombre_producto} - Lote {l.id_produccion} (stock: {l.stock} | costo: {l.costo_unitario} | recomendado: {l.precio_recomendado} Bs)
            </option>
          ))}
        </select>
        <input type="number" placeholder="Cantidad"
          value={linCantidad} onChange={(e) => setLinCantidad(e.target.value)} />
        <input type="number" placeholder="Precio de venta"
          value={linPrecio} onChange={(e) => setLinPrecio(e.target.value)} />
        <select value={linCuenta} onChange={(e) => setLinCuenta(e.target.value)}>
          <option value="">-- Cuenta destino --</option>
          {cuentas.map((c) => (
            <option key={c.id_cuenta} value={c.id_cuenta}>{c.nombre}</option>
          ))}
        </select>
        <button onClick={agregarLinea}>Agregar línea</button>
      </div>

      {/* Líneas de la venta */}
      <ul>
        {lineas.map((l, i) => (
          <li key={i}>
            {nombreLote(l.id_produccion)} — {l.cantidad} × {l.precio_real} Bs = {(l.cantidad * l.precio_real).toFixed(2)} Bs
            → {nombreCuenta(l.id_cuenta)}
            {' '}<button onClick={() => quitarLinea(i)}>quitar</button>
          </li>
        ))}
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