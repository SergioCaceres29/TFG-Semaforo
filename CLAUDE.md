# CLAUDE.md — Prototipo de conteo vehicular y simulación semafórica (TFG UNAE)

> Este archivo es la especificación para la IA (Context Spec, Boundary Spec y Quality Spec) exigida en la Etapa 3 del TFG (§4.2.1).
> Detalle completo bajo demanda: `docs/specs/requisitos.md` (RF, RNF, RN, HU, CA y CP) y `docs/specs/diseno.md` (clases, flujos, estados, esquema SQL).
> Leé la sección correspondiente de esos archivos ANTES de implementar cualquier HU o RF.
> Fuente de verdad: `Documentacion TFG Semaforo.docx`. Última sincronización con el Word: **11/11/2026**.

## 1. Context Spec

### Rol de la IA
Asistente de programación que implementa **una historia de usuario por vez**, bajo la revisión del autor.

### Qué es
Prueba de concepto (PoC) académica, sin cliente ni usuarios finales. Aplicación de escritorio en Python que trabaja en **tres momentos**:
1. **Análisis**: carga **tres videos pregrabados mp4** (1920×1080), **uno por carril**, grabados por separado en el mismo lapso en la intersección Ruta 14 y C. Sagrado Corazón de Jesús, Cambyreta. Detecta y clasifica vehículos en **3 clases: auto, moto, camión** con un modelo YOLO26n propio (`modelos/best.pt`) y mide la demanda de cada carril por **ocupación por intervalo** dentro de su zona virtual (sin tracking). Se persiste en SQLite. Durante el análisis **no hay semáforo**.
2. **Generación de planes**: al terminar el análisis, un **único motor de reglas** recorre la demanda registrada de los tres carriles y genera el **plan RECOMENDADO**; con los mismos videos y tiempos se genera el **plan FIJO** (ciclo de tiempos fijos) para comparar.
3. **Demostración y comparación**: un simulador propio reproduce el plan elegido sobre los videos, **sin ejecutar el modelo**: el video de cada carril avanza en verde o amarillo y se congela en rojo (RN-11). Se muestran las métricas de comparación de ambos planes (RF-17).
Además: valida el conteo automático contra un conteo manual (RF-15).

Rol único: **operador técnico** (sin login, sin usuarios, sin concurrencia).
Autor: Sergio Andrés Cáceres Surnyak. Metodología: Scrum (sprints de 1,5 semanas).

### Stack fijo (Tabla 29 del TFG; NO cambiar ni agregar nada sin preguntar)
- Python 3.13 · Ultralytics + **YOLO26 nano** · OpenCV 4.13 · PyTorch · SQLite 3.47 (módulo `sqlite3` de la biblioteca estándar) · tkinter.
- PyTorch: **`torch==2.14.*` desde el índice `cu126`** (la GTX 1050 Ti es Pascal; 2.15+ ya no la soporta). Si la GPU falla, usar CPU.
- Calidad: **`unittest`** (pruebas) y **`ruff`** (estilo, solo en desarrollo). Ambos aprobados en el TFG. `pytest` NO.
- Equipo de referencia: notebook Windows 11, i7-9750H, 16 GB RAM, GTX 1050 Ti 4 GB. Entrenamiento en Google Colab; inferencia local.
- Exportación CSV con el módulo `csv` estándar (RF-14), codificación `utf-8-sig` para que Excel la abra bien (RNF-10).

### Glosario obligatorio (en código, comentarios y mensajes)
- **carril** (nunca «acceso»), **precisión** (nunca «exactitud»), **Cambyreta** sin tilde. Paquete `semaforo` sin tilde.
- **Carril**: cada franja por la que los vehículos ingresan a la intersección. Son siempre 3; cada uno tiene **su propio video**, su zona virtual y su semáforo. Se identifica por su posición en la interfaz (1, 2, 3) y por un nombre.
- **Zona virtual**: polígono (≥ 3 vértices) sobre el primer cuadro del video de un carril, que delimita su área de conteo.
- **Intervalo de evaluación**: período al cierre del cual se consolida el conteo y el motor evalúa la prioridad.
- **Ejecución**: un análisis (completo o parcial) **de los tres videos en simultáneo** con un conjunto de parámetros, **junto con los planes generados a partir de él**.
- **Plan semafórico**: secuencia verde/amarillo/rojo de cada carril durante la duración del análisis. Tipos: `RECOMENDADO` (motor de reglas) y `FIJO` (comparación).
- **Demostración**: reproducción de los tres videos aplicando un plan (RN-11).
- **Tiempo de verde sin demanda**: segundos en que un carril está en verde con ocupación cero en su zona.
- **Espera acumulada**: suma, por cada segundo en rojo, de la ocupación del carril (vehículos·s). En ambas métricas, menor es mejor.
- **Tiempo**:
  - En el **análisis**, segundos del video (`n_cuadro / fps`).
  - En el **plan y la demostración**, **segundos de simulación** (`t_sim`, desde el inicio del plan). Cada carril además tiene su **tiempo de video** (`t_video[p]`), que solo avanza en verde o amarillo.
  - El reloj del sistema solo marca el ritmo de la reproducción, **nunca la lógica**.

## 2. Arquitectura (RNF-07: módulos independientes, Tabla 28 del TFG)

Monolito modular local. Un archivo por módulo en `src/semaforo/`, cada uno con la clase del diagrama de clases de diseño:

| Archivo | Clase | Responsabilidad | HU/RF |
|---|---|---|---|
| `modelos.py` | dataclasses | `Deteccion`, `Zona`, `Parametros`, `MetadatosVideo`, enums `Clase`, `EstadoSemaforo`, `EstadoEjecucion`, `TipoPlan` | — |
| `captura.py` | `LectorVideo` | abrir mp4, validar, metadatos; leer cuadros **en continuo (análisis) y por carril (demostración)** | HU-01, HU-09 / RF-01, RF-16 |
| `configuracion.py` | (funciones) | validación de zonas y parámetros | HU-02 / RF-02, RF-03, RF-10 |
| `deteccion.py` | `Detector` | cargar `best.pt`, detectar, filtrar por clase y confianza | HU-03 / RF-04, RF-05 |
| `conteo.py` | `ContadorZonas` | punto-en-polígono, ocupación por zona/clase/intervalo | HU-04 / RF-06 |
| `decision.py` | `MotorDecision` | sobre la demanda **registrada**: umbral, mayor demanda, desempate, ciclo fijo; genera plan RECOMENDADO y FIJO | HU-05 / RF-07, RF-17 |
| `control_fases.py` | `ControladorSemaforo` | máquina de estados por carril, tiempos mín/máx, amarillo, avance de `t_video` por carril | HU-06 / RF-08 |
| `visualizacion.py` | `Visualizador` | dibujar cajas, zonas, conteos y semáforos | HU-07, HU-09 / RF-09, RF-16 |
| `persistencia.py` + `esquema.sql` | `RepositorioSQLite` | único acceso a SQLite, esquema, inserciones, consultas, CSV | HU-08 / RF-11..14 |
| `validacion.py` | `ValidadorResultados` | conteo manual, métricas de validación **y métricas de comparación de planes** | RF-15, RF-17 |
| `nucleo.py` | `GestorEjecucion`, `GestorDemostracion` | orquesta el análisis, la generación de planes y la demostración | CU-02, CU-06, RF-16 |
| `interfaz.py` | `InterfazPrincipal` | ventana tkinter: barra lateral de módulos, 3 tarjetas carril, panel de comparación | CU-01, CU-02, CU-03, CU-06 |
| `__main__.py` | — | entrada: `python -m semaforo` | — |

Reglas de dependencia (§4.1 del TFG):
- Solo `nucleo.py` coordina módulos. Los demás importan únicamente `modelos.py` (excepción: `decision.py` usa `control_fases.py`).
- Solo `persistencia.py` importa `sqlite3`. Solo `deteccion.py` importa `ultralytics`/`torch`.
- `decision.py` y `control_fases.py` son **Python puro** (sin cv2, sin I/O, sin reloj) para probarlos de forma determinista y ejecutarlos sobre los conteos registrados.
- La interfaz no toma decisiones: solo muestra los estados que recibe del plan.
- La demostración **no** importa ni usa `Detector` y **no escribe** en la base.

## 3. Boundary Spec (lo que la IA NO puede hacer ni asumir)

- NO agregar dependencias, frameworks, GUIs, ORMs ni servicios. Si algo parece necesario, **preguntar primero** y justificar.
- NO implementar: video en vivo/cámaras, OCR de placas, web, móvil, API, tracking de vehículos, conexión a semáforos reales, autenticación.
- NO implementar las **mejoras futuras** sin pedido explícito: recálculo del plan con otros parámetros sin volver a analizar, ni línea de tiempo gráfica de fases.
- NO cambiar el esquema de base de datos de `docs/specs/diseno.md` sin aprobación. NO hacer UPDATE/DELETE sobre `conteo` ni `evento_fase` (RNF-09).
- NO agregar clases de vehículos fuera de auto/moto/camión (RN-02).
- NO usar videos de validación para entrenar (RN-10). NO tocar `dataset/`, `datos/videos/` ni `modelos/*.pt` salvo pedido explícito.
- NO inventar reglas de negocio. Si un caso no está cubierto por RN-01..RN-11 o por la sección 6, **preguntar**.
- NO avanzar a otra HU sin que la actual pase sus pruebas y yo la apruebe.
- NO hacer commits ni push sin que lo pida.

## 4. Quality Spec

- PEP 8, controlado con **ruff**. Nombres en **español**: clases en `PascalCase` (como en los diagramas), funciones/variables en `snake_case` (`leer_cuadro`, `seleccionar_carril_prioritario`), constantes en `MAYUSCULAS`.
- Type hints en todas las funciones públicas y docstring breve que cite el RF/RN que implementa (ej. `"""RN-07: desempate por mayor tiempo en rojo."""`).
- Funciones cortas, sin lógica duplicada, sin código muerto ni `print` de depuración (usar `logging`).
- Errores: excepciones propias en `modelos.py` (`ErrorVideo`, `ErrorConfiguracion`). Ante archivo inexistente, corrupto o no-mp4: mensaje controlado y el programa sigue operativo (RNF-05). Nunca `except:` vacío.
- Parámetros configurables en `Parametros` (dataclass), nunca números mágicos en el código.
- Windows: rutas con `pathlib`, y `if __name__ == "__main__":` en todo script que use Ultralytics.
- **Pruebas obligatorias**: cada criterio de aceptación (CA) tiene al menos una prueba en `tests/`, nombrada con su caso de prueba: `test_cp07_desempate_por_tiempo_en_rojo`. Mapa CA → CP en `docs/specs/requisitos.md` (Tabla 33 del TFG, CP-01..CP-27).

## 5. Flujo de trabajo por HU (seguir siempre)

1. Leer la HU y sus CA en `docs/specs/requisitos.md` y lo relevante de `docs/specs/diseno.md`.
2. Proponer un plan corto (archivos a tocar, funciones, pruebas) y **esperar mi aprobación**.
3. Escribir primero las pruebas de los CA, luego el código mínimo que las hace pasar.
4. Ejecutar las pruebas (y ruff) y mostrar el resultado real. No declarar «listo» con pruebas fallando.
5. Auditar: ¿respeta las RN? ¿algún import prohibido? ¿coherente con la documentación del TFG?
6. Resumir en 5 líneas: qué se hizo, CA cubiertos, CP aprobados, pendientes.
7. Actualizar la tabla de avance (sección 7).

### Comandos (Windows, PowerShell, desde la raíz)
- Activar entorno: `.\.venv\Scripts\Activate.ps1`
- Ejecutar app: `python -m semaforo`
- Pruebas: `python -m unittest discover -s tests -v`
- Estilo: `ruff check src tests` (pendiente instalar/configurar en `pyproject.toml`; pedir antes)
- Verificar modelo: `python herramientas/verificar_modelo.py`
- Ramas Git: `main` (estable) · `develop` (integración) · `feature/HU-0X-nombre` o `feature/RF-XX-nombre` · `hotfix/*`. SemVer: `v0.1.0` (Sprint 1) … `v0.4.0` (Sprint 4), `v1.0.0` entrega final.
- Commits: `HU-04: conteo por ocupación al cierre del intervalo (RF-06, RN-03)`.

## 6. Decisiones de implementación (no reinterpretar)

- **Conteo (RF-06, RN-03)**: `cantidad` = vehículos presentes en la zona **en el cuadro de cierre** de cada intervalo, por clase. Así un vehículo no se cuenta dos veces en el mismo intervalo, sin tracking. El conteo manual sigue el mismo criterio.
- **Demanda de un carril** = suma de las tres clases en ese cuadro de cierre.
- **Tres carriles, un video por carril**: siempre son 3 carriles y cada uno se graba por separado. Los tres videos comparten un único `MotorDecision` y un único `ControladorSemaforo`.
- **Sincronización del análisis**: los tres videos se grabaron en el mismo lapso, con iguales fps; el cuadro `n` de cada video corresponde al mismo instante `t = n / fps`. Si los fps no coinciden → `ErrorVideo` con mensaje controlado. Si la duración difiere, se procesa **hasta el final del más corto**.
- **Zonas por video**: una sola zona virtual por video, la del carril que filma.
- **Pertenencia a zona** (A CONFIRMAR): punto de referencia = centro inferior de la caja `((x1+x2)/2, y2)`; `cv2.pointPolygonTest >= 0`. Las detecciones de un video solo se evalúan contra la zona de ese video.
- **Análisis sin semáforo**: el bucle de cuadros solo detecta, cuenta, guarda y muestra. El motor **no** corre dentro del bucle.
- **Generación de planes** (HU-05, HU-06): al terminar el análisis (estado aún EnEjecucion), se generan **ambos** planes con duración = tramo analizado, y recién entonces la ejecución pasa a Finalizada. Se generan completos y luego se insertan en `evento_fase` con su `tipo_plan` (así cada evento ya conoce su `duracion`).
- **RN-11 en la generación**: cada carril lleva su `t_video[p]`, que avanza solo en verde/amarillo; la demanda de un carril en rojo es la ocupación registrada en el instante en que su video quedó detenido. Aplica a los dos planes. Regla exacta para leer la ocupación en `t_video` y reloj de evaluación: **A CONFIRMAR** (ver `diseno.md` §4.1).
- **Movimientos conflictivos (RN-06)** (A CONFIRMAR): solo un carril en verde a la vez; el resto en rojo.
- **Ciclo fijo (RN-08)** (confirmado en el Word): rotación por posición 1 → 2 → 3, cada carril con `verde_max` seguido del amarillo. Aplicado durante todo el análisis = plan FIJO. Al iniciar el plan RECOMENDADO, el carril 1 arranca en verde por ciclo fijo (A CONFIRMAR).
- **Verde máximo alcanzado (RN-05)** (cambiado en el Word, nov/2026): el carril cede aunque tenga la mayor demanda y el verde pasa **al siguiente carril del ciclo fijo** (ya no al siguiente candidato sobre el umbral).
- **Demostración (RF-16, RN-11)**: sin modelo y sin escritura en la base; lee videos, conteos y eventos del plan elegido. En rojo se repite el último cuadro. Controles: reproducir, pausar, detener, velocidad ×1/×2. Muestra zona, conteo registrado y semáforo (sin cajas de detección).
- **Métricas de comparación (RF-17)**: se calculan sobre la ocupación registrada, no sobre la imagen (los vehículos grabados obedecen al semáforo real, riesgo R-11). Las calcula `validacion.py`. Cómo cuenta el amarillo: A CONFIRMAR (se asume que no suma a ninguna).
- **Estados de la ejecución**: Creada → EnEjecucion → Finalizada | Abortada. **Sin Pausada**: el análisis se puede cancelar (→ Abortada, se conservan los conteos), no pausar; pausar/detener la demostración no cambia el estado.
- **Mapeo de clases del modelo**: índice 0 = auto, 1 = moto, 2 = camión (debe coincidir con `dataset/data.yaml`). Camión incluye ómnibus (RN-02).
- **Interfaz: tkinter** (biblioteca estándar, sin Pillow ni otros paquetes). Barra lateral izquierda con acceso a todos los módulos; panel principal con 3 tarjetas, una por carril, con su video, conteo por clase y, **solo durante la demostración**, su semáforo dibujado en un `Canvas`; debajo, panel de comparación de los dos planes. Los cuadros se muestran en `tk.PhotoImage` a partir de bytes PPM generados con `cv2.imencode` en `visualizacion.py`. El análisis corre en un hilo aparte y se comunica con la interfaz mediante `queue.Queue` + `after()` (tkinter no es seguro entre hilos). Trazado de zonas sobre un `Canvas` de tkinter.
- **Esquema con 3 videos** (aprobado 28/10/2026): `ejecucion` no tiene `id_video`; los tres videos van en `ejecucion_video(id_ejecucion, id_video, posicion 1..3)`. Ver `docs/specs/diseno.md` §5.
- **Esquema, cambios del Word nov/2026** (pendientes en `esquema.sql`): `evento_fase.tipo_plan` (RECOMENDADO/FIJO), `evento_fase.marca_tiempo` en segundos de simulación, `ejecucion.estado` sin `Pausada`. Aplicar al empezar HU-08 (estado) y RF-12 (tipo_plan), avisando antes.
- **Rendimiento con 3 videos** (A CONFIRMAR al medir RNF-03): detección en lote de los 3 cuadros; si no alcanza, detectar cada *k* cuadros pero siempre en el cuadro de cierre del intervalo. RNF-03 mide solo el análisis.

## 7. Estado y avance (actualizar al cerrar cada HU)

| Sprint | Fechas | Alcance | Estado |
|---|---|---|---|
| 0 | 19/10–29/10 | Entorno, dataset, entrenamiento en Colab, `best.pt` · adelanto: esqueleto visual de la interfaz (semáforos simulados) | en curso |
| 1 | 30/10–09/11 | HU-01, HU-02, **HU-08**, RF-10 (+ conteo manual de referencia, tarea QA) | en curso · HU-01 aprobada · HU-02 en revisión (CP-02, CP-03 OK) · RF-10 en revisión (CP-10 OK) · HU-08 pendiente |
| 2 | 10/11–20/11 | HU-03, HU-04 (sprint sin holgura) | pendiente |
| 3 | 21/11–01/12 | HU-05, HU-06, RF-12 (generación de ambos planes) | pendiente |
| 4 | 02/12–10/12 | HU-07, **HU-09** (demostración y comparación, RF-16, RF-17), integración (80 %: 14 de 17 RF) | pendiente |
| Cierre | > 10/12 | RF-13, RF-14, RF-15, Etapa 4 (≥ 80 % de CP aprobados) | pendiente |

Metas medibles: mAP50 ≥ 80 % (RNF-01) · precisión de conteo ≥ 90 % (RNF-02) · tiempo del análisis ≤ 2 × duración del video (RNF-03) · RAM ≤ 8 GB (RNF-04) · configurar tres videos nuevos en ≤ 10 min (RNF-06).
