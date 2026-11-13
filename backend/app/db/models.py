"""Modelos de datos (Fase 3 · Modelo de datos propuesto, §7 del plan).

Convenciones:
- Todo el dinero y las cantidades se almacenan en `Numeric` (nunca float).
- Las cantidades en inventario se expresan en *unidad base* del producto.
- Los detalles de operación guardan *snapshots* (factor, precio, costo) para que
  cambiar un dato maestro nunca altere la historia.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# --- Precisiones -----------------------------------------------------------
CANT = Numeric(20, 4)  # cantidad en unidad base
FACTOR = Numeric(20, 6)  # factor de conversión
MONEDA = Numeric(14, 2)  # importes
COSTO_UNIT = Numeric(16, 6)  # costo por unidad base


class Dimension(str, enum.Enum):
    UNIDAD = "UNIDAD"
    PESO = "PESO"
    VOLUMEN = "VOLUMEN"


class TipoMovimiento(str, enum.Enum):
    SALDO_INICIAL = "SALDO_INICIAL"
    ABASTECIMIENTO = "ABASTECIMIENTO"
    VENTA = "VENTA"
    REVERSO_VENTA = "REVERSO_VENTA"
    REVERSO_ABASTECIMIENTO = "REVERSO_ABASTECIMIENTO"
    AJUSTE_ADMINISTRATIVO = "AJUSTE_ADMINISTRATIVO"


class EstadoOperacion(str, enum.Enum):
    BORRADOR = "BORRADOR"
    CONFIRMADO = "CONFIRMADO"
    ANULADO = "ANULADO"
    REVERTIDO = "REVERTIDO"


class RolNombre(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    VENDEDOR = "vendedor"


# --- Seguridad y configuración --------------------------------------------
class Rol(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(200))

    usuarios: Mapped[list[UsuarioRol]] = relationship(back_populates="rol")


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    usuario: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list[UsuarioRol]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class UsuarioRol(Base):
    __tablename__ = "usuario_roles"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    rol_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    usuario: Mapped[Usuario] = relationship(back_populates="roles")
    rol: Mapped[Rol] = relationship(back_populates="usuarios")


class Configuracion(Base, TimestampMixin):
    __tablename__ = "configuracion"

    clave: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[str | None] = mapped_column(Text)


class Secuencia(Base):
    """Numeración de comprobantes internos (V-000123, A-000045)."""

    __tablename__ = "secuencias"

    tipo: Mapped[str] = mapped_column(String(20), primary_key=True)
    almacen_id: Mapped[int] = mapped_column(
        ForeignKey("almacenes.id", ondelete="CASCADE"), primary_key=True
    )
    valor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# --- Almacén y catálogo ----------------------------------------------------
class Almacen(Base, TimestampMixin):
    __tablename__ = "almacenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UnidadMedida(Base, TimestampMixin):
    __tablename__ = "unidades_medida"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    dimension: Mapped[Dimension] = mapped_column(
        SAEnum(Dimension, native_enum=False, length=20), nullable=False
    )
    paso_minimo: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Categoria(Base, TimestampMixin):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Marca(Base, TimestampMixin):
    __tablename__ = "marcas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Producto(Base, TimestampMixin):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))
    marca_id: Mapped[int | None] = mapped_column(ForeignKey("marcas.id"))
    unidad_base_id: Mapped[int] = mapped_column(
        ForeignKey("unidades_medida.id"), nullable=False
    )
    stock_minimo_base: Mapped[int] = mapped_column(Numeric(20, 4), default=0, nullable=False)
    permite_fraccion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    categoria: Mapped[Categoria | None] = relationship()
    marca: Mapped[Marca | None] = relationship()
    unidad_base: Mapped[UnidadMedida] = relationship()
    presentaciones: Mapped[list[PresentacionProducto]] = relationship(
        back_populates="producto", cascade="all, delete-orphan"
    )


class PresentacionProducto(Base, TimestampMixin):
    __tablename__ = "presentaciones_producto"
    __table_args__ = (UniqueConstraint("producto_id", "nombre", name="uq_pp_producto_nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    factor_base: Mapped[int] = mapped_column(FACTOR, nullable=False)
    precio_venta: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)
    costo_referencia: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)
    codigo_barras: Mapped[str | None] = mapped_column(String(64), index=True)
    es_compra: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    es_venta: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permite_fraccion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    producto: Mapped[Producto] = relationship(back_populates="presentaciones")


class Proveedor(Base, TimestampMixin):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    ruc: Mapped[str | None] = mapped_column(String(20), index=True)
    telefono: Mapped[str | None] = mapped_column(String(40))
    contacto: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(120))
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductoProveedor(Base, TimestampMixin):
    __tablename__ = "productos_proveedores"
    __table_args__ = (
        UniqueConstraint("producto_id", "proveedor_id", name="uq_pp_proveedor_producto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proveedor_id: Mapped[int] = mapped_column(
        ForeignKey("proveedores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    habitual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    presentacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("presentaciones_producto.id")
    )
    ultimo_costo: Mapped[int | None] = mapped_column(MONEDA)
    ultima_fecha_compra: Mapped[date | None] = mapped_column(Date)
    observacion: Mapped[str | None] = mapped_column(Text)


# --- Operaciones comerciales ----------------------------------------------
class Abastecimiento(Base, TimestampMixin):
    __tablename__ = "abastecimientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    proveedor_id: Mapped[int] = mapped_column(
        ForeignKey("proveedores.id"), nullable=False, index=True
    )
    almacen_id: Mapped[int] = mapped_column(
        ForeignKey("almacenes.id"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    documento: Mapped[str | None] = mapped_column(String(60), index=True)
    observaciones: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[EstadoOperacion] = mapped_column(
        SAEnum(EstadoOperacion, native_enum=False, length=20),
        default=EstadoOperacion.CONFIRMADO,
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    total: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)
    anulado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)

    proveedor: Mapped[Proveedor] = relationship()
    almacen: Mapped[Almacen] = relationship()
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    detalles: Mapped[list[DetalleAbastecimiento]] = relationship(
        back_populates="abastecimiento", cascade="all, delete-orphan"
    )


class DetalleAbastecimiento(Base):
    __tablename__ = "detalle_abastecimientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    abastecimiento_id: Mapped[int] = mapped_column(
        ForeignKey("abastecimientos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False, index=True
    )
    presentacion_id: Mapped[int] = mapped_column(
        ForeignKey("presentaciones_producto.id"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(CANT, nullable=False)
    factor_snapshot: Mapped[int] = mapped_column(FACTOR, nullable=False)
    cantidad_base: Mapped[int] = mapped_column(CANT, nullable=False)
    costo_unitario: Mapped[int] = mapped_column(MONEDA, nullable=False)
    costo_base: Mapped[int] = mapped_column(COSTO_UNIT, nullable=False)
    subtotal: Mapped[int] = mapped_column(MONEDA, nullable=False)

    abastecimiento: Mapped[Abastecimiento] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship()
    presentacion: Mapped[PresentacionProducto] = relationship()


class Venta(Base, TimestampMixin):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    almacen_id: Mapped[int] = mapped_column(
        ForeignKey("almacenes.id"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estado: Mapped[EstadoOperacion] = mapped_column(
        SAEnum(EstadoOperacion, native_enum=False, length=20),
        default=EstadoOperacion.CONFIRMADO,
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    total: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)
    costo_total: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    cliente: Mapped[str | None] = mapped_column(String(160))
    forma_pago: Mapped[str | None] = mapped_column(String(30))
    monto_recibido: Mapped[int | None] = mapped_column(MONEDA)
    vuelto: Mapped[int | None] = mapped_column(MONEDA)
    observaciones: Mapped[str | None] = mapped_column(Text)
    anulado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_anulacion: Mapped[str | None] = mapped_column(Text)

    # --- Impresión del ticket -------------------------------------------
    ticket_impreso: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impreso_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    impresion_error: Mapped[str | None] = mapped_column(Text)

    almacen: Mapped[Almacen] = relationship()
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    detalles: Mapped[list[DetalleVenta]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )
    impresiones: Mapped[list["ImpresionVenta"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )


class ImpresionVenta(Base):
    """Registro de cada impresión del ticket de una venta (auditoría de impresión)."""

    __tablename__ = "impresiones_venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)  # OK | ERROR
    mensaje: Mapped[str | None] = mapped_column(Text)
    reimpresion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    duracion_ms: Mapped[int | None] = mapped_column(Integer)

    venta: Mapped[Venta] = relationship(back_populates="impresiones")


class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False, index=True
    )
    presentacion_id: Mapped[int] = mapped_column(
        ForeignKey("presentaciones_producto.id"), nullable=False
    )
    cantidad: Mapped[int] = mapped_column(CANT, nullable=False)
    factor_snapshot: Mapped[int] = mapped_column(FACTOR, nullable=False)
    cantidad_base: Mapped[int] = mapped_column(CANT, nullable=False)
    precio_unitario: Mapped[int] = mapped_column(MONEDA, nullable=False)
    precio_original: Mapped[int | None] = mapped_column(MONEDA)
    motivo_precio: Mapped[str | None] = mapped_column(String(120))
    costo_base_snapshot: Mapped[int] = mapped_column(COSTO_UNIT, nullable=False)
    subtotal: Mapped[int] = mapped_column(MONEDA, nullable=False)
    costo_total_linea: Mapped[int] = mapped_column(MONEDA, default=0, nullable=False)

    venta: Mapped[Venta] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship()
    presentacion: Mapped[PresentacionProducto] = relationship()


# --- Inventario ------------------------------------------------------------
class Existencia(Base):
    """Existencia actual por (almacén, producto). Lectura rápida del stock."""

    __tablename__ = "existencias"
    __table_args__ = (
        UniqueConstraint("almacen_id", "producto_id", name="uq_existencias_almacen_producto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    almacen_id: Mapped[int] = mapped_column(
        ForeignKey("almacenes.id"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False, index=True
    )
    cantidad_base: Mapped[int] = mapped_column(CANT, default=0, nullable=False)
    costo_promedio_base: Mapped[int] = mapped_column(COSTO_UNIT, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class MovimientoInventario(Base):
    """Kardex: cada línea es una entrada o salida auditable del inventario."""

    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False, index=True
    )
    almacen_id: Mapped[int] = mapped_column(
        ForeignKey("almacenes.id"), nullable=False, index=True
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(
        SAEnum(TipoMovimiento, native_enum=False, length=30), nullable=False, index=True
    )
    cantidad_base_signed: Mapped[int] = mapped_column(CANT, nullable=False)
    saldo_base_despues: Mapped[int] = mapped_column(CANT, nullable=False)
    costo_unitario_base: Mapped[int] = mapped_column(COSTO_UNIT, default=0, nullable=False)
    origen_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    origen_id: Mapped[int] = mapped_column(Integer, nullable=False)
    referencia: Mapped[str | None] = mapped_column(String(40))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class AjusteInventario(Base, TimestampMixin):
    """Ajuste administrativo de inventario (pérdida, rotura, conteo)."""

    __tablename__ = "ajustes_inventario"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacenes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), nullable=False, index=True
    )
    tipo: Mapped[TipoMovimiento] = mapped_column(
        SAEnum(TipoMovimiento, native_enum=False, length=30), nullable=False
    )
    cantidad_base: Mapped[int] = mapped_column(CANT, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[EstadoOperacion] = mapped_column(
        SAEnum(EstadoOperacion, native_enum=False, length=20),
        default=EstadoOperacion.CONFIRMADO,
        nullable=False,
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entidad: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entidad_id: Mapped[int | None] = mapped_column(Integer)
    detalle: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
