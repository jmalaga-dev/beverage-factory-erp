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
