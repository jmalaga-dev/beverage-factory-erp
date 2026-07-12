import { useState } from 'react'
import { apiGet } from '../api'
import SelectorBuscable from './SelectorBuscable'

// "Resolver por FIFO" (mejora 3.1): eliges un producto (materia prima,
// intermedio o terminado) y una cantidad total, y llama al resolver FIFO del
// backend, que devuelve que lotes usar del mas antiguo al mas nuevo. Las
// asignaciones se entregan al padre (onResolver), que las agrega a su lista de
// insumos/lineas. Es una sugerencia: el usuario luego edita.
//
// Props:
//   origen: 'MP' | 'INTERMEDIO' | 'TERMINADO'
//   opciones, obtenerId, obtenerTexto, placeholder: para el selector de producto
//   onResolver(idProducto, asignaciones): callback con el resultado
function SelectorFifo({ origen, opciones, obtenerId, obtenerTexto, placeholder, onResolver }) {
  const [idProducto, setIdProducto] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [mensaje, setMensaje] = useState('')

  function resolver() {
    if (idProducto === '' || cantidad === '') { setMensaje('Elige producto y cantidad'); return }
    apiGet(`/fifo/${origen}/${idProducto}?cantidad=${parseFloat(cantidad)}`)
      .then((d) => {
        if (d.asignaciones.length === 0) { setMensaje('Sin stock disponible para ese producto'); return }
        onResolver(parseInt(idProducto), d.asignaciones)
        setMensaje(d.faltante > 0
          ? `Ojo: faltan ${d.faltante} (no hay stock suficiente; se agregó solo lo disponible)`
          : '')
        setIdProducto(''); setCantidad('')
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div style={{ background: '#eef', padding: '0.4rem', margin: '0.3rem 0' }}>
      <span style={{ fontSize: '0.85em', color: '#557' }}>Resolver por FIFO: </span>
      <SelectorBuscable
        opciones={opciones} valor={idProducto} onCambiar={setIdProducto}
        obtenerId={obtenerId} obtenerTexto={obtenerTexto} placeholder={placeholder}
      />
      <input type="number" placeholder="Cantidad total"
        value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
      <button onClick={resolver}>Resolver FIFO</button>
      {mensaje && <span style={{ marginLeft: '0.5rem', color: '#a06000' }}>{mensaje}</span>}
    </div>
  )
}

export default SelectorFifo
