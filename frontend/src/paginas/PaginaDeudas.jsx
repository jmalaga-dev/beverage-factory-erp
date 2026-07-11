import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

// Deudas y amortizacion (mejoras 7.0 y 7.3). Tres acciones:
//   - Deuda simple: sube el pasivo sin mover caja (interes, gasto que pago un tercero).
//   - Prestamo: sube el pasivo y entra dinero a una cuenta.
//   - Pago: baja el pasivo descontando de una cuenta elegida.
// El balance ya resta las deudas, asi que se reflejan solas en el patrimonio.
function PaginaDeudas() {
  const [deudas, setDeudas] = useState([])
  const [cuentas, setCuentas] = useState([])

  // Deuda simple
  const [descSimple, setDescSimple] = useState('')
  const [montoSimple, setMontoSimple] = useState('')

  // Prestamo con ingreso
  const [descPrestamo, setDescPrestamo] = useState('')
  const [montoPrestamo, setMontoPrestamo] = useState('')
  const [idCuentaPrestamo, setIdCuentaPrestamo] = useState('')

  // Pago
  const [idDeudaPago, setIdDeudaPago] = useState('')
  const [montoPago, setMontoPago] = useState('')
  const [idCuentaPago, setIdCuentaPago] = useState('')

  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/deudas').then(setDeudas).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrarSimple() {
    if (descSimple.trim() === '' || montoSimple === '') {
      setMensaje('Completa descripción y monto de la deuda')
      return
    }
    apiPost('/deudas/simple', { descripcion: descSimple, monto: parseFloat(montoSimple) })
      .then(() => { setMensaje('Deuda registrada'); setDescSimple(''); setMontoSimple(''); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function registrarPrestamo() {
    if (descPrestamo.trim() === '' || montoPrestamo === '' || idCuentaPrestamo === '') {
      setMensaje('Completa descripción, monto y cuenta destino del préstamo')
      return
    }
    apiPost('/deudas/prestamo', {
      descripcion: descPrestamo,
      monto: parseFloat(montoPrestamo),
      id_cuenta_destino: parseInt(idCuentaPrestamo),
    })
      .then(() => {
        setMensaje('Préstamo registrado')
        setDescPrestamo(''); setMontoPrestamo(''); setIdCuentaPrestamo('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function registrarPago() {
    if (idDeudaPago === '' || montoPago === '' || idCuentaPago === '') {
      setMensaje('Completa deuda, monto y cuenta del pago')
      return
    }
    const deuda = deudas.find((d) => d.id_deuda === parseInt(idDeudaPago))
    if (deuda && parseFloat(montoPago) > deuda.saldo) {
      setMensaje(`El pago supera el saldo de la deuda (${deuda.saldo} Bs)`)
      return
    }
    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(idCuentaPago))
    if (cuenta && parseFloat(montoPago) > cuenta.saldo) {
      setMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs`)
      return
    }
    apiPost('/deudas/pago', {
      id_deuda: parseInt(idDeudaPago),
      monto: parseFloat(montoPago),
      id_cuenta: parseInt(idCuentaPago),
    })
      .then(() => {
        setMensaje('Pago registrado')
        setIdDeudaPago(''); setMontoPago(''); setIdCuentaPago('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  const deudasConSaldo = deudas.filter((d) => d.saldo > 0)

  return (
    <div>
      <h2>Deudas</h2>

      <table border="1">
        <thead>
          <tr><th>Descripción</th><th>Saldo</th></tr>
        </thead>
        <tbody>
          {deudas.map((d) => (
            <tr key={d.id_deuda} style={d.saldo <= 0 ? { opacity: 0.5 } : {}}>
              <td>{d.descripcion}</td>
              <td>{d.saldo}</td>
            </tr>
          ))}
          {deudas.length === 0 && <tr><td colSpan={2}>Sin deudas registradas</td></tr>}
        </tbody>
      </table>

      {mensaje && <p>{mensaje}</p>}

      <h3>Registrar deuda simple (sin ingreso de dinero)</h3>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Ej: el interés que cobra el banco, o un gasto que alguien pagó por ti. Sube
        la deuda pero no entra dinero a ninguna cuenta.
      </p>
      <div>
        <input type="text" placeholder="Descripción (a quién / por qué)"
          value={descSimple} onChange={(e) => setDescSimple(e.target.value)} />
        <input type="number" placeholder="Monto"
          value={montoSimple} onChange={(e) => setMontoSimple(e.target.value)} />
        <button onClick={registrarSimple}>Registrar deuda</button>
      </div>

      <h3>Registrar préstamo (entra dinero a una cuenta)</h3>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Ej: el banco te presta 100 a la Billetera Fábrica. Sube la deuda y entra el
        dinero a la cuenta, en un solo paso.
      </p>
      <div>
        <input type="text" placeholder="Descripción (quién presta)"
          value={descPrestamo} onChange={(e) => setDescPrestamo(e.target.value)} />
        <input type="number" placeholder="Monto"
          value={montoPrestamo} onChange={(e) => setMontoPrestamo(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuentaPrestamo}
          onCambiar={setIdCuentaPrestamo}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta a dónde entra --"
        />
        <button onClick={registrarPrestamo}>Registrar préstamo</button>
      </div>

      <h3>Pagar / amortizar una deuda</h3>
      <div>
        <SelectorBuscable
          opciones={deudasConSaldo}
          valor={idDeudaPago}
          onCambiar={setIdDeudaPago}
          obtenerId={(d) => d.id_deuda}
          obtenerTexto={(d) => `${d.descripcion} (saldo: ${d.saldo})`}
          placeholder="-- Deuda a pagar --"
        />
        <input type="number" placeholder="Monto"
          value={montoPago} onChange={(e) => setMontoPago(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuentaPago}
          onCambiar={setIdCuentaPago}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta de dónde sale --"
        />
        <button onClick={registrarPago}>Registrar pago</button>
      </div>
    </div>
  )
}

export default PaginaDeudas
