import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './App.css'
import MenuCategoria from './componentes/MenuCategoria'
import { FechaGlobalProvider, useFechaGlobal } from './componentes/FechaGlobal'
import PaginaClientes from './paginas/PaginaClientes'
import PaginaCompras from './paginas/PaginaCompras'
import PaginaCatalogos from './paginas/PaginaCatalogos'
import PaginaProveedores from './paginas/PaginaProveedores'
import PaginaJornadas from './paginas/PaginaJornadas'
import PaginaProduccionIntermedia from './paginas/PaginaProduccionIntermedia'
import PaginaProduccionTerminada from './paginas/PaginaProduccionTerminada'
import PaginaVentas from './paginas/PaginaVentas'
import PaginaPagos from './paginas/PaginaPagos'
import PaginaGastos from './paginas/PaginaGastos'
import PaginaTransferencias from './paginas/PaginaTransferencias'
import PaginaDeudas from './paginas/PaginaDeudas'
import PaginaAbsorcion from './paginas/PaginaAbsorcion'
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
    { to: '/proveedores', label: 'Proveedores' },
  ] },
  { titulo: 'Producción', links: [
    { to: '/compras', label: 'Compras' },
    { to: '/jornadas', label: 'Jornadas' },
    { to: '/produccion-intermedia', label: 'Prod. Intermedia' },
    { to: '/produccion-terminada', label: 'Prod. Terminada' },
    { to: '/absorcion', label: 'Absorción' },
  ] },
  { titulo: 'Ventas', links: [
    { to: '/clientes', label: 'Clientes' },
    { to: '/ventas', label: 'Ventas' },
  ] },
  { titulo: 'Finanzas', links: [
    { to: '/pagos', label: 'Pagos' },
    { to: '/gastos', label: 'Gastos' },
    { to: '/transferencias', label: 'Transferencias' },
    { to: '/deudas', label: 'Deudas' },
  ] },
  { titulo: 'Cierre', links: [
    { to: '/mermas', label: 'Mermas' },
    { to: '/activos', label: 'Activos' },
    { to: '/balance', label: 'Balance' },
    { to: '/comparar-balances', label: 'Comparar cierres' },
  ] },
]

// Input de la fecha global (mejora 6.10), junto al título. Si tiene valor,
// los formularios lo usan como fecha por defecto en vez de "hoy".
function FechaGlobalInput() {
  const { fechaGlobal, setFechaGlobal } = useFechaGlobal()
  return (
    <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
      <label style={{ fontSize: '0.9em', color: fechaGlobal ? '#a06000' : '#888' }}>
        Fecha para nuevos registros:{' '}
        <input type="date" value={fechaGlobal} onChange={(e) => setFechaGlobal(e.target.value)} />
        {' '}
        {fechaGlobal
          ? <span>(se usará esta fecha en vez de hoy — <button onClick={() => setFechaGlobal('')}>usar hoy</button>)</span>
          : <span>(vacío = hoy, como siempre)</span>}
      </label>
    </div>
  )
}

function AppInterno() {
  return (
    <BrowserRouter>
      <div>
        <h1>Fábrica V2</h1>
        <FechaGlobalInput />

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
          <Route path="/proveedores" element={<PaginaProveedores />} />
          <Route path="/jornadas" element={<PaginaJornadas />} />
          <Route path="/produccion-intermedia" element={<PaginaProduccionIntermedia />} />
          <Route path="/produccion-terminada" element={<PaginaProduccionTerminada />} />
          <Route path="/ventas" element={<PaginaVentas />} />
          <Route path="/pagos" element={<PaginaPagos />} />
          <Route path="/gastos" element={<PaginaGastos />} />
          <Route path="/transferencias" element={<PaginaTransferencias />} />
          <Route path="/deudas" element={<PaginaDeudas />} />
          <Route path="/absorcion" element={<PaginaAbsorcion />} />
          <Route path="/mermas" element={<PaginaMermas />} />
          <Route path="/activos" element={<PaginaActivos />} />
          <Route path="/balance" element={<PaginaBalance />} />
          <Route path="/comparar-balances" element={<PaginaComparativaBalances />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

function App() {
  return (
    <FechaGlobalProvider>
      <AppInterno />
    </FechaGlobalProvider>
  )
}

export default App