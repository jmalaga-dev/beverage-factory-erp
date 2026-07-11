import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero } from '../formato'

function PaginaMermas() {
  const { fechaParaEnviar } = useFechaGlobal()
  const [lotesMP, setLotesMP] = useState([])
  const [lotesInt, setLotesInt] = useState([])
  const [lotesTerm, setLotesTerm] = useState([])

  const [tipo, setTipo] = useState('MERMA')
  const [origen, setOrigen] = useState('COMPRA')   // COMPRA / PRODUCCION_INTERMEDIO / PRODUCCION
  const [sentidoAjuste, setSentidoAjuste] = useState('SALIDA')  // solo aplica a AJUSTE
  const [idLote, setIdLote] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [motivo, setMotivo] = useState('')
  const [mensaje, setMensaje] = useState('')

  // Absorcion del costo de la merma (mejora 1.4): control visible aqui, donde
  // se registra la merma que descuenta stock. El costo perdido se reparte
  // entre las botellas futuras.
  const [absorberMerma, setAbsorberMerma] = useState(true)
  const [botellasAbsorcion, setBotellasAbsorcion] = useState('')  // vacio = tasa por defecto
  const [tasa, setTasa] = useState(10)

  function cargar() {
    apiGet('/lotes-compra').then(setLotesMP).catch(console.error)
    apiGet('/producciones-intermedias').then(setLotesInt).catch(console.error)
    apiGet('/producciones-terminadas').then(setLotesTerm).catch(console.error)
    apiGet('/items-absorcion').then((d) => setTasa(d.tasa_defecto)).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Costo unitario del lote elegido, segun su origen (para estimar el costo
  // que se absorbera en una merma).
  function costoUnitarioLote() {
    const id = parseInt(idLote)
    if (origen === 'COMPRA') {
      const l = lotesMP.find((x) => x.id_compra === id)
      return l && l.cantidad_compra ? l.precio_compra / l.cantidad_compra : 0
    }
    if (origen === 'PRODUCCION_INTERMEDIO') {
      return lotesInt.find((x) => x.id_produccion_intermedio === id)?.costo_unitario || 0
    }
    return lotesTerm.find((x) => x.id_produccion === id)?.costo_unitario || 0
  }

  // Costo que se absorbera = cantidad a mermar x costo unitario del lote
  const esMerma = tipo === 'MERMA'
  const costoAbsorber = (esMerma && idLote !== '' && cantidad !== '')
    ? parseFloat(cantidad) * costoUnitarioLote()
    : 0
  const botellasSugeridas = costoAbsorber > 0 ? costoAbsorber * tasa : null

  // Determinar el sentido según el tipo
  function calcularSentido() {
    if (tipo === 'MERMA') return 'SALIDA'          // merma siempre resta
    if (tipo === 'DEVOLUCION') return 'ENTRADA'    // devolución siempre suma
    return sentidoAjuste                            // ajuste: lo elige el usuario
  }

  // Los lotes del origen elegido (para el desplegable)
  function lotesDelOrigen() {
    if (origen === 'COMPRA') return lotesMP.map((l) => ({
      id: l.id_compra, texto: `${l.nombre_materia} - Lote ${l.id_compra} (rest: ${l.cantidad_restante})`
    }))
    if (origen === 'PRODUCCION_INTERMEDIO') return lotesInt.map((l) => ({
      id: l.id_produccion_intermedio, texto: `${l.descripcion} - Lote ${l.id_produccion_intermedio} (rest: ${l.cantidad_restante})`
    }))
    return lotesTerm.map((l) => ({
      id: l.id_produccion, texto: `${l.descripcion} - Lote ${l.id_produccion} (rest: ${l.cantidad_restante})`
    }))
  }

  // Cuanto le queda al lote elegido, segun el origen (para validar la salida)
  function restanteDelLote() {
    const id = parseInt(idLote)
    if (origen === 'COMPRA') return lotesMP.find((l) => l.id_compra === id)?.cantidad_restante
    if (origen === 'PRODUCCION_INTERMEDIO') return lotesInt.find((l) => l.id_produccion_intermedio === id)?.cantidad_restante
    return lotesTerm.find((l) => l.id_produccion === id)?.cantidad_restante
  }

  function registrar() {
    if (idLote === '' || cantidad === '') {
      setMensaje('Elige lote y cantidad')
      return
    }

    // Solo cuando el movimiento resta stock tiene sentido validar contra el restante
    if (calcularSentido() === 'SALIDA') {
      const restante = restanteDelLote()
      if (restante !== undefined && parseFloat(cantidad) > restante) {
        setMensaje(`Ese lote solo tiene ${restante} disponible`)
        return
      }
    }

    // Armar el body con el id según el origen
    const body = {
      tipo: tipo,
      sentido: calcularSentido(),
      origen_lote: origen,
      cantidad: parseFloat(cantidad),
      motivo: motivo || null,
      id_compra: origen === 'COMPRA' ? parseInt(idLote) : null,
      id_prod_intermedio: origen === 'PRODUCCION_INTERMEDIO' ? parseInt(idLote) : null,
      id_produccion: origen === 'PRODUCCION' ? parseInt(idLote) : null,
      // Absorcion (solo se usa en el backend cuando es MERMA)
      absorber_costo: esMerma ? absorberMerma : false,
      botellas_estimadas_absorcion:
        esMerma && absorberMerma && botellasAbsorcion !== '' ? parseFloat(botellasAbsorcion) : null,
      fecha: fechaParaEnviar,
    }

    apiPost('/movimientos-inventario', body)
      .then(() => {
        setMensaje('Movimiento de inventario registrado')
        setIdLote(''); setCantidad(''); setMotivo(''); setBotellasAbsorcion('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div>
      <h2>Mermas y ajustes de inventario</h2>
      <div>
        {/* Tipo */}
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="MERMA">Merma (resta - se echó a perder)</option>
          <option value="AJUSTE">Ajuste (corrección de conteo)</option>
          <option value="DEVOLUCION">Devolución (suma - vuelve al stock)</option>
        </select>

        {/* Si es ajuste, elegir si suma o resta */}
        {tipo === 'AJUSTE' && (
          <select value={sentidoAjuste} onChange={(e) => setSentidoAjuste(e.target.value)}>
            <option value="SALIDA">Faltó (restar)</option>
            <option value="ENTRADA">Sobró (sumar)</option>
          </select>
        )}

        {/* Origen del lote */}
        <select value={origen} onChange={(e) => { setOrigen(e.target.value); setIdLote('') }}>
          <option value="COMPRA">Materia prima</option>
          <option value="PRODUCCION_INTERMEDIO">Producto intermedio</option>
          <option value="PRODUCCION">Producto terminado</option>
        </select>

        {/* Lote según el origen */}
        <SelectorBuscable
          opciones={lotesDelOrigen()}
          valor={idLote}
          onCambiar={setIdLote}
          obtenerId={(l) => l.id}
          obtenerTexto={(l) => l.texto}
          placeholder="-- Lote --"
        />

        <input type="number" placeholder="Cantidad"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
        <input type="text" placeholder="Motivo"
          value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <button onClick={registrar}>Registrar</button>
      </div>

      {/* Aviso del sentido que se aplicará */}
      <p>Este movimiento va a <strong>{calcularSentido() === 'SALIDA' ? 'RESTAR' : 'SUMAR'}</strong> stock.</p>

      {/* Control de absorcion, solo para MERMA (mejora 1.4). El costo perdido
          se reparte entre las botellas que se produzcan despues. */}
      {esMerma && (
        <div style={{ border: '1px solid #ccc', padding: '0.5rem', margin: '0.5rem 0' }}>
          <label>
            <input type="checkbox" checked={absorberMerma}
              onChange={(e) => setAbsorberMerma(e.target.checked)} />
            {' '}Absorber este costo en las botellas futuras
          </label>
          {absorberMerma && (
            <div style={{ marginTop: '0.4rem' }}>
              <span>
                Costo a absorber:{' '}
                <strong>{costoAbsorber > 0 ? costoAbsorber.toFixed(2) : '—'} Bs</strong>
                {botellasSugeridas != null && (
                  <span style={{ color: '#888' }}> (≈ {(costoAbsorber / botellasSugeridas).toFixed(4)} Bs/botella)</span>
                )}
              </span>
              <div style={{ marginTop: '0.3rem' }}>
                <input type="number"
                  placeholder={botellasSugeridas != null ? `Botellas estimadas (sug. ${botellasSugeridas})` : 'Botellas estimadas'}
                  value={botellasAbsorcion} onChange={(e) => setBotellasAbsorcion(e.target.value)} />
                <span style={{ color: '#888', fontSize: '0.85em' }}>
                  {' '}vacío = costo × {tasa}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {mensaje && <p>{mensaje}</p>}

      <h2>Stock actual — Materia prima</h2>
      <table border="1">
        <thead><tr><th>Lote</th><th>Materia</th><th>Restante</th></tr></thead>
        <tbody>
          {lotesMP.map((l) => (
            <tr key={l.id_compra}>
              <td>{l.id_compra}</td><td>{l.nombre_materia}</td><td>{fmtNumero(l.cantidad_restante)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Stock actual — Producto intermedio</h2>
      <table border="1">
        <thead><tr><th>Lote</th><th>Producto</th><th>Restante</th><th>Costo</th></tr></thead>
        <tbody>
          {lotesInt.map((l) => (
            <tr key={l.id_produccion_intermedio}>
              <td>{l.id_produccion_intermedio}</td><td>{l.descripcion}</td>
              <td>{fmtNumero(l.cantidad_restante)}</td><td>{fmtNumero(l.costo_unitario, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Stock actual — Producto terminado</h2>
      <table border="1">
        <thead><tr><th>Lote</th><th>Producto</th><th>Restante</th><th>Costo</th></tr></thead>
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

export default PaginaMermas