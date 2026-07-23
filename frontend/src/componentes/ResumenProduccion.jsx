import { fmtNumero } from '../formato'

// Resumen consolidado antes de producir (item 6b): texto plano, mismo espíritu
// que el "detalle día a día" del Balance. Ayuda a revisar de un vistazo qué se
// va a consumir (sumado por producto, no por lote) — sirve para cazar un insumo
// equivocado (ej. tapa azul en vez de negra) sin leer lote por lote.
//
// Aparece apenas hay algún insumo cargado (manual o por receta). El encabezado
// "Se está produciendo ..." solo se muestra cuando ya hay producto y cantidad;
// las tres líneas de insumos, cuando la categoría tiene algo. Compartido por
// Producción Intermedia y Terminada.
function ResumenProduccion({ encabezado, mp, intermedio, trabajo }) {
  if (mp.length === 0 && intermedio.length === 0 && trabajo.length === 0) return null
  return (
    <div style={{ background: '#eef6ff', padding: '0.6rem', margin: '0.5rem 0', border: '1px solid #bcd' }}>
      <strong>Resumen antes de producir</strong>
      {encabezado && <div>Se está produciendo {encabezado}</div>}
      {mp.length > 0 && (
        <div>Con estas materias primas: {mp.map((m) => `${m.nombre} (${fmtNumero(m.valor, 6)})`).join(', ')}</div>
      )}
      {intermedio.length > 0 && (
        <div>Con estos productos intermedios: {intermedio.map((m) => `${m.nombre} (${fmtNumero(m.valor, 6)}${m.extra ? ' ' + m.extra : ''})`).join(', ')}</div>
      )}
      {trabajo.length > 0 && (
        <div>Con estas horas de trabajadores: {trabajo.map((t) => `${t.nombre} (${fmtNumero(t.valor, 2)} h)`).join(', ')}</div>
      )}
    </div>
  )
}

export default ResumenProduccion
