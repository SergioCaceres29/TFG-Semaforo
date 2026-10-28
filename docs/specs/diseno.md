# Diseño técnico (fuente: diagramas UML y modelo de datos del TFG)

En los diagramas aparece la palabra «acceso» (por ejemplo `seleccionarAccesoPrioritario`). En el código se usa siempre **carril**: `seleccionar_carril_prioritario`, `obtener_demanda_por_carril`.

## 1. Clases de diseño (métodos en snake_case)

```
InterfazPrincipal: seleccionar_archivo(posicion), trazar_zonas(posicion), configurar_parametros(), iniciar_procesamiento(), mostrar_estados(estados)
GestorEjecucion  (-id_ejecucion: int): ejecutar(videos, parametros), pausar(), finalizar()
LectorVideo      : abrir(ruta) -> bool, leer_cuadro() -> (cuadro, marca_tiempo), obtener_metadatos(), cerrar()
Detector         (-umbral_confianza: float): cargar_modelo(pesos), detectar(cuadro) -> list[Deteccion], filtrar_por_clase()
ContadorZonas    : cargar_zonas(id_video), evaluar_pertenencia(deteccion), acumular_por_intervalo(), obtener_demanda_por_carril()
MotorDecision    (-umbral_demanda: int): evaluar(demanda, estado), seleccionar_carril_prioritario(), resolver_empate(), aplicar_ciclo_por_defecto()
ControladorSemaforo (-estado_actual: dict): solicitar_transicion(carril), verificar_tiempos(), obtener_estados()
Visualizador     : dibujar_detecciones(), dibujar_zonas(), dibujar_conteos(), dibujar_estado_semaforico()
RepositorioSQLite: insertar_ejecucion(), insertar_conteo(), insertar_evento_fase(), consultar_conteos(), exportar_csv()
ValidadorResultados: cargar_conteo_manual(), calcular_metricas(), generar_reporte()
```

Tres carriles, un video por carril: `GestorEjecucion` crea un `LectorVideo` por carril (posiciones 1, 2, 3) y comparte un único `Detector`, `ContadorZonas`, `MotorDecision` y `ControladorSemaforo`. Cada video tiene una sola zona virtual, la de su carril.

Dependencias (del diagrama): InterfazPrincipal → GestorEjecucion, ValidadorResultados. GestorEjecucion → LectorVideo, Detector, ContadorZonas, MotorDecision, Visualizador, RepositorioSQLite. MotorDecision → ControladorSemaforo. ContadorZonas, ControladorSemaforo y ValidadorResultados → RepositorioSQLite (en la implementación, a través de lo que el núcleo les pase; ellos no abren la base).

## 2. Bucle de ejecución (diagrama de secuencia, CU-02)

```
iniciar_procesamiento(videos[1..3], parametros)
  validar: mismos fps en los 3 videos (si no, ErrorVideo)
  id_ejecucion = repo.insertar_ejecucion(parametros, videos)  # estado EnEjecucion (RF-13) + ejecucion_video
  lectores[p].abrir(videos[p]) para p = 1, 2, 3
  mientras los 3 lectores tengan cuadros:                     # termina con el video más corto
      para cada carril p: cuadros[p], t = lectores[p].leer_cuadro()   # mismo n → mismo t = n / fps
      detecciones[p] = detector.detectar(cuadros[p])          # en lote; ya filtradas por clase y confianza
      ocupacion[p] = contador.acumular(detecciones[p], zona[p])  # cada video solo contra su zona
      controlador.actualizar(t)                               # vencimientos de amarillo / verde máximo
      si t cierra un intervalo:
          repo.insertar_conteo(id_ejecucion, zona, clase, cantidad, inicio, fin)   # por zona y clase
          estados = motor.evaluar(demanda_por_carril, umbral, estado_actual)
            └─ controlador.solicitar_transicion(carril)
                 si permitida: repo.insertar_evento_fase(...) y nuevos estados
                 si no (restricción temporal): mantiene el estado vigente
      para cada carril p: imagen[p] = visualizador.componer(cuadros[p], detecciones[p], conteos[p])  # bytes PPM
      cola.put(cuadros anotados, conteos, estados, t)         # la interfaz la lee con after()
  lectores.cerrar(); estado Finalizada; devolver resumen
```

## 3. Máquina de estados de un carril (RN-05, RN-06, RN-08)

Estados: `ROJO`, `VERDE_MINIMO`, `VERDE_EXTENDIDO`, `AMARILLO` (en la base se guarda VERDE, AMARILLO o ROJO).

| Desde | Evento [condición] / acción | Hacia |
|---|---|---|
| (inicio) | — | ROJO |
| ROJO | evaluación periódica [no seleccionado] / incrementar tiempo en rojo | ROJO |
| ROJO | asignar prioridad [demanda > umbral y seleccionado, o turno del ciclo fijo] / iniciar temporizador de verde | VERDE_MINIMO |
| VERDE_MINIMO | fin del tiempo mínimo [conserva la mayor demanda] / continuar temporizador | VERDE_EXTENDIDO |
| VERDE_MINIMO | fin del tiempo mínimo [otro carril tiene mayor demanda] / iniciar amarillo | AMARILLO |
| VERDE_EXTENDIDO | evaluación periódica [otro supera la demanda o se alcanzó el máximo] / registrar evento de fase | AMARILLO |
| AMARILLO | fin del tiempo de amarillo / liberar prioridad; el carril entrante pasa a VERDE_MINIMO | ROJO |

Invariantes que las pruebas deben verificar:
- Nunca hay más de un carril en VERDE_* (decisión de diseño: un solo carril en verde a la vez).
- Ningún verde dura menos que `verde_min` ni más que `verde_max`.
- No existe transición directa de VERDE_* a ROJO.
- El tiempo en rojo acumulado de cada carril se reinicia al pasar a verde.

## 4. Decisión de prioridad (diagrama de actividades)

```
recibir demanda consolidada por carril
si algún carril supera el umbral:
    elegir el de mayor demanda
    si hay empate: elegir el de mayor tiempo acumulado en rojo        # RN-07
sino:
    elegir el siguiente carril del ciclo fijo                          # RN-08
controlador:
    si el elegido ya tiene verde: ¿alcanzó verde_max? -> si sí, debe ceder
    si no lo tiene: ¿el verde vigente cumplió verde_min?
    si la transición se autoriza: amarillo al saliente -> rojo al saliente y verde al entrante
    si no: mantener el verde vigente
registrar el evento de fase con la demanda asociada (RF-12)
```

## 5. Esquema SQLite (diccionario de datos, Tabla 17)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS video (
    id_video        INTEGER PRIMARY KEY,
    nombre_archivo  TEXT NOT NULL,
    duracion_seg    REAL NOT NULL,
    fps             REAL NOT NULL,
    resolucion      TEXT NOT NULL,          -- ej. '1920x1080'
    fecha_captura   TEXT
);

CREATE TABLE IF NOT EXISTS zona_virtual (
    id_zona         INTEGER PRIMARY KEY,
    id_video        INTEGER NOT NULL REFERENCES video(id_video),
    nombre_carril   TEXT NOT NULL,
    vertices        TEXT NOT NULL,          -- JSON: [[x, y], ...] con al menos 3 puntos
    UNIQUE (id_video, nombre_carril)
);

CREATE TABLE IF NOT EXISTS clase_vehiculo (
    id_clase        INTEGER PRIMARY KEY,
    descripcion     TEXT NOT NULL UNIQUE    -- 'auto', 'moto', 'camion'
);

CREATE TABLE IF NOT EXISTS ejecucion (
    id_ejecucion     INTEGER PRIMARY KEY,
    fecha_hora       TEXT NOT NULL,
    version_modelo   TEXT NOT NULL,
    umbral_demanda   INTEGER NOT NULL CHECK (umbral_demanda >= 0),
    umbral_confianza REAL NOT NULL CHECK (umbral_confianza BETWEEN 0 AND 1),
    intervalo_seg    INTEGER NOT NULL CHECK (intervalo_seg > 0),
    verde_min        INTEGER NOT NULL CHECK (verde_min > 0),
    verde_max        INTEGER NOT NULL CHECK (verde_max >= verde_min),
    amarillo         INTEGER NOT NULL CHECK (amarillo > 0),
    estado           TEXT NOT NULL CHECK (estado IN ('Creada','EnEjecucion','Pausada','Finalizada','Abortada'))
);

CREATE TABLE IF NOT EXISTS ejecucion_video (        -- los 3 videos de una ejecución, uno por carril
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_video         INTEGER NOT NULL REFERENCES video(id_video),
    posicion         INTEGER NOT NULL CHECK (posicion BETWEEN 1 AND 3),
    PRIMARY KEY (id_ejecucion, posicion)
);

CREATE TABLE IF NOT EXISTS conteo (                 -- solo inserción (RNF-09)
    id_conteo        INTEGER PRIMARY KEY,
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona          INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase         INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    cantidad         INTEGER NOT NULL CHECK (cantidad >= 0),
    intervalo_inicio REAL NOT NULL,
    intervalo_fin    REAL NOT NULL CHECK (intervalo_fin > intervalo_inicio)
);

CREATE TABLE IF NOT EXISTS evento_fase (            -- solo inserción (RNF-09)
    id_evento        INTEGER PRIMARY KEY,
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona          INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    estado           TEXT NOT NULL CHECK (estado IN ('VERDE','AMARILLO','ROJO')),
    marca_tiempo     REAL NOT NULL,
    duracion         INTEGER NOT NULL CHECK (duracion >= 0),
    demanda_asociada INTEGER NOT NULL CHECK (demanda_asociada >= 0)
);

CREATE TABLE IF NOT EXISTS conteo_manual (
    id_conteo_manual    INTEGER PRIMARY KEY,
    id_video            INTEGER NOT NULL REFERENCES video(id_video),
    id_zona             INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase            INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    intervalo_inicio    REAL NOT NULL,
    intervalo_fin       REAL NOT NULL CHECK (intervalo_fin > intervalo_inicio),
    cantidad_referencia INTEGER NOT NULL CHECK (cantidad_referencia >= 0)
);

CREATE TABLE IF NOT EXISTS metrica_validacion (
    id_metrica    INTEGER PRIMARY KEY,
    id_ejecucion  INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona       INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase      INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    precision     REAL NOT NULL,     -- (1 - Σ|Ca - Cm| / ΣCm) × 100
    error_conteo  REAL NOT NULL      -- Σ|Ca - Cm|
);

-- RNF-09: bloqueo de UPDATE y DELETE en tablas históricas
CREATE TRIGGER IF NOT EXISTS conteo_sin_update BEFORE UPDATE ON conteo
BEGIN SELECT RAISE(ABORT, 'conteo es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS conteo_sin_delete BEFORE DELETE ON conteo
BEGIN SELECT RAISE(ABORT, 'conteo es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS evento_sin_update BEFORE UPDATE ON evento_fase
BEGIN SELECT RAISE(ABORT, 'evento_fase es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS evento_sin_delete BEFORE DELETE ON evento_fase
BEGIN SELECT RAISE(ABORT, 'evento_fase es de solo insercion (RNF-09)'); END;

INSERT OR IGNORE INTO clase_vehiculo (id_clase, descripcion) VALUES (1,'auto'), (2,'moto'), (3,'camion');
```

Notas:
- El esquema vive en `src/semaforo/esquema.sql` y `RepositorioSQLite` lo aplica al abrir la base (`datos/db/semaforo.db`).
- Cada conteo se confirma (`commit`) al cierre de su intervalo, para que una interrupción no pierda lo ya guardado (HU-08 CA-04).
- Cambio aprobado el 28/10/2026: `ejecucion` ya no tiene `id_video`; los tres videos se asocian en `ejecucion_video` (posición 1–3 = carril en la interfaz). Cada video tiene una sola fila en `zona_virtual`.
- `ejecucion.estado` sí se actualiza (Creada → EnEjecucion → Finalizada/Abortada); solo `conteo` y `evento_fase` son de solo inserción.
- Mapeo índice del modelo → `clase_vehiculo.id_clase`: 0 → 1 (auto), 1 → 2 (moto), 2 → 3 (camion).

## 6. Interfaz del operador (tkinter)

```
┌────────────┬───────────────────────────────────────────────────────────┐
│ Barra      │  Encabezado: título de la vista · estado de la ejecución  │
│ lateral    ├───────────────────────────────────────────────────────────┤
│            │  ┌ Carril 1 ──────┐ ┌ Carril 2 ──────┐ ┌ Carril 3 ──────┐ │
│ Panel      │  │ video   │ sem. │ │ video   │ sem. │ │ video   │ sem. │ │
│ Videos y   │  │ conteo por clase│ │ conteo por clase│ │ conteo por clase│ │
│  zonas     │  │ [Cargar] [Zona] │ │ [Cargar] [Zona] │ │ [Cargar] [Zona] │ │
│ Parámetros │  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ Ejecución  ├───────────────────────────────────────────────────────────┤
│ Resultados │  ▶ Iniciar  ⏸ Pausar  ■ Detener   t del video · progreso  │
│ Validación │                                                           │
│ Exportar   │                                                           │
└────────────┴───────────────────────────────────────────────────────────┘
```

- Solo biblioteca estándar (`tkinter`, `ttk`): sin Pillow. Los cuadros llegan como bytes PPM (`cv2.imencode` en `visualizacion.py`) y se muestran con `tk.PhotoImage`.
- `GestorEjecucion` corre en un hilo aparte y envía mensajes (`CambioFase`, `ActualizacionCarril`, `ProgresoEjecucion` de `modelos.py`) por una `queue.Queue`. La interfaz la vacía con `after()`; nunca se toca un widget desde otro hilo.
- La interfaz no decide nada: solo muestra los estados que recibe del motor (`mostrar_estados`).

## 7. Estructura del repositorio

```
semaforo-tfg/
├── CLAUDE.md
├── .claude/rules/            # reglas que se cargan solo al tocar ciertos archivos
├── docs/specs/               # requisitos.md, diseno.md
├── src/semaforo/             # un archivo por módulo (ver tabla en CLAUDE.md) + esquema.sql
├── tests/                    # test_<modulo>.py, una prueba por CA nombrada con su CP
├── notebooks/entrenamiento_colab.ipynb
├── herramientas/             # scripts auxiliares: extraer cuadros, pre-etiquetar, dividir dataset
├── modelos/best.pt           # NO se versiona (.gitignore)
├── datos/videos/  datos/db/  # NO se versiona
├── dataset/                  # NO se versiona; respaldo en Google Drive
├── requirements.txt
└── README.md
```
