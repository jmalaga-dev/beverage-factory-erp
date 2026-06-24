"""
models.py
Los 31 modelos de Fabrica V2 representados como clases de SQLAlchemy.
Cada clase = una tabla. Cada Column = una columna. ForeignKey = llave foranea.
relationship = atajo de navegacion entre objetos (reemplaza los JOIN manuales).

Convencion:
  - Clases con el nombre exacto de la tabla (mayusculas que coinciden con PostgreSQL).
  - Atributos de relacion en minuscula: singular para "uno", plural para "muchos".
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


# =========================================================
# CATALOGOS BASE
# =========================================================

class Materia_Prima(Base):
    __tablename__ = "Materia_Prima"

    Id_Materia_Prima = Column(Integer, primary_key=True)
    Descripcion_Materia_Prima = Column(String, nullable=False)
    Unidad_Materia_Prima = Column(String, nullable=False)

    compras = relationship("Compra", back_populates="materia_prima")


class Trabajador(Base):
    __tablename__ = "Trabajador"

    Id_Trabajador = Column(Integer, primary_key=True)
    Nombre_Trabajador = Column(String, nullable=False)
    Pago_Trabajador = Column(Numeric)
    Horas_Base_Trabajador = Column(Numeric)

    registros = relationship("Registro_Trabajador", back_populates="trabajador")


class Producto_Intermedio(Base):
    __tablename__ = "Producto_Intermedio"

    Id_Producto_Intermedio = Column(Integer, primary_key=True)
    Descripcion_Producto_Intermedio = Column(String, nullable=False)
    Litros_Botella_Final = Column(Numeric)

    producciones = relationship("Produccion_Intermedio", back_populates="producto_intermedio")


class Producto_Terminado(Base):
    __tablename__ = "Producto_Terminado"

    Id_Producto_Terminado = Column(Integer, primary_key=True)
    Descripcion_Producto_Terminado = Column(String, nullable=False)
    Precio_Venta_Recomendado_Producto_Terminado = Column(Numeric)

    producciones = relationship("Produccion", back_populates="producto_terminado")
    horas_mes = relationship("Horas_Producto_Mes", back_populates="producto_terminado")
    balance_detalles = relationship("Balance_Detalle_Producto", back_populates="producto_terminado")


class Sector(Base):
    __tablename__ = "Sector"

    Id_Sector = Column(Integer, primary_key=True)
    Nombre_Sector = Column(String, unique=True, nullable=False)

    clientes = relationship("Cliente", back_populates="sector")


class Cuenta(Base):
    __tablename__ = "Cuenta"

    Id_Cuenta = Column(Integer, primary_key=True)
    Nombre_Cuenta = Column(String, unique=True, nullable=False)
    Saldo_Actual_Cuenta = Column(Numeric, nullable=False, default=0)


class Grupo_Movimiento(Base):
    __tablename__ = "Grupo_Movimiento"

    Id_Grupo_Movimiento = Column(Integer, primary_key=True)
    Nombre_Grupo_Movimiento = Column(String, unique=True, nullable=False)

    movimientos = relationship("Movimiento", back_populates="grupo")


class Deuda(Base):
    __tablename__ = "Deuda"

    Id_Deuda = Column(Integer, primary_key=True)
    Descripcion_Deuda = Column(String, unique=True, nullable=False)
    Saldo_Actual_Deuda = Column(Numeric, nullable=False, default=0)

    movimientos = relationship("Movimiento_Deuda", back_populates="deuda")


class Tipo_Bien(Base):
    __tablename__ = "Tipo_Bien"

    Id_Tipo_Bien = Column(Integer, primary_key=True)
    Nombre_Tipo_Bien = Column(String, unique=True, nullable=False)

    activos = relationship("Activo", back_populates="tipo_bien")


class Gasto_Extra(Base):
    __tablename__ = "Gasto_Extra"

    Id_Gasto_Extra = Column(Integer, primary_key=True)
    Descripcion_Gasto_Extra = Column(String, nullable=False)
    Precio_Mensual_Gasto_Extra = Column(Numeric)

    prorrateos = relationship("Prorrateo_Mensual", back_populates="gasto_extra")


# =========================================================
# FINANZAS
# =========================================================

class Movimiento(Base):
    __tablename__ = "Movimiento"

    Id_Movimiento = Column(Integer, primary_key=True)
    Fecha_Movimiento = Column(Date, nullable=False)
    Tipo_Movimiento = Column(String, nullable=False)
    Id_Cuenta_Origen = Column(Integer, ForeignKey("Cuenta.Id_Cuenta"), nullable=True)
    Id_Cuenta_Destino = Column(Integer, ForeignKey("Cuenta.Id_Cuenta"), nullable=True)
    Monto_Movimiento = Column(Numeric, nullable=False)
    Descripcion_Movimiento = Column(String)
    Id_Grupo_Movimiento = Column(Integer, ForeignKey("Grupo_Movimiento.Id_Grupo_Movimiento"), nullable=True)

    # Dos FK a la misma tabla Cuenta: hay que indicar cual usa cada relacion
    cuenta_origen = relationship("Cuenta", foreign_keys=[Id_Cuenta_Origen])
    cuenta_destino = relationship("Cuenta", foreign_keys=[Id_Cuenta_Destino])
    grupo = relationship("Grupo_Movimiento", back_populates="movimientos")


class Movimiento_Deuda(Base):
    __tablename__ = "Movimiento_Deuda"

    Id_Movimiento_Deuda = Column(Integer, primary_key=True)
    Id_Deuda = Column(Integer, ForeignKey("Deuda.Id_Deuda"), nullable=False)
    Fecha_Movimiento_Deuda = Column(Date, nullable=False)
    Tipo_Movimiento_Deuda = Column(String, nullable=False)
    Monto_Movimiento_Deuda = Column(Numeric, nullable=False)
    Id_Cuenta_Pago = Column(Integer, ForeignKey("Cuenta.Id_Cuenta"), nullable=True)

    deuda = relationship("Deuda", back_populates="movimientos")
    cuenta_pago = relationship("Cuenta")


# =========================================================
# ACTIVOS FIJOS
# =========================================================

class Activo(Base):
    __tablename__ = "Activo"

    Id_Activo = Column(Integer, primary_key=True)
    Id_Tipo_Bien = Column(Integer, ForeignKey("Tipo_Bien.Id_Tipo_Bien"), nullable=False)
    Descripcion_Activo = Column(String, nullable=False)
    Valor_Activo = Column(Numeric, nullable=False)

    tipo_bien = relationship("Tipo_Bien", back_populates="activos")


# =========================================================
# COMPRAS
# =========================================================

class Compra(Base):
    __tablename__ = "Compra"

    Id_Compra = Column(Integer, primary_key=True)
    Id_Materia_Prima = Column(Integer, ForeignKey("Materia_Prima.Id_Materia_Prima"), nullable=False)
    Fecha_Compra = Column(Date, nullable=False)
    Cantidad_Compra = Column(Numeric, nullable=False)
    Precio_Compra = Column(Numeric, nullable=False)
    Cantidad_Restante_Compra = Column(Numeric, nullable=False)
    Id_Movimiento = Column(Integer, ForeignKey("Movimiento.Id_Movimiento"), nullable=True)

    materia_prima = relationship("Materia_Prima", back_populates="compras")
    movimiento = relationship("Movimiento")


# =========================================================
# JORNADAS DE TRABAJO
# =========================================================

class Registro_Trabajador(Base):
    __tablename__ = "Registro_Trabajador"

    Id_Registro_Trabajador = Column(Integer, primary_key=True)
    Id_Trabajador = Column(Integer, ForeignKey("Trabajador.Id_Trabajador"), nullable=False)
    Fecha_Registro_Trabajador = Column(Date, nullable=False)
    Horas_Registro_Trabajador = Column(Numeric, nullable=False)
    Horas_Restante_Registro_Trabajador = Column(Numeric)
    Id_Movimiento = Column(Integer, ForeignKey("Movimiento.Id_Movimiento"), nullable=True)
    Id_Pago_Trabajador = Column(Integer, ForeignKey("Pago_Trabajador.Id_Pago_Trabajador"), nullable=True)  # NUEVO

    trabajador = relationship("Trabajador", back_populates="registros")
    movimiento = relationship("Movimiento")
    pago = relationship("Pago_Trabajador", back_populates="jornadas")  # NUEVO


# =========================================================
# PAGO DE HORAS DE TRABAJO
# =========================================================

class Pago_Trabajador(Base):
    __tablename__ = "Pago_Trabajador"

    Id_Pago_Trabajador = Column(Integer, primary_key=True)
    Id_Trabajador = Column(Integer, ForeignKey("Trabajador.Id_Trabajador"), nullable=False)
    Fecha_Pago_Trabajador = Column(Date, nullable=False)
    Monto_Sugerido_Pago = Column(Numeric)
    Monto_Real_Pago = Column(Numeric, nullable=False)
    Id_Movimiento = Column(Integer, ForeignKey("Movimiento.Id_Movimiento"), nullable=True)

    trabajador = relationship("Trabajador")
    movimiento = relationship("Movimiento")
    # Las jornadas que cubre este pago (la relacion inversa)
    jornadas = relationship("Registro_Trabajador", back_populates="pago")


# =========================================================
# PRODUCCION INTERMEDIA + DETALLES
# =========================================================

class Produccion_Intermedio(Base):
    __tablename__ = "Produccion_Intermedio"

    Id_Produccion_Intermedio = Column(Integer, primary_key=True)
    Id_Producto_Intermedio = Column(Integer, ForeignKey("Producto_Intermedio.Id_Producto_Intermedio"), nullable=False)
    Fecha_Produccion_Intermedio = Column(Date, nullable=False)
    Cantidad_Producida = Column(Numeric, nullable=False)
    Cantidad_Restante_Producida = Column(Numeric, nullable=False)
    Costo_Unitario_Produccion_Intermedio = Column(Numeric)  # NUEVO

    producto_intermedio = relationship("Producto_Intermedio", back_populates="producciones")
    detalle_mp = relationship("Detalle_PI_Materia_Prima", back_populates="produccion")
    detalle_trabajo = relationship("Detalle_PI_Trabajo", back_populates="produccion")


class Detalle_PI_Materia_Prima(Base):
    __tablename__ = "Detalle_PI_Materia_Prima"

    Id_Detalle_PI_MP = Column(Integer, primary_key=True)
    Id_Produccion_Intermedio = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=False)
    Id_Compra = Column(Integer, ForeignKey("Compra.Id_Compra"), nullable=False)
    Cantidad_Usada = Column(Numeric, nullable=False)

    produccion = relationship("Produccion_Intermedio", back_populates="detalle_mp")
    compra = relationship("Compra")


class Detalle_PI_Trabajo(Base):
    __tablename__ = "Detalle_PI_Trabajo"

    Id_Detalle_PI_Trab = Column(Integer, primary_key=True)
    Id_Produccion_Intermedio = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=False)
    Id_Registro_Trabajador = Column(Integer, ForeignKey("Registro_Trabajador.Id_Registro_Trabajador"), nullable=False)
    Horas_Usadas = Column(Numeric, nullable=False)

    produccion = relationship("Produccion_Intermedio", back_populates="detalle_trabajo")
    registro = relationship("Registro_Trabajador")


class Detalle_PI_Intermedio(Base):
    __tablename__ = "Detalle_PI_Intermedio"

    Id_Detalle_PI_Int = Column(Integer, primary_key=True)
    Id_Produccion_Intermedio = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=False)
    Id_Produccion_Intermedio_Origen = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=False)
    Cantidad_Usada = Column(Numeric, nullable=False)

    # Dos FK a la misma tabla: hay que indicar cual usa cada relacion
    produccion = relationship("Produccion_Intermedio", foreign_keys=[Id_Produccion_Intermedio])
    produccion_origen = relationship("Produccion_Intermedio", foreign_keys=[Id_Produccion_Intermedio_Origen])


# =========================================================
# PRODUCCION (producto terminado) + DETALLES
# =========================================================

class Produccion(Base):
    __tablename__ = "Produccion"

    Id_Produccion = Column(Integer, primary_key=True)
    Id_Producto_Terminado = Column(Integer, ForeignKey("Producto_Terminado.Id_Producto_Terminado"), nullable=False)
    Fecha_Produccion = Column(Date, nullable=False)
    Cantidad_Producida_Produccion = Column(Numeric, nullable=False)
    Precio_Unitario_Producto_Terminado = Column(Numeric)
    Cantidad_Restante_Produccion = Column(Numeric, nullable=False)

    producto_terminado = relationship("Producto_Terminado", back_populates="producciones")
    detalle_intermedio = relationship("Detalle_Prod_Intermedio", back_populates="produccion")
    detalle_mp = relationship("Detalle_Prod_Materia_Prima", back_populates="produccion")
    detalle_trabajo = relationship("Detalle_Prod_Trabajador", back_populates="produccion")
    ventas = relationship("Detalle_Venta", back_populates="produccion")


class Detalle_Prod_Intermedio(Base):
    __tablename__ = "Detalle_Prod_Intermedio"

    Id_Detalle_Prod_Int = Column(Integer, primary_key=True)
    Id_Produccion = Column(Integer, ForeignKey("Produccion.Id_Produccion"), nullable=False)
    Id_Produccion_Intermedio = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=False)
    Cantidad_Usada = Column(Numeric, nullable=False)

    produccion = relationship("Produccion", back_populates="detalle_intermedio")
    produccion_intermedio = relationship("Produccion_Intermedio")


class Detalle_Prod_Materia_Prima(Base):
    __tablename__ = "Detalle_Prod_Materia_Prima"

    Id_Detalle_Prod_MP = Column(Integer, primary_key=True)
    Id_Produccion = Column(Integer, ForeignKey("Produccion.Id_Produccion"), nullable=False)
    Id_Compra = Column(Integer, ForeignKey("Compra.Id_Compra"), nullable=False)
    Cantidad_Usada = Column(Numeric, nullable=False)

    produccion = relationship("Produccion", back_populates="detalle_mp")
    compra = relationship("Compra")


class Detalle_Prod_Trabajador(Base):
    __tablename__ = "Detalle_Prod_Trabajador"

    Id_Detalle_Prod_Trab = Column(Integer, primary_key=True)
    Id_Produccion = Column(Integer, ForeignKey("Produccion.Id_Produccion"), nullable=False)
    Id_Registro_Trabajador = Column(Integer, ForeignKey("Registro_Trabajador.Id_Registro_Trabajador"), nullable=False)
    Horas_Usadas = Column(Numeric, nullable=False)

    produccion = relationship("Produccion", back_populates="detalle_trabajo")
    registro = relationship("Registro_Trabajador")


# =========================================================
# CLIENTES Y VENTAS
# =========================================================

class Cliente(Base):
    __tablename__ = "Cliente"

    Id_Cliente = Column(Integer, primary_key=True)
    Nombre_Cliente = Column(String, nullable=False)
    Apellido_Cliente = Column(String)
    Celular_Cliente = Column(String)
    Licoreria_Cliente = Column(String)
    Latitud_Cliente = Column(Numeric)
    Longitud_Cliente = Column(Numeric)
    Id_Sector = Column(Integer, ForeignKey("Sector.Id_Sector"), nullable=True)

    sector = relationship("Sector", back_populates="clientes")
    ventas = relationship("Venta", back_populates="cliente")


class Venta(Base):
    __tablename__ = "Venta"

    Id_Venta = Column(Integer, primary_key=True)
    Id_Cliente = Column(Integer, ForeignKey("Cliente.Id_Cliente"), nullable=False)
    Fecha_Venta = Column(Date, nullable=False)

    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("Detalle_Venta", back_populates="venta")


class Detalle_Venta(Base):
    __tablename__ = "Detalle_Venta"

    Id_Detalle_Venta = Column(Integer, primary_key=True)
    Id_Venta = Column(Integer, ForeignKey("Venta.Id_Venta"), nullable=False)
    Id_Produccion = Column(Integer, ForeignKey("Produccion.Id_Produccion"), nullable=False)
    Cantidad_Venta = Column(Numeric, nullable=False)
    Precio_Venta_Real = Column(Numeric, nullable=False)
    Id_Movimiento = Column(Integer, ForeignKey("Movimiento.Id_Movimiento"), nullable=True)

    venta = relationship("Venta", back_populates="detalles")
    produccion = relationship("Produccion", back_populates="ventas")
    movimiento = relationship("Movimiento")


# =========================================================
# GASTOS EXTRA: horas por producto/mes y prorrateo
# =========================================================

class Horas_Producto_Mes(Base):
    __tablename__ = "Horas_Producto_Mes"

    Id_Horas_Producto_Mes = Column(Integer, primary_key=True)
    Id_Producto_Terminado = Column(Integer, ForeignKey("Producto_Terminado.Id_Producto_Terminado"), nullable=False)
    Anio_Mes = Column(String, nullable=False)
    Horas_Producto_Mes = Column(Numeric, nullable=False)

    producto_terminado = relationship("Producto_Terminado", back_populates="horas_mes")
    prorrateos = relationship("Prorrateo_Mensual", back_populates="horas_mes")


class Prorrateo_Mensual(Base):
    __tablename__ = "Prorrateo_Mensual"

    Id_Prorrateo = Column(Integer, primary_key=True)
    Id_Horas_Producto_Mes = Column(Integer, ForeignKey("Horas_Producto_Mes.Id_Horas_Producto_Mes"), nullable=False)
    Id_Gasto_Extra = Column(Integer, ForeignKey("Gasto_Extra.Id_Gasto_Extra"), nullable=False)
    Gasto_Extra_Asignado = Column(Numeric, nullable=False)

    horas_mes = relationship("Horas_Producto_Mes", back_populates="prorrateos")
    gasto_extra = relationship("Gasto_Extra", back_populates="prorrateos")


# =========================================================
# MOVIMIENTOS DE INVENTARIO
# =========================================================

class Movimiento_Inventario(Base):
    __tablename__ = "Movimiento_Inventario"

    Id_Movimiento_Inventario = Column(Integer, primary_key=True)
    Fecha_Movimiento_Inventario = Column(Date, nullable=False)
    Tipo_Movimiento_Inventario = Column(String, nullable=False)
    Sentido_Movimiento_Inventario = Column(String, nullable=False)
    Origen_Lote = Column(String, nullable=False)
    Id_Compra = Column(Integer, ForeignKey("Compra.Id_Compra"), nullable=True)
    Id_Produccion = Column(Integer, ForeignKey("Produccion.Id_Produccion"), nullable=True)
    Id_Produccion_Intermedio = Column(Integer, ForeignKey("Produccion_Intermedio.Id_Produccion_Intermedio"), nullable=True)
    Cantidad_Movimiento_Inventario = Column(Numeric, nullable=False)
    Motivo_Movimiento_Inventario = Column(String)
    Ref_Reproceso = Column(Integer)

    compra = relationship("Compra")
    produccion = relationship("Produccion")
    produccion_intermedio = relationship("Produccion_Intermedio")


# =========================================================
# BALANCE (foto semanal) + detalle por producto
# =========================================================

class Balance(Base):
    __tablename__ = "Balance"

    Id_Balance = Column(Integer, primary_key=True)
    Fecha_Balance = Column(Date, nullable=False)
    Total_Efectivo = Column(Numeric)
    Total_Inmuebles = Column(Numeric)
    Total_Equipos = Column(Numeric)
    Total_Otros_Activos = Column(Numeric)
    Valor_Stock_Materia_Prima = Column(Numeric)
    Valor_Stock_Producto_Terminado = Column(Numeric)
    Total_Deudas = Column(Numeric)
    Ventas_Semana = Column(Numeric)
    Compras_Semana = Column(Numeric)
    Gastos_Semana = Column(Numeric)
    Escenario_A = Column(Numeric)
    Escenario_B = Column(Numeric)
    Escenario_C = Column(Numeric)
    Patrimonio = Column(Numeric)

    detalles = relationship("Balance_Detalle_Producto", back_populates="balance")


class Balance_Detalle_Producto(Base):
    __tablename__ = "Balance_Detalle_Producto"

    Id_Balance_Detalle = Column(Integer, primary_key=True)
    Id_Balance = Column(Integer, ForeignKey("Balance.Id_Balance"), nullable=False)
    Id_Producto_Terminado = Column(Integer, ForeignKey("Producto_Terminado.Id_Producto_Terminado"), nullable=False)
    Cantidad_En_Stock = Column(Numeric)
    Valor_En_Stock = Column(Numeric)

    balance = relationship("Balance", back_populates="detalles")
    producto_terminado = relationship("Producto_Terminado", back_populates="balance_detalles")