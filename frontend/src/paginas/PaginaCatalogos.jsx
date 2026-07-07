import { useState, useEffect } from 'react'
import { apiGet, apiPost } from '../api'

// Componente reutilizable: un catálogo genérico de crear + listar
function Catalogo({ titulo, endpoint, campos, camposTabla }) {
  const [items, setItems] = useState([])
  const [valores, setValores] = useState({})
  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet(`/${endpoint}`).then(setItems).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function crear() {
    // Validar que los campos obligatorios estén llenos
    for (const campo of campos) {
      if (campo.obligatorio && !valores[campo.nombre]) {
        setMensaje(`${campo.label} es obligatorio`)
        return
      }
    }

    // Armar el body convirtiendo números
    const body = {}
    for (const campo of campos) {
      let v = valores[campo.nombre]
      if (campo.tipo === 'number' && v) v = parseFloat(v)
      body[campo.nombre] = v || null
    }

    apiPost(`/${endpoint}`, body)
      .then(() => {
        setMensaje(`${titulo} creado`)
        setValores({})
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  return (
    <div style={{ marginBottom: '2rem' }}>
      <h3>{titulo}</h3>
      <div>
        {campos.map((campo) => (
          <input
            key={campo.nombre}
            type={campo.tipo === 'number' ? 'number' : 'text'}
            placeholder={campo.label}
            value={valores[campo.nombre] || ''}
            onChange={(e) => setValores({ ...valores, [campo.nombre]: e.target.value })}
          />
        ))}
        <button onClick={crear}>Agregar</button>
      </div>
      {mensaje && <p>{mensaje}</p>}
      <table border="1">
        <thead>
          <tr>{camposTabla.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i}>
              {camposTabla.map((c) => <td key={c.key}>{item[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// La página que junta todos los catálogos
function PaginaCatalogos() {
  return (
    <div>
      <h2>Catálogos</h2>

      <Catalogo
        titulo="Materia Prima"
        endpoint="materias-primas"
        campos={[
          { nombre: 'descripcion', label: 'Descripción', tipo: 'text', obligatorio: true },
          { nombre: 'unidad', label: 'Unidad', tipo: 'text', obligatorio: true },
        ]}
        camposTabla={[
          { key: 'descripcion', label: 'Descripción' },
          { key: 'unidad', label: 'Unidad' },
        ]}
      />

      <Catalogo
        titulo="Trabajador"
        endpoint="trabajadores"
        campos={[
          { nombre: 'nombre', label: 'Nombre', tipo: 'text', obligatorio: true },
          { nombre: 'pago', label: 'Pago por hora', tipo: 'number', obligatorio: true },
          { nombre: 'horas_base', label: 'Horas base', tipo: 'number' },
        ]}
        camposTabla={[
          { key: 'nombre', label: 'Nombre' },
          { key: 'pago', label: 'Pago/hora' },
          { key: 'horas_base', label: 'Horas base' },
        ]}
      />

      <Catalogo
        titulo="Producto Terminado"
        endpoint="productos-terminados"
        campos={[
          { nombre: 'descripcion', label: 'Descripción', tipo: 'text', obligatorio: true },
          { nombre: 'precio_recomendado', label: 'Precio recomendado', tipo: 'number' },
        ]}
        camposTabla={[
          { key: 'descripcion', label: 'Descripción' },
          { key: 'precio_recomendado', label: 'Precio rec.' },
        ]}
      />

      <Catalogo
        titulo="Producto Intermedio"
        endpoint="productos-intermedios"
        campos={[
          { nombre: 'descripcion', label: 'Descripción', tipo: 'text', obligatorio: true },
          { nombre: 'litros', label: 'Litros', tipo: 'number' },
        ]}
        camposTabla={[
          { key: 'descripcion', label: 'Descripción' },
          { key: 'litros', label: 'Litros' },
        ]}
      />

      <Catalogo
        titulo="Grupo de Movimiento"
        endpoint="grupos"
        campos={[{ nombre: 'nombre', label: 'Nombre', tipo: 'text', obligatorio: true }]}
        camposTabla={[{ key: 'nombre', label: 'Nombre' }]}
      />

      <Catalogo
        titulo="Gasto Extra"
        endpoint="gastos-extra"
        campos={[
          { nombre: 'descripcion', label: 'Descripción', tipo: 'text', obligatorio: true },
          { nombre: 'precio_mensual', label: 'Precio mensual', tipo: 'number', obligatorio: true },
        ]}
        camposTabla={[
          { key: 'descripcion', label: 'Descripción' },
          { key: 'precio_mensual', label: 'Precio/mes' },
        ]}
      />
    </div>
  )
}

export default PaginaCatalogos