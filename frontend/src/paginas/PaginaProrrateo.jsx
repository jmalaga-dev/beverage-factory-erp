import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero, fmtMoneda } from '../formato'

// Mes actual en formato YYYY-MM (local).
function mesActual() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 7)
}

function PaginaProrrateo() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [anioMes, setAnioMes] = useState(mesActual())
  const [recurrentes, setRecurrentes] = useState([])   // gastos extra recurrentes (catalogo)
  const [estado, setEstado] = useState(null)           // gastos del mes + estado de pago
  const [preview, setPreview] = useState(null)         // reparto del mes
  const [cuentas, setCuentas] = useState([])

  // Alta de un monto del mes
  const [selGasto, setSelGasto] = useState('')
  const [monto, setMonto] = useState('')
  // Pago: cuenta elegida por fila
  const [cuentaPago, setCuentaPago] = useState({})     // {id_gasto_extra_mes: id_cuenta}
  const [mensaje, setMensaje] = useState('')

  function cargar(mes) {
    if (!mes || mes.trim() === '') return
    apiGet('/gastos-extra').then((g) => setRecurrentes(g.filter((x) => x.habilitado))).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet(`/gastos-mes/${mes}`).then(setEstado).catch((e) => setMensaje(e.message))
    apiGet(`/prorrateo/preview/${mes}`).then(setPreview).catch((e) => setMensaje(e.message))
  }

  // Cargar el mes actual al entrar a la pantalla: sin esto, "cargar" solo se
  // disparaba al tocar el selector de mes, y julio (el mes por defecto de
  // mesActual()) quedaba sin gastos visibles hasta cambiar de mes y volver.
  useEffect(() => { cargar(anioMes) }, [])

  function cambiarMes(mes) { setAnioMes(mes); setMensaje(''); cargar(mes) }

  function agregarMonto() {
    if (selGasto === '' || monto === '') { setMensaje('Elige el gasto y su monto del mes'); return }
    apiPost('/gastos-mes', { id_gasto_extra: parseInt(selGasto), anio_mes: anioMes, monto: parseFloat(monto) })
      .then(() => { setSelGasto(''); setMonto(''); setMensaje(''); cargar(anioMes) })
      .catch((e) => setMensaje(e.message))
  }

  function pagar(idGastoMes) {
    const idCuenta = cuentaPago[idGastoMes]
    if (!idCuenta) { setMensaje('Elige la cuenta para pagar ese gasto'); return }
    apiPost(`/gastos-mes/${idGastoMes}/pagar`, { id_cuenta: parseInt(idCuenta), fecha: fechaParaEnviar })
      .then(() => { setMensaje('Gasto pagado'); cargar(anioMes) })
      .catch((e) => setMensaje(e.message))
  }

  function ejecutar() {
    apiPost('/prorrateos', { anio_mes: anioMes })
      .then((d) => { setMensaje(`Prorrateo hecho: ${d.asignaciones} asignaciones (${d.productos} productos × ${d.gastos} gastos)`); cargar(anioMes) })
      .catch((e) => setMensaje(e.message))
  }

  // Sugerir el monto típico del gasto elegido
  function elegirGasto(id) {
    setSelGasto(id)
    const g = recurrentes.find((x) => x.id_gasto_extra === parseInt(id))
    if (g && g.precio_mensual) setMonto(String(g.precio_mensual))
  }

  return (
    <div>
      <h2>Cierre de mes — prorrateo de gastos</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Registra el monto real de cada gasto del mes (luz, agua…), págalos, y
        reparte el total entre los productos según las <strong>horas-hombre</strong>
        {' '}(directas + heredadas) que cada uno consumió ese mes. Solo se puede
        prorratear cuando todos los gastos del mes están pagados.
      </p>

      <div style={{ margin: '0.5rem 0' }}>
        Mes <input type="month" value={anioMes} onChange={(e) => cambiarMes(e.target.value)} />
      </div>

      {mensaje && <p style={{ color: '#a06000' }}>{mensaje}</p>}

      {/* ===== Gastos del mes ===== */}
      <h3>Gastos del mes</h3>
      <div style={{ margin: '0.4rem 0' }}>
        <SelectorBuscable
          opciones={recurrentes}
          valor={selGasto}
          onCambiar={elegirGasto}
          obtenerId={(g) => g.id_gasto_extra}
          obtenerTexto={(g) => `${g.descripcion} (típico ${fmtMoneda(g.precio_mensual)} Bs)`}
          placeholder="-- Gasto recurrente --"
        />
        <input type="number" placeholder="Monto de este mes" value={monto} onChange={(e) => setMonto(e.target.value)} />
        <button onClick={agregarMonto}>Guardar monto</button>
      </div>

      {estado && estado.detalle.length > 0 ? (
        <table border="1" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr><th>Gasto</th><th>Monto</th><th>Estado</th><th>Pago</th></tr>
          </thead>
          <tbody>
            {estado.detalle.map((g) => (
              <tr key={g.id_gasto_extra_mes}>
                <td>{g.descripcion}</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(g.monto)}</td>
                <td>{g.pagado ? `✅ pagado (${g.fecha_pago}, ${g.cuenta_pago})` : '⏳ pendiente'}</td>
                <td>
                  {!g.pagado && (
                    <>
                      <SelectorBuscable
                        opciones={cuentas.filter((c) => c.habilitado)}
                        valor={cuentaPago[g.id_gasto_extra_mes] || ''}
                        onCambiar={(v) => setCuentaPago({ ...cuentaPago, [g.id_gasto_extra_mes]: v })}
                        obtenerId={(c) => c.id_cuenta}
                        obtenerTexto={(c) => `${c.nombre} (${fmtMoneda(c.saldo)})`}
                        placeholder="-- Cuenta --"
                      />
                      {' '}<button onClick={() => pagar(g.id_gasto_extra_mes)}>Pagar</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            <tr style={{ fontWeight: 'bold' }}>
              <td>Total</td><td style={{ textAlign: 'right' }}>{fmtMoneda(estado.total)}</td>
              <td colSpan={2}>{estado.pagados}/{estado.cantidad} pagados</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#888' }}>Aún no registraste gastos para este mes.</p>
      )}

      {/* ===== Prorrateo ===== */}
      <h3>Reparto entre productos (por horas-hombre)</h3>
      {preview && (
        <>
          {preview.productos.length > 0 ? (
            <table border="1" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr><th>Producto</th><th>Horas del mes</th><th>%</th><th>Gasto asignado</th></tr>
              </thead>
              <tbody>
                {preview.productos.map((p) => (
                  <tr key={p.id_producto}>
                    <td>{p.nombre}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNumero(p.horas, 2)}</td>
                    <td style={{ textAlign: 'right' }}>{fmtNumero(p.fraccion, 2)}%</td>
                    <td style={{ textAlign: 'right' }}>{fmtMoneda(p.asignado_total)}</td>
                  </tr>
                ))}
                <tr style={{ fontWeight: 'bold' }}>
                  <td>Total</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(preview.total_horas, 2)}</td>
                  <td></td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(preview.total_gastos)}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p style={{ color: '#888' }}>No hay producción con horas registrada ese mes.</p>
          )}

          <p style={{ marginTop: '0.6rem' }}>
            {preview.ya_prorrateado ? (
              <span style={{ color: 'green' }}>✅ Este mes ya fue prorrateado.</span>
            ) : preview.puede ? (
              <button onClick={ejecutar} style={{ fontWeight: 'bold' }}>EJECUTAR PRORRATEO</button>
            ) : (
              <span style={{ color: '#a06000' }}>No se puede prorratear todavía: {preview.motivo}</span>
            )}
          </p>
        </>
      )}
    </div>
  )
}

export default PaginaProrrateo
