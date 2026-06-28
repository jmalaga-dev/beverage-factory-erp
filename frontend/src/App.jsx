import { useState, useEffect } from 'react'
import './App.css'

function App() {
  // Estado: aqui guardaremos la lista de clientes que venga de la API
  const [clientes, setClientes] = useState([])

  // useEffect: se ejecuta cuando el componente aparece por primera vez.
  // Aqui pedimos los clientes a la API.
  useEffect(() => {
    fetch('http://127.0.0.1:8000/clientes')        // pide a la API
      .then((respuesta) => respuesta.json())        // convierte la respuesta a JSON
      .then((datos) => setClientes(datos))          // guarda los clientes en el estado
      .catch((error) => console.error('Error al cargar clientes:', error))
  }, [])  // el [] vacio significa "solo una vez, al aparecer"

  return (
    <div>
      <h1>Fábrica V2</h1>
      <h2>Clientes</h2>

      <ul>
        {clientes.map((cliente) => (
          <li key={cliente.id_cliente}>
            {cliente.nombre} — celular: {cliente.celular || 'sin dato'}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App