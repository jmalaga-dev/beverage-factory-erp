import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero, fmtMoneda } from '../formato'

function PaginaCompras() {
  const { fechaParaEnviar } = useFechaGlobal()
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

  // ----- Registrar VARIAS compras a la vez, como tabla: cada línea es una
  // compra independiente (su propia materia, cantidad, precio y proveedor).
  // La cuenta de cada línea NO se elige a mano: se gasta primero la cuenta
  // Fábrica, línea por línea, hasta que ya no alcanza, y de ahí en adelante
  // sale de Casa (ver preview en vivo desde /compras-lote/preview). -----
  const [loteLineas, setLoteLineas] = useState([])   // [{id_materia_prima, nombreMateria, cantidad, precioTotal, id_proveedor, nombreProveedor}]
  const [loteMateria, setLoteMateria] = useState('')
  const [loteCantidad, setLoteCantidad] = useState('')
  const [lotePrecioTotal, setLotePrecioTotal] = useState('')
  const [loteProveedores, setLoteProveedores] = useState([])
  const [loteIdProveedor, setLoteIdProveedor] = useState('')
  const [lotePreview, setLotePreview] = useState(null)   // { asignaciones, total_fabrica, total_casa, saldo_fabrica, saldo_casa }
  const [lotePreviewError, setLotePreviewError] = useState('')
  const [loteMensaje, setLoteMensaje] = useState('')

  // ----- Compra dividida por proporción (mejora 3.8): un pliego se reparte
  // entre varias materias primas segun factor x cantidad (ej. area). -----
  const [divIdCuenta, setDivIdCuenta] = useState('')
  const [divPrecioTotal, setDivPrecioTotal] = useState('')
  const [divLineas, setDivLineas] = useState([])   // [{id_materia_prima, cantidad, factor}]
  const [divMateria, setDivMateria] = useState('')
  const [divCantidad, setDivCantidad] = useState('')
  const [divFactor, setDivFactor] = useState('')
  const [divProveedores, setDivProveedores] = useState([])   // interseccion de proveedores activos
  const [divIdProveedor, setDivIdProveedor] = useState('')
  const [divACredito, setDivACredito] = useState(false)
  const [divMontoPagado, setDivMontoPagado] = useState('')
  const [divPendiente, setDivPendiente] = useState(false)
  const [divMensaje, setDivMensaje] = useState('')

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

  // Cuando cambia la materia elegida para agregar una línea a la tabla,
  // traer sus proveedores activos (mismo patron que el formulario simple)
  useEffect(() => {
    if (loteMateria === '') {
      setLoteProveedores([])
      setLoteIdProveedor('')
      return
    }
    apiGet(`/proveedores-por-materia/${loteMateria}`)
      .then((provs) => {
        setLoteProveedores(provs)
        setLoteIdProveedor(provs.length === 1 ? String(provs[0].id_proveedor) : '')
      })
      .catch(console.error)
  }, [loteMateria])

  function agregarLineaLote() {
    if (loteMateria === '' || loteCantidad === '' || lotePrecioTotal === '') {
      setLoteMensaje('Completa materia, cantidad y precio total de la línea'); return
    }
    if (loteProveedores.length === 0) {
      setLoteMensaje('Esta materia prima no tiene proveedores. Regístrale uno en Proveedores antes de comprar.'); return
    }
    if (loteIdProveedor === '') {
      setLoteMensaje('Elige de qué proveedor se compró esta línea'); return
    }
    const materia = materias.find((m) => m.id_materia_prima === parseInt(loteMateria))
    const proveedor = loteProveedores.find((p) => p.id_proveedor === parseInt(loteIdProveedor))
    setLoteLineas([...loteLineas, {
      id_materia_prima: parseInt(loteMateria),
      nombreMateria: materia ? materia.descripcion : loteMateria,
      cantidad: parseFloat(loteCantidad),
      precioTotal: parseFloat(lotePrecioTotal),
      id_proveedor: parseInt(loteIdProveedor),
      nombreProveedor: proveedor ? proveedor.nombre : '',
    }])
    setLoteMateria(''); setLoteCantidad(''); setLotePrecioTotal('')
    setLoteProveedores([]); setLoteIdProveedor(''); setLoteMensaje('')
  }
  function quitarLineaLote(i) { setLoteLineas(loteLineas.filter((_, idx) => idx !== i)) }

  // Suma total en vivo (para ver cuanto se esta gastando en total)
  const loteTotalGeneral = loteLineas.reduce((s, l) => s + l.precioTotal, 0)

  // Preview en vivo: de que cuenta sale cada linea (Fabrica primero, Casa
  // despues), calculado por el backend para no duplicar la logica de saldos.
  useEffect(() => {
    if (loteLineas.length === 0) {
      setLotePreview(null); setLotePreviewError(''); return
    }
    apiPost('/compras-lote/preview', {
      lineas: loteLineas.map((l) => ({
        id_materia_prima: l.id_materia_prima,
        cantidad: l.cantidad,
        precio_total: l.precioTotal,
        id_proveedor: l.id_proveedor,
      })),
    })
      .then((r) => { setLotePreview(r); setLotePreviewError('') })
      .catch((e) => { setLotePreview(null); setLotePreviewError(e.message) })
  }, [loteLineas])

  function registrarComprasLote() {
    if (loteLineas.length === 0) { setLoteMensaje('Agrega al menos una línea'); return }
    if (lotePreviewError) { setLoteMensaje(lotePreviewError); return }
    apiPost('/compras-lote', {
      lineas: loteLineas.map((l) => ({
        id_materia_prima: l.id_materia_prima,
        cantidad: l.cantidad,
        precio_total: l.precioTotal,
        id_proveedor: l.id_proveedor,
      })),
      fecha: fechaParaEnviar,
    })
      .then((r) => {
        setLoteMensaje(r.mensaje || 'Compras registradas correctamente')
        setLoteLineas([])
        setLotePreview(null)
        cargarDatos()
      })
      .catch((e) => setLoteMensaje(e.message))
  }

  // ----- Compra dividida (mejora 3.8): el proveedor debe vender TODAS las
  // materias primas de las líneas cargadas, así que se calcula la
  // intersección de sus proveedores activos (uno por línea, cruzados). -----
  useEffect(() => {
    if (divLineas.length === 0) {
      setDivProveedores([]); setDivIdProveedor('')
      return
    }
    const idsUnicos = [...new Set(divLineas.map((l) => l.id_materia_prima))]
    Promise.all(idsUnicos.map((id) => apiGet(`/proveedores-por-materia/${id}`)))
      .then((listas) => {
        const interseccion = listas.reduce((acc, lista) => {
          const ids = new Set(lista.map((p) => p.id_proveedor))
          return acc.filter((p) => ids.has(p.id_proveedor))
        }, listas[0] || [])
        setDivProveedores(interseccion)
        setDivIdProveedor(interseccion.length === 1 ? String(interseccion[0].id_proveedor) : '')
      })
      .catch(console.error)
  }, [divLineas])

  function agregarLineaDividida() {
    if (divMateria === '' || divCantidad === '' || divFactor === '') {
      setDivMensaje('Completa materia, cantidad y factor de la línea'); return
    }
    if (divLineas.some((l) => l.id_materia_prima === parseInt(divMateria))) {
      setDivMensaje('Esa materia prima ya está en la lista'); return
    }
    setDivLineas([...divLineas, {
      id_materia_prima: parseInt(divMateria),
      cantidad: parseFloat(divCantidad),
      factor: parseFloat(divFactor),
    }])
    setDivMateria(''); setDivCantidad(''); setDivFactor(''); setDivMensaje('')
  }
  function quitarLineaDividida(i) { setDivLineas(divLineas.filter((_, idx) => idx !== i)) }

  // Reparto en vivo: SOLO por factor (proporción = factor/factor_total). La
  // cantidad no pesa en el reparto, solo sirve para el precio unitario y
  // para registrar el lote correctamente.
  const divFactorTotal = divLineas.reduce((s, l) => s + l.factor, 0)
  const divPreview = divLineas.map((l) => {
    const proporcion = divFactorTotal > 0 ? l.factor / divFactorTotal : 0
    const precioAsignado = divPrecioTotal !== '' ? proporcion * parseFloat(divPrecioTotal) : 0
    const precioUnitario = l.cantidad > 0 ? precioAsignado / l.cantidad : 0
    return { ...l, proporcion, precioAsignado, precioUnitario }
  })
  const divPagoAhora = divACredito ? parseFloat(divMontoPagado || '0') : parseFloat(divPrecioTotal || '0')
  const divFaltante = parseFloat(divPrecioTotal || '0') - divPagoAhora
  const divNombreProveedorSel = divProveedores.find((p) => p.id_proveedor === parseInt(divIdProveedor))?.nombre

  function nombreMateriaDiv(id) {
    const m = materias.find((x) => x.id_materia_prima === id)
    return m ? m.descripcion : id
  }

  function registrarCompraDividida() {
    if (divLineas.length === 0) { setDivMensaje('Agrega al menos una línea'); return }
    if (divIdCuenta === '' || divPrecioTotal === '') { setDivMensaje('Completa cuenta y precio total'); return }
    if (divProveedores.length === 0) {
      setDivMensaje('Ningún proveedor vende TODAS estas materias primas. Revisa Proveedores.'); return
    }
    if (divIdProveedor === '') { setDivMensaje('Elige de qué proveedor se compró el pliego'); return }
    if (divACredito) {
      if (divMontoPagado === '' || divPagoAhora < 0) { setDivMensaje('Indica cuánto se paga ahora (0 o más)'); return }
      if (divPagoAhora > parseFloat(divPrecioTotal)) { setDivMensaje('El monto pagado no puede superar el precio total'); return }
    }
    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(divIdCuenta))
    if (cuenta && divPagoAhora > cuenta.saldo) {
      setDivMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs y el pago es de ${divPagoAhora} Bs`); return
    }

    apiPost('/compras-divididas', {
      id_cuenta: parseInt(divIdCuenta),
      precio_total: parseFloat(divPrecioTotal),
      lineas: divLineas,
      id_proveedor: parseInt(divIdProveedor),
      monto_pagado: divACredito ? divPagoAhora : null,
      recibida: !divPendiente,
      fecha: fechaParaEnviar,
    })
      .then((r) => {
        setDivMensaje(r.mensaje || 'Compra dividida registrada correctamente')
        setDivIdCuenta(''); setDivPrecioTotal(''); setDivLineas([])
        setDivIdProveedor(''); setDivACredito(false); setDivMontoPagado(''); setDivPendiente(false)
        cargarDatos()
      })
      .catch((e) => setDivMensaje(e.message))
  }

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
      fecha: fechaParaEnviar,
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

      {/* Registrar varias compras a la vez, como tabla: cada linea es una
          compra independiente. La cuenta se asigna sola: Fabrica primero,
          Casa despues. */}
      <h2>Registrar varias compras a la vez (tabla)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Agrega una línea por cada materia prima que compraste. La cuenta de
        pago se asigna sola: primero se gasta <strong>Fábrica</strong> línea
        por línea hasta que ya no alcanza, y de ahí en adelante se paga con
        <strong> Casa</strong>. Todas las líneas se registran de contado y
        recibidas (para crédito o pedido pendiente, usa el formulario de arriba).
      </p>
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        {/* Agregar línea */}
        <div>
          <SelectorBuscable
            opciones={materias.filter((m) => m.habilitado)}
            valor={loteMateria}
            onCambiar={setLoteMateria}
            obtenerId={(m) => m.id_materia_prima}
            obtenerTexto={(m) => m.descripcion}
            placeholder="-- Materia prima --"
          />
          <input type="text" placeholder="Cantidad"
            value={loteCantidad} onChange={(e) => setLoteCantidad(e.target.value)} />
          <input type="text" placeholder="Precio total"
            value={lotePrecioTotal} onChange={(e) => setLotePrecioTotal(e.target.value)} />

          {loteMateria !== '' && loteProveedores.length === 0 && (
            <span style={{ color: '#a00' }}>
              {' '}Sin proveedores para esta materia — regístrale uno en Proveedores.
            </span>
          )}
          {loteProveedores.length === 1 && (
            <span> Proveedor: {loteProveedores[0].nombre}</span>
          )}
          {loteProveedores.length > 1 && (
            <SelectorBuscable
              opciones={loteProveedores}
              valor={loteIdProveedor}
              onCambiar={setLoteIdProveedor}
              obtenerId={(p) => p.id_proveedor}
              obtenerTexto={(p) => p.nombre}
              placeholder="-- Proveedor --"
            />
          )}
          <button onClick={agregarLineaLote}>Agregar línea</button>
        </div>

        {/* Tabla de líneas cargadas, con la cuenta asignada en vivo */}
        {loteLineas.length > 0 && (
          <table border="1" style={{ marginTop: '0.5rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr><th>Materia prima</th><th>Cant.</th><th>Precio total</th><th>Proveedor</th><th>Cuenta</th><th></th></tr>
            </thead>
            <tbody>
              {loteLineas.map((l, i) => (
                <tr key={i}>
                  <td>{l.nombreMateria}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(l.cantidad)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(l.precioTotal)}</td>
                  <td>{l.nombreProveedor}</td>
                  <td>{lotePreview?.asignaciones?.[i] === 'CASA' ? 'Casa' : lotePreview?.asignaciones?.[i] === 'FABRICA' ? 'Fábrica' : '—'}</td>
                  <td><button onClick={() => quitarLineaLote(i)}>quitar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Suma en vivo: total general y cuanto va a cada billetera */}
        {loteLineas.length > 0 && (
          <p style={{ marginTop: '0.5rem' }}>
            <strong>Total: {fmtMoneda(loteTotalGeneral)}</strong>
            {lotePreview && (
              <>
                {' '}— Fábrica: {fmtMoneda(lotePreview.total_fabrica)} (saldo {fmtMoneda(lotePreview.saldo_fabrica)})
                {' '}— Casa: {fmtMoneda(lotePreview.total_casa)} (saldo {fmtMoneda(lotePreview.saldo_casa)})
              </>
            )}
          </p>
        )}
        {lotePreviewError && <p style={{ color: '#a00' }}>{lotePreviewError}</p>}

        <button onClick={registrarComprasLote} style={{ marginTop: '0.5rem' }}>
          Registrar {loteLineas.length > 0 ? `las ${loteLineas.length} compras` : 'compras'}
        </button>
        {loteMensaje && <p>{loteMensaje}</p>}
      </div>

      {/* Compra dividida por proporción (mejora 3.8): un pliego que se
          reparte entre varias materias primas según su factor. */}
      <h2>Compra dividida (pliego)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Ej: un pliego de 100 Bs con etiquetas de varios tamaños. El costo se
        reparte <strong>solo por el factor</strong> de cada línea (ej. el área
        que ocupa esa etiqueta en el pliego; para otros repartos, cualquier
        número proporcional). La <strong>cantidad no afecta el reparto</strong>:
        solo sirve para registrar el lote y calcular el precio unitario.
      </p>
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        <div>
          <SelectorBuscable
            opciones={cuentas.filter((c) => c.habilitado)}
            valor={divIdCuenta}
            onCambiar={setDivIdCuenta}
            obtenerId={(c) => c.id_cuenta}
            obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
            placeholder="-- Cuenta --"
          />
          <input type="text" placeholder="Precio total del pliego"
            value={divPrecioTotal} onChange={(e) => setDivPrecioTotal(e.target.value)} />
        </div>

        {/* Agregar línea */}
        <div style={{ marginTop: '0.5rem' }}>
          <SelectorBuscable
            opciones={materias.filter((m) => m.habilitado)}
            valor={divMateria}
            onCambiar={setDivMateria}
            obtenerId={(m) => m.id_materia_prima}
            obtenerTexto={(m) => m.descripcion}
            placeholder="-- Materia prima --"
          />
          <input type="text" placeholder="Cantidad"
            value={divCantidad} onChange={(e) => setDivCantidad(e.target.value)} />
          <input type="text" placeholder="Factor (ej. área)"
            value={divFactor} onChange={(e) => setDivFactor(e.target.value)} />
          <button onClick={agregarLineaDividida}>Agregar línea</button>
        </div>

        {/* Reparto en vivo */}
        {divPreview.length > 0 && (
          <table border="1" style={{ marginTop: '0.5rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr><th>Materia prima</th><th>Cant.</th><th>Factor</th><th>%</th><th>Precio asignado</th><th>Precio unit.</th><th></th></tr>
            </thead>
            <tbody>
              {divPreview.map((l, i) => (
                <tr key={i}>
                  <td>{nombreMateriaDiv(l.id_materia_prima)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(l.cantidad)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(l.factor)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(l.proporcion * 100, 1)}%</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(l.precioAsignado)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(l.precioUnitario)}</td>
                  <td><button onClick={() => quitarLineaDividida(i)}>quitar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Proveedor: debe vender TODAS las materias de las líneas cargadas */}
        {divLineas.length > 0 && divProveedores.length === 0 && (
          <p style={{ color: '#a00' }}>
            Ningún proveedor vende todas estas materias primas a la vez — regístralo en Proveedores.
          </p>
        )}
        {divProveedores.length === 1 && (
          <p>Proveedor: {divProveedores[0].nombre}</p>
        )}
        {divProveedores.length > 1 && (
          <div style={{ marginTop: '0.4rem' }}>
            <SelectorBuscable
              opciones={divProveedores}
              valor={divIdProveedor}
              onCambiar={setDivIdProveedor}
              obtenerId={(p) => p.id_proveedor}
              obtenerTexto={(p) => p.nombre}
              placeholder="-- Proveedor --"
            />
          </div>
        )}

        {/* Crédito / pedido pendiente (reutiliza 5.1) */}
        <div style={{ marginTop: '0.5rem' }}>
          <label>
            <input type="checkbox" checked={divACredito}
              onChange={(e) => { setDivACredito(e.target.checked); if (!e.target.checked) setDivMontoPagado('') }} />
            {' '}A crédito (pago solo una parte ahora)
          </label>
          {divACredito && (
            <span style={{ marginLeft: '0.5rem' }}>
              <input type="text" placeholder="Monto pagado ahora"
                value={divMontoPagado} onChange={(e) => setDivMontoPagado(e.target.value)} />
              {divPrecioTotal !== '' && divFaltante > 0 && (
                <span style={{ color: '#a06000' }}>
                  {' '}Se creará deuda de {divFaltante.toFixed(2)} Bs
                  {divNombreProveedorSel ? ` a ${divNombreProveedorSel}` : ''}
                </span>
              )}
            </span>
          )}
        </div>
        <div>
          <label>
            <input type="checkbox" checked={divPendiente}
              onChange={(e) => setDivPendiente(e.target.checked)} />
            {' '}Pedido pendiente (aún no llega — no entra al stock hasta recibirlo)
          </label>
        </div>

        <button onClick={registrarCompraDividida} style={{ marginTop: '0.5rem' }}>Registrar compra dividida</button>
        {divMensaje && <p>{divMensaje}</p>}
      </div>

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
                  <td>{fmtNumero(p.cantidad)}</td>
                  <td>{fmtMoneda(p.precio_compra)}</td>
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
              <td>{fmtNumero(s.stock_total)}</td>
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
              <td>{fmtNumero(l.cantidad_restante)}</td>
              <td>{fmtMoneda(l.precio_compra)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaCompras