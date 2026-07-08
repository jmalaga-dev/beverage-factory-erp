import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

// Un grupo del menu principal: un titulo clickeable que despliega sus
// paginas. Se resalta si la ruta actual pertenece a este grupo.
function MenuCategoria({ titulo, links }) {
  const [abierto, setAbierto] = useState(false)
  const contenedorRef = useRef(null)
  const location = useLocation()
  const activa = links.some((l) => l.to === location.pathname)

  useEffect(() => {
    function alClickFuera(e) {
      if (contenedorRef.current && !contenedorRef.current.contains(e.target)) {
        setAbierto(false)
      }
    }
    document.addEventListener('mousedown', alClickFuera)
    return () => document.removeEventListener('mousedown', alClickFuera)
  }, [])

  return (
    <span ref={contenedorRef}
      onMouseEnter={() => setAbierto(true)}
      onMouseLeave={() => setAbierto(false)}
      style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={() => setAbierto(!abierto)}
        style={{
          background: 'none',
          border: 'none',
          font: 'inherit',
          cursor: 'pointer',
          color: activa ? 'var(--accent)' : 'inherit',
          padding: '4px 8px',
        }}
      >
        {titulo} {abierto ? '▴' : '▾'}
      </button>
      {abierto && (
        <ul style={{
          position: 'absolute', zIndex: 10, top: '100%', left: 0,
          background: 'var(--bg)', border: '1px solid var(--border)',
          listStyle: 'none', margin: 0, padding: '4px', minWidth: '180px',
          textAlign: 'left',
        }}>
          {links.map((l) => (
            <li key={l.to}>
              <NavLink
                to={l.to}
                onClick={() => setAbierto(false)}
                style={({ isActive }) => ({
                  display: 'block',
                  padding: '6px 8px',
                  color: isActive ? 'var(--accent)' : 'var(--text)',
                  textDecoration: 'none',
                })}
              >
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </span>
  )
}

export default MenuCategoria
