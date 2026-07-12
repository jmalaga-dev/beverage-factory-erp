// insumos.js
// Helper para fusionar lineas de insumo del mismo lote: si un lote ya está en
// la lista, suma su cantidad en vez de agregar una fila duplicada. Así FIFO,
// recetas y el agregado manual no dejan filas repetidas del mismo lote (que
// además el backend rechazaría o sumaría defensivamente).
//   lista: filas actuales, nuevos: filas a agregar, campoId: 'id_compra' | 'id_prod' | 'id_registro'
//   campoCantidad: 'cantidad' | 'horas' (default 'cantidad')
export function fusionar(lista, nuevos, campoId, campoCantidad = 'cantidad') {
  const resultado = lista.map((x) => ({ ...x }))
  for (const n of nuevos) {
    const existente = resultado.find((x) => x[campoId] === n[campoId])
    if (existente) existente[campoCantidad] += n[campoCantidad]
    else resultado.push({ ...n })
  }
  return resultado
}
