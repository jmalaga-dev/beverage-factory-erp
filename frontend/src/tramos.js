// tramos.js
// Como se lee el reparto de una linea entre las dos billeteras (bloque C).
//
// El backend devuelve, por cada linea de la tabla de gastos/compras, la lista
// de TRAMOS de los que sale: normalmente uno solo, y dos cuando la linea cruzo
// el limite de la primera billetera y se partio.
//
// Compartido por Gastos y Compras para que las dos pantallas lo digan igual.

import { fmtMoneda } from './formato'

const NOMBRE_ROL = { CASA: 'Casa', FABRICA: 'Fábrica', EXTERNO: 'Externo' }

export function nombreCuenta(rol) {
  return NOMBRE_ROL[rol] || rol
}

// Texto de la columna "Cuenta" de una linea.
//   un tramo   -> "Casa"
//   dos tramos -> "Casa 40,00 + Fábrica 30,00"
//   externa    -> "Externo (Juan)"   (no sale de ninguna cuenta propia)
// El monto solo cuando esta partida: en el caso normal ya esta en su propia
// columna y repetirlo seria ruido.
export function textoTramos(tramos) {
  if (!tramos || tramos.length === 0) return '—'
  if (tramos.length === 1) {
    const t = tramos[0]
    if (t.rol === 'EXTERNO') return `Externo${t.quien ? ` (${t.quien})` : ''}`
    return nombreCuenta(t.rol)
  }
  return tramos
    .map((t) => `${nombreCuenta(t.rol)} ${fmtMoneda(Number(t.monto))}`)
    .join(' + ')
}

export function estaPartida(tramos) {
  return !!tramos && tramos.length > 1
}

export function esExterna(tramos) {
  return !!tramos && tramos.length === 1 && tramos[0].rol === 'EXTERNO'
}
