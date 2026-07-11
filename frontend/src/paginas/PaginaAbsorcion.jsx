import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'

// Absorcion de costos indirectos por botella (mejora 1.4). Se registran
// utensilios/equipos y feriados: sale dinero de una cuenta y su costo se
// reparte entre las botellas que se produzcan despues. Las mermas crean sus
// items solas (al registrar la merma). "Botellas estimadas" es cuantas
// botellas se calcula que cubriran el costo; el sistema sugiere costo x tasa.
function PaginaAbsorcion() {
  const [cuentas, setCuentas] = useState([])
  const [items, setItems] = useState([])
  const [tasa, setTasa] = useState(10)

  // Formulario (compartido por utensilio y feriado; el tipo lo decide el boton)
  const [descripcion, setDescripcion] = useState('')
  const [costo, setCosto] = useState('')
  const [idCuenta, setIdCuenta] = useState('')
  const [botellas, setBotellas] = useState('')  // vacio = usar sugerencia (costo x tasa)
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/cuentas').then(setCuentas).catch(console.error)
    apiGet('/items-absorcion').then((d) => { setItems(d.items); setTasa(d.tasa_defecto) }).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  // Sugerencia de botellas estimadas si el usuario no la escribe
  const sugerencia = costo !== '' ? parseFloat(costo) * tasa : null

  function registrar(endpoint, etiqueta) {
    if (descripcion.trim() === '' || costo === '' || idCuenta === '') {
      setMensaje('Completa descripción, costo y cuenta')
      return
    }
    const cuenta = cuentas.find((c) => c.id_cuenta === parseInt(idCuenta))
    if (cuenta && parseFloat(costo) > cuenta.saldo) {
      setMensaje(`Saldo insuficiente: la cuenta tiene ${cuenta.saldo} Bs`)
      return
    }
    apiPost(`/${endpoint}`, {
      descripcion,
      costo: parseFloat(costo),
      id_cuenta: parseInt(idCuenta),
      botellas_estimadas: botellas !== '' ? parseFloat(botellas) : null,
    })
      .then(() => {
        setMensaje(`${etiqueta} registrado`)
        setDescripcion(''); setCosto(''); setIdCuenta(''); setBotellas('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  const tipoTexto = { UTENSILIO: 'Utensilio/equipo', FERIADO: 'Feriado', MERMA: 'Merma' }

  return (
    <div>
      <h2>Absorción de costos por botella</h2>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Costos que no son insumo directo (un barril, un feriado, una merma) se
        reparten entre las botellas que se produzcan después: cada producción
        les descuenta su parte hasta saldarlos. Así el precio de venta los cubre.
      </p>

      <h3>Registrar utensilio / equipo o feriado</h3>
      <div>
        <input type="text" placeholder="Descripción"
          value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        <input type="number" placeholder="Costo"
          value={costo} onChange={(e) => setCosto(e.target.value)} />
        <SelectorBuscable
          opciones={cuentas.filter((c) => c.habilitado)}
          valor={idCuenta}
          onCambiar={setIdCuenta}
          obtenerId={(c) => c.id_cuenta}
          obtenerTexto={(c) => `${c.nombre} (saldo: ${c.saldo})`}
          placeholder="-- Cuenta de dónde sale --"
        />
        <input type="number"
          placeholder={sugerencia != null ? `Botellas estimadas (sug. ${sugerencia})` : 'Botellas estimadas'}
          value={botellas} onChange={(e) => setBotellas(e.target.value)} />
        <button onClick={() => registrar('utensilios', 'Utensilio')}>Registrar utensilio</button>
        {' '}
        <button onClick={() => registrar('feriados', 'Feriado')}>Registrar feriado</button>
      </div>
      <p style={{ fontSize: '0.85em', color: '#888' }}>
        Si dejas "botellas estimadas" vacío, se usa costo × {tasa} = {sugerencia != null ? sugerencia : '—'} botellas.
      </p>

      {mensaje && <p>{mensaje}</p>}

      <h3>Items en absorción</h3>
      <p style={{ fontSize: '0.85em', color: '#888' }}>
        Los ítems de tipo <strong>Merma</strong> no se registran aquí: nacen al
        registrar una merma en <strong>Cierre → Mermas</strong> (que descuenta el
        stock) y aparecen en esta tabla automáticamente.
      </p>
      <table border="1">
        <thead>
          <tr>
            <th>Tipo</th><th>Descripción</th><th>Costo</th>
            <th>Bs/botella</th><th>Botellas restantes</th><th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id_item_absorcion} style={it.saldado ? { opacity: 0.5 } : {}}>
              <td>{tipoTexto[it.tipo] || it.tipo}</td>
              <td>{it.descripcion}</td>
              <td>{it.costo}</td>
              <td>{it.costo_por_botella}</td>
              <td>{it.botellas_restantes} / {it.botellas_estimadas}</td>
              <td>{it.saldado ? 'Saldado' : 'Absorbiendo'}</td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={6}>Sin items en absorción</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaAbsorcion
