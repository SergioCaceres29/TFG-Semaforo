# Diseño técnico (fuente: diagramas UML y modelo de datos del TFG)

En los diagramas aparece la palabra «acceso» (por ejemplo `seleccionarAccesoPrioritario`). En el código se usa siempre **carril**: `seleccionar_carril_prioritario`, `obtener_demanda_por_carril`.

## 1. Clases de diseño (métodos en snake_case)

```
InterfazPrincipal: seleccionar_archivo(posicion), trazar_zonas(posicion), configurar_parametros(), iniciar_analisis(),
                   cancelar_analisis(), elegir_plan(tipo_plan), reproducir(), pausar(), detener(), cambiar_velocidad(factor),
                   mostrar_estados(estados), mostrar_comparacion(metricas)
GestorEjecucion  (-id_ejecucion: int): analizar(videos, parametros), cancelar(), generar_planes()
GestorDemostracion: cargar_plan(id_ejecucion, tipo_plan), reproducir(), pausar(), detener(), cambiar_velocidad(factor)
LectorVideo      : abrir(ruta) -> bool, leer_cuadro() -> (cuadro, marca_tiempo), ir_a_cuadro(n), obtener_metadatos(), cerrar()
Detector         (-umbral_confianza: float): cargar_modelo(pesos), detectar(cuadros) -> list[list[Deteccion]], filtrar_por_clase()
ContadorZonas    : cargar_zonas(id_video), evaluar_pertenencia(deteccion), acumular_por_intervalo(), obtener_demanda_por_carril()
MotorDecision    (-umbral_demanda: int): generar_plan_recomendado(demanda_registrada, duracion), generar_plan_fijo(duracion),
                   seleccionar_carril_prioritario(), resolver_empate(), aplicar_ciclo_por_defecto()
ControladorSemaforo (-estado_actual: dict): solicitar_transicion(carril), avanzar(t_sim), verificar_tiempos(), obtener_estados()
Visualizador     : dibujar_detecciones(), dibujar_zonas(), dibujar_conteos(), dibujar_estado_semaforico()
RepositorioSQLite: insertar_ejecucion(), actualizar_estado_ejecucion(), insertar_conteo(), insertar_evento_fase(),
                   consultar_conteos(), consultar_plan(id_ejecucion, tipo_plan), exportar_csv()
ValidadorResultados: cargar_conteo_manual(), calcular_metricas(), calcular_comparacion_planes(), generar_reporte()
```

`GestorDemostracion` vive en `nucleo.py` (Tabla 28: el núcleo coordina el análisis **y** la demostración). Los nombres de métodos nuevos son propuesta: confirmarlos en el plan de cada HU.

Tres carriles, un video por carril: `GestorEjecucion` crea un `LectorVideo` por carril (posiciones 1, 2, 3) y comparte un único `Detector`, `ContadorZonas`, `MotorDecision` y `ControladorSemaforo`. Cada video tiene una sola zona virtual, la de su carril.

Dependencias (del diagrama): InterfazPrincipal → GestorEjecucion, GestorDemostracion, ValidadorResultados. GestorEjecucion → LectorVideo, Detector, ContadorZonas, MotorDecision, Visualizador, RepositorioSQLite. GestorDemostracion → LectorVideo, Visualizador, RepositorioSQLite (lee videos, conteos y eventos de fase; **no** usa Detector ni escribe en la base). MotorDecision → ControladorSemaforo. ContadorZonas, ControladorSemaforo y ValidadorResultados → RepositorioSQLite (en la implementación, a través de lo que el núcleo les pase; ellos no abren la base).

## 2. Flujo de una ejecución (diagrama de secuencia, CU-02 y CU-06)

### 2.1 Análisis (sin semáforo)

```
iniciar_analisis(videos[1..3], parametros)
  validar: mismos fps en los 3 videos (si no, ErrorVideo)
  id_ejecucion = repo.insertar_ejecucion(parametros, videos)  # Creada → EnEjecucion (RF-13) + ejecucion_video
  lectores[p].abrir(videos[p]) para p = 1, 2, 3
  mientras los 3 lectores tengan cuadros y no se canceló:     # termina con el video más corto
      para cada carril p: cuadros[p], t = lectores[p].leer_cuadro()   # mismo n → mismo t = n / fps (s del video)
      detecciones = detector.detectar(cuadros[1..3])          # en lote; ya filtradas por clase y confianza
      ocupacion[p] = contador.acumular(detecciones[p], zona[p])  # cada video solo contra su zona
      si t cierra un intervalo:
          repo.insertar_conteo(id_ejecucion, zona, clase, cantidad, inicio, fin)   # por zona y clase; commit
      para cada carril p: imagen[p] = visualizador.componer(cuadros[p], detecciones[p], conteos[p])  # bytes PPM
      cola.put(cuadros anotados, conteos, t)                  # la interfaz la lee con after(); sin estados de semáforo
  lectores.cerrar()
  si se canceló o hubo error de lectura: estado Abortada (los conteos guardados se conservan) y terminar
  generar_planes()                                            # 2.2
  estado Finalizada; devolver resumen
```

### 2.2 Generación de planes (Python puro, después del análisis)

```
demanda_registrada = repo.consultar_conteos(id_ejecucion)     # por carril e intervalo, en s del video
duracion = duración del tramo analizado (s)
para tipo_plan en (RECOMENDADO, FIJO):
    t_sim = 0; t_video[p] = 0 para p = 1, 2, 3                # cada carril tiene su propio tiempo de video
    mientras t_sim < duracion:                                # HU-06 CA-05
        demanda[p] = ocupación registrada en t_video[p]       # RN-11 (regla exacta A CONFIRMAR, ver §4.1)
        si t_sim cierra un intervalo de evaluación:
            RECOMENDADO → motor.evaluar(demanda, estados)  └─ controlador.solicitar_transicion(carril)
            FIJO        → turno del ciclo 1 → 2 → 3 con verde_max + amarillo (RN-08)
        controlador.avanzar(t_sim)                            # vencimientos de amarillo / verde mín / verde máx
        para cada carril p en VERDE o AMARILLO: t_video[p] avanza; en ROJO queda congelado
    eventos del plan → repo.insertar_evento_fase(id_ejecucion, tipo_plan, zona, estado, marca_tiempo=t_sim, duracion, demanda)
```

- Los planes se generan completos antes de insertarse, así cada evento ya conoce su `duracion` (compatible con solo inserción).
- Los dos planes usan los mismos videos, la misma duración y los mismos tiempos de fase (CP-27).

### 2.3 Demostración (sin modelo, sin escritura en la base)

```
elegir_plan(tipo_plan); eventos = repo.consultar_plan(id_ejecucion, tipo_plan)
por cada tic de reproducción (after(); el reloj del sistema solo marca el ritmo):
    t_sim += paso × velocidad (1 o 2)
    estados = estado de cada carril en t_sim según eventos
    para cada carril p: si VERDE o AMARILLO → leer el siguiente cuadro; si ROJO → repetir el último cuadro (RN-11)
    imagen[p] = visualizador.componer(cuadro[p], zona[p], conteo registrado en t_video[p], estado[p])  # sin cajas
pausar / detener: solo cambian la reproducción; la ejecución y sus registros no cambian
```

- Debajo de las tarjetas, panel con las métricas de comparación de ambos planes (RF-17), calculadas por `validacion.py` sobre la ocupación registrada.

## 3. Máquina de estados de un carril (RN-05, RN-06, RN-08)

Todo el tiempo de esta sección es **tiempo de simulación** (`t_sim`), no tiempo del video.

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
- El tiempo de video de un carril (`t_video[p]`) solo avanza en VERDE_* o AMARILLO (RN-11); en ROJO queda congelado. Siempre `t_video[p] ≤ t_sim`.

## 4. Decisión de prioridad (diagrama de actividades, Figura 6)

```
recibir la demanda de cada carril en el instante de su video (RN-11)
si algún carril supera el umbral (>):
    elegir el de mayor demanda
    si hay empate: elegir el de mayor tiempo acumulado en rojo        # RN-07
sino:
    elegir el siguiente carril del ciclo fijo                          # RN-08
controlador:
    si el elegido ya tiene verde: ¿alcanzó verde_max? -> si sí, cede al SIGUIENTE CARRIL DEL CICLO FIJO   # RN-05 (Word nov/2026)
    si no lo tiene: ¿el verde vigente cumplió verde_min?
    si la transición se autoriza: amarillo al saliente -> rojo al saliente y verde al entrante
    si no: mantener el verde vigente
agregar el evento al plan (con su tipo de plan y la demanda asociada) para registrarlo (RF-12)
```

### 4.1 Puntos abiertos de la generación de planes (preguntar antes de HU-05/HU-06)

1. **Demanda en `t_video[p]`** (RN-11): el conteo existe solo al cierre de cada intervalo. Opciones: (a) la del último intervalo cerrado (`intervalo_fin ≤ t_video`), con 0 antes del primer cierre; (b) la del intervalo que contiene `t_video`. Con (a), un carril congelado antes de su primer cierre queda con demanda 0 y solo recibe verde por ciclo fijo o por RN-05.
2. **Reloj de evaluación**: se asume que la evaluación ocurre cada `intervalo_seg` de **tiempo de simulación** (HU-05 CA-01).
3. **Estado inicial del plan RECOMENDADO**: se mantiene la decisión previa (carril 1 en verde por ciclo fijo en `t_sim = 0`), A CONFIRMAR.
4. **Amarillo en las métricas**: ¿cuenta como «verde sin demanda», como «espera» o en ninguna? Se asume ninguna.
5. **Ejecución abortada**: se asume que no genera planes (Figura 10: los planes se generan al terminar los videos).

## 5. Esquema SQLite (diccionario de datos, Tabla 18)

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
    estado           TEXT NOT NULL CHECK (estado IN ('Creada','EnEjecucion','Finalizada','Abortada'))   -- sin 'Pausada' (Figura 10, nov/2026)
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
    tipo_plan        TEXT NOT NULL CHECK (tipo_plan IN ('RECOMENDADO','FIJO')),   -- nuevo (RF-12, RF-17)
    id_zona          INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    estado           TEXT NOT NULL CHECK (estado IN ('VERDE','AMARILLO','ROJO')),
    marca_tiempo     REAL NOT NULL,          -- segundos de SIMULACIÓN del plan (no del video)
    duracion         INTEGER NOT NULL CHECK (duracion >= 0),
    demanda_asociada INTEGER NOT NULL CHECK (demanda_asociada >= 0)   -- demanda en el instante del video del carril (RN-11)
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
- `ejecucion.estado` sí se actualiza (Creada → EnEjecucion → Finalizada/Abortada); solo `conteo` y `evento_fase` son de solo inserción. Los controles de la demostración no cambian este estado.
- **Cambios del diccionario de datos del Word (Tabla 18, nov/2026)**: `evento_fase.tipo_plan` (RECOMENDADO/FIJO) y `marca_tiempo` en segundos de simulación; `ejecucion.estado` sin `Pausada`. Vienen del documento aprobado por el autor, pero **`src/semaforo/esquema.sql` y `EstadoEjecucion` todavía no están actualizados**: aplicarlo como primer paso de la HU que toque esas tablas (HU-08 para `ejecucion`, RF-12 para `evento_fase`), avisando antes. Como `CREATE TABLE IF NOT EXISTS` no altera tablas existentes, una base `semaforo.db` creada antes del cambio debe recrearse (solo tiene datos de desarrollo).
- Unidades de tiempo: `conteo`, `conteo_manual` y `video` en segundos del video; `evento_fase` en segundos de simulación.
- Mapeo índice del modelo → `clase_vehiculo.id_clase`: 0 → 1 (auto), 1 → 2 (moto), 2 → 3 (camion).

## 6. Interfaz del operador (tkinter)

```
┌────────────┬───────────────────────────────────────────────────────────┐
│ Barra      │  Encabezado: título de la vista · estado de la ejecución  │
│ lateral    ├───────────────────────────────────────────────────────────┤
│            │  ┌ Carril 1 ──────┐ ┌ Carril 2 ──────┐ ┌ Carril 3 ──────┐ │
│ Panel      │  │ video  │ sem.* │ │ video  │ sem.* │ │ video  │ sem.* │ │
│ Videos y   │  │ conteo por clase│ │ conteo por clase│ │ conteo por clase│ │
│  zonas     │  │ [Cargar] [Zona] │ │ [Cargar] [Zona] │ │ [Cargar] [Zona] │ │
│ Parámetros │  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
│ Análisis   ├───────────────────────────────────────────────────────────┤
│ Demostr.   │  Análisis:  ▶ Iniciar  ■ Cancelar   t del video · progreso │
│ Resultados │  Demo: plan [Recomendado|Fijo] ▶ ⏸ ■  ×1/×2   t de simul. │
│ Validación ├───────────────────────────────────────────────────────────┤
│ Exportar   │  Comparación: verde sin demanda · espera acumulada (por    │
│            │  carril y total) — Recomendado vs Fijo  (RF-17)           │
└────────────┴───────────────────────────────────────────────────────────┘
* el semáforo solo se muestra durante la demostración
```

- Solo biblioteca estándar (`tkinter`, `ttk`): sin Pillow. Los cuadros llegan como bytes PPM (`cv2.imencode` en `visualizacion.py`) y se muestran con `tk.PhotoImage`.
- Análisis: `GestorEjecucion` corre en un hilo aparte y envía mensajes (`ActualizacionCarril`, `ProgresoEjecucion` de `modelos.py`) por una `queue.Queue`. La interfaz la vacía con `after()`; nunca se toca un widget desde otro hilo. Durante el análisis se puede **cancelar** (→ Abortada), no pausar.
- Demostración: el ritmo lo marca `after()` (reloj del sistema solo para la cadencia); la lógica usa `t_sim`. Envía `CambioFase` al cambiar de estado un carril. Velocidad ×1 o ×2.
- La interfaz no decide nada: solo muestra los estados que recibe del plan (`mostrar_estados`).
- Mejoras futuras **fuera de alcance** (no implementar sin pedido): recalcular el plan con otros parámetros sin re-analizar, y línea de tiempo gráfica de fases.

## 7. Estructura del repositorio

```
semaforo-tfg/
├── CLAUDE.md
├── .claude/rules/            # reglas que se cargan solo al tocar ciertos archivos
├── docs/specs/               # requisitos.md, diseno.md
├── src/semaforo/             # un archivo por módulo (ver tabla en CLAUDE.md) + esquema.sql
├── tests/                    # test_<modulo>.py, una prueba por CA nombrada con su CP
├── notebooks/entrenamiento_colab.ipynb
├── herramientas/             # scripts auxiliares (verificar_modelo.py: versiones, CUDA y mapeo de clases — paso 5 del despliegue)
├── modelos/best.pt           # NO se versiona (.gitignore)
├── datos/videos/  datos/db/  # NO se versiona
├── dataset/                  # NO se versiona; respaldo en Google Drive
├── requirements.txt
└── README.md
```
