import { useState } from 'react'

// Tabla de solo lectura, plegable (mismo patron que Catalogos), con
// buscador (filtra por cualquier columna) y ordenada alfabeticamente
// por una clave. Pensada para listas largas tipo catalogo (ver 6.3/6.4).
function TablaFiltrable({ titulo, filas, columnas, claveOrden, abiertoInicial = false }) {
  const [filtro, setFiltro] = useState('')
  const [abierto, setAbierto] = useState(abiertoInicial)

  const filtradas = filas
    .filter((f) =>
      columnas.some((c) => String(f[c.key] ?? '').toLowerCase().includes(filtro.toLowerCase()))
    )
    .sort((a, b) => String(a[claveOrden]).localeCompare(String(b[claveOrden]), 'es'))

  return (
    <div style={{ marginBottom: '1rem' }}>
      <h3 style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setAbierto(!abierto)}>
        {abierto ? '▾' : '▸'} {titulo} ({filas.length})
      </h3>
      {abierto && (
        <>
          <input
            type="text"
            placeholder="Buscar..."
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            style={{ display: 'block', marginBottom: '0.5rem' }}
          />
          <table border="1">
            <thead>
              <tr>{columnas.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
            </thead>
            <tbody>
              {filtradas.length === 0 && (
                <tr><td colSpan={columnas.length}>Sin resultados</td></tr>
              )}
              {filtradas.map((f, i) => (
                <tr key={i}>
                  {columnas.map((c) => (
                    <td key={c.key}>{c.formato ? c.formato(f[c.key]) : f[c.key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default TablaFiltrable
