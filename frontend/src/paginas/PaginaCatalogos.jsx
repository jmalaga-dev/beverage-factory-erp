import Catalogo from '../componentes/Catalogo'

// La página que junta todos los catálogos. El componente Catalogo (en
// componentes/) trae crear + listar + editar + habilitar/deshabilitar + borrar;
// aquí solo se configura cada catálogo (mejora 6.1).
function PaginaCatalogos() {
  return (
    <div>
      <h2>Catálogos</h2>
      <p style={{ fontSize: '0.9em', color: '#888' }}>
        Editar un registro es seguro (no afecta el historial). Para dar de baja algo
        que ya se usó, deshabilítalo: desaparece de los desplegables sin borrarse.
        Borrar solo está disponible si el registro no tiene historial.
      </p>

      <Catalogo
        titulo="Materia Prima"
        abiertoInicial={true}
        endpoint="materias-primas"
        idKey="id_materia_prima"
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
        abiertoInicial={false}
        endpoint="trabajadores"
        idKey="id_trabajador"
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
        abiertoInicial={false}
        endpoint="productos-terminados"
        idKey="id_producto_terminado"
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
        abiertoInicial={false}
        endpoint="productos-intermedios"
        idKey="id_producto_intermedio"
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
        abiertoInicial={false}
        endpoint="grupos"
        idKey="id_grupo"
        campos={[{ nombre: 'nombre', label: 'Nombre', tipo: 'text', obligatorio: true }]}
        camposTabla={[{ key: 'nombre', label: 'Nombre' }]}
      />

      <Catalogo
        titulo="Gasto Extra"
        abiertoInicial={false}
        endpoint="gastos-extra"
        idKey="id_gasto_extra"
        campos={[
          { nombre: 'descripcion', label: 'Descripción', tipo: 'text', obligatorio: true },
          { nombre: 'precio_mensual', label: 'Precio mensual', tipo: 'number', obligatorio: true },
        ]}
        camposTabla={[
          { key: 'descripcion', label: 'Descripción' },
          { key: 'precio_mensual', label: 'Precio/mes' },
        ]}
      />

      {/* Cuenta: solo se edita el nombre; el saldo se deriva de los movimientos,
          no se crea desde aquí. Por eso permitirCrear=false. */}
      <Catalogo
        titulo="Cuenta"
        abiertoInicial={false}
        endpoint="cuentas"
        idKey="id_cuenta"
        permitirCrear={false}
        campos={[{ nombre: 'nombre', label: 'Nombre', tipo: 'text', obligatorio: true }]}
        camposTabla={[
          { key: 'nombre', label: 'Nombre' },
          { key: 'saldo', label: 'Saldo' },
        ]}
      />
    </div>
  )
}

export default PaginaCatalogos
