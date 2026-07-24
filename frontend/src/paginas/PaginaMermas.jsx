import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import TablaFiltrable from '../componentes/TablaFiltrable'
import InputCalculo from '../componentes/InputCalculo'
import { useFechaGlobal } from '../componentes/FechaGlobal'
import { fmtNumero } from '../formato'
import { evaluar } from '../calculo'

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

  // Limpieza de residuos bajo el umbral (mejora 3.5). Flujo en dos pasos:
  // `residuos` en null = todavia no se busco; [] = se busco y no hay.
  // `elegidos` guarda solo los DESTILDADOS (ausente = tildado), para que la
  // lista arranque toda seleccionada sin tener que llenar el objeto.
  const [residuos, setResiduos] = useState(null)
  const [elegidos, setElegidos] = useState({})
  const [umbral, setUmbral] = useState(0.0001)

  function cargar() {
    apiGet('/lotes-compra').then(setLotesMP).catch(console.error)
    apiGet('/producciones-intermedias').then(setLotesInt).catch(console.error)
    apiGet('/producciones-terminadas').then(setLotesTerm).catch(console.error)
    apiGet('/items-absorcion').then((d) => setTasa(d.tasa_defecto)).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Paso 1: mostrar qué se pondría en cero. No toca nada todavía.
  function buscarResiduos() {
    apiGet('/residuos')
      .then((d) => {
        setUmbral(d.umbral)
        setResiduos(d.residuos)
        setElegidos({})
        setMensaje('')
      })
      .catch((e) => setMensaje(e.message))
  }

  // Paso 2: aplicar la merma, solo sobre los que quedaron tildados.
  function confirmarLimpieza() {
    const seleccion = residuos
      .filter((r) => elegidos[`${r.origen}-${r.id_lote}`] !== false)
      .map((r) => ({ origen: r.origen, id_lote: r.id_lote }))
    if (seleccion.length === 0) { setMensaje('No dejaste ningún residuo seleccionado'); return }

    apiPost('/residuos/limpiar', { seleccion, fecha: fechaParaEnviar })
      .then((d) => {
        const omitidos = d.omitidos.length > 0
          ? ` (${d.omitidos.length} se omitieron: cambiaron desde la vista previa)`
          : ''
        setMensaje(`${d.limpiados.length} lotes cerrados en cero${omitidos}`)
        setResiduos(null)
        setElegidos({})
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

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
  const cantidadNum = evaluar(cantidad)
  const costoAbsorber = (esMerma && idLote !== '' && cantidad !== '' && !Number.isNaN(cantidadNum))
    ? cantidadNum * costoUnitarioLote()
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
    if (Number.isNaN(cantidadNum)) { setMensaje('La cantidad no es una operación válida'); return }
    const botellasAbsorcionNum = evaluar(botellasAbsorcion)
    if (botellasAbsorcion !== '' && Number.isNaN(botellasAbsorcionNum)) {
      setMensaje('Las botellas estimadas no son una operación válida'); return
    }

    // Solo cuando el movimiento resta stock tiene sentido validar contra el restante
    if (calcularSentido() === 'SALIDA') {
      const restante = restanteDelLote()
      if (restante !== undefined && cantidadNum > restante) {
        setMensaje(`Ese lote solo tiene ${restante} disponible`)
        return
      }
    }

    // Armar el body con el id según el origen
    const body = {
      tipo: tipo,
      sentido: calcularSentido(),
      origen_lote: origen,
      cantidad: cantidadNum,
      motivo: motivo || null,
      id_compra: origen === 'COMPRA' ? parseInt(idLote) : null,
      id_prod_intermedio: origen === 'PRODUCCION_INTERMEDIO' ? parseInt(idLote) : null,
      id_produccion: origen === 'PRODUCCION' ? parseInt(idLote) : null,
      // Absorcion (solo se usa en el backend cuando es MERMA)
      absorber_costo: esMerma ? absorberMerma : false,
      botellas_estimadas_absorcion:
        esMerma && absorberMerma && botellasAbsorcion !== '' ? botellasAbsorcionNum : null,
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

        <InputCalculo value={cantidad} onChange={setCantidad} placeholder="Cantidad" />
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
                <InputCalculo
                  placeholder={botellasSugeridas != null ? `Botellas estimadas (sug. ${botellasSugeridas})` : 'Botellas estimadas'}
                  value={botellasAbsorcion} onChange={setBotellasAbsorcion} />
                <span style={{ color: '#888', fontSize: '0.85em' }}>
                  {' '}vacío = costo × {tasa}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {mensaje && <p>{mensaje}</p>}

      {/* --- Limpieza de residuos bajo el umbral (mejora 3.5) --- */}
      <h2>Limpiar residuos de stock</h2>
      <p style={{ fontSize: '0.9em', color: '#666' }}>
        Lotes que quedaron con un resto minúsculo (menos de {umbral}) y nunca
        se cierran del todo. No afectan el balance —ya se excluyen de todos los
        cálculos— pero se acumulan. Cerrarlos genera una <strong>merma</strong> por
        ese resto exacto: no borra el lote, deja el evento registrado.
      </p>
      <button onClick={buscarResiduos}>Buscar residuos</button>

      {residuos !== null && residuos.length === 0 && (
        <p style={{ color: '#575' }}>No hay residuos: todos los lotes están limpios.</p>
      )}

      {residuos !== null && residuos.length > 0 && (
        <div style={{ border: '1px solid #a06000', padding: '0.6rem', margin: '0.5rem 0' }}>
          <p style={{ marginTop: 0 }}>
            <strong>Se pondrán en cero estos {residuos.length} lotes.</strong> Revisá
            antes de confirmar; destildá el que quieras dejar como está.
          </p>
          <table border="1">
            <thead>
              <tr><th></th><th>Origen</th><th>Lote</th><th>Producto</th><th>Resto a mermar</th></tr>
            </thead>
            <tbody>
              {residuos.map((r) => {
                const clave = `${r.origen}-${r.id_lote}`
                return (
                  <tr key={clave}>
                    <td>
                      <input type="checkbox" checked={elegidos[clave] !== false}
                        onChange={(e) => setElegidos({ ...elegidos, [clave]: e.target.checked })} />
                    </td>
                    <td>{r.origen}</td>
                    <td>{r.id_lote}</td>
                    <td>{r.nombre}</td>
                    <td style={{ textAlign: 'right' }}>{r.restante}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <p>
            <button onClick={confirmarLimpieza}>
              CONFIRMAR y mermar {residuos.filter((r) => elegidos[`${r.origen}-${r.id_lote}`] !== false).length} lotes
            </button>
            {' '}
            <button onClick={() => { setResiduos(null); setElegidos({}) }}>Cancelar</button>
          </p>
        </div>
      )}

      {/* --- Stock actual, plegable: son tablas largas que casi siempre
              estorban mientras se carga una merma (mismo patrón que 6.4) --- */}
      <TablaFiltrable
        titulo="Stock actual — Materia prima"
        filas={lotesMP}
        claveOrden="nombre_materia"
        columnas={[
          { key: 'id_compra', label: 'Lote' },
          { key: 'nombre_materia', label: 'Materia' },
          { key: 'cantidad_restante', label: 'Restante', formato: (v) => fmtNumero(v) },
        ]}
      />
      <TablaFiltrable
        titulo="Stock actual — Producto intermedio"
        filas={lotesInt}
        claveOrden="descripcion"
        columnas={[
          { key: 'id_produccion_intermedio', label: 'Lote' },
          { key: 'descripcion', label: 'Producto' },
          { key: 'cantidad_restante', label: 'Restante', formato: (v) => fmtNumero(v) },
          { key: 'unidad', label: 'Unidad' },
          { key: 'costo_unitario', label: 'Costo', formato: (v) => fmtNumero(v, 4) },
        ]}
      />
      <TablaFiltrable
        titulo="Stock actual — Producto terminado"
        filas={lotesTerm}
        claveOrden="descripcion"
        columnas={[
          { key: 'id_produccion', label: 'Lote' },
          { key: 'descripcion', label: 'Producto' },
          { key: 'cantidad_restante', label: 'Restante', formato: (v) => fmtNumero(v) },
          { key: 'costo_unitario', label: 'Costo', formato: (v) => fmtNumero(v, 4) },
        ]}
      />
    </div>
  )
}

export default PaginaMermas