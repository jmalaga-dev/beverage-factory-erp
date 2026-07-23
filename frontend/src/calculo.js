// Evalúa una expresión aritmética simple escrita en una caja de texto, para
// poder tipear "45*3", "72*3" o "500*0.25" en vez de calcular a mano el total
// (items 2 y 11 — replica lo que en Excel se hacía con celdas). Solo permite
// dígitos, punto, los operadores + - * / y paréntesis: al no aceptar letras, la
// expresión no puede referenciar nada del entorno, así que evaluarla con
// Function es seguro en esta app local de un solo usuario (la coma se toma como
// separador decimal). Devuelve un número finito, o NaN si está vacía o es
// inválida — quien la use decide qué hacer con el NaN (avisar, ignorar).
export function evaluar(texto) {
  if (texto === null || texto === undefined) return NaN
  const limpio = String(texto).trim().replace(/,/g, '.')
  if (limpio === '') return NaN
  if (!/^[0-9+\-*/.()\s]+$/.test(limpio)) return NaN
  try {
    const valor = Function(`"use strict";return (${limpio})`)()
    return typeof valor === 'number' && isFinite(valor) ? valor : NaN
  } catch {
    return NaN
  }
}
