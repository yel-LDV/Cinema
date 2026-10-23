# Diagramas de Cinema

Este archivo contiene el código **Mermaid** de los diagramas del proyecto. Se
puede visualizar directamente en GitHub, en VS Code (extensión Markdown
Preview Mermaid) o pegando cada bloque en <https://mermaid.live>.

## 1. Diagrama general del proyecto

```mermaid
flowchart TD
    subgraph GUI["Capa de presentación (Tkinter)"]
        L["main.py<br/>Lanzador"]
        U["frontend/app_usuario.py<br/>AppUsuario"]
        A["panel/app_admin.py<br/>AppAdmin"]
        TH["frontend/theme.py<br/>tema, tablas, mapa de asientos"]
    end

    subgraph NEG["Capa de negocio"]
        S["backend/models.py<br/>CineService + entidades"]
        AU["backend/auth.py<br/>login de administración"]
        PO["backend/poster.py<br/>carteles archivo/URL"]
        PDF["backend/pdf_generator.py<br/>TicketPDF / ReporteVentasPDF"]
    end

    subgraph DAT["Capa de datos y archivos"]
        DB[("MariaDB<br/>base cinema")]
        SQ[("SQLite<br/>pruebas automáticas")]
        CFG["data/config.json<br/>usuarios admin"]
        CAR["data/Carteles/<br/>cartel_&lt;id&gt;.png"]
        OUT["tickets/ y reportes/<br/>PDFs generados"]
    end

    L --> U
    L --> A
    L --> AU
    U --> TH
    A --> TH
    U --> S
    A --> S
    A --> PO
    A --> PDF
    U --> PDF
    S --> DB
    S -. "ruta .db (tests)" .-> SQ
    AU --> CFG
    PO --> CAR
    PDF --> OUT
    MIG["scripts/migrar_sqlite_a_mariadb.py"] --> DB
    SQ -. "migración histórica" .-> MIG

    classDef gui fill:#171231,stroke:#9D5CFF,color:#EDE7FF;
    classDef neg fill:#0D0B1E,stroke:#00E5FF,color:#EDE7FF;
    classDef dat fill:#241A4A,stroke:#FF2BD8,color:#EDE7FF;
    class L,U,A,TH gui;
    class S,AU,PO,PDF neg;
    class DB,SQ,CFG,CAR,OUT,MIG dat;
```

## 2. Diagrama de clases principal

```mermaid
classDiagram
    class Lanzador {
        +servicio: CineService
        +raiz: Tk
        +abrir_usuario()
        +abrir_admin()
        +_pedir_login()
    }

    class AppUsuario {
        +servicio: CineService
        +_v_comprar(pelicula)
        +_v_lugares()
        +_v_cancelar()
        +_v_ventas()
    }

    class AppAdmin {
        +servicio: CineService
        +_v_alta_pelicula()
        +_v_editar_pelicula()
        +_v_alta_funcion()
        +_v_cancelar()
        +_r_general()
    }

    class CineService {
        +crear_pelicula()
        +editar_pelicula()
        +crear_funcion()
        +listar_asientos(funcion_id)
        +comprar_boletos(funcion_id, cliente, posiciones)
        +cancelar_compra(folio)
        +ventas_detalladas()
        +ventas_reporte(ambito, valor)
    }

    class Pelicula {
        +id
        +titulo
        +genero
        +duracion_min
        +clasificacion
        +precio_base
        +activa
        +imagen
    }

    class Funcion {
        +id
        +pelicula_id
        +sala
        +horario
        +capacidad
        +ocupados
        +disponibles
    }

    class Cliente {
        +nombre
        +edad
        +calcular_descuento()
        +validar_clasificacion()
    }

    class Venta {
        +id
        +folio
        +funcion_id
        +cliente_nombre
        +edad
        +cantidad_boletos
        +precio_unitario
        +descuento_pct
        +total
        +estado
    }

    Lanzador --> AppUsuario
    Lanzador --> AppAdmin
    AppUsuario --> CineService
    AppAdmin --> CineService
    CineService --> Pelicula
    CineService --> Funcion
    CineService --> Cliente
    CineService --> Venta
```

## 3. Diagrama entidad-relación de la base de datos (3FN)

```mermaid
erDiagram
    GENEROS {
        int id PK
        varchar nombre UK
    }

    CLASIFICACIONES {
        int id PK
        varchar codigo UK
        int edad_minima
    }

    SALAS {
        int id PK
        varchar nombre UK
    }

    ASIENTOS {
        int id PK
        int sala_id FK
        varchar fila
        int numero
    }

    PELICULAS {
        int id PK
        varchar titulo
        int genero_id FK
        int duracion_min
        int clasificacion_id FK
        decimal precio_base
        boolean activa
        varchar imagen
    }

    FUNCIONES {
        int id PK
        int pelicula_id FK
        int sala_id FK
        varchar horario
    }

    CLIENTES {
        int id PK
        varchar nombre
        int edad
    }

    DESCUENTOS {
        int id PK
        int edad_min
        int edad_max
        decimal porcentaje
    }

    ESTADOS_VENTA {
        int id PK
        varchar nombre UK
    }

    VENTAS {
        int id PK
        varchar folio UK
        int cliente_id FK
        int funcion_id FK
        int estado_id FK
        datetime fecha_hora
        decimal precio_unitario
        decimal descuento_pct
    }

    BOLETOS {
        int venta_id PK
        int asiento_id PK
    }

    GENEROS ||--o{ PELICULAS : "clasifica"
    CLASIFICACIONES ||--o{ PELICULAS : "restringe edad"
    SALAS ||--o{ ASIENTOS : "contiene"
    SALAS ||--o{ FUNCIONES : "alberga"
    PELICULAS ||--o{ FUNCIONES : "se programa"
    CLIENTES ||--o{ VENTAS : "realiza"
    FUNCIONES ||--o{ VENTAS : "recibe"
    ESTADOS_VENTA ||--o{ VENTAS : "define estado"
    VENTAS ||--o{ BOLETOS : "incluye"
    ASIENTOS ||--o{ BOLETOS : "se ocupa"
    DESCUENTOS }o..o{ CLIENTES : "rango de edad (conceptual)"
```

`BOLETOS` es la tabla asociativa de la relación N:M entre `VENTAS` y
`ASIENTOS`. La función de una venta se obtiene por `VENTAS.funcion_id`; la
disponibilidad de un asiento se calcula cruzando `BOLETOS` con las ventas
`activa` de esa función y la sala del asiento.

## 4. Flujo de compra y generación del ticket

```mermaid
sequenceDiagram
    actor Cliente
    participant UI as AppUsuario
    participant S as CineService
    participant DB as MariaDB
    participant PDF as TicketPDF

    Cliente->>UI: elige película, función y asientos
    UI->>S: listar_asientos(funcion_id)
    S->>DB: asientos de la sala + boletos de ventas activas
    DB-->>S: asientos y ocupación
    S-->>UI: posiciones libres/ocupadas
    Cliente->>UI: Confirma compra
    UI->>S: comprar_boletos(funcion_id, cliente, posiciones)
    S->>DB: INSERT clientes
    S->>DB: INSERT ventas (precio/descuento históricos)
    S->>DB: INSERT boletos
    DB-->>S: venta registrada
    S-->>UI: Venta con folio y total
    UI->>S: detalle_venta(folio)
    S-->>UI: datos enriquecidos
    UI->>PDF: generar(detalle)
    PDF-->>UI: tickets/ticket_V00001.pdf
```

## 5. Normalización aplicada

- **1FN**: todos los atributos son atómicos. `asientos` separa `fila` y
  `numero`; la posición `F-5` se deriva en la consulta.
- **2FN**: `boletos` tiene clave compuesta `(venta_id, asiento_id)` y no
  contiene atributos dependientes de una sola parte de la clave.
- **3FN**: los catálogos (`generos`, `clasificaciones`, `descuentos`,
  `estados_venta`) y las entidades (`salas`, `asientos`, `peliculas`,
  `funciones`, `clientes`, `ventas`) están separados. No hay dependencias
  transitivas: el género, la clasificación, la sala y el estado se referencian
  por ID.
- **Datos derivados**: `funciones` no almacena capacidad ni ocupados;
  `asientos` no almacena estado ni posición; `ventas` no almacena cantidad de
  boletos ni total. Se calculan con `COUNT`, joins y las reglas de negocio.
- **Histórico**: `ventas.precio_unitario` y `ventas.descuento_pct` son
  instantáneas de la compra, no valores derivados del catálogo actual.
