import { useState } from 'react'
import { apiGet, apiPost } from '../api'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero, fmtMoneda } from '../formato'

// Fecha de hoy en formato YYYY-MM-DD (local), para los inputs de fecha.
function hoyISO() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
function menosDias(iso, dias) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() - dias)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

function PaginaCierreSemanal() {
  const { fechaGlobal } = useFechaGlobal()
  const base = fechaGlobal || hoyISO()

  const [desde, setDesde] = useState(menosDias(base, 6))
  const [hasta, setHasta] = useState(base)
  const [plan, setPlan] = useState(null)
  const [mensaje, setMensaje] = useState('')

  function verReparto() {
    setMensaje('')
    apiGet(`/cierre-semanal/preview?desde=${desde}&hasta=${hasta}`)
      .then((d) => { setPlan(d); if (d.sin_datos) setMensaje(d.sin_datos) })
      .catch((e) => { setPlan(null); setMensaje(e.message) })
  }

  function confirmar() {
    apiPost('/cierre-semanal', { desde, hasta })
      .then((r) => {
        setMensaje(`Cierre hecho: ${r.lotes_cerrados} lote(s), ${r.jornadas_repartidas} jornada(s), ${fmtNumero(r.total_horas)} h, ${fmtMoneda(r.total_costo_trabajo)} Bs de trabajo repartidos.`)
        setPlan(null)
      })
      .catch((e) => setMensaje(e.message))
  }

  const hayReparto = plan && !plan.sin_datos && plan.productos.length > 0

  return (
    <div>
      <h2>Cierre de producción (prorrateo de horas)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Reparte las <strong>horas en standby</strong> del rango entre los productos
        terminados producidos (sin trabajo aún) en ese rango, en proporción a sus
        <strong> botellas producidas</strong>, y le suma a cada lote su costo de
        trabajo. Las jornadas ya usadas y los lotes que ya tienen trabajo no se tocan.
      </p>

      <div style={{ margin: '0.5rem 0' }}>
        Desde <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        {' '}Hasta <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        {' '}<button onClick={verReparto}>Ver reparto</button>
      </div>

      {mensaje && <p style={{ color: hayReparto ? 'green' : '#a06000' }}>{mensaje}</p>}

      {hayReparto && (
        <>
          {/* Jornadas en standby que se van a repartir */}
          <h3>Horas en standby a repartir</h3>
          <table border="1" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr><th>Jornada</th><th>Trabajador</th><th>Fecha</th><th>Horas</th><th>Tarifa</th><th>Valor</th></tr>
            </thead>
            <tbody>
              {plan.jornadas.map((j) => (
                <tr key={j.id_jornada}>
                  <td>{j.id_jornada}</td><td>{j.nombre_trabajador}</td><td>{j.fecha}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(j.horas)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(j.tarifa)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(j.valor)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 'bold' }}>
                <td colSpan={3}>Total</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(plan.total_horas)}</td>
                <td></td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(plan.total_valor_trabajo)}</td>
              </tr>
            </tbody>
          </table>

          {/* Reparto por producto */}
          <h3>Reparto entre los terminados ({fmtNumero(plan.total_botellas)} botellas)</h3>
          <table border="1" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Lote</th><th>Producto</th><th>Botellas</th><th>%</th>
                <th>Horas asignadas</th><th>Costo actual</th><th>+ Trabajo</th><th>Costo nuevo</th>
              </tr>
            </thead>
            <tbody>
              {plan.productos.map((p) => (
                <tr key={p.id_produccion}>
                  <td>{p.id_produccion}</td>
                  <td>{p.nombre}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.botellas)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.proporcion, 2)}%</td>
                  <td style={{ fontSize: '0.85em' }}>
                    {p.asignaciones.map((a, i) => (
                      <span key={i}>{a.nombre_trabajador}: {fmtNumero(a.horas)}h{i < p.asignaciones.length - 1 ? ', ' : ''}</span>
                    ))}
                  </td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.costo_unit_actual, 4)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(p.costo_trabajo)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{fmtNumero(p.costo_unit_nuevo, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p style={{ marginTop: '0.6rem' }}>
            <button onClick={confirmar} style={{ fontWeight: 'bold' }}>CONFIRMAR CIERRE</button>
            {' '}<span style={{ fontSize: '0.85em', color: '#888' }}>
              (esto asigna el trabajo y actualiza los costos; no se puede deshacer solo)
            </span>
          </p>
        </>
      )}
    </div>
  )
}

export default PaginaCierreSemanal
