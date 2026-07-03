import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import PaginaClientes from './paginas/PaginaClientes'
import PaginaCompras from './paginas/PaginaCompras'

function App() {
  return (
    <BrowserRouter>
      <div>
        <h1>Fábrica V2</h1>

        {/* Menú de navegación */}
        <nav>
          <Link to="/clientes">Clientes</Link>
          {' | '}
          <Link to="/compras">Compras</Link>
        </nav>

        {/* Aquí se muestra la pantalla según la ruta */}
        <Routes>
          <Route path="/clientes" element={<PaginaClientes />} />
          <Route path="/compras" element={<PaginaCompras />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App