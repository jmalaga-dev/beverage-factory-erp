import { useState } from 'react'
import { apiGet } from '../api'
import SelectorBuscable from './SelectorBuscable'
import CantidadPaquetes, { totalBotellas } from './CantidadPaquetes'
import InputCalculo from './InputCalculo'

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
//   obtenerBotellasPorPaquete(opcion): opcional. Si se pasa, la cantidad se
//     carga en paquetes + botellas sueltas (6.13). Solo aplica a producto
//     terminado; materia prima e intermedio no se empaquetan y lo omiten.
function SelectorFifo({ origen, opciones, obtenerId, obtenerTexto, placeholder, onResolver, obtenerBotellasPorPaquete }) {
  const [idProducto, setIdProducto] = useState('')
  const [paquetes, setPaquetes] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [mensaje, setMensaje] = useState('')

  const elegido = idProducto !== ''
    ? opciones.find((o) => String(obtenerId(o)) === String(idProducto))
    : null
  const bpp = elegido && obtenerBotellasPorPaquete ? obtenerBotellasPorPaquete(elegido) : 1
  const total = totalBotellas(paquetes, cantidad, bpp)

  function elegir(id) {
    setIdProducto(id)
    // Igual que en las lineas de venta: los paquetes cargados pertenecen al
    // tamaño de paquete del producto anterior.
    setPaquetes(''); setCantidad('')
  }

  function resolver() {
    if (idProducto === '' || total <= 0) { setMensaje('Elige producto y cantidad'); return }
    apiGet(`/fifo/${origen}/${idProducto}?cantidad=${total}`)
      .then((d) => {
        if (d.asignaciones.length === 0) { setMensaje('Sin stock disponible para ese producto'); return }
        onResolver(parseInt(idProducto), d.asignaciones)
        setMensaje(d.faltante > 0
          ? `Ojo: faltan ${d.faltante} (no hay stock suficiente; se agregó solo lo disponible)`
          : '')
        setIdProducto(''); setPaquetes(''); setCantidad('')
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div style={{ background: '#eef', padding: '0.4rem', margin: '0.3rem 0' }}>
      <span style={{ fontSize: '0.85em', color: '#557' }}>Resolver por FIFO: </span>
      <SelectorBuscable
        opciones={opciones} valor={idProducto} onCambiar={elegir}
        obtenerId={obtenerId} obtenerTexto={obtenerTexto} placeholder={placeholder}
      />
      {obtenerBotellasPorPaquete ? (
        <CantidadPaquetes
          botellasPorPaquete={bpp}
          paquetes={paquetes}
          botellas={cantidad}
          onCambiarPaquetes={setPaquetes}
          onCambiarBotellas={setCantidad}
        />
      ) : (
        <InputCalculo value={cantidad} onChange={setCantidad} placeholder="Cantidad total" />
      )}
      <button onClick={resolver}>Resolver FIFO</button>
      {mensaje && <span style={{ marginLeft: '0.5rem', color: '#a06000' }}>{mensaje}</span>}
    </div>
  )
}

export default SelectorFifo
