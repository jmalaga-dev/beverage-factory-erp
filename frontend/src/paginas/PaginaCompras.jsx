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

  // Proveedores activos de la materia elegida (mejora 5.1). Segun cuantos
  // haya: 0 -> bloquear y pedir registrar; 1 -> autoseleccion; >1 -> elegir.
  const [proveedores, setProveedores] = useState([])
  const [idProveedor, setIdProveedor] = useState('')

  // Compra a credito / pedido pendiente (mejora 5.1 ampliacion)
  const [aCredito, setACredito] = useState(false)       // pago parcial
  const [montoPagado, setMontoPagado] = useState('')
  const [pendiente, setPendiente] = useState(false)      // aun no llego
  const [pedidos, setPedidos] = useState([])

  const [mensaje, setMensaje] = useState('')

  // Cargar todos los datos que la pantalla necesita
  function cargarDatos() {
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/stock-materia-prima').then(setStockGeneral).catch(console.error)
    apiGet('/lotes-compra').then(setLotes).catch(console.error)
    apiGet('/pedidos-pendientes').then(setPedidos).catch(console.error)
  }

  useEffect(() => {
    cargarDatos()
  }, [])

  // Cuando cambia la materia prima, traer sus proveedores activos
  useEffect(() => {
    if (idMateria === '') {
      setProveedores([])
      setIdProveedor('')
      return
    }
    apiGet(`/proveedores-por-materia/${idMateria}`)
      .then((provs) => {
        setProveedores(provs)
        // Autoseleccion si hay exactamente uno
        setIdProveedor(provs.length === 1 ? String(provs[0].id_proveedor) : '')
      })
      .catch(console.error)
  }, [idMateria])

  // Cuánto se paga ahora: si es a crédito, el monto pagado; si no, el total.
  const pagoAhora = aCredito ? parseFloat(montoPagado || '0') : parseFloat(precioTotal || '0')
  const faltante = (parseFloat(precioTotal || '0') - pagoAhora)
  const nombreProveedorSel = proveedores.find((p) => p.id_proveedor === parseInt(idProveedor))?.nombre

  function registrarCompra() {
    if (idMateria === '' || idCuenta === '' || cantidad === '' || precioTotal === '') {
      setMensaje('Completa todos los campos')
      return
    }

    // Proveedor obligatorio (mejora 5.1)
    if (proveedores.length === 0) {
      setMensaje('Esta materia prima no tiene proveedores. Regístrale uno en la pantalla de Proveedores antes de comprar.')
      return
    }
    if (idProveedor === '') {
      setMensaje('Elige de qué proveedor se compró')
      return
    }

    if (aCredito) {
      if (montoPagado === '' || pagoAhora < 0) {
        setMensaje('Indica cuánto se paga ahora (0 o más)')
        return
      }
      if (pagoAhora > parseFloat(precioTotal)) {
        setMensaje('El monto pagado no puede superar el precio total')
        return
      }
    }

    // Aviso local de saldo insuficiente sobre lo que se paga AHORA
    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(idCuenta))
    if (cuenta && pagoAhora > cuenta.saldo) {
      setMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs y el pago es de ${pagoAhora} Bs`)
      return
    }

    apiPost('/compras', {
      id_materia_prima: parseInt(idMateria),
      id_cuenta: parseInt(idCuenta),
      cantidad: parseFloat(cantidad),
      precio_total: parseFloat(precioTotal),
      id_proveedor: parseInt(idProveedor),
      // Solo se manda monto_pagado cuando es a credito; si no, el backend paga total
      monto_pagado: aCredito ? pagoAhora : null,
      recibida: !pendiente,
    })
      .then((r) => {
        setMensaje(r.mensaje || 'Compra registrada correctamente')
        setIdMateria('')
        setIdCuenta('')
        setCantidad('')
        setPrecioTotal('')
        setProveedores([])
        setIdProveedor('')
        setACredito(false)
        setMontoPagado('')
        setPendiente(false)
        cargarDatos()   // recargar todo: stock, lotes y pedidos cambiaron
      })
      .catch((e) => setMensaje(e.message))
  }

  function recibirPedido(idCompra) {
    apiPost(`/compras/${idCompra}/recibir`, {})
      .then(() => { setMensaje('Pedido recibido, el stock ya está disponible'); cargarDatos() })
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
          opciones={materias.filter((m) => m.habilitado)}
          valor={idMateria}
          onCambiar={setIdMateria}
          obtenerId={(m) => m.id_materia_prima}
          obtenerTexto={(m) => m.descripcion}
          placeholder="-- Materia prima --"
        />

        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuenta}
          onCambiar={setIdCuenta}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta --"
        />

        {/* Proveedor (mejora 5.1): solo aparece desplegable si hay mas de uno.
            Con uno, ya quedo autoseleccionado. Con ninguno, se avisa. */}
        {idMateria !== '' && proveedores.length === 0 && (
          <span style={{ color: '#a00' }}>
            Sin proveedores para esta materia — regístrale uno en Proveedores.
          </span>
        )}
        {proveedores.length === 1 && (
          <span>Proveedor: {proveedores[0].nombre}</span>
        )}
        {proveedores.length > 1 && (
          <SelectorBuscable
            opciones={proveedores}
            valor={idProveedor}
            onCambiar={setIdProveedor}
            obtenerId={(p) => p.id_proveedor}
            obtenerTexto={(p) => p.nombre}
            placeholder="-- Proveedor --"
          />
        )}

        <input type="text" placeholder="Cantidad"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
        <input type="text" placeholder="Precio total"
          value={precioTotal} onChange={(e) => setPrecioTotal(e.target.value)} />

        {/* Compra a credito / pedido pendiente (mejora 5.1 ampliacion) */}
        <div style={{ marginTop: '0.5rem' }}>
          <label>
            <input type="checkbox" checked={aCredito}
              onChange={(e) => { setACredito(e.target.checked); if (!e.target.checked) setMontoPagado('') }} />
            {' '}A crédito (pago solo una parte ahora)
          </label>
          {aCredito && (
            <span style={{ marginLeft: '0.5rem' }}>
              <input type="text" placeholder="Monto pagado ahora"
                value={montoPagado} onChange={(e) => setMontoPagado(e.target.value)} />
              {precioTotal !== '' && faltante > 0 && (
                <span style={{ color: '#a06000' }}>
                  {' '}Se creará deuda de {faltante.toFixed(2)} Bs
                  {nombreProveedorSel ? ` a ${nombreProveedorSel}` : ''}
                </span>
              )}
            </span>
          )}
        </div>
        <div>
          <label>
            <input type="checkbox" checked={pendiente}
              onChange={(e) => setPendiente(e.target.checked)} />
            {' '}Pedido pendiente (aún no llega — no entra al stock hasta recibirlo)
          </label>
        </div>

        <button onClick={registrarCompra}>Registrar compra</button>
      </div>

      {mensaje && <p>{mensaje}</p>}

      {/* Pedidos pendientes de recibir (mejora 5.1 ampliacion) */}
      {pedidos.length > 0 && (
        <>
          <h2>Pedidos pendientes de recibir</h2>
          <table border="1">
            <thead>
              <tr><th>Pedido</th><th>Materia prima</th><th>Cantidad</th><th>Precio</th><th>Proveedor</th><th>Acción</th></tr>
            </thead>
            <tbody>
              {pedidos.map((p) => (
                <tr key={p.id_compra}>
                  <td>{p.id_compra}</td>
                  <td>{p.nombre_materia}</td>
                  <td>{p.cantidad}</td>
                  <td>{p.precio_compra}</td>
                  <td>{p.proveedor || '—'}</td>
                  <td><button onClick={() => recibirPedido(p.id_compra)}>Recibir</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

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