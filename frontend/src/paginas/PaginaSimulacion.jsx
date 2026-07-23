import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import InputCalculo from '../componentes/InputCalculo'
import { fmtMoneda, fmtNumero } from '../formato'
import { evaluar } from '../calculo'

// Simulacion de producto nuevo (mejora 1.5). Pantalla de SOLO LECTURA: arma
// una receta hipotetica y muestra su costo en 3 escenarios segun el historico
// real de cada insumo. No registra nada, no toca stock ni dinero.
function PaginaSimulacion() {
  const [materias, setMaterias] = useState([])
  const [intermedios, setIntermedios] = useState([])

  // Receta hipotetica
  const [insumos, setInsumos] = useState([])   // [{tipo, id_insumo, cantidad, nombre}]
  const [insTipo, setInsTipo] = useState('MP')
  const [insId, setInsId] = useState('')
  const [insCantidad, setInsCantidad] = useState('')

  const [rendimiento, setRendimiento] = useState('')
  const [litrosPorBotella, setLitrosPorBotella] = useState('0.75')
  const [botellasPorPaquete, setBotellasPorPaquete] = useState('6')
  const [meses, setMeses] = useState('12')

  const [resultado, setResultado] = useState(null)
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    apiGet('/materias-primas').then(setMaterias).catch(console.error)
    apiGet('/productos-intermedios').then(setIntermedios).catch(console.error)
  }, [])

  const opciones = insTipo === 'MP'
    ? materias.filter((m) => m.habilitado)
    : intermedios.filter((p) => p.habilitado)
  const obtenerId = insTipo === 'MP'
    ? ((m) => m.id_materia_prima)
    : ((p) => p.id_producto_intermedio)

  function agregarInsumo() {
    const cantNum = evaluar(insCantidad)
    if (insId === '' || insCantidad === '' || Number.isNaN(cantNum) || cantNum <= 0) {
      setMensaje('Elige un insumo y una cantidad mayor a cero')
      return
    }
    const op = opciones.find((o) => String(obtenerId(o)) === String(insId))
    setInsumos([...insumos, {
      tipo: insTipo,
      id_insumo: parseInt(insId),
      cantidad: cantNum,
      nombre: op ? op.descripcion : `#${insId}`,
    }])
    setInsId(''); setInsCantidad(''); setMensaje('')
  }

  function quitarInsumo(i) { setInsumos(insumos.filter((_, idx) => idx !== i)) }

  function simular() {
    if (insumos.length === 0) { setMensaje('Agrega al menos un insumo'); return }
    const rendimientoNum = evaluar(rendimiento)
    if (rendimiento === '' || Number.isNaN(rendimientoNum) || rendimientoNum <= 0) {
      setMensaje('Indica cuánto rinde la receta'); return
    }
    apiPost('/simulacion', {
      insumos: insumos.map((i) => ({ tipo: i.tipo, id_insumo: i.id_insumo, cantidad: i.cantidad })),
      rendimiento: rendimientoNum,
      litros_por_botella: litrosPorBotella === '' ? null : parseFloat(litrosPorBotella),
      botellas_por_paquete: parseInt(botellasPorPaquete) || 1,
      meses: parseInt(meses),
    })
      .then((d) => { setResultado(d); setMensaje('') })
      .catch((e) => { setResultado(null); setMensaje(e.message) })
  }

  // Re-simular al cambiar la ventana, si ya hay un resultado en pantalla:
  // el punto de la ventana configurable es ver cómo se mueven los escenarios.
  useEffect(() => {
    if (resultado) simular()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meses])

  const esc = resultado ? resultado.escenarios : null
  const ref = resultado ? resultado.referencia : null

  const columnas = [
    ['barato', 'Más barato', '#e8f5e9'],
    ['promedio', 'Promedio ponderado', '#e3f2fd'],
    ['caro', 'Más caro', '#fdecea'],
  ]

  return (
    <div>
      <h2>Simulación de producto nuevo</h2>
      <p style={{ fontSize: '0.9em', color: '#666' }}>
        Arma una receta hipotética y calcula su costo con los precios reales de
        tu historial, en tres escenarios. <strong>No registra nada</strong>: no
        toca stock ni dinero.
      </p>

      {/* --- Receta hipotética --- */}
      <h3>1. Insumos de la receta</h3>
      <div>
        <select value={insTipo} onChange={(e) => { setInsTipo(e.target.value); setInsId('') }}>
          <option value="MP">Materia prima</option>
          <option value="INTERMEDIO">Producto intermedio</option>
        </select>
        <SelectorBuscable
          opciones={opciones}
          valor={insId}
          onCambiar={setInsId}
          obtenerId={obtenerId}
          obtenerTexto={(o) => o.descripcion}
          placeholder={insTipo === 'MP' ? '-- Materia prima --' : '-- Producto intermedio --'}
        />
        <InputCalculo value={insCantidad} onChange={setInsCantidad} placeholder="Cantidad" />
        <button onClick={agregarInsumo}>Agregar insumo</button>
      </div>

      {insumos.length > 0 && (
        <table border="1" style={{ marginTop: '0.5rem' }}>
          <thead><tr><th>Tipo</th><th>Insumo</th><th>Cantidad</th><th></th></tr></thead>
          <tbody>
            {insumos.map((i, idx) => (
              <tr key={idx}>
                <td>{i.tipo === 'MP' ? 'Materia prima' : 'Intermedio'}</td>
                <td>{i.nombre}</td>
                <td style={{ textAlign: 'right' }}>{fmtNumero(i.cantidad)}</td>
                <td><button onClick={() => quitarInsumo(idx)}>quitar</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* --- Rendimiento y presentación --- */}
      <h3>2. Cuánto rinde y en qué se envasa</h3>
      <div>
        <label>Rinde:{' '}
          <InputCalculo value={rendimiento} onChange={setRendimiento} placeholder="ej. 30" width="6rem" />
        </label>{' '}
        <label>Litros por botella:{' '}
          <input type="number" step="0.01" style={{ width: '5rem' }}
            value={litrosPorBotella} onChange={(e) => setLitrosPorBotella(e.target.value)} />
        </label>{' '}
        <label>Botellas por paquete:{' '}
          <input type="number" style={{ width: '4rem' }}
            value={botellasPorPaquete} onChange={(e) => setBotellasPorPaquete(e.target.value)} />
        </label>
      </div>

      {/* --- Ventana de tiempo --- */}
      <h3>3. Qué historial mirar</h3>
      <div>
        <label>Últimos{' '}
          <input type="number" style={{ width: '4rem' }}
            value={meses} onChange={(e) => setMeses(e.target.value)} /> meses
        </label>
        <span style={{ marginLeft: '0.5rem', color: '#557', fontSize: '0.85em' }}>
          (0 = todo el historial. Ojo: con muchos años, el escenario "más
          barato" puede venir de un precio que ya no existe.)
        </span>
      </div>

      <p><button onClick={simular}>SIMULAR</button></p>
      {mensaje && <p style={{ color: '#a00' }}>{mensaje}</p>}

      {resultado && (
        <>
          {resultado.incompleto && (
            <p style={{ color: '#a06000' }}>
              ⚠ Hay insumos sin historial: el total no los incluye y se queda corto.
            </p>
          )}

          <h3>Precio de cada insumo en la ventana</h3>
          <p style={{ fontSize: '0.85em', color: '#666' }}>
            Ventana: {resultado.ventana.desde || 'todo el historial'} a {resultado.ventana.hasta}.
            El promedio es <strong>ponderado por cantidad</strong> (Bs totales ÷ cantidad total),
            no un promedio simple de precios.
          </p>
          <table border="1">
            <thead>
              <tr>
                <th>Insumo</th><th>Cant.</th><th>Veces</th>
                <th>Más barato</th><th>Promedio</th><th>Más caro</th><th>Aviso</th>
              </tr>
            </thead>
            <tbody>
              {resultado.insumos.map((i, idx) => (
                <tr key={idx}>
                  <td>{i.nombre}{i.unidad ? ` (${i.unidad})` : ''}</td>
                  <td style={{ textAlign: 'right' }}>{fmtNumero(i.cantidad)}</td>
                  <td style={{ textAlign: 'right' }}>{i.n}</td>
                  <td style={{ textAlign: 'right' }}>{i.barato == null ? '—' : fmtMoneda(i.barato)}</td>
                  <td style={{ textAlign: 'right' }}>{i.promedio == null ? '—' : fmtMoneda(i.promedio)}</td>
                  <td style={{ textAlign: 'right' }}>{i.caro == null ? '—' : fmtMoneda(i.caro)}</td>
                  <td style={{ fontSize: '0.85em', color: '#a06000' }}>{i.aviso || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Costo en los 3 escenarios</h3>
          <p style={{ fontSize: '0.85em', color: '#666' }}>
            {fmtNumero(resultado.rendimiento)} de producto
            {resultado.botellas_resultantes != null &&
              ` = ${fmtNumero(resultado.botellas_resultantes)} botellas de ${resultado.litros_por_botella} L`}
            {resultado.botellas_resultantes != null &&
              ` (paquete de ${resultado.botellas_por_paquete})`}
          </p>
          <table border="1" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Escenario</th><th>Costo total</th><th>Por unidad</th>
                <th>Por botella</th><th>Por paquete</th>
              </tr>
            </thead>
            <tbody>
              {columnas.map(([clave, titulo, fondo]) => (
                <tr key={clave} style={{ background: fondo }}>
                  <td><strong>{titulo}</strong></td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(esc[clave].costo_total)}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(esc[clave].por_unidad)}</td>
                  <td style={{ textAlign: 'right' }}>
                    {esc[clave].por_botella == null ? '—' : fmtMoneda(esc[clave].por_botella)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {esc[clave].por_paquete == null ? '—' : fmtMoneda(esc[clave].por_paquete)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* --- Carga fija que estos escenarios NO incluyen --- */}
          <h3>Lo que estos números todavía no incluyen</h3>
          <p style={{ fontSize: '0.85em', color: '#666' }}>
            Arriba solo están los <strong>insumos</strong>. Estos tres promedios
            salen de tu historial real (Bs totales ÷ botellas producidas en la
            misma ventana) y son lo que carga una botella cualquiera de la
            fábrica. Son de referencia: no se pueden editar.
          </p>
          <table border="1">
            <tbody>
              <tr><td>Mano de obra</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(ref.mano_obra)} Bs/botella</td></tr>
              <tr><td>Absorción (utensilios, feriados, mermas)</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(ref.absorcion)} Bs/botella</td></tr>
              <tr><td>Gastos extra (luz, agua, internet...)</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(ref.gastos_extra)} Bs/botella</td></tr>
              <tr style={{ fontWeight: 'bold' }}><td>Carga fija total</td>
                <td style={{ textAlign: 'right' }}>{fmtMoneda(ref.total)} Bs/botella</td></tr>
            </tbody>
          </table>
          <p style={{ fontSize: '0.8em', color: '#888' }}>
            Calculado sobre {fmtNumero(ref.botellas_periodo)} botellas producidas en la ventana.
          </p>

          <h3>Costo con carga completa</h3>
          <table border="1" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr><th>Escenario</th><th>Por botella</th><th>Por paquete</th></tr>
            </thead>
            <tbody>
              {columnas.map(([clave, titulo, fondo]) => (
                <tr key={clave} style={{ background: fondo }}>
                  <td><strong>{titulo}</strong> + carga fija</td>
                  <td style={{ textAlign: 'right' }}>
                    {esc[clave].por_botella_con_carga == null ? '—' : fmtMoneda(esc[clave].por_botella_con_carga)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {esc[clave].por_paquete_con_carga == null ? '—' : fmtMoneda(esc[clave].por_paquete_con_carga)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default PaginaSimulacion
