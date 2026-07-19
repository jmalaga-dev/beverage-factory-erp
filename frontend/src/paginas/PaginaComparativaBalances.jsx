import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import FilaBalance from '../componentes/FilaBalance'
import DetalleFoto from '../componentes/DetalleFoto'
import { filasBalance, filasMovimientos } from '../filasBalance'
import { fmtMoneda } from '../formato'

// Etiqueta de una foto en el selector. Como varias fotos pueden compartir
// fecha, se antepone el id para poder distinguirlas.
function etiquetaFoto(b) {
  return `#${b.id_balance} — ${b.fecha}`
}

function PaginaComparativaBalances() {
  const [balances, setBalances] = useState([])
  const [idA, setIdA] = useState('')
  const [idB, setIdB] = useState('')

  useEffect(() => {
    apiGet('/balances')
      .then((lista) => {
        setBalances(lista)
        // Por defecto: A = penúltima foto, B = última. Así la diferencia
        // (B − A) muestra el cambio del último cierre respecto al anterior.
        if (lista.length >= 2) {
          setIdB(String(lista[0].id_balance))
          setIdA(String(lista[1].id_balance))
        } else if (lista.length === 1) {
          setIdB(String(lista[0].id_balance))
          setIdA(String(lista[0].id_balance))
        }
      })
      .catch(console.error)
  }, [])

  const fotoA = balances.find((b) => String(b.id_balance) === idA) || null
  const fotoB = balances.find((b) => String(b.id_balance) === idB) || null

  // Diferencia B − A con color (verde sube, rojo baja). Si a alguna de las
  // dos fotos le falta el dato (columna agregada después), no se compara.
  function diff(campo) {
    if (!fotoA || !fotoB) return null
    const a = fotoA[campo]
    const b = fotoB[campo]
    if (a == null || b == null) return <span style={{ color: 'gray' }}>—</span>
    const d = b - a
    const color = d > 0 ? 'lightgreen' : d < 0 ? 'salmon' : 'gray'
    const signo = d > 0 ? '+' : ''
    return <span style={{ color }}>{signo}{fmtMoneda(d)}</span>
  }

  // Un importe de una foto: a la derecha y en rojo si es negativo. Una foto
  // vieja puede no tener un campo agregado después: se muestra '—', no 0.
  function celdaImporte(foto, campo) {
    const v = foto ? foto[campo] : null
    if (v == null) return <td className="num">—</td>
    return <td className={`num${v < 0 ? ' negativo' : ''}`}>{fmtMoneda(v)}</td>
  }

  return (
    <div>
      <h2>Comparar cierres — informe entre dos fotos de balance</h2>

      <div className="no-imprimir" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '1rem' }}>
        <label>
          <strong className="etiqueta-foto-a">Foto A</strong>:{' '}
          <select value={idA} onChange={(e) => setIdA(e.target.value)}>
            {balances.map((b) => (
              <option key={b.id_balance} value={b.id_balance}>{etiquetaFoto(b)}</option>
            ))}
          </select>
        </label>
        <label>
          <strong className="etiqueta-foto-b">Foto B</strong>:{' '}
          <select value={idB} onChange={(e) => setIdB(e.target.value)}>
            {balances.map((b) => (
              <option key={b.id_balance} value={b.id_balance}>{etiquetaFoto(b)}</option>
            ))}
          </select>
        </label>
        <button onClick={() => window.print()}>Imprimir / PDF</button>
      </div>

      {balances.length < 2 && (
        <p>Se necesitan al menos dos fotos guardadas para comparar. Tomá fotos desde la pantalla de Balance.</p>
      )}

      <table className="tabla-balance">
        <thead>
          <tr>
            <th>Concepto</th>
            <th className="num col-foto-a">Foto A {fotoA ? `(${etiquetaFoto(fotoA)})` : ''}</th>
            <th className="num col-foto-b">Foto B {fotoB ? `(${etiquetaFoto(fotoB)})` : ''}</th>
            <th className="num">Diferencia (B − A)</th>
          </tr>
        </thead>
        <tbody>
          {filasBalance.map((fila, i) => (
            <FilaBalance key={fila.campo || `sep${i}`} fila={fila}>
              {celdaImporte(fotoA, fila.campo)}
              {celdaImporte(fotoB, fila.campo)}
              <td className="num">{diff(fila.campo)}</td>
            </FilaBalance>
          ))}

          <FilaBalance fila={{ tipo: 'separador' }} />
          <tr className="bal-subtotal">
            <td colSpan="4">Movimientos de la semana previa a cada foto</td>
          </tr>
          {filasMovimientos.map((fila) => (
            <FilaBalance key={fila.campo} fila={{ ...fila, tipo: 'componente' }}>
              {celdaImporte(fotoA, fila.campo)}
              {celdaImporte(fotoB, fila.campo)}
              <td className="num">{diff(fila.campo)}</td>
            </FilaBalance>
          ))}
        </tbody>
      </table>

      {/* Detalle por item de cada foto (4.6). Va después de la tabla: primero
          se compara el conjunto, y recién si algo llama la atención se abre a
          ver de qué productos está compuesto. */}
      <h2 style={{ marginTop: '2rem' }} className="no-imprimir">Detalle por item de cada foto</h2>
      <div className="no-imprimir">
        <DetalleFoto
          variante="a"
          idBalance={fotoA ? fotoA.id_balance : null}
          titulo={`Detalle Foto A ${fotoA ? `(${etiquetaFoto(fotoA)})` : ''}`}
        />
        <DetalleFoto
          variante="b"
          idBalance={fotoB ? fotoB.id_balance : null}
          titulo={`Detalle Foto B ${fotoB ? `(${etiquetaFoto(fotoB)})` : ''}`}
        />
      </div>
    </div>
  )
}

export default PaginaComparativaBalances
