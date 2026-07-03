import { useState, useEffect } from 'react'

function PaginaCompras() {
  const [materias, setMaterias] = useState([])
  const [cuentas, setCuentas] = useState([])
  const [stockGeneral, setStockGeneral] = useState([])
  const [lotes, setLotes] = useState([])

  // Campos del formulario
  const [idMateria, setIdMateria] = useState('')
  const [idCuenta, setIdCuenta] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [precioTotal, setPrecioTotal] = useState('')

  const [mensaje, setMensaje] = useState('')

  // Cargar todos los datos que la pantalla necesita
  function cargarDatos() {
    fetch('http://127.0.0.1:8000/materias-primas')
      .then((r) => r.json()).then(setMaterias).catch(console.error)
    fetch('http://127.0.0.1:8000/cuentas')
      .then((r) => r.json()).then(setCuentas).catch(console.error)
    fetch('http://127.0.0.1:8000/stock-materia-prima')
      .then((r) => r.json()).then(setStockGeneral).catch(console.error)
    fetch('http://127.0.0.1:8000/lotes-compra')
      .then((r) => r.json()).then(setLotes).catch(console.error)
  }

  useEffect(() => {
    cargarDatos()
  }, [])

  function registrarCompra() {
    if (idMateria === '' || idCuenta === '' || cantidad === '' || precioTotal === '') {
      setMensaje('Completa todos los campos')
      return
    }

    fetch('http://127.0.0.1:8000/compras', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_materia_prima: parseInt(idMateria),
        id_cuenta: parseInt(idCuenta),
        cantidad: parseFloat(cantidad),
        precio_total: parseFloat(precioTotal),
      }),
    })
      .then((r) => {
        if (!r.ok) {
          return r.json().then((err) => {
            throw new Error(err.detail || 'Error al registrar compra')
          })
        }
        return r.json()
      })
      .then(() => {
        setMensaje('Compra registrada correctamente')
        setIdMateria('')
        setIdCuenta('')
        setCantidad('')
        setPrecioTotal('')
        cargarDatos()   // recargar todo: stock y lotes cambiaron
      })
      .catch((e) => setMensaje(e.message))
  }

  // Helper: nombre de una materia prima por su id (para la tabla de lotes)
  function nombreMateria(id) {
    const m = materias.find((x) => x.id_materia_prima === id)
    return m ? m.descripcion : id
  }

  return (
    <div>
      <h2>Registrar compra</h2>

      <div>
        <select value={idMateria} onChange={(e) => setIdMateria(e.target.value)}>
          <option value="">-- Materia prima --</option>
          {materias.map((m) => (
            <option key={m.id_materia_prima} value={m.id_materia_prima}>
              {m.descripcion}
            </option>
          ))}
        </select>

        <select value={idCuenta} onChange={(e) => setIdCuenta(e.target.value)}>
          <option value="">-- Cuenta --</option>
          {cuentas.map((c) => (
            <option key={c.id_cuenta} value={c.id_cuenta}>
              {c.nombre} (saldo: {c.saldo})
            </option>
          ))}
        </select>

        <input type="text" placeholder="Cantidad"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
        <input type="text" placeholder="Precio total"
          value={precioTotal} onChange={(e) => setPrecioTotal(e.target.value)} />

        <button onClick={registrarCompra}>Registrar compra</button>
      </div>

      {mensaje && <p>{mensaje}</p>}

      {/* Tabla 1: stock general por materia prima */}
      <h2>Stock general (sin lote)</h2>
      <table border="1">
        <thead>
          <tr><th>Materia prima</th><th>Unidad</th><th>Stock total</th></tr>
        </thead>
        <tbody>
          {stockGeneral.map((s) => (
            <tr key={s.id_materia_prima}>
              <td>{s.descripcion}</td>
              <td>{s.unidad}</td>
              <td>{s.stock_total}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Tabla 2: stock por lote */}
      <h2>Stock por lote</h2>
      <table border="1">
        <thead>
          <tr><th>Lote</th><th>Materia prima</th><th>Restante</th><th>Precio lote</th></tr>
        </thead>
        <tbody>
          {lotes.map((l) => (
            <tr key={l.id_compra}>
              <td>{l.id_compra}</td>
              <td>{nombreMateria(l.id_materia_prima)}</td>
              <td>{l.cantidad_restante}</td>
              <td>{l.precio_compra}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaCompras