import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import MenuCategoria from './componentes/MenuCategoria'
import PaginaClientes from './paginas/PaginaClientes'
import PaginaCompras from './paginas/PaginaCompras'
import PaginaCatalogos from './paginas/PaginaCatalogos'
import PaginaJornadas from './paginas/PaginaJornadas'
import PaginaProduccionIntermedia from './paginas/PaginaProduccionIntermedia'
import PaginaProduccionTerminada from './paginas/PaginaProduccionTerminada'
import PaginaVentas from './paginas/PaginaVentas'
import PaginaPagos from './paginas/PaginaPagos'
import PaginaGastos from './paginas/PaginaGastos'
import PaginaTransferencias from './paginas/PaginaTransferencias'
import PaginaMermas from './paginas/PaginaMermas'
//import PaginaProrrateo from './paginas/PaginaProrrateo'  // oculto en MVP: requiere horas heredadas (v2)
import PaginaActivos from './paginas/PaginaActivos'
import PaginaBalance from './paginas/PaginaBalance'
import PaginaComparativaBalances from './paginas/PaginaComparativaBalances'

// Grupos del menu principal: agrupan las paginas por su lugar en el
// flujo del negocio, en vez de una lista plana de 11 links.
const categorias = [
  { titulo: 'Configurar', links: [
    { to: '/catalogos', label: 'Catálogos' },
  ] },
  { titulo: 'Producción', links: [
    { to: '/compras', label: 'Compras' },
    { to: '/jornadas', label: 'Jornadas' },
    { to: '/produccion-intermedia', label: 'Prod. Intermedia' },
    { to: '/produccion-terminada', label: 'Prod. Terminada' },
  ] },
  { titulo: 'Ventas', links: [
    { to: '/clientes', label: 'Clientes' },
    { to: '/ventas', label: 'Ventas' },
  ] },
  { titulo: 'Finanzas', links: [
    { to: '/pagos', label: 'Pagos' },
    { to: '/gastos', label: 'Gastos' },
    { to: '/transferencias', label: 'Transferencias' },
  ] },
  { titulo: 'Cierre', links: [
    { to: '/mermas', label: 'Mermas' },
    { to: '/activos', label: 'Activos' },
    { to: '/balance', label: 'Balance' },
    { to: '/comparar-balances', label: 'Comparar cierres' },
  ] },
]

function App() {
  return (
    <BrowserRouter>
      <div>
        <h1>Fábrica V2</h1>

        {/* Menú de navegación agrupado por categorías */}
        <nav style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap' }}>
          {categorias.map((c) => (
            <MenuCategoria key={c.titulo} titulo={c.titulo} links={c.links} />
          ))}
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
          <Route path="/transferencias" element={<PaginaTransferencias />} />
          <Route path="/mermas" element={<PaginaMermas />} />
          <Route path="/activos" element={<PaginaActivos />} />
          <Route path="/balance" element={<PaginaBalance />} />
          <Route path="/comparar-balances" element={<PaginaComparativaBalances />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App