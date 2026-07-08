import { useEffect, useRef, useState } from 'react'

// Reemplazo de <select> para listas que pueden crecer mucho (materias primas,
// productos, clientes, lotes...). Es un input de texto: al enfocarlo se abre
// una lista filtrada por lo que se escribe, en vez de tener que scrollear un
// <select> largo. Al elegir una opcion, avisa el id via onCambiar (como string,
// igual que hacia el value de un <select> nativo).
function SelectorBuscable({ opciones, valor, onCambiar, obtenerId, obtenerTexto, placeholder }) {
  const [busqueda, setBusqueda] = useState('')
  const [abierto, setAbierto] = useState(false)
  const contenedorRef = useRef(null)

  const opcionSeleccionada = opciones.find((o) => String(obtenerId(o)) === String(valor))
  const textoMostrado = abierto ? busqueda : (opcionSeleccionada ? obtenerTexto(opcionSeleccionada) : '')

  const filtradas = opciones.filter((o) =>
    obtenerTexto(o).toLowerCase().includes(busqueda.toLowerCase())
  )

  // Cerrar la lista si se hace click fuera del componente
  useEffect(() => {
    function alClickFuera(e) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) {
        setAbierto(false)
        setBusqueda('')
      }
    }
    document.addEventListener('mousedown', alClickFuera)
    return () => document.removeEventListener('mousedown', alClickFuera)
  }, [])

  function elegir(o) {
    onCambiar(String(obtenerId(o)))
    setBusqueda('')
    setAbierto(false)
  }

  return (
    <span ref={contenedorRef} style={{ position: 'relative', display: 'inline-block' }}>
      <input
        type="text"
        placeholder={placeholder}
        value={textoMostrado}
        onFocus={() => { setAbierto(true); setBusqueda('') }}
        onChange={(e) => setBusqueda(e.target.value)}
      />
      {valor && !abierto && (
        <button type="button" onClick={() => onCambiar('')} title="Quitar seleccion"
          style={{ marginLeft: '2px' }}>
          ×
        </button>
      )}
      {abierto && (
        <ul style={{
          position: 'absolute', zIndex: 10, top: '100%', left: 0,
          background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)',
          listStyle: 'none', margin: 0, padding: '4px', maxHeight: '220px', overflowY: 'auto',
          minWidth: '260px', textAlign: 'left',
        }}>
          {filtradas.length === 0 && (
            <li style={{ padding: '4px 6px', opacity: 0.7 }}>Sin resultados</li>
          )}
          {filtradas.map((o) => (
            <li key={obtenerId(o)}
              onMouseDown={() => elegir(o)}
              style={{ padding: '4px 6px', cursor: 'pointer' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-bg)' }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}>
              {obtenerTexto(o)}
            </li>
          ))}
        </ul>
      )}
    </span>
  )
}

export default SelectorBuscable
