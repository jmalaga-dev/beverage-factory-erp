import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import InputCalculo from '../componentes/InputCalculo'
import { fmtMoneda } from '../formato'
import { evaluar } from '../calculo'

// Categorias fijas (ligadas a las columnas del Balance: Total_Inmuebles/
// Total_Equipos/Total_Otros_Activos). Se eligen al crear el tipo de bien,
// en vez de adivinarlas por el nombre (mejora 4.2).
const CATEGORIAS_TIPO_BIEN = [
  { valor: 'INMUEBLE', etiqueta: 'Inmueble' },
  { valor: 'EQUIPO', etiqueta: 'Equipo' },
  { valor: 'OTRO', etiqueta: 'Otro' },
]

function PaginaActivos() {
  const [tipos, setTipos] = useState([])
  const [activos, setActivos] = useState([])

  // Formulario de tipo de bien
  const [nuevoTipo, setNuevoTipo] = useState('')
  const [nuevaCategoria, setNuevaCategoria] = useState('')

  // Edicion in-line de la categoria de un tipo de bien
  const [editandoTipo, setEditandoTipo] = useState(null)
  const [editCategoria, setEditCategoria] = useState('')

  // Formulario de activo
  const [descripcion, setDescripcion] = useState('')
  const [valor, setValor] = useState('')
  const [idTipo, setIdTipo] = useState('')

  // Edicion in-line de un activo
  const [editando, setEditando] = useState(null)
  const [editDescripcion, setEditDescripcion] = useState('')
  const [editValor, setEditValor] = useState('')
  const [editTipo, setEditTipo] = useState('')

  const [mensaje, setMensaje] = useState('')

  function cargar() {
    apiGet('/tipos-bien').then(setTipos).catch(console.error)
    apiGet('/activos').then(setActivos).catch(console.error)
  }

  useEffect(() => { cargar() }, [])

  function crearTipo() {
    if (nuevoTipo.trim() === '') { setMensaje('El nombre del tipo es obligatorio'); return }
    if (nuevaCategoria === '') { setMensaje('Elige la categoría del tipo (Inmueble/Equipo/Otro)'); return }
    apiPost('/tipos-bien', { nombre: nuevoTipo, categoria: nuevaCategoria })
      .then(() => { setMensaje('Tipo de bien listo'); setNuevoTipo(''); setNuevaCategoria(''); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicionTipo(t) {
    setEditandoTipo(t.id_tipo_bien)
    setEditCategoria(t.categoria)
  }

  function guardarCategoriaTipo(id) {
    apiPatch(`/tipos-bien/${id}`, { categoria: editCategoria })
      .then(() => { setMensaje('Categoría actualizada'); setEditandoTipo(null); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function crearActivo() {
    if (descripcion.trim() === '' || valor === '' || idTipo === '') {
      setMensaje('Completa descripción, valor y tipo de bien')
      return
    }
    const valorNum = evaluar(valor)
    if (Number.isNaN(valorNum)) { setMensaje('El valor no es una operación válida'); return }
    apiPost('/activos', {
      descripcion,
      valor: valorNum,
      id_tipo_bien: parseInt(idTipo),
    })
      .then(() => {
        setMensaje('Activo registrado')
        setDescripcion(''); setValor(''); setIdTipo('')
        cargar()
      })
      .catch((e) => setMensaje(e.message))
  }

  function empezarEdicion(a) {
    setEditando(a.id_activo)
    setEditDescripcion(a.descripcion)
    setEditValor(String(a.valor))
    setEditTipo(String(a.id_tipo_bien))
  }

  function guardarEdicion(id) {
    const editValorNum = evaluar(editValor)
    if (Number.isNaN(editValorNum)) { setMensaje('El valor no es una operación válida'); return }
    apiPatch(`/activos/${id}`, {
      descripcion: editDescripcion,
      valor: editValorNum,
      id_tipo_bien: parseInt(editTipo),
    })
      .then(() => { setMensaje('Activo actualizado'); setEditando(null); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function eliminarActivo(id) {
    if (!window.confirm('¿Dar de baja este activo? No se puede deshacer.')) return
    apiDelete(`/activos/${id}`)
      .then(() => { setMensaje('Activo eliminado'); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  const totalActivos = activos.reduce((s, a) => s + a.valor, 0)

  return (
    <div>
      <h2>Activos fijos</h2>
      <p>Casa, vehículo, equipos... suman al patrimonio y a los escenarios de liquidez en el Balance.</p>

      {/* Crear tipo de bien */}
      <h3>Tipo de bien</h3>
      <div>
        <input type="text" placeholder="Nuevo tipo (ej. Casa, Vehículo de reparto)"
          value={nuevoTipo} onChange={(e) => setNuevoTipo(e.target.value)} />
        <select value={nuevaCategoria} onChange={(e) => setNuevaCategoria(e.target.value)}>
          <option value="">-- Categoría --</option>
          {CATEGORIAS_TIPO_BIEN.map((c) => (
            <option key={c.valor} value={c.valor}>{c.etiqueta}</option>
          ))}
        </select>
        <button onClick={crearTipo}>Agregar tipo</button>
      </div>

      <table border="1">
        <thead>
          <tr><th>Tipo de bien</th><th>Categoría</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {tipos.map((t) => (
            <tr key={t.id_tipo_bien}>
              <td>{t.nombre}</td>
              <td>
                {editandoTipo === t.id_tipo_bien ? (
                  <select value={editCategoria} onChange={(e) => setEditCategoria(e.target.value)}>
                    {CATEGORIAS_TIPO_BIEN.map((c) => (
                      <option key={c.valor} value={c.valor}>{c.etiqueta}</option>
                    ))}
                  </select>
                ) : (
                  CATEGORIAS_TIPO_BIEN.find((c) => c.valor === t.categoria)?.etiqueta || t.categoria
                )}
              </td>
              <td>
                {editandoTipo === t.id_tipo_bien ? (
                  <>
                    <button onClick={() => guardarCategoriaTipo(t.id_tipo_bien)}>Guardar</button>
                    {' '}<button onClick={() => setEditandoTipo(null)}>Cancelar</button>
                  </>
                ) : (
                  <button onClick={() => empezarEdicionTipo(t)}>Editar categoría</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Crear activo */}
      <h3>Nuevo activo</h3>
      <div>
        <input type="text" placeholder="Descripción"
          value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        <InputCalculo value={valor} onChange={setValor} placeholder="Valor" decimales={2} />
        <SelectorBuscable
          opciones={tipos}
          valor={idTipo}
          onCambiar={setIdTipo}
          obtenerId={(t) => t.id_tipo_bien}
          obtenerTexto={(t) => t.nombre}
          placeholder="-- Tipo de bien --"
        />
        <button onClick={crearActivo}>Registrar activo</button>
      </div>

      {mensaje && <p>{mensaje}</p>}

      <h3>Activos registrados (total: {fmtMoneda(totalActivos)} Bs)</h3>
      <table border="1">
        <thead>
          <tr><th>Descripción</th><th>Tipo</th><th>Valor</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {activos.map((a) => (
            editando === a.id_activo ? (
              <tr key={a.id_activo}>
                <td>
                  <input type="text" value={editDescripcion}
                    onChange={(e) => setEditDescripcion(e.target.value)} />
                </td>
                <td>
                  <SelectorBuscable
                    opciones={tipos}
                    valor={editTipo}
                    onCambiar={setEditTipo}
                    obtenerId={(t) => t.id_tipo_bien}
                    obtenerTexto={(t) => t.nombre}
                    placeholder="-- Tipo --"
                  />
                </td>
                <td>
                  <InputCalculo width="90px" value={editValor}
                    onChange={setEditValor} decimales={2} />
                </td>
                <td>
                  <button onClick={() => guardarEdicion(a.id_activo)}>Guardar</button>
                  {' '}<button onClick={() => setEditando(null)}>Cancelar</button>
                </td>
              </tr>
            ) : (
              <tr key={a.id_activo}>
                <td>{a.descripcion}</td>
                <td>{a.tipo_bien}</td>
                <td>{fmtMoneda(a.valor)}</td>
                <td>
                  <button onClick={() => empezarEdicion(a)}>Editar</button>
                  {' '}<button onClick={() => eliminarActivo(a.id_activo)}>Eliminar</button>
                </td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default PaginaActivos
