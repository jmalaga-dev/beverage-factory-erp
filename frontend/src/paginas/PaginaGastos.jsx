import { useState, useEffect } from 'react'

function PaginaGastos() {
  const [cuentas, setCuentas] = useState([])
  const [grupos, setGrupos] = useState([])

  const [idCuenta, setIdCuenta] = useState('')
  const [monto, setMonto] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [idGrupo, setIdGrupo] = useState('')
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    fetch('http://127.0.0.1:8000/cuentas')
      .then((r) => r.json()).then(setCuentas).catch(console.error)
    fetch('http://127.0.0.1:8000/grupos')
      .then((r) => r.json()).then(setGrupos).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function registrar() {
    if (idCuenta === '' || monto === '' || descripcion.trim() === '') {
      setMensaje('Completa cuenta, monto y descripción')
      return
    }
    fetch('http://127.0.0.1:8000/gastos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id_cuenta: parseInt(idCuenta),
        monto: parseFloat(monto),
        descripcion: descripcion,
        id_grupo: idGrupo ? parseInt(idGrupo) : null,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
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