import { createContext, useContext, useState } from 'react'

// Fecha global (mejora 6.10): si se llena, todos los formularios que crean
// registros con fecha la usan por defecto en vez de "hoy". Pensado para el
// caso real de cargar datos atrasados (una semana sin poder registrar, se
// anota en papel y se pasa todo cronológicamente el fin de semana). El
// backend ya acepta `fecha` explícita en todo (`fecha or date.today()`), así
// que esto es puramente un valor por defecto en el frontend.
const FechaGlobalContext = createContext(null)

export function FechaGlobalProvider({ children }) {
  const [fechaGlobal, setFechaGlobal] = useState('')  // '' = usar hoy (comportamiento actual)
  return (
    <FechaGlobalContext.Provider value={{ fechaGlobal, setFechaGlobal }}>
      {children}
    </FechaGlobalContext.Provider>
  )
}

// Hook de conveniencia: devuelve la fecha a mandar en un POST (o null si no
// hay fecha global fijada, para que el backend use hoy como siempre).
export function useFechaGlobal() {
  const ctx = useContext(FechaGlobalContext)
  if (!ctx) throw new Error('useFechaGlobal debe usarse dentro de FechaGlobalProvider')
  return {
    fechaGlobal: ctx.fechaGlobal,
    setFechaGlobal: ctx.setFechaGlobal,
    fechaParaEnviar: ctx.fechaGlobal || null,
  }
}
