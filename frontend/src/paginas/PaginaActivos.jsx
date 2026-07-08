import { useState, useEffect } from 'react'
import { apiDelete, apiGet, apiPatch, apiPost } from '../api'
import SelectorBuscable from '../componentes/SelectorBuscable'
import { fmtMoneda } from '../formato'

function PaginaActivos() {
  const [tipos, setTipos] = useState([])
  const [activos, setActivos] = useState([])

  // Formulario de tipo de bien
  const [nuevoTipo, setNuevoTipo] = useState('')

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
    apiPost('/tipos-bien', { nombre: nuevoTipo })
      .then(() => { setMensaje('Tipo de bien listo'); setNuevoTipo(''); cargar() })
      .catch((e) => setMensaje(e.message))
  }

  function crearActivo() {
    if (descripcion.trim() === '' || valor === '' || idTipo === '') {
      setMensaje('Completa descripción, valor y tipo de bien')
      return
    }
    apiPost('/activos', {
      descripcion,
      valor: parseFloat(valor),
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
    apiPatch(`/activos/${id}`, {
      descripcion: editDescripcion,
      valor: parseFloat(editValor),
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
      <p>Casa, vehículo, equipos... suman al patrimonio (Escenario A) en el Balance.</p>

      {/* Crear tipo de bien */}
      <h3>Tipo de bien</h3>
      <div>
        <input type="text" placeholder="Nuevo tipo (ej. Inmueble, Vehículo)"
          value={nuevoTipo} onChange={(e) => setNuevoTipo(e.target.value)} />
        <button onClick={crearTipo}>Agregar tipo</button>
      </div>

      {/* Crear activo */}
      <h3>Nuevo activo</h3>
      <div>
        <input type="text" placeholder="Descripción"
          value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        <input type="number" placeholder="Valor"
          value={valor} onChange={(e) => setValor(e.target.value)} />
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
                  <input type="number" style={{ width: '90px' }} value={editValor}
                    onChange={(e) => setEditValor(e.target.value)} />
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
