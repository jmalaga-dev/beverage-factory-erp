import { useState, useEffect } from 'react'
import { apiGet } from '../api'
import TablaFiltrable from './TablaFiltrable'
import { fmtMoneda, fmtNumero } from '../formato'

// Detalle por item de una foto de balance guardada (mejora 4.6): un
// desplegable que adentro tiene los cuatro bloques, cada uno plegable a su
// vez (materia prima, intermedio, terminado y activos).
//
// Muestra lo que quedó CONGELADO en la foto, no el catálogo de hoy: la
// descripción de cada item es la copia que se guardó ese día. Por eso
// responde "cómo estaba", que es justo lo que la comparativa necesita.
//
// Las fotos anteriores a la migración 024 solo tienen el bloque de producto
// terminado. Sus otros bloques salen vacíos porque ese dato nunca se guardó,
// no porque valieran cero — y eso se aclara en pantalla, para no leer un
// hueco de datos como un stock en cero.
const BLOQUES = [
  ['MP', 'Materia prima'],
  ['INTERMEDIO', 'Producto intermedio'],
  ['TERMINADO', 'Producto terminado'],
  ['ACTIVO', 'Activos fijos'],
]

// `variante` ('a' | 'b') solo elige el color; el contenido es idéntico.
function DetalleFoto({ idBalance, titulo, variante = 'a' }) {
  const [abierto, setAbierto] = useState(false)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  // Se pide recién al desplegar, no al cargar la pantalla: son dos fotos y
  // cada una puede traer cientos de filas que casi nunca se miran.
  useEffect(() => {
    if (!abierto || idBalance == null || datos) return
    apiGet(`/balances/${idBalance}/detalle`)
      .then(setDatos)
      .catch((e) => setError(e.message))
  }, [abierto, idBalance, datos])

  // Si cambia la foto elegida, descartar lo cargado de la anterior.
  useEffect(() => { setDatos(null); setError('') }, [idBalance])

  if (idBalance == null) return null

  return (
    <div className={`detalle-foto detalle-foto--${variante}`}>
      <h3 className="detalle-foto__titulo" onClick={() => setAbierto(!abierto)}>
        {abierto ? '▾' : '▸'} {titulo}
      </h3>

      {abierto && error && <p style={{ color: '#a00' }}>{error}</p>}
      {abierto && !datos && !error && <p>Cargando…</p>}

      {abierto && datos && (
        <div className="detalle-foto__bloques" style={{ marginLeft: '1rem' }}>
          {BLOQUES.map(([clave, nombre]) => {
            const filas = datos.bloques[clave] || []
            // Un bloque vacío se muestra igual, dicho con todas las letras.
            // Si se ocultara, al comparar una foto vieja (que solo guardaba
            // producto terminado) contra una nueva, los bloques faltantes se
            // leerían como "no tenía stock de eso" en vez de "no se guardaba".
            if (filas.length === 0) {
              return (
                <p key={clave} style={{ color: '#a06000', margin: '0.3rem 0' }}>
                  <strong>{nombre}:</strong> sin detalle guardado en esta foto
                  (es anterior a que se empezara a capturar este bloque).
                </p>
              )
            }
            const esActivo = clave === 'ACTIVO'
            return (
              <TablaFiltrable
                key={clave}
                titulo={`${nombre} — ${fmtMoneda(datos.totales[clave])} Bs`}
                filas={filas}
                claveOrden="descripcion"
                columnas={[
                  { key: 'descripcion', label: nombre },
                  // Un activo es una unidad: su cantidad no significa nada.
                  ...(esActivo ? [] : [{ key: 'cantidad', label: 'Cantidad', formato: (v) => fmtNumero(v) }]),
                  { key: 'valor', label: 'Valor (Bs)', formato: (v) => fmtMoneda(v) },
                ]}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

export default DetalleFoto
