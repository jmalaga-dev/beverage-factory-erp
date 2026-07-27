import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import InputCalculo from '../componentes/InputCalculo'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero, fmtMoneda } from '../formato'
import { fusionar } from '../insumos'
import { evaluar } from '../calculo'

// Editor de insumos NUEVOS del reproceso (materia prima + trabajo): las tapas,
// etiquetas y horas que se agregan al re-procesar. Controlado por el padre:
// value = { mp: [{id_compra, cantidad}], trabajo: [{id_registro, horas}] }.
function InsumosNuevos({ lotesCompra, jornadas, value, onChange }) {
  const [mpLote, setMpLote] = useState('')
  const [mpCant, setMpCant] = useState('')
  const [trabJor, setTrabJor] = useState('')
  const [trabHoras, setTrabHoras] = useState('')

  function agregarMP() {
    if (mpLote === '' || mpCant === '') return
    const cant = evaluar(mpCant)
    if (Number.isNaN(cant)) return
    onChange({ ...value, mp: fusionar(value.mp, [{ id_compra: parseInt(mpLote), cantidad: cant }], 'id_compra') })
    setMpLote(''); setMpCant('')
  }
  function agregarTrab() {
    if (trabJor === '' || trabHoras === '') return
    const hs = evaluar(trabHoras)
    if (Number.isNaN(hs)) return
    onChange({ ...value, trabajo: [...value.trabajo, { id_registro: parseInt(trabJor), horas: hs }] })
    setTrabJor(''); setTrabHoras('')
  }
  const nombreLote = (id) => { const l = lotesCompra.find((x) => x.id_compra === id); return l ? `${l.nombre_materia} - Lote ${id}` : `Lote ${id}` }
  const nombreJor = (id) => { const j = jornadas.find((x) => x.id_jornada === id); return j ? `${j.nombre_trabajador} (${j.fecha})` : `Jornada ${id}` }

  return (
    <div style={{ borderLeft: '3px solid #ccd', paddingLeft: '0.6rem', margin: '0.4rem 0' }}>
      <div style={{ fontSize: '0.85em', color: '#557' }}>Insumos nuevos (opcional: tapas, etiquetas, trabajo)</div>
      {/* Materia prima */}
      <div>
        <SelectorBuscable opciones={lotesCompra} valor={mpLote} onCambiar={setMpLote}
          obtenerId={(l) => l.id_compra}
          obtenerTexto={(l) => `${l.nombre_materia} - Lote ${l.id_compra} (rest: ${l.cantidad_restante})`}
          placeholder="-- Lote MP --" />
        <InputCalculo value={mpCant} onChange={setMpCant} placeholder="Cantidad" width="6rem" />
        <button onClick={agregarMP}>+ MP</button>
      </div>
      <ul style={{ margin: '0.2rem 0' }}>
        {value.mp.map((x, i) => (
          <li key={i}>{nombreLote(x.id_compra)} — {x.cantidad}{' '}
            <button onClick={() => onChange({ ...value, mp: value.mp.filter((_, idx) => idx !== i) })}>quitar</button></li>
        ))}
      </ul>
      {/* Trabajo */}
      <div>
        <SelectorBuscable opciones={jornadas} valor={trabJor} onCambiar={setTrabJor}
          obtenerId={(j) => j.id_jornada}
          obtenerTexto={(j) => `${j.nombre_trabajador} - ${j.fecha} (quedan ${j.horas_restantes}h)`}
          placeholder="-- Jornada --" />
        <InputCalculo value={trabHoras} onChange={setTrabHoras} placeholder="Horas" width="6rem" />
        <button onClick={agregarTrab}>+ Trabajo</button>
      </div>
      <ul style={{ margin: '0.2rem 0' }}>
        {value.trabajo.map((x, i) => (
          <li key={i}>{nombreJor(x.id_registro)} — {x.horas}h{' '}
            <button onClick={() => onChange({ ...value, trabajo: value.trabajo.filter((_, idx) => idx !== i) })}>quitar</button></li>
        ))}
      </ul>
    </div>
  )
}

const INSUMOS_VACIO = { mp: [], trabajo: [] }

function PaginaDevoluciones() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [lotesTerm, setLotesTerm] = useState([])
  const [cuentas, setCuentas] = useState([])
  const [ventas, setVentas] = useState([])
  const [lotesCompra, setLotesCompra] = useState([])
  const [jornadas, setJornadas] = useState([])
  const [tasa, setTasa] = useState(10)

  // --- Devolución ---
  const [vincular, setVincular] = useState(false)
  const [idVenta, setIdVenta] = useState('')
  const [detalleVenta, setDetalleVenta] = useState(null)   // {lineas: [...]}
  const [lineaSel, setLineaSel] = useState('')             // id_produccion elegido de la venta
  const [devLote, setDevLote] = useState('')               // id_produccion (directo o desde la venta)
  const [devCantidad, setDevCantidad] = useState('')
  const [devCuenta, setDevCuenta] = useState('')
  const [devMonto, setDevMonto] = useState('')
  const [devDestino, setDevDestino] = useState('STOCK')
  const [devMotivo, setDevMotivo] = useState('')
  const [devAbsorber, setDevAbsorber] = useState(true)
  const [devBotellas, setDevBotellas] = useState('')
  const [devRepProducida, setDevRepProducida] = useState('')
  const [devRepInsumos, setDevRepInsumos] = useState(INSUMOS_VACIO)
  const [msgDev, setMsgDev] = useState('')

  // --- Reproceso directo ---
  const [dirLote, setDirLote] = useState('')
  const [dirCantidad, setDirCantidad] = useState('')
  const [dirProducida, setDirProducida] = useState('')
  const [dirInsumos, setDirInsumos] = useState(INSUMOS_VACIO)
  const [msgDir, setMsgDir] = useState('')

  function cargar() {
    apiGet('/producciones-terminadas').then(setLotesTerm).catch(console.error)
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/ventas').then(setVentas).catch(console.error)
    apiGet('/lotes-compra').then(setLotesCompra).catch(console.error)
    apiGet('/jornadas').then((d) => setJornadas(d.filter((j) => j.horas_restantes > 0))).catch(console.error)
    apiGet('/items-absorcion').then((d) => setTasa(d.tasa_defecto)).catch(console.error)
  }
  useEffect(() => { cargar() }, [])

  // Línea de venta elegida (para precio vendido y validación de cantidad)
  const lineaVenta = detalleVenta && lineaSel !== ''
    ? detalleVenta.lineas.find((l) => l.id_produccion === parseInt(lineaSel)) : null

  // Al elegir una venta, traer su detalle
  function elegirVenta(id) {
    setIdVenta(id); setLineaSel(''); setDevLote(''); setDetalleVenta(null)
    if (id !== '') apiGet(`/ventas/${id}`).then(setDetalleVenta).catch((e) => setMsgDev(e.message))
  }
  // Al elegir una línea de la venta, fijar el lote y (si hay cantidad) el reembolso
  function elegirLinea(idProd) {
    setLineaSel(idProd); setDevLote(idProd)
    const l = detalleVenta?.lineas.find((x) => x.id_produccion === parseInt(idProd))
    const cantEval = evaluar(devCantidad)
    if (l && devCantidad !== '' && !Number.isNaN(cantEval)) setDevMonto((l.precio_real * cantEval).toFixed(2))
  }
  // Al cambiar la cantidad, si está vinculada, autocompletar el reembolso sugerido
  function cambiarCantidad(v) {
    setDevCantidad(v)
    const vEval = evaluar(v)
    if (lineaVenta && v !== '' && !Number.isNaN(vEval)) setDevMonto((lineaVenta.precio_real * vEval).toFixed(2))
  }

  // Costo unitario del lote de devolución (para estimar merma / arrastre)
  const loteDevInfo = lotesTerm.find((l) => l.id_produccion === parseInt(devLote))

  function registrarDevolucion() {
    if (devLote === '') { setMsgDev('Elige el lote devuelto (por la venta o directo)'); return }
    const cantNum = evaluar(devCantidad)
    if (devCantidad === '' || Number.isNaN(cantNum) || cantNum <= 0) { setMsgDev('Indica la cantidad devuelta'); return }
    if (devCuenta === '') { setMsgDev('Elige la cuenta del reembolso'); return }
    const montoNum = evaluar(devMonto)
    if (devMonto === '' || Number.isNaN(montoNum) || montoNum < 0) { setMsgDev('Indica el monto del reembolso (0 si no devuelves dinero)'); return }
    if (lineaVenta && cantNum > lineaVenta.cantidad) {
      setMsgDev(`En esa venta se vendieron ${lineaVenta.cantidad} de ese lote; no puedes devolver más`); return
    }
    const botellasNum = evaluar(devBotellas)
    const repProducidaNum = evaluar(devRepProducida)
    if (devDestino === 'REPROCESO' && (devRepProducida === '' || Number.isNaN(repProducidaNum) || repProducidaNum <= 0)) {
      setMsgDev('Indica cuántas botellas produce el reproceso'); return
    }
    const body = {
      id_produccion: parseInt(devLote),
      cantidad: cantNum,
      id_cuenta: parseInt(devCuenta),
      monto_reembolso: montoNum,
      destino: devDestino,
      id_venta: vincular && idVenta !== '' ? parseInt(idVenta) : null,
      motivo: devMotivo || null,
      fecha: fechaParaEnviar,
      absorber_costo: devDestino === 'MERMA' ? devAbsorber : false,
      botellas_estimadas_absorcion: devDestino === 'MERMA' && devAbsorber && devBotellas !== '' && !Number.isNaN(botellasNum) ? botellasNum : null,
      reproceso: devDestino === 'REPROCESO' ? {
        cantidad_producida: repProducidaNum,
        insumos_mp: devRepInsumos.mp.map((x) => [x.id_compra, x.cantidad]),
        insumos_trabajo: devRepInsumos.trabajo.map((x) => [x.id_registro, x.horas]),
      } : null,
    }
    apiPost('/devoluciones', body)
      .then((d) => {
        setMsgDev('Devolución registrada' + (d.id_produccion_nuevo ? ` — lote nuevo ${d.id_produccion_nuevo} (costo ${d.costo_unitario_nuevo} Bs)` : ''))
        setIdVenta(''); setDetalleVenta(null); setLineaSel(''); setDevLote(''); setDevCantidad('')
        setDevMonto(''); setDevMotivo(''); setDevBotellas(''); setDevRepProducida(''); setDevRepInsumos(INSUMOS_VACIO)
        cargar()
      })
      .catch((e) => setMsgDev(e.message))
  }

  function registrarReprocesoDirecto() {
    if (dirLote === '') { setMsgDir('Elige el lote a reprocesar'); return }
    const dirCantNum = evaluar(dirCantidad)
    const dirProdNum = evaluar(dirProducida)
    if (dirCantidad === '' || Number.isNaN(dirCantNum) || dirCantNum <= 0) { setMsgDir('Indica cuánto reprocesar'); return }
    if (dirProducida === '' || Number.isNaN(dirProdNum) || dirProdNum <= 0) { setMsgDir('Indica cuántas botellas produce'); return }
    if (dirProdNum > dirCantNum) { setMsgDir('El reproceso no puede producir más de lo que consume'); return }
    const origen = lotesTerm.find((l) => l.id_produccion === parseInt(dirLote))
    if (origen && dirCantNum > origen.cantidad_restante) { setMsgDir(`Ese lote solo tiene ${origen.cantidad_restante}`); return }
    apiPost('/reprocesos', {
      id_produccion_origen: parseInt(dirLote),
      cantidad: dirCantNum,
      cantidad_producida: dirProdNum,
      insumos_mp: dirInsumos.mp.map((x) => [x.id_compra, x.cantidad]),
      insumos_trabajo: dirInsumos.trabajo.map((x) => [x.id_registro, x.horas]),
      fecha: fechaParaEnviar,
    })
      .then((d) => {
        setMsgDir(`Reproceso registrado — lote nuevo ${d.id_produccion_nuevo} (costo ${d.costo_unitario} Bs)`)
        setDirLote(''); setDirCantidad(''); setDirProducida(''); setDirInsumos(INSUMOS_VACIO)
        cargar()
      })
      .catch((e) => setMsgDir(e.message))
  }

  return (
    <div>
      <h2>Devoluciones y Reproceso</h2>

      {/* ============ DEVOLUCIÓN ============ */}
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        <h3>Devolución de venta</h3>
        <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
          Sale un reembolso de una cuenta y el producto vuelve al stock; según el destino, además se desecha (merma) o se reprocesa.
        </p>

        {/* Vínculo opcional con la venta */}
        <label>
          <input type="checkbox" checked={vincular} onChange={(e) => { setVincular(e.target.checked); elegirVenta('') }} />
          {' '}Vincular a la venta original (autocompleta el reembolso y valida la cantidad)
        </label>

        {vincular && (
          <div style={{ margin: '0.4rem 0' }}>
            {/* Acá se muestra el BRUTO, no el ingreso neto: para encontrar la
                venta a devolver, el número útil es el que pagó el cliente, que
                es lo que se le reembolsa. El taxi ya se pagó y no vuelve. */}
            <SelectorBuscable opciones={ventas} valor={idVenta} onCambiar={elegirVenta}
              obtenerId={(v) => v.id_venta}
              obtenerTexto={(v) => `Venta ${v.id_venta} - ${v.cliente} (${v.fecha}, ${fmtMoneda(v.bruto ?? v.total)} Bs)`}
              placeholder="-- Venta --" />
            {detalleVenta && (
              <SelectorBuscable opciones={detalleVenta.lineas} valor={lineaSel} onCambiar={elegirLinea}
                obtenerId={(l) => l.id_produccion}
                obtenerTexto={(l) => `${l.nombre_producto} - Lote ${l.id_produccion} (vendidas ${l.cantidad} a ${fmtMoneda(l.precio_real)} Bs)`}
                placeholder="-- Línea de la venta --" />
            )}
          </div>
        )}

        {/* Lote directo (si no se vincula) */}
        {!vincular && (
          <div style={{ margin: '0.4rem 0' }}>
            <SelectorBuscable opciones={lotesTerm} valor={devLote} onCambiar={setDevLote}
              obtenerId={(l) => l.id_produccion}
              obtenerTexto={(l) => `${l.descripcion} - Lote ${l.id_produccion} (rest: ${l.cantidad_restante}, costo ${l.costo_unitario})`}
              placeholder="-- Lote devuelto --" />
          </div>
        )}

        <div style={{ margin: '0.4rem 0' }}>
          <InputCalculo value={devCantidad} onChange={cambiarCantidad} placeholder="Cantidad devuelta" width="9rem" />
          <SelectorBuscable opciones={cuentas.filter((c) => c.habilitado)} valor={devCuenta} onCambiar={setDevCuenta}
            obtenerId={(c) => c.id_cuenta} obtenerTexto={(c) => c.nombre} placeholder="-- Cuenta del reembolso --" />
          <InputCalculo value={devMonto} onChange={setDevMonto} placeholder="Monto reembolso" width="9rem" decimales={2} />
          {lineaVenta && <span style={{ fontSize: '0.8em', color: '#888' }}> (sugerido {fmtMoneda(lineaVenta.precio_real * (Number.isNaN(evaluar(devCantidad)) ? 0 : evaluar(devCantidad)))} Bs)</span>}
        </div>

        <div style={{ margin: '0.4rem 0' }}>
          <input type="text" placeholder="Motivo (opcional)" value={devMotivo} onChange={(e) => setDevMotivo(e.target.value)} style={{ width: '18rem' }} />
        </div>

        {/* Destino del producto devuelto */}
        <div style={{ margin: '0.4rem 0' }}>
          Destino del producto:{' '}
          <select value={devDestino} onChange={(e) => setDevDestino(e.target.value)}>
            <option value="STOCK">Vuelve al stock (está bueno)</option>
            <option value="MERMA">Se desecha como merma</option>
            <option value="REPROCESO">Se reprocesa</option>
          </select>
        </div>

        {/* Opciones de MERMA (absorción, mejora 1.4) */}
        {devDestino === 'MERMA' && (
          <div style={{ background: '#f7f7f7', padding: '0.4rem', margin: '0.3rem 0' }}>
            <label>
              <input type="checkbox" checked={devAbsorber} onChange={(e) => setDevAbsorber(e.target.checked)} />
              {' '}Absorber el costo en las botellas futuras
            </label>
            {devAbsorber && loteDevInfo && devCantidad !== '' && (
              <div style={{ marginTop: '0.3rem', fontSize: '0.9em' }}>
                Costo a absorber: <strong>{fmtMoneda(loteDevInfo.costo_unitario * (Number.isNaN(evaluar(devCantidad)) ? 0 : evaluar(devCantidad)))} Bs</strong>
                <div>
                  <InputCalculo placeholder={`Botellas estimadas (sug. costo × ${tasa})`} value={devBotellas}
                    onChange={setDevBotellas} width="18rem" />
                  <span style={{ color: '#888', fontSize: '0.85em' }}> vacío = costo × {tasa}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Opciones de REPROCESO */}
        {devDestino === 'REPROCESO' && (
          <div style={{ background: '#f7f7ff', padding: '0.4rem', margin: '0.3rem 0' }}>
            <div>
              Botellas que produce el reproceso:{' '}
              <InputCalculo value={devRepProducida} onChange={setDevRepProducida} placeholder="≤ cantidad devuelta" width="9rem" />
            </div>
            <InsumosNuevos lotesCompra={lotesCompra} jornadas={jornadas} value={devRepInsumos} onChange={setDevRepInsumos} />
          </div>
        )}

        <button onClick={registrarDevolucion}>REGISTRAR DEVOLUCIÓN</button>
        {msgDev && <p>{msgDev}</p>}
      </div>

      {/* ============ REPROCESO DIRECTO ============ */}
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        <h3>Reproceso directo (sin devolución)</h3>
        <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
          Reprocesa parte de un lote (ej. se rompió la tapa de unas botellas en el depósito) en un lote nuevo del mismo producto.
        </p>
        <div style={{ margin: '0.4rem 0' }}>
          <SelectorBuscable opciones={lotesTerm} valor={dirLote} onCambiar={setDirLote}
            obtenerId={(l) => l.id_produccion}
            obtenerTexto={(l) => `${l.descripcion} - Lote ${l.id_produccion} (rest: ${l.cantidad_restante}, costo ${l.costo_unitario})`}
            placeholder="-- Lote a reprocesar --" />
        </div>
        <div style={{ margin: '0.4rem 0' }}>
          <InputCalculo value={dirCantidad} onChange={setDirCantidad} placeholder="Cantidad a reprocesar" width="11rem" />
          <InputCalculo value={dirProducida} onChange={setDirProducida} placeholder="Botellas producidas" width="11rem" />
        </div>
        <InsumosNuevos lotesCompra={lotesCompra} jornadas={jornadas} value={dirInsumos} onChange={setDirInsumos} />
        <button onClick={registrarReprocesoDirecto}>REGISTRAR REPROCESO</button>
        {msgDir && <p>{msgDir}</p>}
      </div>

      {/* Stock terminado por lote, para referencia */}
      <h3>Stock de producto terminado por lote</h3>
      <table border="1">
        <thead><tr><th>Lote</th><th>Producto</th><th>Restante</th><th>Costo unit.</th></tr></thead>
        <tbody>
          {lotesTerm.map((l) => (
            <tr key={l.id_produccion}>
              <td>{l.id_produccion}</td><td>{l.descripcion}</td>
              <td>{fmtNumero(l.cantidad_restante)}</td><td>{fmtNumero(l.costo_unitario, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaDevoluciones
