# Cinema 🎬

Sistema de venta de boletos de cine con interfaz gráfica en **Tkinter**, tema
**neón** (morado/rosa/cian), persistencia en **MariaDB**, diseño **orientado a
objetos**, modelo de datos **normalizado a 3FN** y generación de **tickets y
estados de cuenta en PDF** (reportlab).

## Características

- **Pasarela de películas** con carteles (imagen o link de internet) en la home
  del usuario: cada película se selecciona tocando su imagen.
- **Compra de boletos** con descuentos por edad y generación automática del
  **ticket en PDF**.
- **Varias ventanas de cliente a la vez**: puedes abrir y operar varias ventanas
  de compra simultáneamente.
- **Validación de clasificación**: se bloquea la venta cuando la edad del
  cliente no cumple la clasificación de la película.
- **Asientos físicos compartidos** entre funciones: cada sala tiene sus
  asientos y la ocupación se calcula por función.
- **Cancelación de compras**: la venta pasa a `cancelada` y sus asientos vuelven
  a estar disponibles sin borrar el historial.
- **Historial de ventas** (incluye las canceladas).
- **Panel de administración**: alta/baja/edición de películas con cartel
  (archivo o URL), alta de funciones y ver/cancelar cualquier venta.
- **Estados de cuenta en PDF**: general, por película, por día o por mes (solo
  cuentan ventas activas).
- **Base de datos MariaDB** con conexión configurable por variables de entorno;
  **SQLite** se usa únicamente en las pruebas automáticas.
- Persistencia completa: nada se pierde al cerrar el programa.

## Arquitectura

```
CinePy/
├── main.py                       # Lanzador: elige Usuario o Panel Admin
├── requirements.txt              # reportlab, pytest, Pillow, PyMySQL
├── DIAGRAMAS.md                  # Diagramas Mermaid del proyecto y de la BD
├── .env.example                  # Variables de conexión a MariaDB
├── backend/                      # Lógica y datos (sin Tkinter)
│   ├── database.py               # Conexión MariaDB/SQLite + esquema 3FN
│   ├── models.py                 # Dominio + CineService (reglas de negocio)
│   ├── auth.py                   # Login de administración (config.json)
│   ├── poster.py                 # Carteles (archivo/URL) y miniaturas
│   └── pdf_generator.py          # TicketPDF y ReporteVentasPDF
├── frontend/                     # Interfaz del usuario final
│   ├── theme.py                  # Paleta, estilos y pasarela de películas
│   └── app_usuario.py            # Home con pasarela + módulos del menú
├── panel/                        # Interfaz de administración
│   └── app_admin.py              # CRUD (con cartel), ventas y reportes
├── scripts/
│   ├── crear_bd_mariadb.sql      # Crea base y usuario en MariaDB
│   ├── migrar_sqlite_a_mariadb.py# Migra la BD SQLite histórica
│   └── verificar_conexion.py     # Diagnóstico de conexión y esquema
├── tests/                        # Suite de pruebas (pytest + SQLite)
├── data/config.json              # Cuentas de administración (no versionado)
├── data/Carteles/                # Carteles de las películas
├── tickets/                      # PDFs de boletos generados
└── reportes/                     # PDFs de estados de cuenta
```

El **backend nunca toca Tkinter**; el frontend y el panel **no tocan SQL
directamente**: ambas interfaces conversan con `CineService`, la fachada única
con las reglas de negocio. `backend/database.py` expone la misma interfaz para
**MariaDB** (ejecución normal) y **SQLite** (pruebas).

## Modelo de datos normalizado (3FN)

El esquema está documentado con diagramas en **[DIAGRAMAS.md](DIAGRAMAS.md)**.

| Tabla | Propósito | Clave |
|---|---|---|
| `generos` | Catálogo de géneros | `id` |
| `clasificaciones` | Catálogo y edad mínima | `id`, `codigo` único |
| `salas` | Salas físicas | `id` |
| `asientos` | Asientos físicos de cada sala | `id`, único `(sala_id, fila, numero)` |
| `peliculas` | Catálogo de películas | `id`, FK a género y clasificación |
| `funciones` | Función de una película en una sala/horario | `id`, FKs |
| `clientes` | Datos del cliente | `id` |
| `descuentos` | Rangos de edad y porcentaje | `id` |
| `estados_venta` | `activa`, `cancelada` | `id` |
| `ventas` | Cabecera de la venta (precio y descuento históricos) | `id`, `folio` único |
| `boletos` | Relación N:M entre venta y asiento | PK `(venta_id, asiento_id)` |

Decisiones de normalización:

- **1FN**: columnas atómicas, sin listas repetidas. La posición del asiento se
  deriva de `fila` + `numero`; no se almacena.
- **2FN**: `boletos` usa una clave compuesta y no tiene atributos que dependan
  solo de una parte de la clave.
- **3FN**: los catálogos están separados (género, clasificación, descuento,
  estado), los asientos son físicos y compartidos por las funciones de una sala,
  y el cliente vive en su propia tabla.
- **Sin redundancia derivada**: `funciones` no guarda `capacidad` ni `ocupados`;
  `asientos` no guarda `estado`; `ventas` no guarda `cantidad_boletos` ni
  `total`. Todo se calcula con joins/agregados al consultar.
- **Snapshots históricos**: `ventas.precio_unitario` y `ventas.descuento_pct`
  conservan el precio y descuento aplicados al momento de la compra; no se
  recalculan si cambia la película o la tabla de descuentos.

## Reglas de negocio

**Descuentos por edad** (sembrados en la tabla `descuentos`):

| Edad | Descuento |
|---|---|
| 0 – 12 | 50% |
| 13 – 17 | 20% |
| 18 – 59 | 0% |
| 60+ | 30% |

**Edad mínima por clasificación** (sembrada en `clasificaciones`):

| Clasificación | Edad mínima |
|---|---|
| AA, A, B | Sin restricción |
| B15 | 15 |
| C, D, R | 18 |

## Requisitos

- **Python 3.10+** y Tkinter (`python3-tk`).
- **MariaDB 10.5+** (probado con MariaDB 10.11).
- Dependencias de Python en `requirements.txt` (`PyMySQL`, `reportlab`,
  `Pillow`, `pytest`).

## Instalación

```bash
# Debian/Ubuntu
sudo apt install -y python3-tk python3-venv mariadb-server

# Entorno virtual
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Base y usuario de MariaDB (una sola vez)
sudo mariadb < scripts/crear_bd_mariadb.sql
```

## Conexión a la base de datos

La conexión se configura con variables de entorno:

| Variable | Valor por defecto |
|---|---|
| `CINEMA_DB_HOST` | `127.0.0.1` |
| `CINEMA_DB_PORT` | `3306` |
| `CINEMA_DB_USER` | `cinema` |
| `CINEMA_DB_PASSWORD` | `cinema123` |
| `CINEMA_DB_NAME` | `cinema` |

Puedes copiar `.env.example` a `.env`, exportar las variables en la shell o
cambiar los valores directamente:

```bash
export CINEMA_DB_USER=cinema
export CINEMA_DB_PASSWORD=cinema123
export CINEMA_DB_NAME=cinema
```

Verifica la conexión y el esquema:

```bash
.venv/bin/python scripts/verificar_conexion.py
```

`CineService()` usa MariaDB por defecto. Cuando se le pasa una ruta de archivo
(`CineService("ruta.db")`), usa SQLite; esto es lo que hacen las pruebas para no
depender del servidor.

## Migración desde la versión SQLite

La versión anterior guardaba todo en `data/cine.db`. El script de migración
conserva películas, funciones, ventas, folios, fechas, estados y asientos:

```bash
# Migrar data/cine.db a la base MariaDB configurada
.venv/bin/python scripts/migrar_sqlite_a_mariadb.py

# Reemplazar los datos del destino (borra las tablas antes de migrar)
.venv/bin/python scripts/migrar_sqlite_a_mariadb.py --recrear
```

El destino debe estar vacío salvo que se use `--recrear`. Las salas se crean con
la capacidad máxima encontrada para cada nombre y los asientos físicos se
comparten entre funciones.

## Uso

```bash
.venv/bin/python main.py
```

En el lanzador elige **Usuario** o **Administración** (este último pide usuario y
contraseña).

### Módulos del usuario

1. **Cartelera (pasarela)** — tarjetas con la imagen de cada película; se
   recorren con ◀ ▶ o la rueda del ratón. Tocar una imagen abre la compra.
2. **Comprar boletos** — eliges función y asientos en el mapa de la sala
   (verde=libre, rojo=ocupado, cian=seleccionado). Se muestra el descuento y el
   total antes de confirmar. Al confirmar se genera
   `tickets/ticket_<folio>.pdf`.
3. **Lugares disponibles** — capacidad, ocupados y libres por función.
4. **Cancelar compra** — por folio; la venta queda cancelada y los asientos se
   liberan sin borrar el historial.
5. **Mostrar ventas** — historial completo.
6. **Salir**.

Se pueden abrir varias ventanas de usuario a la vez.

### Panel de administración

- **Acceso**: credenciales en `data/config.json` (se crea con `admin` /
  `admin123` en el primer intento). Para cambiar cuentas se edita el archivo:
  ```json
  {
    "admins": [
      {"usuario": "admin", "hash": "<sha256 de la contraseña>"}
    ]
  }
  ```
  El hash se calcula con:
  `python3 -c "import hashlib; print(hashlib.sha256('miclave'.encode()).hexdigest())"`.
  La contraseña nunca se guarda en texto plano.
- **Películas**: ver catálogo, alta, edición y baja. El cartel se asigna con
  **"De archivo"** o pegando un **link** y pulsando **"Usar link"**. La imagen se
  valida, reescala y guarda en `data/Carteles/cartel_<id>.png`.
- **Funciones**: ver todas, crear funciones (sala, horario, capacidad) y ver el
  mapa de asientos. Las funciones de una misma sala no pueden solaparse.
- **Ventas**: ver cualquiera y cancelar por folio.
- **Reportes PDF**: general, por película, por día (`AAAA-MM-DD`) o por mes
  (`AAAA-MM`) en `reportes/`, y los abre con el visor predeterminado.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

Las pruebas usan una base SQLite temporal (no requieren MariaDB) y cubren
descuentos, clasificación, asientos físicos compartidos, ocupación derivada,
normalización, compras, cancelaciones, horarios, edición de películas, carteles
(archivo/URL/errores), autenticación, reportes y generación real de PDFs.

## Solución de problemas

**No se puede conectar a MariaDB**

- Comprueba el servicio: `sudo systemctl status mariadb`.
- Ejecuta `sudo mariadb < scripts/crear_bd_mariadb.sql`.
- Revisa `CINEMA_DB_*` y prueba `.venv/bin/python scripts/verificar_conexion.py`.

**El panel de administración queda detrás del lanzador**

- Se corrigió con geometría centrada, `lift()`/`focus_force()` y
  `self.raiz.lower()` al abrir paneles y subventanas. Es un comportamiento
  dependiente del gestor de ventanas.

> Los directorios `data/`, `tickets/` y `reportes/` se crean en el primer
> arranque. Los carteles y los PDFs no se versionan.
