import { useState, useEffect } from 'react'

function PaginaMermas() {
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

  function cargar() {
    fetch('http://127.0.0.1:8000/lotes-compra')
      .then((r) => r.json()).then(setLotesMP).catch(console.error)
    fetch('http://127.0.0.1:8000/producciones-intermedias')
      .then((r) => r.json()).then(setLotesInt).catch(console.error)
    fetch('http://127.0.0.1:8000/producciones-terminadas')
      .then((r) => r.json()).then(setLotesTerm).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

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

  function registrar() {
    if (idLote === '' || cantidad === '') {
      setMensaje('Elige lote y cantidad')
      return
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
    }

    fetch('http://127.0.0.1:8000/movimientos-inventario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((e) => { throw new Error(e.detail || 'Error') })
        return r.json()
      })
      .then(() => {
        setMensaje('Movimiento de inventario registrado')
        setIdLote(''); setCantidad(''); setMotivo('')
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
        <select value={idLote} onChange={(e) => setIdLote(e.target.value)}>
          <option value="">-- Lote --</option>
          {lotesDelOrigen().map((l) => (
            <option key={l.id} value={l.id}>{l.texto}</option>
          ))}
        </select>

        <input type="number" placeholder="Cantidad"
          value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
        <input type="text" placeholder="Motivo"
          value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <button onClick={registrar}>Registrar</button>
      </div>

      {/* Aviso del sentido que se aplicará */}
      <p>Este movimiento va a <strong>{calcularSentido() === 'SALIDA' ? 'RESTAR' : 'SUMAR'}</strong> stock.</p>

      {mensaje && <p>{mensaje}</p>}

      <h2>Stock actual — Materia prima</h2>
      <table border="1">
        <thead><tr><th>Lote</th><th>Materia</th><th>Restante</th></tr></thead>
        <tbody>
          {lotesMP.map((l) => (
            <tr key={l.id_compra}>
              <td>{l.id_compra}</td><td>{l.nombre_materia}</td><td>{l.cantidad_restante}</td>
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
              <td>{l.cantidad_restante}</td><td>{l.costo_unitario}</td>
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
              <td>{l.cantidad_restante}</td><td>{l.costo_unitario}</td>
            </tr>
          ))}
        </tbody>
      </table>

          
      
    </div>
  )
}

export default PaginaMermas