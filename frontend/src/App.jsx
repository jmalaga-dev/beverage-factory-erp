import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import PaginaClientes from './paginas/PaginaClientes'
import PaginaCompras from './paginas/PaginaCompras'
import PaginaCatalogos from './paginas/PaginaCatalogos'
import PaginaJornadas from './paginas/PaginaJornadas'
import PaginaProduccionIntermedia from './paginas/PaginaProduccionIntermedia'
import PaginaProduccionTerminada from './paginas/PaginaProduccionTerminada'
import PaginaVentas from './paginas/PaginaVentas'
import PaginaPagos from './paginas/PaginaPagos'
import PaginaGastos from './paginas/PaginaGastos'
import PaginaMermas from './paginas/PaginaMermas'
//import PaginaProrrateo from './paginas/PaginaProrrateo'  // oculto en MVP: requiere horas heredadas (v2)
import PaginaBalance from './paginas/PaginaBalance'

function App() {
  return (
    <BrowserRouter>
      <div>
        <h1>Fábrica V2</h1>

        {/* Menú de navegación */}
        <nav>
          <Link to="/catalogos">Catálogos</Link>
          {' | '}
          <Link to="/compras">Compras</Link>
          {' | '}
          <Link to="/jornadas">Jornadas</Link>
          {' | '}
          <Link to="/produccion-intermedia">Prod. Intermedia</Link>
          {' | '}
          <Link to="/produccion-terminada">Prod. Terminada</Link>
          {' | '}
          <Link to="/clientes">Clientes</Link>
          {' | '}
          <Link to="/ventas">Ventas</Link>
          {' | '}
          <Link to="/pagos">Pagos</Link>
          {' | '}
          <Link to="/gastos">Gastos</Link>
          {' | '}
          <Link to="/mermas">Mermas</Link>

          {' | '}
          <Link to="/balance">Balance</Link>
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
          <Route path="/pagos" element={<PaginaPagos />} />
          <Route path="/gastos" element={<PaginaGastos />} />
          <Route path="/mermas" element={<PaginaMermas />} />
          
          <Route path="/balance" element={<PaginaBalance />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App