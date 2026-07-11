import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'

function PaginaGastos() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [cuentas, setCuentas] = useState([])
  const [grupos, setGrupos] = useState([])

  const [idCuenta, setIdCuenta] = useState('')
  const [monto, setMonto] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [idGrupo, setIdGrupo] = useState('')
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/grupos').then(setGrupos).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrar() {
    if (idCuenta === '' || monto === '' || descripcion.trim() === '') {
      setMensaje('Completa cuenta, monto y descripción')
      return
    }

    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(idCuenta))
    if (cuenta && parseFloat(monto) > cuenta.saldo) {
      setMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs y el gasto es de ${monto} Bs`)
      return
    }

    apiPost('/gastos', {
      id_cuenta: parseInt(idCuenta),
      monto: parseFloat(monto),
      descripcion: descripcion,
      id_grupo: idGrupo ? parseInt(idGrupo) : null,
      fecha: fechaParaEnviar,
    })
      .then(() => {
        setMensaje('Gasto registrado')
        setMonto('')
        setDescripcion('')
        setIdGrupo('')
        cargar()   // recargar cuentas (el saldo cambió)
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Registrar gasto</h2>
      <div>
        <input type="text" placeholder="Descripción (en qué se gastó)"
          value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        <input type="number" placeholder="Monto"
          value={monto} onChange={(e) => setMonto(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuenta}
          onCambiar={setIdCuenta}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta de dónde sale --"
        />
        <SelectorBuscable
          opciones={grupos.filter((g) => g.habilitado)}
          valor={idGrupo}
          onCambiar={setIdGrupo}
          obtenerId={(g) => g.id_grupo}
          obtenerTexto={(g) => g.nombre}
          placeholder="-- Grupo (opcional) --"
        />
        <button onClick={registrar}>Registrar gasto</button>
      </div>
      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaGastos