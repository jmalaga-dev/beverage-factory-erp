import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtMoneda } from '../formato'

// Reparto de un gasto por prioridad de cuentas (mejora 2.B): el sistema propone
// de qué cuentas sacar el gasto según el tipo (familiar → Casa primero; de
// fábrica → Fábrica primero), el usuario ajusta, y se registra como varios
// movimientos SALIDA coordinados.
function PaginaRepartoGasto() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [grupos, setGrupos] = useState([])

  const [descripcion, setDescripcion] = useState('')
  const [monto, setMonto] = useState('')
  const [tipo, setTipo] = useState('FAMILIAR')
  const [idGrupo, setIdGrupo] = useState('')
  const [fuentes, setFuentes] = useState(null)   // propuesta editable
  const [mensaje, setMensaje] = useState('')

  useEffect(() => { apiGet('/grupos').then(setGrupos).catch(console.error) }, [])

  function proponer() {
    if (monto === '' || parseFloat(monto) <= 0) { setMensaje('Indica el monto del gasto'); return }
    apiGet(`/reparto/preview?monto=${parseFloat(monto)}&tipo=${tipo}`)
      .then((d) => {
        setFuentes(d.fuentes)
        setMensaje(d.cubierto ? '' : `Ojo: las cuentas no alcanzan, faltan ${fmtMoneda(d.faltante)} Bs`)
      })
      .catch((e) => setMensaje(e.message))
  }

  function cambiarUtilizado(i, valor) {
    setFuentes(fuentes.map((f, idx) => (idx === i ? { ...f, utilizado: parseFloat(valor) || 0 } : f)))
  }

  const sumaUtilizado = fuentes ? fuentes.reduce((s, f) => s + f.utilizado, 0) : 0
  const montoNum = parseFloat(monto) || 0
  const cuadra = fuentes && Math.abs(sumaUtilizado - montoNum) < 0.01 && montoNum > 0

  function registrar() {
    if (descripcion.trim() === '') { setMensaje('Indica la descripción del gasto'); return }
    if (!cuadra) { setMensaje(`La suma de las fuentes (${fmtMoneda(sumaUtilizado)}) debe igualar el monto (${fmtMoneda(montoNum)})`); return }
    const fuentesUsadas = fuentes.filter((f) => f.utilizado > 0).map((f) => ({ id_cuenta: f.id_cuenta, monto: f.utilizado }))
    apiPost('/reparto-gasto', {
      descripcion: descripcion,
      fuentes: fuentesUsadas,
      id_grupo: idGrupo ? parseInt(idGrupo) : null,
      fecha: fechaParaEnviar,
    })
      .then((d) => {
        setMensaje(`Gasto registrado: ${d.movimientos} movimiento(s), total ${fmtMoneda(d.total)} Bs`)
        setDescripcion(''); setMonto(''); setIdGrupo(''); setFuentes(null)
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Gasto por prioridad de cuentas</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        El sistema propone de qué cuentas sacar el gasto según su tipo (familiar
        → primero Casa; de fábrica → primero Fábrica), respetando saldos y
        partiendo entre cuentas si la primera no alcanza. Podés ajustar cuánto
        sale de cada una antes de confirmar.
      </p>

      <div style={{ margin: '0.5rem 0' }}>
        <input type="text" placeholder="Descripción (en qué se gastó)"
          value={descripcion} onChange={(e) => setDescripcion(e.target.value)} style={{ width: '16rem' }} />
        <input type="number" placeholder="Monto total"
          value={monto} onChange={(e) => { setMonto(e.target.value); setFuentes(null) }} style={{ width: '9rem' }} />
        <select value={tipo} onChange={(e) => { setTipo(e.target.value); setFuentes(null) }}>
          <option value="FAMILIAR">Gasto familiar (Casa → Fábrica)</option>
          <option value="FABRICA">Gasto de fábrica (Fábrica → Casa)</option>
        </select>
        <SelectorBuscable
          opciones={grupos.filter((g) => g.habilitado)}
          valor={idGrupo}
          onCambiar={setIdGrupo}
          obtenerId={(g) => g.id_grupo}
          obtenerTexto={(g) => g.nombre}
          placeholder="-- Grupo (opcional) --"
        />
        <button onClick={proponer}>Proponer reparto</button>
      </div>

      {fuentes && (
        <>
          <table border="1" style={{ borderCollapse: 'collapse', marginTop: '0.5rem' }}>
            <thead>
              <tr><th>Cuenta</th><th>Rol</th><th>Disponible</th><th>A usar</th></tr>
            </thead>
            <tbody>
              {fuentes.map((f, i) => (
                <tr key={f.id_cuenta} style={f.utilizado > f.disponible ? { color: 'red' } : undefined}>
                  <td>{f.nombre}</td>
                  <td>{f.rol}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(f.disponible)}</td>
                  <td style={{ textAlign: 'right' }}>
                    <input type="number" value={f.utilizado}
                      onChange={(e) => cambiarUtilizado(i, e.target.value)}
                      style={{ width: '6.5rem', textAlign: 'right' }} />
                  </td>
                </tr>
              ))}
              <tr style={{ fontWeight: 'bold', color: cuadra ? 'green' : '#a06000' }}>
                <td colSpan={3}>Suma a usar (debe igualar {fmtMoneda(montoNum)})</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(sumaUtilizado)}</td>
              </tr>
            </tbody>
          </table>

          <p style={{ marginTop: '0.6rem' }}>
            <button onClick={registrar} disabled={!cuadra}>REGISTRAR GASTO</button>
          </p>
        </>
      )}

      {mensaje && <p>{mensaje}</p>}
    </div>
  )
}

export default PaginaRepartoGasto
