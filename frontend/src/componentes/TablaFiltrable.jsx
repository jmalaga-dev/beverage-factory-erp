import { useState } from 'react'

// Tabla de solo lectura, plegable (mismo patron que Catalogos), con
// buscador (filtra por cualquier columna) y ordenada alfabeticamente
// por una clave. Pensada para listas largas tipo catalogo (ver 6.3/6.4).
//
// estiloFila: opcional, (fila) => objeto de estilo. Para marcar visualmente
// filas segun su estado (ej. una deuda ya saldada, atenuada).
// totales: opcional, array de `key` de columnas a sumar (ej. ['stock_total',
// 'paquetes_equivalentes']). Agrega una fila "Total" al pie, calculada sobre
// las filas FILTRADAS (respeta la busqueda). Pensado para sumatorias donde una
// sola unidad no alcanza (item 13): stock en botellas Y su equivalente en
// paquetes a la vez, sin tener que elegir una.
// acciones: opcional, (fila) => nodo JSX. Si se pasa, agrega una columna
// "Acciones" al final con lo que devuelva (ej. un boton Eliminar por fila).
function TablaFiltrable({ titulo, filas, columnas, claveOrden, abiertoInicial = false, estiloFila, totales, acciones }) {
  const [filtro, setFiltro] = useState('')
  const [abierto, setAbierto] = useState(abiertoInicial)

  const filtradas = filas
    .filter((f) =>
      columnas.some((c) => String(f[c.key] ?? '').toLowerCase().includes(filtro.toLowerCase()))
    )
    .sort((a, b) => String(a[claveOrden]).localeCompare(String(b[claveOrden]), 'es'))

  const sumas = totales && filtradas.length > 0
    ? Object.fromEntries(totales.map((key) => [key, filtradas.reduce((s, f) => s + (Number(f[key]) || 0), 0)]))
    : null

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
              <tr>
                {columnas.map((c) => <th key={c.key}>{c.label}</th>)}
                {acciones && <th>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {filtradas.length === 0 && (
                <tr><td colSpan={columnas.length + (acciones ? 1 : 0)}>Sin resultados</td></tr>
              )}
              {filtradas.map((f, i) => (
                <tr key={i} style={estiloFila ? estiloFila(f) : undefined}>
                  {columnas.map((c) => (
                    <td key={c.key}>{c.formato ? c.formato(f[c.key]) : f[c.key]}</td>
                  ))}
                  {acciones && <td>{acciones(f)}</td>}
                </tr>
              ))}
              {sumas && (
                <tr style={{ fontWeight: 'bold' }}>
                  {columnas.map((c, i) => (
                    <td key={c.key}>
                      {c.key in sumas
                        ? (c.formato ? c.formato(sumas[c.key]) : sumas[c.key])
                        : (i === 0 ? 'Total' : '')}
                    </td>
                  ))}
                  {acciones && <td></td>}
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default TablaFiltrable
