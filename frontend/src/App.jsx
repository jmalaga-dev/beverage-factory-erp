import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import PaginaClientes from './paginas/PaginaClientes'
import PaginaCompras from './paginas/PaginaCompras'
import PaginaCatalogos from './paginas/PaginaCatalogos'
import PaginaJornadas from './paginas/PaginaJornadas'
import PaginaProduccionIntermedia from './paginas/PaginaProduccionIntermedia'
import PaginaProduccionTerminada from './paginas/PaginaProduccionTerminada'
import PaginaVentas from './paginas/PaginaVentas'

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
          {' | '}
          <Link to="/catalogos">Catálogos</Link>
          {' | '}
          <Link to="/jornadas">Jornadas</Link>
          {' | '}
          <Link to="/produccion-intermedia">Prod. Intermedia</Link>
          {' | '}
          <Link to="/produccion-terminada">Prod. Terminada</Link>
          {' | '}
          <Link to="/ventas">Ventas</Link>
        </nav>

        {/* Aquí se muestra la pantalla según la ruta */}
        <Routes>
          <Route path="/clientes" element={<PaginaClientes />} />
          <Route path="/compras" element={<PaginaCompras />} />
          <Route path="/catalogos" element={<PaginaCatalogos />} />
          <Route path="/jornadas" element={<PaginaJornadas />} />
          <Route path="/produccion-intermedia" element={<PaginaProduccionIntermedia />} />
          <Route path="/produccion-terminada" element={<PaginaProduccionTerminada />} />
          <Route path="/ventas" element={<PaginaVentas />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App