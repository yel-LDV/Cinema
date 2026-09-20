# CinePy — Cine Neón 🎬

Sistema de venta de boletos de cine con interfaz gráfica en **Tkinter**, tema **neón** (morado/rosa/cian), persistencia en **SQLite**, diseño **orientado a objetos** y generación de **tickets y estados de cuenta en PDF** (reportlab).

## Características

- **Cartelera** con películas, horarios, salas y lugares disponibles.
- **Compra de boletos** con descuentos por edad y generación automática del **ticket en PDF**.
- **Validación de clasificación**: se bloquea la venta cuando la edad del cliente no cumple la clasificación de la película.
- **Cancelación de compras**: libera los lugares ocupados (una sola vez).
- **Historial de ventas** (incluye las canceladas).
- **Panel de administración**: alta/baja de películas y funciones, ver y cancelar cualquier venta.
- **Estados de cuenta en PDF**: general, por película, por día o por mes (solo cuentan ventas activas).
- Persistencia completa: **nada se pierde al cerrar el programa**.

## Arquitectura

```
CinePy/
├── main.py                  # Lanzador: elige Usuario o Panel Admin
├── requirements.txt
├── backend/                 # Lógica y datos (sin Tkinter)
│   ├── database.py           # Conexión y esquema SQLite
│   ├── models.py              # Clases de dominio + CineService (reglas de negocio)
│   └── pdf_generator.py       # TicketPDF y ReporteVentasPDF
├── frontend/                 # Interfaz del usuario final
│   ├── theme.py                # Paleta y estilos neón (compartida)
│   └── app_usuario.py          # Los 6 módulos del menú
├── panel/                    # Interfaz de administración
│   └── app_admin.py            # CRUD, ventas, reportes
├── tests/                    # Suite de pruebas (pytest)
├── data/cine.db              # Base de datos (se crea sola)
├── tickets/                  # PDFs de boletos generados
└── reportes/                 # PDFs de estados de cuenta
```

El **backend nunca toca Tkinter**; el frontend y el panel **no tocan SQL directamente**: ambas interfaces solo conversan con `CineService`, la fachada única con las reglas de negocio (disponibilidad, descuentos, clasificación, cancelación).

## Reglas de negocio

**Descuentos por edad** (configurables en `backend/models.py`):

| Edad | Descuento |
|---|---|
| 0 – 12 | 50% |
| 13 – 17 | 20% |
| 18 – 59 | 0% |
| 60+ | 30% |

**Edad mínima por clasificación** (configurable en `backend/models.py`):

| Clasificación | Edad mínima |
|---|---|
| AA, A, B | Sin restricción |
| B15 | 15 |
| C, D, R | 18 |

## Instalación

Requiere **Python 3.10+** y el paquete del sistema `python3-tk` (Tkinter).

```bash
# Debian/Ubuntu
sudo apt install -y python3-tk python3-venv

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Uso

```bash
.venv/bin/python main.py
```

En el lanzador elige **Usuario** o **Administración**:

### Módulos del usuario

1. **Mostrar películas** — cartelera con géneros, duración, clasificación y precio.
2. **Comprar boletos** — eliges función, cliente, edad y cantidad; se muestra el descuento y el total antes de confirmar. Al confirmar se genera `tickets/ticket_<folio>.pdf`.
3. **Lugares disponibles** — tablero por función (capacidad, ocupados y libres).
4. **Cancelar compra** — por folio; libera los lugares e invalida la cuenta.
5. **Mostrar ventas** — historial completo con folio, película, cliente y total.
6. **Salir**.

### Panel de administración

- **Películas**: ver catálogo, alta y baja (la baja la quita de la cartelera e impide nuevas ventas).
- **Funciones**: ver todas y crear funciones (sala, horario, capacidad).
- **Ventas**: ver cualquiera y cancelar por folio.
- **Reportes PDF**: genera estados de cuenta **general**, **por película**, **por día** (`AAAA-MM-DD`) o **por mes** (`AAAA-MM`) en `reportes/`, y los abre con el visor predeterminado.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

Cubren los bordes de descuentos (12/13/17/18/59/60 años), bloqueo por disponibilidad y clasificación, unicidad del folio, cancelación/doble cancelación, totales de reportes y generación real de PDFs.

> Los directorios `data/`, `tickets/` y `reportes/` se crean en el primer arranque. Si borras `data/cine.db`, el programa vuelve a sembrar un catálogo de ejemplo.