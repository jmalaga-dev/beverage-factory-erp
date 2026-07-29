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

const ETIQUETA_BASE = { botellas: 'Botellas', paquetes: 'Paquetes equivalentes' }

// Formatea una diferencia con signo y color (verde suma, ámbar resta).
function Delta({ valor, decimales = 2, sufijo = '' }) {
  const v = Number(valor) || 0
  if (Math.abs(v) < 0.005) return <span style={{ color: '#888' }}>=</span>
  const color = v > 0 ? '#0a7d2c' : '#a06000'
  const signo = v > 0 ? '+' : ''
  return <span style={{ color }}>{signo}{fmtNumero(v, decimales)}{sufijo}</span>
}

function PaginaCierreSemanal() {
  const { fechaGlobal } = useFechaGlobal()
  const base = fechaGlobal || hoyISO()

  const [desde, setDesde] = useState(menosDias(base, 6))
  const [hasta, setHasta] = useState(base)
  const [baseReparto, setBaseReparto] = useState('botellas')
  const [plan, setPlan] = useState(null)
  const [mensaje, setMensaje] = useState('')

  // Carga la vista previa para una base dada (sin tocar nada en la BD).
  function cargar(b) {
    setMensaje('')
    apiGet(`/cierre-semanal/preview?desde=${desde}&hasta=${hasta}&base=${b}`)
      .then((d) => { setPlan(d); if (d.sin_datos) setMensaje(d.sin_datos) })
      .catch((e) => { setPlan(null); setMensaje(e.message) })
  }

  function verReparto() {
    cargar(baseReparto)
  }

  // Cambiar la base: si ya hay una vista cargada, la recalcula al vuelo.
  function cambiarBase(b) {
    if (b === baseReparto) return
    setBaseReparto(b)
    if (plan) cargar(b)
  }

  function confirmar() {
    apiPost('/cierre-semanal', { desde, hasta, base: baseReparto })
      .then((r) => {
        const gastos = r.gastos_repartidos
          ? `, ${r.gastos_repartidos} gasto(s) de fábrica por ${fmtMoneda(r.total_gastos)} Bs`
          : ''
        setMensaje(`Cierre hecho (base: ${ETIQUETA_BASE[baseReparto]}): ${r.lotes_cerrados} lote(s), ${r.jornadas_repartidas} jornada(s), ${fmtNumero(r.total_horas)} h, ${fmtMoneda(r.total_costo_trabajo)} Bs de trabajo${gastos}.`)
        setPlan(null)
      })
      .catch((e) => setMensaje(e.message))
  }

  const hayReparto = plan && !plan.sin_datos && plan.productos.length > 0
  const otra = baseReparto === 'botellas' ? 'paquetes' : 'botellas'
  // Gastos de fábrica del rango (bloque E). Puede haberlos aunque no haya
  // reparto posible: en ese caso quedan pendientes y hay que avisarlo.
  const gastos = plan?.gastos || []
  const gastosPendientes = plan?.gastos_pendientes || []

  return (
    <div>
      <h2>Cierre de producción (prorrateo de horas y gastos de fábrica)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Reparte las <strong>horas en standby</strong> del rango —y los{' '}
        <strong>gastos de fábrica</strong> de los grupos marcados como “Cierre prod.”
        en Catálogos— entre los productos terminados producidos (sin trabajo aún) en
        ese rango, y se los suma al costo de cada lote. El reparto se hace en
        proporción a la <strong>base</strong> elegida abajo, la misma para las horas y
        para los gastos. Las jornadas ya usadas, los lotes que ya tienen trabajo y los
        gastos ya repartidos no se tocan.
      </p>

      <div style={{ margin: '0.5rem 0' }}>
        Desde <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        {' '}Hasta <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        {' '}<button onClick={verReparto}>Ver reparto</button>
      </div>

      {/* Selector de base del reparto */}
      <div style={{ margin: '0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <span style={{ fontWeight: 'bold' }}>Base del reparto:</span>
        {['botellas', 'paquetes'].map((b) => (
          <button
            key={b}
            onClick={() => cambiarBase(b)}
            style={{
              fontWeight: baseReparto === b ? 'bold' : 'normal',
              background: baseReparto === b ? '#1d4ed8' : '#eee',
              color: baseReparto === b ? '#fff' : '#333',
              border: '1px solid #bbb', borderRadius: 4, padding: '0.25rem 0.7rem', cursor: 'pointer',
            }}
          >
            {ETIQUETA_BASE[b]}
          </button>
        ))}
        <span style={{ fontSize: '0.8em', color: '#888' }}>
          (por defecto Botellas — la mejora; Paquetes replica el prorrateo del Excel)
        </span>
      </div>

      {mensaje && <p style={{ color: hayReparto ? 'green' : '#a06000' }}>{mensaje}</p>}

      {/* Gastos de fábrica encontrados pero SIN lotes donde repartirse: no se
          pierden, los toma el próximo cierre que sí tenga producción. Se avisa
          porque si no desaparecerían en silencio. */}
      {gastosPendientes.length > 0 && (
        <div style={{ background: '#fff4e0', border: '1px solid #e0b070', padding: '0.5rem', margin: '0.5rem 0' }}>
          <strong>Hay {gastosPendientes.length} gasto(s) de fábrica en este rango sin dónde repartirse</strong>
          {' '}({fmtMoneda(gastosPendientes.reduce((s, g) => s + g.monto, 0))} Bs).
          <div style={{ fontSize: '0.85em', color: '#7a5a20' }}>
            No hay producción terminada sin trabajo asignado en el rango. Quedan
            pendientes y los tomará el próximo cierre que sí tenga producción.
          </div>
        </div>
      )}

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

          {/* Gastos de fábrica que también se reparten (bloque E) */}
          {gastos.length > 0 && (
            <>
              <h3>Gastos de fábrica a repartir</h3>
              <p style={{ fontSize: '0.82em', color: '#666', marginTop: 0 }}>
                Gastos del rango cuyo grupo está marcado como “Cierre prod.” en
                Catálogos (ej. los extras que se dan a los trabajadores). Se reparten
                entre los mismos productos y con la misma base que las horas, y se
                suman al costo del lote. Un gasto ya repartido en un cierre anterior
                no vuelve a aparecer.
              </p>
              <table border="1" style={{ borderCollapse: 'collapse' }}>
                <thead>
                  <tr><th>Mov.</th><th>Descripción</th><th>Grupo</th><th>Fecha</th><th>Monto</th></tr>
                </thead>
                <tbody>
                  {gastos.map((g) => (
                    <tr key={g.id_movimiento}>
                      <td>{g.id_movimiento}</td>
                      <td>{g.descripcion}</td>
                      <td>{g.grupo}</td>
                      <td>{g.fecha}</td>
                      <td style={{ textAlign: 'right' }}>{fmtMoneda(g.monto)}</td>
                    </tr>
                  ))}
                  <tr style={{ fontWeight: 'bold' }}>
                    <td colSpan={4}>Total</td>
                    <td style={{ textAlign: 'right' }}>{fmtMoneda(plan.total_gastos)}</td>
                  </tr>
                </tbody>
              </table>
            </>
          )}

          {/* Reparto por producto */}
          <h3>
            Reparto entre los terminados — base <span style={{ color: '#1d4ed8' }}>{ETIQUETA_BASE[baseReparto]}</span>
            {' '}({fmtNumero(plan.total_botellas)} botellas / {fmtNumero(plan.total_paquetes, 2)} paquetes)
          </h3>
          <p style={{ fontSize: '0.82em', color: '#666', marginTop: 0 }}>
            La columna <strong>“Varía vs {ETIQUETA_BASE[otra]}”</strong> muestra cuánto
            cambia el reparto de este producto respecto a la otra base (horas y Bs de
            trabajo): verde = recibe más con la base actual, ámbar = recibe menos.
          </p>
          <table border="1" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Lote</th><th>Producto</th><th>Botellas</th><th>Paquetes</th><th>%</th>
                <th>Horas asignadas</th><th>+ Trabajo</th>
                {gastos.length > 0 && <th>+ Gasto fábrica</th>}
                <th>Varía vs {ETIQUETA_BASE[otra]}</th>
                <th>Costo actual</th><th>Costo nuevo</th>
              </tr>
            </thead>
            <tbody>
              {plan.productos.map((p) => (
                <tr key={p.id_produccion}>
                  <td>{p.id_produccion}</td>
                  <td>{p.nombre}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.botellas)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.paquetes, 2)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.proporcion, 2)}%</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.horas_total, 2)} h</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(p.costo_trabajo)}</td>
                  {gastos.length > 0 && (
                    <td style={{ textAlign: 'right' }}>{fmtMoneda(p.costo_gasto)}</td>
                  )}
                  <td style={{ textAlign: 'right', fontSize: '0.85em' }}>
                    <Delta valor={p.horas_total - p.horas_total_alt} sufijo=" h" /><br />
                    <Delta valor={p.costo_trabajo - p.costo_trabajo_alt} sufijo=" Bs" />
                    {gastos.length > 0 && (
                      <><br /><Delta valor={p.costo_gasto - p.costo_gasto_alt} sufijo=" Bs gasto" /></>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(p.costo_unit_actual, 4)}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{fmtNumero(p.costo_unit_nuevo, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p style={{ marginTop: '0.6rem' }}>
            <button onClick={confirmar} style={{ fontWeight: 'bold' }}>
              CONFIRMAR CIERRE (base {ETIQUETA_BASE[baseReparto]})
            </button>
            {' '}<span style={{ fontSize: '0.85em', color: '#888' }}>
              (esto asigna el trabajo con la base seleccionada y actualiza los costos; no se puede deshacer solo)
            </span>
          </p>
        </>
      )}
    </div>
  )
}

export default PaginaCierreSemanal
