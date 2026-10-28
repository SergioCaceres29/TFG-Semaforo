# Requisitos del prototipo (fuente: Documentacion TFG Semaforo.docx, Etapa 1)

Este archivo es la referencia de qué construir y cómo verificarlo. Si algo de aquí contradice el código, manda este archivo.

## Requisitos funcionales (MoSCoW)

| Cód. | Requisito | Descripción | Prio. | Caso de prueba |
|---|---|---|---|---|
| RF-01 | Carga de video pregrabado | Seleccionar y cargar tres mp4 locales, uno por carril, validando extensión, apertura y fps iguales antes de procesar. | M | CP-01 |
| RF-02 | Definición de zonas virtuales | Delimitar una zona poligonal sobre el primer cuadro del video de cada carril. | M | CP-02 |
| RF-03 | Persistencia de zonas | Guardar coordenadas de zonas por video para reutilizarlas sin redefinir. | M | CP-03 |
| RF-04 | Detección de vehículos | Procesar cuadros con el modelo y obtener cajas con nivel de certeza. | M | CP-04 |
| RF-05 | Clasificación | Clasificar cada detección en auto, moto o camión; descartar lo demás. | M | CP-05 |
| RF-06 | Conteo de demanda por zona | Cantidad de vehículos dentro de cada zona en cada intervalo, por clase. | M | CP-06 |
| RF-07 | Motor de reglas de prioridad | Comparar demanda de cada carril contra umbral configurable y decidir prioridad. | M | CP-07 |
| RF-08 | Recreación del control semafórico | Simular verde/amarillo/rojo por carril respetando verde mínimo y máximo. | M | CP-08 |
| RF-09 | Visualización | Ventana con los tres videos, cajas, clase, conteo vigente por zona y el semáforo de cada carril. | M | CP-09 |
| RF-10 | Parametrización del ciclo | Configurar umbral de demanda, verde mín/máx y amarillo antes de ejecutar. | S | CP-10 |
| RF-11 | Registro de conteos | Guardar cada conteo por zona, clase e intervalo con marca de tiempo del video. | M | CP-11 |
| RF-12 | Registro de eventos de fase | Guardar cada cambio de estado: carril, estado, duración, demanda que lo motivó. | S | CP-12 |
| RF-13 | Registro de parámetros | Guardar los tres videos (con su carril), umbrales, tiempos de fase y versión del modelo de cada ejecución. | S | CP-13 |
| RF-14 | Exportación CSV | Exportar conteos a CSV con la biblioteca estándar. | S | CP-14 |
| RF-15 | Métricas de validación | Cargar conteo manual de un video y calcular error y precisión por clase. | S | CP-15 |
| RF-16 | Reproducción controlada | Iniciar, pausar y detener sin perder registros persistidos. | C | CP-16 |

Meta al 10/12/2026: 13 de 16 RF (todos los M + RF-10, RF-12, RF-13). RF-14, RF-15 y RF-16 quedan para el cierre.

## Requisitos no funcionales (ISO/IEC 25010)

| Cód. | Requisito | Métrica de aceptación | CP |
|---|---|---|---|
| RNF-01 | Precisión del modelo | mAP ≥ 80 % sobre conjunto de prueba independiente, 3 clases. | CP-17 |
| RNF-02 | Precisión del conteo | ≥ 90 % frente al conteo manual en videos de validación. | CP-18 |
| RNF-03 | Tiempo de procesamiento | Tiempo total ≤ 2 × duración del video en la notebook de referencia. | CP-19 |
| RNF-04 | Consumo de recursos | ≤ 8 GB de RAM con video 1920×1080. | CP-20 |
| RNF-05 | Estabilidad | Archivo inexistente, corrupto o no admitido → mensaje controlado y sigue operativo. | CP-21 |
| RNF-06 | Facilidad de configuración | Definir zonas y ejecutar un video nuevo en ≤ 10 min sin tocar código. | CP-22 |
| RNF-07 | Modularidad | Módulos independientes: captura, detección, conteo, decisión, visualización, persistencia. | CP-23 |
| RNF-08 | Portabilidad | Instalación en Windows 11 con entorno virtual y `requirements.txt`. | CP-24 |
| RNF-09 | Integridad | `conteo` y `evento_fase` de solo inserción; nada histórico se sobrescribe. | CP-25 |
| RNF-10 | Interoperabilidad | CSV abre en planilla de cálculo sin perder estructura ni tildes. | CP-26 |

## Reglas de negocio

| Cód. | Regla | Descripción |
|---|---|---|
| RN-01 | Origen de datos | Solo videos pregrabados mp4 de la intersección de estudio: uno por carril (3 en total), grabados en el mismo lapso de tiempo. |
| RN-02 | Clases admitidas | Solo auto, moto y camión. Otra categoría se descarta y no suma demanda. |
| RN-03 | Unicidad del conteo | Un vehículo en una zona cuenta una sola vez por intervalo (ocupación en el cuadro de cierre). |
| RN-04 | Asignación de prioridad | Prioridad al carril con mayor demanda que además supere el umbral. |
| RN-05 | Verde acotado | Todo verde tiene duración mínima y máxima; nadie conserva el verde más allá del máximo. |
| RN-06 | Transición segura | Verde → amarillo (duración fija) → rojo. Nunca dos carriles conflictivos en verde a la vez. |
| RN-07 | Empates | A igual demanda, gana el carril con más tiempo acumulado en rojo. |
| RN-08 | Comportamiento por defecto | Si ningún carril supera el umbral, ciclo de tiempos fijos (línea base). |
| RN-09 | Trazabilidad | Todo conteo y evento de fase lleva id de ejecución, zona y marca de tiempo del video. |
| RN-10 | Independencia de la validación | Los videos de validación no pueden estar en el entrenamiento. |

## Historias de usuario y criterios de aceptación

### HU-01 · Carga de video pregrabado — Sprint 1 · 3 pts · RF-01 · RN-01 · CP-01, CP-21
- CA-01: al seleccionar un archivo local se muestra la ruta y se habilita la carga.
- CA-02: NO admite extensiones distintas de mp4; mensaje de error controlado y sigue operativo.
- CA-03: con archivo válido muestra el primer cuadro y registra metadatos: duración, fps, resolución.
- CA-04: mp4 que no abre (corrupto) → informa sin interrumpir la ejecución.
- CA-05: se carga un video en cada uno de los 3 carriles; la ejecución no se habilita hasta tener los tres.
- CA-06: si los fps de los tres videos no coinciden → error controlado. Si la duración difiere, se procesa hasta el final del más corto.

### HU-02 · Definición y persistencia de zonas virtuales — Sprint 1 · 5 pts · RF-02, RF-03 · RN-04, RN-09 · CP-02, CP-03
- CA-01: sobre el primer cuadro del video de cada carril, el operador marca vértices; el sistema dibuja el polígono y pide el nombre del carril.
- CA-02: NO acepta polígonos de < 3 vértices, más de una zona por video ni dos carriles con el mismo nombre.
- CA-03: al confirmar, las coordenadas se guardan asociadas al video.
- CA-04: se puede modificar vértices o eliminar una zona sin redefinir las demás.

### RF-10 · Parametrización del ciclo — Sprint 1 · CP-10
- Antes de ejecutar se configuran: umbral de demanda (entero ≥ 0), umbral de confianza (0–1), intervalo (s > 0), verde mínimo (s > 0), verde máximo (≥ verde mínimo), amarillo (s > 0). Valores inválidos se rechazan con mensaje.

### HU-03 · Detección y clasificación — Sprint 2 · 8 pts · RF-04, RF-05 · RN-02, RN-10 · CP-04, CP-05, CP-17
- CA-01: por cada cuadro se obtienen cajas con su nivel de confianza.
- CA-02: cada detección es auto, moto o camión; NO se contabilizan otros objetos.
- CA-03: detecciones con confianza menor al umbral se descartan y no suman demanda.
- CA-04: el modelo alcanza mAP ≥ 80 % en el conjunto de prueba independiente.

### HU-04 · Conteo de demanda por zona — Sprint 2 · 8 pts · RF-06 · RN-03 · CP-06, CP-18
- CA-01: cada vehículo válido se asigna a la zona que lo contiene, o se descarta si no está en ninguna.
- CA-02: el conteo se consolida por zona y por clase al cierre de cada intervalo.
- CA-03: un vehículo que permanece en la zona en cuadros consecutivos NO se cuenta más de una vez en el intervalo.
- CA-04: precisión ≥ 90 % frente al conteo manual en los videos de validación.

### HU-05 · Asignación de prioridad — Sprint 3 · 5 pts · RF-07 · RN-04, RN-07, RN-08 · CP-07
- CA-01: son candidatos los carriles cuya demanda supera el umbral.
- CA-02: recibe prioridad el candidato de mayor demanda.
- CA-03: empate → gana el de mayor tiempo acumulado en rojo.
- CA-04: si nadie supera el umbral → ciclo de tiempos fijos.

### HU-06 · Recreación virtual del control semafórico — Sprint 3 · 8 pts · RF-08 · RN-05, RN-06 · CP-08
- CA-01: cada carril está siempre en verde, amarillo o rojo.
- CA-02: nadie conserva el verde más allá del máximo; ninguna transición antes del mínimo.
- CA-03: verde → rojo siempre pasa por amarillo de duración fija.
- CA-04: NO hay dos carriles conflictivos en verde al mismo tiempo.

### RF-12 · Registro de eventos de fase — Sprint 3 · CP-12
- Cada cambio de estado se inserta en `evento_fase` con carril, estado, marca de tiempo, duración y demanda asociada.

### HU-07 · Visualización — Sprint 4 · 5 pts · RF-09 · RN-06 · CP-09
- CA-01: cajas con la clase de cada vehículo en cada cuadro.
- CA-02: contorno de cada zona y su conteo vigente.
- CA-03: estado simulado de cada carril, actualizado en el momento de la transición.
- CA-04: los tres videos se muestran en simultáneo, cada uno junto al semáforo de su carril.

### HU-08 · Registro persistente de conteos — Sprint 4 · 3 pts · RF-11 · RN-09 · CP-11, CP-25
- CA-01: al cierre de cada intervalo se guarda un registro por zona y clase con la marca de tiempo del video.
- CA-02: todo registro lleva id de ejecución y zona.
- CA-03: NO se sobrescriben ejecuciones anteriores; re-ejecutar los mismos videos crea registros nuevos.
- CA-04: si el proceso se interrumpe, lo ya guardado se conserva.

### RF-13 · Registro de parámetros de ejecución — Sprint 4 · CP-13
- Cada ejecución guarda video, umbrales, intervalo, tiempos de fase, versión del modelo y estado.

### Cierre: RF-14 (CSV), RF-15 (métricas), RF-16 (pausa/detención)
- RF-15: precisión = (1 − Σ|Ca − Cm| / ΣCm) × 100 por zona y clase; error = Σ|Ca − Cm|. Ca = conteo automático, Cm = manual.
- RF-16: estados Creada → EnEjecucion ⇄ Pausada → Finalizada | Abortada; al abortar se conservan los registros.
