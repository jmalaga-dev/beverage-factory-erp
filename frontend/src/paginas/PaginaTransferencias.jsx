import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'

function PaginaTransferencias() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [cuentas, setCuentas] = useState([])

  // Transferencia entre cuentas propias
  const [idOrigen, setIdOrigen] = useState('')
  const [idDestino, setIdDestino] = useState('')
  const [montoTransferencia, setMontoTransferencia] = useState('')
  const [descripcionTransferencia, setDescripcionTransferencia] = useState('')
  const [mensajeTransferencia, setMensajeTransferencia] = useState('')

  // Ingreso externo
  const [idCuentaIngreso, setIdCuentaIngreso] = useState('')
  const [montoIngreso, setMontoIngreso] = useState('')
  const [descripcionIngreso, setDescripcionIngreso] = useState('')
  const [mensajeIngreso, setMensajeIngreso] = useState('')

  function cargar() {
    apiGet('/cuentas').then(setCuentas).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrarTransferencia() {
    if (idOrigen === '' || idDestino === '' || montoTransferencia === '' || descripcionTransferencia.trim() === '') {
      setMensajeTransferencia('Completa cuenta origen, destino, monto y descripción')
      return
    }
    if (idOrigen === idDestino) {
      setMensajeTransferencia('La cuenta de origen y destino no pueden ser la misma')
      return
    }

    const origen = cuentas.find((c) => c.id_cuenta === parseInt(idOrigen))
    if (origen && parseFloat(montoTransferencia) > origen.saldo) {
      setMensajeTransferencia(`Saldo insuficiente: la cuenta tiene ${origen.saldo} Bs y la transferencia es de ${montoTransferencia} Bs`)
      return
    }

    apiPost('/transferencias', {
      id_cuenta_origen: parseInt(idOrigen),
      id_cuenta_destino: parseInt(idDestino),
      monto: parseFloat(montoTransferencia),
      descripcion: descripcionTransferencia,
      fecha: fechaParaEnviar,
    })
      .then(() => {
        setMensajeTransferencia('Transferencia registrada')
        setMontoTransferencia('')
        setDescripcionTransferencia('')
        cargar()
      })
      .catch((e) => setMensajeTransferencia(e.message))
  }

  function registrarIngresoExterno() {
    if (idCuentaIngreso === '' || montoIngreso === '' || descripcionIngreso.trim() === '') {
      setMensajeIngreso('Completa cuenta, monto y descripción')
      return
    }

    apiPost('/ingresos-externos', {
      id_cuenta_destino: parseInt(idCuentaIngreso),
      monto: parseFloat(montoIngreso),
      descripcion: descripcionIngreso,
      fecha: fechaParaEnviar,
    })
      .then(() => {
        setMensajeIngreso('Ingreso externo registrado')
        setMontoIngreso('')
        setDescripcionIngreso('')
        cargar()
      })
      .catch((e) => setMensajeIngreso(e.message))
  }

  return (
    <div>
      <h2>Transferencias e ingresos externos</h2>

      <h3>Transferir entre cuentas propias</h3>
      <div>
        <input type="text" placeholder="Descripción"
          value={descripcionTransferencia} onChange={(e) => setDescripcionTransferencia(e.target.value)} />
        <input type="number" placeholder="Monto"
          value={montoTransferencia} onChange={(e) => setMontoTransferencia(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idOrigen}
          onCambiar={setIdOrigen}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta de dónde sale --"
        />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idDestino}
          onCambiar={setIdDestino}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta a dónde entra --"
        />
        <button onClick={registrarTransferencia}>Transferir</button>
      </div>
      {mensajeTransferencia && <p>{mensajeTransferencia}</p>}

      <h3>Ingreso externo (aporte de fuera de la fábrica)</h3>
      <div>
        <input type="text" placeholder="Descripción (de dónde viene)"
          value={descripcionIngreso} onChange={(e) => setDescripcionIngreso(e.target.value)} />
        <input type="number" placeholder="Monto"
          value={montoIngreso} onChange={(e) => setMontoIngreso(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuentaIngreso}
          onCambiar={setIdCuentaIngreso}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta a dónde entra --"
        />
        <button onClick={registrarIngresoExterno}>Registrar ingreso</button>
      </div>
      {mensajeIngreso && <p>{mensajeIngreso}</p>}
    </div>
  )
}

export default PaginaTransferencias
