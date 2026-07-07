import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'

function PaginaGastos() {
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
    apiPost('/gastos', {
      id_cuenta: parseInt(idCuenta),
      monto: parseFloat(monto),
      descripcion: descripcion,
      id_grupo: idGrupo ? parseInt(idGrupo) : null,
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
        <select value={idCuenta} onChange={(e) => setIdCuenta(e.target.value)}>
          <option value="">-- Cuenta de dónde sale --</option>
          {cuentas.map((c) => (
            <option key={c.id_cuenta} value={c.id_cuenta}>
              {c.nombre} (saldo: {c.saldo})
            </option>
          ))}
        </select>
        <select value={idGrupo} onChange={(e) => setIdGrupo(e.target.value)}>
          <option value="">-- Grupo (opcional) --</option>
          {grupos.map((g) => (
            <option key={g.id_grupo} value={g.id_grupo}>{g.nombre}</option>
          ))}
        </select>
        <button onClick={registrar}>Registrar gasto</button>
      </div>
      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaGastos