import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { apiGet } from '../api'
import { fmtMoneda } from '../formato'

const ROLES = { FABRICA: 'Fábrica', CASA: 'Casa', OTRA: 'Otra' }

// Panel de saldos por cuenta (item 6), desplegable bajo la fecha global en
// TODAS las pantallas: responde de un vistazo "cuanto tengo en cada
// billetera/banco" sin ir a Catalogos. Cero backend nuevo: /cuentas ya trae
// nombre, rol, saldo y habilitado; fmtMoneda ya da el formato pedido
// (miles con punto, 2 decimales con coma).
function PanelSaldos() {
  const location = useLocation()
  const [abierto, setAbierto] = useState(() => localStorage.getItem('panelSaldosAbierto') === '1')
  const [cuentas, setCuentas] = useState([])
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  function cargar() {
    setCargando(true)
    apiGet('/cuentas')
      .then((d) => { setCuentas(d); setError('') })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false))
  }

  // Un saldo viejo es peor que ninguno: se recarga al entrar, al abrir el
  // panel y al cambiar de pantalla (una pantalla que mueve plata pudo
  // cambiarlo). El costo es una consulta liviana a una tabla chica.
  useEffect(() => { cargar() }, [location.pathname])
  useEffect(() => { if (abierto) cargar() }, [abierto])

  function alternar() {
    const nuevo = !abierto
    setAbierto(nuevo)
    localStorage.setItem('panelSaldosAbierto', nuevo ? '1' : '0')
  }

  const habilitadas = cuentas.filter((c) => c.habilitado)
  const total = habilitadas.reduce((s, c) => s + c.saldo, 0)

  return (
    <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
      <button onClick={alternar} style={{
        background: 'none', border: 'none', font: 'inherit', cursor: 'pointer',
        color: 'var(--accent)', fontSize: '0.9em',
      }}>
        {abierto ? '▾' : '▸'} Saldos por cuenta
      </button>

      {abierto && (
        <div style={{ display: 'inline-block', marginTop: '0.3rem', textAlign: 'left' }}>
          {error && <p style={{ color: '#a00', fontSize: '0.85em' }}>{error}</p>}
          {!error && (
            <table border="1" style={{ borderCollapse: 'collapse', fontSize: '0.9em' }}>
              <thead>
                <tr><th>Cuenta</th><th>Rol</th><th>Saldo</th></tr>
              </thead>
              <tbody>
                {habilitadas.map((c) => (
                  <tr key={c.id_cuenta}>
                    <td style={{ padding: '2px 8px' }}>{c.nombre}</td>
                    <td style={{ padding: '2px 8px' }}>{ROLES[c.rol] || c.rol}</td>
                    <td style={{ padding: '2px 8px', textAlign: 'right' }}>{fmtMoneda(c.saldo)}</td>
                  </tr>
                ))}
                {habilitadas.length === 0 && (
                  <tr><td colSpan={3} style={{ padding: '2px 8px' }}>Sin cuentas habilitadas</td></tr>
                )}
                <tr style={{ fontWeight: 'bold' }}>
                  <td style={{ padding: '2px 8px' }} colSpan={2}>Total</td>
                  <td style={{ padding: '2px 8px', textAlign: 'right' }}>{fmtMoneda(total)}</td>
                </tr>
              </tbody>
            </table>
          )}
          <button onClick={cargar} disabled={cargando} style={{ fontSize: '0.8em', marginTop: '0.2rem' }}>
            {cargando ? 'Actualizando…' : '↻ Actualizar'}
          </button>
        </div>
      )}
    </div>
  )
}

export default PanelSaldos
