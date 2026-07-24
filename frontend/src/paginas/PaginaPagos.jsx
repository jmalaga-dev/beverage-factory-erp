import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import InputCalculo from '../componentes/InputCalculo'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { evaluar } from '../calculo'

function PaginaPagos() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [trabajadores, setTrabajadores] = useState([])
  const [cuentas, setCuentas] = useState([])

  const [idTrabajador, setIdTrabajador] = useState('')
  const [sugerido, setSugerido] = useState(null)
  const [jornadasPendientes, setJornadasPendientes] = useState(0)
  const [montoReal, setMontoReal] = useState('')
  const [idCuenta, setIdCuenta] = useState('')
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    // Solo trabajadores con jornadas sin pagar (item 12): no tiene sentido
    // elegir a alguien a quien no se le debe nada. Los deshabilitados con
    // deuda igual aparecen, para poder cerrar su cuenta pendiente (6.5).
    apiGet('/trabajadores-con-deuda').then(setTrabajadores).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Cuando se elige un trabajador, consultar cuánto se le debe
  function elegirTrabajador(id) {
    setIdTrabajador(id)
    setSugerido(null)
    setMontoReal('')
    if (id === '') return

    apiGet(`/trabajadores/${id}/pago-sugerido`)
      .then((data) => {
        setSugerido(data.monto_sugerido)
        setJornadasPendientes(data.jornadas_pendientes)
        setMontoReal(data.monto_sugerido)   // autocompletar con el sugerido
      })
      .catch((e) => setMensaje(e.message))
  }

  function pagar() {
    if (idTrabajador === '' || idCuenta === '' || montoReal === '') {
      setMensaje('Elige trabajador, cuenta y monto')
      return
    }

    const montoRealNum = evaluar(montoReal)
    if (Number.isNaN(montoRealNum)) { setMensaje('El monto no es una operación válida'); return }
    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(idCuenta))
    if (cuenta && montoRealNum > cuenta.saldo) {
      setMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs y el pago es de ${montoRealNum} Bs`)
      return
    }

    apiPost('/pagos', {
      id_trabajador: parseInt(idTrabajador),
      id_cuenta: parseInt(idCuenta),
      monto_real: montoRealNum,
      fecha: fechaParaEnviar,
    })
      .then((data) => {
        setMensaje(`Pago registrado. Sugerido: ${data.sugerido}, pagado: ${data.real}`)
        setIdTrabajador('')
        setSugerido(null)
        setMontoReal('')
        setIdCuenta('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Pago a trabajadores</h2>

      <div>
        <SelectorBuscable
          opciones={trabajadores}
          valor={idTrabajador}
          onCambiar={elegirTrabajador}
          obtenerId={(t) => t.id_trabajador}
          obtenerTexto={(t) => `${t.nombre}${t.habilitado ? '' : ' (deshabilitado)'} — debe ${t.monto_sugerido} Bs`}
          placeholder="-- Trabajador --"
        />
      </div>

      {/* Cuando hay un trabajador elegido, mostrar lo que se le debe */}
      {sugerido !== null && (
        <div>
          <p>
            Jornadas pendientes: {jornadasPendientes} — 
            <strong> Se le debe: {sugerido} Bs</strong>
          </p>
          <div>
            <InputCalculo value={montoReal} onChange={setMontoReal} placeholder="Monto a pagar" decimales={2} />
            <SelectorBuscable
              opciones={cuentas.filter((c) => c.habilitado)}
              valor={idCuenta}
              onCambiar={setIdCuenta}
              obtenerId={(c) => c.id_cuenta}
              obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
              placeholder="-- Cuenta de dónde sale --"
            />
            <button onClick={pagar}>PAGAR</button>
          </div>
        </div>
      )}

      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaPagos