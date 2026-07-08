// api.js
// Punto unico de acceso al backend. En vez de escribir
// 'http://127.0.0.1:8000/...' en cada pantalla, todas las paginas usan
// apiGet / apiPost. Si cambia el puerto o el dominio (al desplegar),
// solo se edita BASE_URL aqui.

const BASE_URL = 'http://127.0.0.1:8000'

// Lee del backend y devuelve el JSON. Si la respuesta es un error,
// lanza una excepcion con el mensaje del backend (campo "detail").
export async function apiGet(ruta) {
  const respuesta = await fetch(`${BASE_URL}${ruta}`)
  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({}))
    throw new Error(error.detail || `Error al cargar ${ruta}`)
  }
  return respuesta.json()
}

// Envia datos al backend (POST con JSON) y devuelve el JSON de respuesta.
// Lanza una excepcion con el "detail" del backend si algo falla.
export async function apiPost(ruta, cuerpo) {
  const respuesta = await fetch(`${BASE_URL}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({}))
    throw new Error(error.detail || `Error en ${ruta}`)
  }
  return respuesta.json()
}

// Igual que apiPost, pero con metodo PATCH (actualizar un campo puntual).
export async function apiPatch(ruta, cuerpo) {
  const respuesta = await fetch(`${BASE_URL}${ruta}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({}))
    throw new Error(error.detail || `Error en ${ruta}`)
  }
  return respuesta.json()
}
