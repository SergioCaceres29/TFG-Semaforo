# CLAUDE.md — Prototipo de conteo vehicular y simulación semafórica (TFG UNAE)

> Este archivo es la especificación para la IA (Context Spec, Boundary Spec y Quality Spec) exigida en la Etapa 3 del TFG.
> Detalle completo bajo demanda: `docs/specs/requisitos.md` (RF, RNF, RN, HU y criterios de aceptación) y `docs/specs/diseno.md` (clases, flujos, estados, esquema SQL).
> Leé la sección correspondiente de esos archivos ANTES de implementar cualquier HU o RF.

## 1. Context Spec

### Qué es
Prueba de concepto (PoC) académica, sin cliente ni usuarios finales. Aplicación de escritorio/script en Python que:
1. Carga un video **pregrabado mp4** (1920×1080) de la intersección Ruta 14 y C. Sagrado Corazón de Jesús, Cambyreta.
2. Detecta y clasifica vehículos en **3 clases: auto, moto, camión** con un modelo YOLO26n propio (`modelos/best.pt`).
3. Mide la demanda de cada **carril** por **ocupación por intervalo** dentro de zonas virtuales poligonales (sin tracking).
4. Un motor de reglas asigna prioridad de paso; un simulador propio recrea el semáforo (verde/amarillo/rojo).
5. Persiste todo en SQLite y valida el conteo automático contra un conteo manual.

Rol único: **operador técnico** (sin login, sin usuarios, sin concurrencia).
Autor: Sergio Andrés Cáceres Surnyak. Metodología: Scrum (sprints de 1,5 semanas).

### Stack fijo (NO cambiar ni agregar nada sin preguntar)
- Python 3.13 · Ultralytics + **YOLO26 nano** · OpenCV 4.13 · PyTorch · SQLite 3.47 (módulo `sqlite3` de la biblioteca estándar)
- PyTorch: **`torch==2.14.*` desde el índice `cu126`** (la GTX 1050 Ti es Pascal; 2.15+ ya no la soporta). Si la GPU falla, usar CPU.
- Equipo de referencia: notebook Windows 11, i7-9750H, 16 GB RAM, GTX 1050 Ti 4 GB. Entrenamiento en Google Colab; inferencia local.
- Exportación CSV con el módulo `csv` estándar (RF-14), codificación `utf-8-sig` para que Excel la abra bien (RNF-10).

### Glosario obligatorio (en código, comentarios y mensajes)
- **carril** (nunca «acceso»), **precisión** (nunca «exactitud»), **Cambyreta** sin tilde.
- Zona virtual = polígono (≥ 3 vértices) sobre el primer cuadro que delimita un carril.
- Intervalo de evaluación = período de video al cierre del cual se consolida el conteo y se evalúa la prioridad.
- Ejecución = un procesamiento (completo o parcial) de un video con un conjunto de parámetros.
- **Todo el tiempo se mide en segundos del video** (`n_cuadro / fps`), nunca con el reloj del sistema.

## 2. Arquitectura (RNF-07: módulos independientes)

Monolito modular local. Un archivo por módulo en `src/semaforo/`, cada uno con la clase del diagrama de clases de diseño:

| Archivo | Clase | Responsabilidad | HU/RF |
|---|---|---|---|
| `modelos.py` | dataclasses | `Deteccion`, `Zona`, `Parametros`, `MetadatosVideo`, enums `Clase`, `EstadoSemaforo`, `EstadoEjecucion` | — |
| `captura.py` | `LectorVideo` | abrir mp4, validar, leer cuadros, metadatos | HU-01 / RF-01 |
| `configuracion.py` | (funciones) | trazado/edición de zonas, parámetros | HU-02 / RF-02, RF-03, RF-10 |
| `deteccion.py` | `Detector` | cargar `best.pt`, detectar, filtrar por clase y confianza | HU-03 / RF-04, RF-05 |
| `conteo.py` | `ContadorZonas` | punto-en-polígono, ocupación por zona/clase/intervalo | HU-04 / RF-06 |
| `decision.py` | `MotorDecision` | umbral, mayor demanda, desempate, ciclo fijo | HU-05 / RF-07 |
| `control_fases.py` | `ControladorSemaforo` | máquina de estados por carril, tiempos mín/máx, amarillo | HU-06 / RF-08 |
| `visualizacion.py` | `Visualizador` | dibujar cajas, zonas, conteos y semáforos | HU-07 / RF-09 |
| `persistencia.py` | `RepositorioSQLite` | único acceso a SQLite, esquema, inserciones, CSV | HU-08 / RF-11..14 |
| `validacion.py` | `ValidadorResultados` | conteo manual, métricas | RF-15 |
| `nucleo.py` | `GestorEjecucion` | orquesta el bucle de cuadros (diagrama de secuencia) | CU-02, RF-16 |
| `interfaz.py` | `InterfazPrincipal` | menú del operador (CU-01, CU-02, CU-03) | — |
| `__main__.py` | — | entrada: `python -m semaforo` | — |

Reglas de dependencia:
- Solo `nucleo.py` coordina módulos. Los demás importan únicamente `modelos.py` (excepción: `decision.py` usa `control_fases.py`).
- Solo `persistencia.py` importa `sqlite3`. Solo `deteccion.py` importa `ultralytics`/`torch`.
- `decision.py` y `control_fases.py` son **Python puro** (sin cv2, sin I/O, sin reloj) para poder probarlos de forma determinista.

## 3. Boundary Spec (lo que la IA NO puede hacer ni asumir)

- NO agregar dependencias, frameworks, GUIs, ORMs ni servicios. Si algo parece necesario, **preguntar primero** y justificar.
- NO implementar: video en vivo/cámaras, OCR de placas, web, móvil, API, tracking de vehículos, conexión a semáforos reales, autenticación.
- NO cambiar el esquema de base de datos de `docs/specs/diseno.md` sin aprobación. NO hacer UPDATE/DELETE sobre `conteo` ni `evento_fase` (RNF-09).
- NO agregar clases de vehículos fuera de auto/moto/camión (RN-02).
- NO usar videos de validación para entrenar (RN-10). NO tocar `dataset/`, `datos/videos/` ni `modelos/*.pt` salvo pedido explícito.
- NO inventar reglas de negocio. Si un caso no está cubierto por RN-01..RN-10 o por la sección 6, **preguntar**.
- NO avanzar a otra HU sin que la actual pase sus pruebas y yo la apruebe.
- NO hacer commits ni push sin que lo pida.

## 4. Quality Spec

- PEP 8. Nombres en **español**: clases en `PascalCase` (como en los diagramas), funciones/variables en `snake_case` (`leer_cuadro`, `seleccionar_carril_prioritario`), constantes en `MAYUSCULAS`.
- Type hints en todas las funciones públicas y docstring breve que cite el RF/RN que implementa (ej. `"""RN-07: desempate por mayor tiempo en rojo."""`).
- Funciones cortas, sin lógica duplicada, sin código muerto ni `print` de depuración (usar `logging`).
- Errores: excepciones propias en `modelos.py` (`ErrorVideo`, `ErrorConfiguracion`). Ante archivo inexistente, corrupto o no-mp4: mensaje controlado y el programa sigue operativo (RNF-05). Nunca `except:` vacío.
- Parámetros configurables en `Parametros` (dataclass), nunca números mágicos en el código.
- Windows: rutas con `pathlib`, y `if __name__ == "__main__":` en todo script que use Ultralytics.
- **Pruebas obligatorias**: cada criterio de aceptación (CA) tiene al menos una prueba en `tests/`, nombrada con su caso de prueba: `test_cp07_desempate_por_tiempo_en_rojo`. Framework y linter: ver sección 6.

## 5. Flujo de trabajo por HU (seguir siempre)

1. Leer la HU y sus CA en `docs/specs/requisitos.md` y lo relevante de `docs/specs/diseno.md`.
2. Proponer un plan corto (archivos a tocar, funciones, pruebas) y **esperar mi aprobación**.
3. Escribir primero las pruebas de los CA, luego el código mínimo que las hace pasar.
4. Ejecutar las pruebas y mostrar el resultado real. No declarar «listo» con pruebas fallando.
5. Auditar: ¿respeta las RN? ¿algún import prohibido? ¿coherente con la documentación del TFG?
6. Resumir en 5 líneas: qué se hizo, CA cubiertos, CP aprobados, pendientes.
7. Actualizar la tabla de avance (sección 7).

### Comandos (Windows, PowerShell, desde la raíz)
- Activar entorno: `.\.venv\Scripts\Activate.ps1`
- Ejecutar app: `python -m semaforo`
- Pruebas: `python -m unittest discover -s tests -v` (o `pytest -v` si se aprueba pytest)
- Ramas Git: `main` (estable) · `develop` (integración) · `feature/HU-0X-nombre` · `hotfix/*`. Versionado SemVer (`v0.1.0` por sprint).
- Commits: `HU-04: conteo por ocupación al cierre del intervalo (RF-06, RN-03)`.

## 6. Decisiones de implementación (no reinterpretar)

- **Conteo (RF-06, RN-03)**: `cantidad` = vehículos presentes en la zona **en el cuadro de cierre** de cada intervalo, por clase. Así un vehículo no se cuenta dos veces en el mismo intervalo, sin tracking.
- **Demanda de un carril** = suma de las tres clases en ese cuadro de cierre.
- **Pertenencia a zona** (A CONFIRMAR): punto de referencia = centro inferior de la caja `((x1+x2)/2, y2)`; `cv2.pointPolygonTest >= 0`. Si cae en dos zonas, va a la primera definida.
- **Movimientos conflictivos (RN-06)** (A CONFIRMAR): solo un carril en verde a la vez; el resto en rojo.
- **Ciclo fijo (RN-08)** (A CONFIRMAR): rotación en el orden de creación de las zonas, verde fijo = `verde_max`. Al iniciar, el primer carril arranca en verde por ciclo fijo.
- **Verde máximo alcanzado (RN-05)**: el carril cede aunque tenga la mayor demanda; pasa al siguiente candidato sobre el umbral y, si no hay, al siguiente del ciclo fijo.
- **Mapeo de clases del modelo**: índice 0 = auto, 1 = moto, 2 = camión (debe coincidir con `dataset/data.yaml`).
- Interfaz (A CONFIRMAR): ventanas OpenCV (HighGUI + callbacks de mouse) para zonas y visualización; `tkinter.filedialog`/`simpledialog` (biblioteca estándar) para elegir archivo y pedir nombres/parámetros.
- Pruebas (A CONFIRMAR): `unittest` (estándar) por defecto; `pytest` y `ruff` solo si los apruebo.

## 7. Estado y avance (actualizar al cerrar cada HU)

| Sprint | Fechas | Alcance | Estado |
|---|---|---|---|
| 0 | 19/10–29/10 | Entorno, dataset, entrenamiento en Colab, `best.pt` | en curso |
| 1 | 30/10–09/11 | HU-01, HU-02, RF-10 | pendiente |
| 2 | 10/11–20/11 | HU-03, HU-04 (sprint sin holgura) | pendiente |
| 3 | 21/11–01/12 | HU-05, HU-06, RF-12 | pendiente |
| 4 | 02/12–10/12 | HU-07, HU-08, RF-13, integración (80 %) | pendiente |
| Cierre | > 10/12 | RF-14, RF-15, RF-16, pruebas Etapa 4 | pendiente |

Metas medibles: mAP ≥ 80 % (RNF-01) · precisión de conteo ≥ 90 % (RNF-02) · tiempo ≤ 2 × duración del video (RNF-03) · RAM ≤ 8 GB (RNF-04) · configurar un video nuevo en ≤ 10 min (RNF-06).
