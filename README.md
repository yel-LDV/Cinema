# Cinema 🎬

Sistema de venta de boletos de cine con interfaz gráfica en **Tkinter**, tema **neón** (morado/rosa/cian), persistencia en **SQLite**, diseño **orientado a objetos** y generación de **tickets y estados de cuenta en PDF** (reportlab).

## Características

- **Pasarela de películas** con carteles (imagen o link de internet) en la home del usuario: cada película se selecciona tocando su imagen.
- **Compra de boletos** con descuentos por edad y generación automática del **ticket en PDF**.
- **Varias ventanas de cliente a la vez**: puedes abrir y operar varias ventanas de compra simultáneamente.
- **Validación de clasificación**: se bloquea la venta cuando la edad del cliente no cumple la clasificación de la película.
- **Cancelación de compras**: libera los lugares ocupados (una sola vez).
- **Historial de ventas** (incluye las canceladas).
- **Panel de administración**: alta/baja/edición de películas con cartel (archivo o URL), alta de funciones y ver/cancelar cualquier venta.
- **Estados de cuenta en PDF**: general, por película, por día o por mes (solo cuentan ventas activas).
- Persistencia completa: **nada se pierde al cerrar el programa**.

## Arquitectura

```
CinePy/
├── main.py                  # Lanzador: elige Usuario o Panel Admin
├── requirements.txt         # reportlab, pytest, Pillow
├── backend/                 # Lógica y datos (sin Tkinter)
│   ├── database.py           # Conexión y esquema SQLite (+ migraciones)
│   ├── models.py              # Clases de dominio + CineService (reglas de negocio)
│   ├── poster.py              # Guardado de carteles (archivo o URL) y miniaturas
│   └── pdf_generator.py       # TicketPDF y ReporteVentasPDF
├── frontend/                 # Interfaz del usuario final
│   ├── theme.py                # Paleta, estilos y pasarela de películas
│   └── app_usuario.py          # Home con pasarela + módulos del menú
├── panel/                    # Interfaz de administración
│   └── app_admin.py            # CRUD (con cartel), ventas, reportes
├── tests/                    # Suite de pruebas (pytest)
├── data/cine.db              # Base de datos (se crea sola)
├── data/Carteles/            # Carteles de las películas (se crean solos)
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

En el lanzador elige **Usuario** o **Administración** (este último pide usuario y contraseña).

### Módulos del usuario

1. **Cartelera (pasarela)** — la home del usuario muestra las películas como **tarjetas con su imagen**; se pueden recorrer con las flechas ◀ ▶ o la rueda del ratón. **Tocar una imagen** abre la compra de esa película (con su primera función ya preseleccionada y el mapa de asientos cargado). Si una película no tiene imagen se muestra un marcador con su título.
2. **Comprar boletos** — eliges la función y el **mapa de asientos de la sala** (verde=libre, rojo=ocupado, cian=seleccionado); el número de asientos elegidos es la cantidad de boletos. Se muestra el descuento y el total antes de confirmar. Al confirmar se genera `tickets/ticket_<folio>.pdf` con los asientos y desaparecen los botones de *Calcular* / *Confirmar compra*; un botón **Volver al inicio** te regresa a la pasarela.
3. **Lugares disponibles** — tablero por función (capacidad, ocupados y libres).
4. **Cancelar compra** — por folio; libera los asientos e invalida la cuenta.
5. **Mostrar ventas** — historial completo con folio, película, cliente y total.
6. **Salir**.

Se pueden abrir **varias ventanas de usuario a la vez** (botón *Usuario* del lanzador las veces que quieras) y operarlas sin bloques: cada ventana de compra es independiente.

### Panel de administración

- **Acceso**: se entra con las credenciales definidas en `data/config.json` (se crea en el primer intento con la cuenta inicial `admin` / `admin123`). Para agregar o cambiar cuentas de administrador solo se edita ese archivo a mano:
  ```json
  {
    "admins": [
      {"usuario": "admin", "hash": "<sha256 de la contraseña>"}
    ]
  }
  ```
  El hash se calcula con `sha256`, p. ej.: `python3 -c "import hashlib; print(hashlib.sha256('miclave'.encode()).hexdigest())"`. La contraseña nunca se guarda en texto plano y la aplicación no tiene ninguna pantalla para crear admins.
- **Películas**: ver catálogo, alta, **editar** (título, género, duración, precio, clasificación) y baja (la baja la quita de la cartelera e impide nuevas ventas). En el alta y la edición se puede asignar el **cartel** de dos formas: con el botón **"De archivo"** (file dialog) o pegando un **link de internet** y pulsando **"Usar link"**. En ambos casos la imagen se valida, se reescala y se guarda en `data/Carteles/cartel_<id>.png`, de modo que la pasarela funciona sin conexión. Formatos permitidos: `png, jpg, jpeg, gif, webp`.
- **Funciones**: ver todas, crear funciones (sala, horario, capacidad) y **ver el mapa de asientos** de cada una. Las funciones de una misma sala no pueden solaparse según la duración de la película.
- **Ventas**: ver cualquiera y cancelar por folio.
- **Reportes PDF**: genera estados de cuenta **general**, **por película**, **por día** (`AAAA-MM-DD`) o **por mes** (`AAAA-MM`) en `reportes/`, y los abre con el visor predeterminado.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

Cubren los bordes de descuentos (12/13/17/18/59/60 años), bloqueo por disponibilidad y clasificación, asientos (ocupados/liberados/al solape), edición de películas (incluida la **imagen**: guardar, conservar, borrar y migración de la columna), guardado de carteles (**archivo, URL, formatos inválidos y links rotos**), unicidad del folio, cancelación/doble cancelación, totales de reportes, autenticación (hash y login) y generación real de PDFs.

> Los directorios `data/`, `tickets/` y `reportes/` se crean en el primer arranque. Si borras `data/cine.db`, el programa vuelve a sembrar un catálogo de ejemplo.

## Solución de problemas

**Bug: al abrir el panel de administración, la pantalla de inicio quedaba encima y los menús "no respondían".**

- **Causa**: los paneles (`AppAdmin`, `AppUsuario`) y sus subventanas son `Toplevel` que no se elevaban sobre la raíz del lanzador; tras cerrarse el diálogo de login (con `grab_set`), el gestor de ventanas devolvía el foco al lanzador y lo apilaba por encima del panel, tapando su columna de menús (los clics caían en el lanzador). Además, `AppAdmin` no tenía dimensiones propias (Tk lo auto-tamañaba según el contenido, desbordando pantallas pequeñas). Es un defecto dependiente del gestor de ventanas, por lo que no se detectaba bajo `xvfb` sin WM.
- **Solución aplicada**: geometría explícita y centrada en ambos paneles (`_centrar`); `lift()` + `focus_force()` al abrir paneles y subventanas; subventanas ancladas al panel (`transient(self)`) en vez de al lanzador; y `self.raiz.lower()` deja el lanzador siempre por debajo de los paneles (sigue accesible para abrir más ventanas).