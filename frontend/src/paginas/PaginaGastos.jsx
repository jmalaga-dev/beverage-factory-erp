import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtMoneda } from '../formato'

function PaginaGastos() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [cuentas, setCuentas] = useState([])
  const [grupos, setGrupos] = useState([])

  const [idCuenta, setIdCuenta] = useState('')
  const [monto, setMonto] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [idGrupo, setIdGrupo] = useState('')
  const [mensaje, setMensaje] = useState('')

  // ----- Registrar VARIOS gastos a la vez, como tabla (misma idea que la
  // tabla de Compras): cada linea es un gasto independiente que sale ENTERO
  // de una cuenta, elegida sola por prioridad. Para gastos el orden por
  // defecto es al reves que en compras: primero CASA, luego FABRICA. -----
  const [loteTipo, setLoteTipo] = useState('FAMILIAR')   // FAMILIAR = Casa->Fabrica, FABRICA = Fabrica->Casa
  const [loteLineas, setLoteLineas] = useState([])   // [{descripcion, monto, id_grupo, nombreGrupo}]
  const [loteDescripcion, setLoteDescripcion] = useState('')
  const [loteMonto, setLoteMonto] = useState('')
  const [loteIdGrupo, setLoteIdGrupo] = useState('')
  const [lotePreview, setLotePreview] = useState(null)   // { asignaciones, total_fabrica, total_casa, saldo_fabrica, saldo_casa }
  const [lotePreviewError, setLotePreviewError] = useState('')
  const [loteMensaje, setLoteMensaje] = useState('')

  function cargar() {
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/grupos').then(setGrupos).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function agregarLineaLote() {
    if (loteDescripcion.trim() === '' || loteMonto === '') {
      setLoteMensaje('Completa descripción y monto de la línea'); return
    }
    const grupo = grupos.find((g) => g.id_grupo === parseInt(loteIdGrupo))
    setLoteLineas([...loteLineas, {
      descripcion: loteDescripcion.trim(),
      monto: parseFloat(loteMonto),
      id_grupo: loteIdGrupo ? parseInt(loteIdGrupo) : null,
      nombreGrupo: grupo ? grupo.nombre : '',
    }])
    setLoteDescripcion(''); setLoteMonto(''); setLoteIdGrupo(''); setLoteMensaje('')
  }
  function quitarLineaLote(i) { setLoteLineas(loteLineas.filter((_, idx) => idx !== i)) }

  // Suma total en vivo
  const loteTotalGeneral = loteLineas.reduce((s, l) => s + l.monto, 0)

  // Preview en vivo: de que cuenta sale cada linea, segun el tipo elegido
  useEffect(() => {
    if (loteLineas.length === 0) {
      setLotePreview(null); setLotePreviewError(''); return
    }
    apiPost('/gastos-lote/preview', {
      lineas: loteLineas.map((l) => ({ monto: l.monto, descripcion: l.descripcion, id_grupo: l.id_grupo })),
      tipo: loteTipo,
    })
      .then((r) => { setLotePreview(r); setLotePreviewError('') })
      .catch((e) => { setLotePreview(null); setLotePreviewError(e.message) })
  }, [loteLineas, loteTipo])

  function registrarGastosLote() {
    if (loteLineas.length === 0) { setLoteMensaje('Agrega al menos una línea'); return }
    if (lotePreviewError) { setLoteMensaje(lotePreviewError); return }
    apiPost('/gastos-lote', {
      lineas: loteLineas.map((l) => ({ monto: l.monto, descripcion: l.descripcion, id_grupo: l.id_grupo })),
      tipo: loteTipo,
      fecha: fechaParaEnviar,
    })
      .then((r) => {
        setLoteMensaje(r.mensaje || 'Gastos registrados correctamente')
        setLoteLineas([])
        setLotePreview(null)
        cargar()   // recargar cuentas (el saldo cambió)
      })
      .catch((e) => setLoteMensaje(e.message))
  }

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

      {/* Registrar varios gastos a la vez, como tabla: cada linea es un
          gasto independiente. La cuenta se asigna sola, por prioridad. */}
      <h2>Registrar varios gastos a la vez (tabla)</h2>
      <p style={{ fontSize: '0.85em', color: '#666', marginTop: 0 }}>
        Agrega una línea por cada gasto. La cuenta de pago se asigna sola,
        por prioridad: con <strong>Gasto familiar</strong> primero se gasta
        Casa línea por línea hasta que ya no alcanza, y de ahí en adelante
        se paga con Fábrica; con <strong>Gasto de fábrica</strong> es al revés.
      </p>
      <div style={{ border: '1px solid #ccc', padding: '0.6rem', margin: '0.5rem 0' }}>
        <div>
          <label>
            Tipo:{' '}
            <select value={loteTipo} onChange={(e) => setLoteTipo(e.target.value)}>
              <option value="FAMILIAR">Gasto familiar (Casa primero)</option>
              <option value="FABRICA">Gasto de fábrica (Fábrica primero)</option>
            </select>
          </label>
        </div>

        {/* Agregar línea */}
        <div style={{ marginTop: '0.5rem' }}>
          <input type="text" placeholder="Descripción"
            value={loteDescripcion} onChange={(e) => setLoteDescripcion(e.target.value)} />
          <input type="text" placeholder="Monto"
            value={loteMonto} onChange={(e) => setLoteMonto(e.target.value)} />
          <SelectorBuscable
            opciones={grupos.filter((g) => g.habilitado)}
            valor={loteIdGrupo}
            onCambiar={setLoteIdGrupo}
            obtenerId={(g) => g.id_grupo}
            obtenerTexto={(g) => g.nombre}
            placeholder="-- Grupo (opcional) --"
          />
          <button onClick={agregarLineaLote}>Agregar línea</button>
        </div>

        {/* Tabla de líneas cargadas, con la cuenta asignada en vivo */}
        {loteLineas.length > 0 && (
          <table border="1" style={{ marginTop: '0.5rem', borderCollapse: 'collapse' }}>
            <thead>
              <tr><th>Descripción</th><th>Monto</th><th>Grupo</th><th>Cuenta</th><th></th></tr>
            </thead>
            <tbody>
              {loteLineas.map((l, i) => (
                <tr key={i}>
                  <td>{l.descripcion}</td>
                  <td style={{ textAlign: 'right' }}>{fmtMoneda(l.monto)}</td>
                  <td>{l.nombreGrupo || '—'}</td>
                  <td>{lotePreview?.asignaciones?.[i] === 'CASA' ? 'Casa' : lotePreview?.asignaciones?.[i] === 'FABRICA' ? 'Fábrica' : '—'}</td>
                  <td><button onClick={() => quitarLineaLote(i)}>quitar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Suma en vivo: total general y cuanto va a cada billetera */}
        {loteLineas.length > 0 && (
          <p style={{ marginTop: '0.5rem' }}>
            <strong>Total: {fmtMoneda(loteTotalGeneral)}</strong>
            {lotePreview && (
              <>
                {' '}— Fábrica: {fmtMoneda(lotePreview.total_fabrica)} (saldo {fmtMoneda(lotePreview.saldo_fabrica)})
                {' '}— Casa: {fmtMoneda(lotePreview.total_casa)} (saldo {fmtMoneda(lotePreview.saldo_casa)})
              </>
            )}
          </p>
        )}
        {lotePreviewError && <p style={{ color: '#a00' }}>{lotePreviewError}</p>}

        <button onClick={registrarGastosLote} style={{ marginTop: '0.5rem' }}>
          Registrar {loteLineas.length > 0 ? `los ${loteLineas.length} gastos` : 'gastos'}
        </button>
        {loteMensaje && <p>{loteMensaje}</p>}
      </div>
    </div>
  )
}

export default PaginaGastos