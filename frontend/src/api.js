// api.js
// Punto unico de acceso al backend. En vez de escribir
// 'http://127.0.0.1:8000/...' en cada pantalla, todas las paginas usan
// apiGet / apiPost. Si cambia el puerto o el dominio (al desplegar),
// solo se edita BASE_URL aqui.

// La URL puede venir de una variable de entorno de Vite (VITE_API_URL), que
// se resuelve al compilar. Sirve para el despliegue con Docker, donde el
// backend no esta en 127.0.0.1:8000. Sin la variable queda el valor de
// siempre, asi que el entorno de desarrollo local no cambia en nada.
//
// El valor especial "MISMO_ORIGEN" deja la base vacia: las llamadas salen
// relativas (fetch('/clientes')) y pegan contra quien haya servido la
// pagina. Lo usa el lanzador local, donde el backend sirve el frontend
// compilado desde su mismo puerto y no hay dos origenes que conciliar. No
// alcanza con pasar la variable vacia: Vite no distingue "vacia" de "no
// definida", asi que hace falta un valor explicito.
const API_URL = import.meta.env.VITE_API_URL
const BASE_URL = API_URL === 'MISMO_ORIGEN' ? '' : (API_URL || 'http://127.0.0.1:8000')

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

// Borra un recurso (DELETE) y devuelve el JSON de respuesta.
export async function apiDelete(ruta) {
  const respuesta = await fetch(`${BASE_URL}${ruta}`, { method: 'DELETE' })
  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({}))
    throw new Error(error.detail || `Error en ${ruta}`)
  }
  return respuesta.json()
}
