// Una fila de la tabla de balance: arma la primera celda (signo, asterisco y
// etiqueta) y le pone la clase segun el `tipo` de la fila (ver filasBalance.js,
// que define la estructura). Las celdas de importes las pasa quien la usa
// (`children`), porque cada pantalla saca sus valores de fuentes distintas:
// Balance compara última foto contra estado actual, y Comparativa compara dos
// fotos guardadas.
//
// Vive aparte porque las dos pantallas la necesitan igual: si el render
// estuviera copiado en cada una, volverían a separarse con el tiempo — que es
// justo lo que ya había pasado con la lista de filas.

const CLASE_POR_TIPO = {
  componente: 'bal-componente',
  subcomponente: 'bal-subcomponente',
  grupo: 'bal-grupo',
  nota: 'bal-nota',
  subtotal: 'bal-subtotal',
}

function FilaBalance({ fila, children }) {
  if (fila.tipo === 'separador') {
    return <tr className="bal-separador"><td colSpan="4" /></tr>
  }

  const clase = CLASE_POR_TIPO[fila.tipo] + (fila.destacado ? ' bal-destacado' : '')
  const esDesglose = fila.tipo === 'subcomponente' || fila.tipo === 'nota'

  return (
    <tr className={clase}>
      <td>
        {fila.signo && <span className="op">{fila.signo}</span>}
        {esDesglose ? '*' : ''}
        {fila.label}
      </td>
      {children}
    </tr>
  )
}

export default FilaBalance
