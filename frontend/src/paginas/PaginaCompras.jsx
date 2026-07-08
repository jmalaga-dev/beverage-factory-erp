import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

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
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/stock-materia-prima').then(setStockGeneral).catch(console.error)
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
  }

  useEffect(() => {
    cargarDatos()
  }, [])

  function registrarCompra() {
    if (idMateria === '' || idCuenta === '' || cantidad === '' || precioTotal === '') {
      setMensaje('Completa todos los campos')
      return
    }

    apiPost('/compras', {
      id_materia_prima: parseInt(idMateria),
      id_cuenta: parseInt(idCuenta),
      cantidad: parseFloat(cantidad),
      precio_total: parseFloat(precioTotal),
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
        <SelectorBuscable
          opciones={materias}
          valor={idMateria}
          onCambiar={setIdMateria}
          obtenerId={(m) => m.id_materia_prima}
          obtenerTexto={(m) => m.descripcion}
          placeholder="-- Materia prima --"
        />

        <SelectorBuscable
          opciones={cuentas}
          valor={idCuenta}
          onCambiar={setIdCuenta}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta --"
        />

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