// formato.js
// Ayudas para mostrar numeros legibles: separador de miles y decimales
// segun la convencion local (es-BO: miles con ".", decimales con ",").
// El backend devuelve numeros crudos (12756.4); estas funciones son solo
// para mostrar, nunca para calcular ni para enviar de vuelta.

// Dinero: siempre 2 decimales. Ej. 12756.4 -> "12.756,40".
export function fmtMoneda(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return new Intl.NumberFormat('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

// Numero generico: hasta `decimales` decimales (sin forzar ceros).
// Ej. fmtNumero(50, 2) -> "50", fmtNumero(4.0863, 4) -> "4,0863".
export function fmtNumero(n, decimales = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return new Intl.NumberFormat('es-BO', {
    maximumFractionDigits: decimales,
  }).format(n)
}

// Una cantidad de botellas expresada tambien en paquetes, para leer de un
// vistazo cuanto es en la unidad en que se vende. Solo presentacion.
// Ej. (56, 8) -> "56 botellas o 7 paquetes"
//     (50, 12) -> "50 botellas o 4,17 paquetes"   (no cierra un paquete exacto)
//     (56, 1)  -> "56 botellas"                   (producto suelto: no hay paquete)
export function fmtBotellasYPaquetes(botellas, botellasPorPaquete) {
  if (botellas === null || botellas === undefined || Number.isNaN(botellas)) return '—'
  const texto = `${fmtNumero(botellas)} botellas`
  // Sin paquete configurado, o paquete de 1: el paquete ES la botella, no
  // aporta nada repetir el mismo numero con otro nombre.
  if (!botellasPorPaquete || botellasPorPaquete <= 1) return texto
  return `${texto} o ${fmtNumero(botellas / botellasPorPaquete)} paquetes`
}
