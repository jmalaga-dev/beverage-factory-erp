// Consolidado de insumos para el resumen pre-producción (item 6b), compartido
// por Producción Intermedia y Terminada (ambas arman las mismas listas de
// insumos). Agrupa POR PRODUCTO, no por lote: suma todas las líneas de una
// misma materia prima / intermedio / trabajador en una sola. Es solo una vista
// para revisar antes de confirmar — el backend sigue recibiendo los lotes
// explícitos y validando el stock; esto no cambia lo que se envía.
//
// Cada helper devuelve [{ nombre, valor, extra }]: `valor` es la cantidad (u
// horas) sumada, `extra` una etiqueta opcional (la unidad del intermedio).

function agrupar(items) {
  const mapa = {}
  for (const it of items) {
    if (!mapa[it.nombre]) mapa[it.nombre] = { nombre: it.nombre, extra: it.extra, valor: 0 }
    mapa[it.nombre].valor += it.valor
  }
  return Object.values(mapa)
}

export function resumenMateriaPrima(insumosMP, lotes) {
  return agrupar(insumosMP.map((x) => {
    const lote = lotes.find((l) => l.id_compra === x.id_compra)
    return { nombre: lote ? lote.nombre_materia : `Lote ${x.id_compra}`, valor: x.cantidad }
  }))
}

export function resumenIntermedios(insumosIntermedio, intermedios) {
  return agrupar(insumosIntermedio.map((x) => {
    const prod = intermedios.find((p) => p.id_produccion_intermedio === x.id_prod)
    return { nombre: prod ? prod.descripcion : `Lote ${x.id_prod}`, extra: prod ? prod.unidad : '', valor: x.cantidad }
  }))
}

export function resumenTrabajo(insumosTrabajo, jornadas) {
  return agrupar(insumosTrabajo.map((x) => {
    const j = jornadas.find((jj) => jj.id_jornada === x.id_registro)
    return { nombre: j ? j.nombre_trabajador : `Jornada ${x.id_registro}`, valor: x.horas }
  }))
}
