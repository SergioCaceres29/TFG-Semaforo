# Requisitos del prototipo (fuente: Documentacion TFG Semaforo.docx, Etapa 1 y Tabla 33)

Este archivo es la referencia de qué construir y cómo verificarlo. Si algo de aquí contradice el código, manda este archivo. Si contradice al Word, manda el Word: avisar y actualizar este archivo.

## Visión en tres momentos (cambio de noviembre 2026)

1. **Análisis** (CU-02, HU-03, HU-04, HU-07, HU-08): los tres videos se recorren sincronizados (`t = n / fps`), se detecta, se cuenta la ocupación por zona y se guarda el conteo al cierre de cada intervalo. **Durante el análisis no hay semáforo**.
2. **Generación de planes** (HU-05, HU-06, RF-12, RF-17): al terminar el análisis, el motor recorre la **demanda registrada** y genera dos planes con la misma duración que el tramo analizado: el **RECOMENDADO** (motor de reglas) y el **FIJO** (ciclo de tiempos fijos). Ambos se guardan en `evento_fase`.
3. **Demostración y comparación** (CU-06, HU-09, RF-16, RF-17): se reproduce el plan elegido sobre los videos **sin ejecutar el modelo**; el video de cada carril avanza en verde o amarillo y se congela en rojo (RN-11). Se muestran las métricas de comparación de ambos planes.

## Requisitos funcionales (MoSCoW)

| Cód. | Requisito | Descripción | Prio. | Caso de prueba |
|---|---|---|---|---|
| RF-01 | Carga de video pregrabado | Seleccionar y cargar tres mp4 locales, uno por carril, validando extensión, apertura y fps iguales antes de procesar. | M | CP-01 |
| RF-02 | Definición de zonas virtuales | Delimitar una zona poligonal sobre el primer cuadro del video de cada carril, asociada a ese carril. | M | CP-02 |
| RF-03 | Persistencia de zonas | Guardar coordenadas de zonas por video para reutilizarlas sin redefinir. | M | CP-03 |
| RF-04 | Detección de vehículos | Procesar cuadros con el modelo y obtener cajas con nivel de certeza. | M | CP-04 |
| RF-05 | Clasificación | Clasificar cada detección en auto, moto o camión; descartar lo demás. | M | CP-05 |
| RF-06 | Conteo de demanda por zona | Cantidad de vehículos dentro de cada zona en cada intervalo, por clase. | M | CP-06 |
| RF-07 | Motor de reglas de prioridad | Recorrer la demanda **registrada** de cada carril, compararla contra un umbral configurable y decidir, en cada intervalo de evaluación, qué carril recibe la prioridad. | M | CP-07 |
| RF-08 | Generación del plan semafórico | Generar la secuencia verde/amarillo/rojo de cada carril aplicando la prioridad y respetando verde mín/máx. El plan dura lo mismo que el tramo analizado. | M | CP-08 |
| RF-09 | Visualización del análisis | Durante el análisis, mostrar los tres videos con cajas, clase y conteo vigente por zona (**sin semáforo**). | M | CP-09 |
| RF-10 | Parametrización del ciclo | Configurar umbral de demanda, verde mín/máx y amarillo antes de ejecutar. | S | CP-10 |
| RF-11 | Registro de conteos | Guardar cada conteo por zona, clase e intervalo con marca de tiempo del video. | M | CP-11 |
| RF-12 | Registro de eventos de fase | Guardar cada cambio de estado de **los planes generados**: tipo de plan (RECOMENDADO/FIJO), carril, estado, instante en **segundos de simulación**, duración y demanda que motivó la decisión. | S | CP-12 |
| RF-13 | Registro de parámetros | Guardar los tres videos (con su carril), umbrales, intervalo, tiempos de fase y versión del modelo de cada ejecución. | S | CP-13 |
| RF-14 | Exportación CSV | Exportar los conteos registrados a CSV con la biblioteca estándar. | S | CP-14 |
| RF-15 | Métricas de validación | Cargar conteo manual de un video y calcular error y precisión por clase. | S | CP-15 |
| RF-16 | Demostración guiada por el plan | Reproducir los tres videos aplicando el plan elegido: cada video avanza en verde o amarillo y se detiene en el último cuadro en rojo. Cada carril muestra zona, conteo y semáforo. Controles: reproducir, pausar, detener, velocidad normal o doble; nada de esto modifica los registros. | M | CP-16 |
| RF-17 | Comparación con el ciclo fijo | Generar con los mismos videos y tiempos de fase un plan de ciclo fijo, permitir reproducir cualquiera de los dos y mostrar para ambos el **tiempo de verde sin demanda** y la **espera acumulada**, por carril y en total. | M | CP-27 |

Meta al 10/12/2026: **14 de 17 RF (82 %)** — todos los M (RF-01 a RF-09, RF-11, RF-16, RF-17) + RF-10 y RF-12. Quedan para el cierre RF-13, RF-14 y RF-15.

## Requisitos no funcionales (ISO/IEC 25010)

| Cód. | Requisito | Métrica de aceptación | CP |
|---|---|---|---|
| RNF-01 | Precisión del modelo | **mAP50** ≥ 80 % sobre conjunto de prueba independiente, 3 clases. | CP-17 |
| RNF-02 | Precisión del conteo | ≥ 90 % frente al conteo manual en videos de validación. | CP-18 |
| RNF-03 | Tiempo de procesamiento | Tiempo del **análisis** de los tres videos ≤ 2 × duración nominal, en la notebook de referencia. La demostración no ejecuta el modelo y no se mide aquí. | CP-19 |
| RNF-04 | Consumo de recursos | ≤ 8 GB de RAM analizando los tres videos 1920×1080. | CP-20 |
| RNF-05 | Estabilidad | Archivo inexistente, corrupto o no admitido → mensaje controlado y sigue operativo. | CP-21 |
| RNF-06 | Facilidad de configuración | Definir las zonas de **tres videos nuevos** y ejecutar en ≤ 10 min sin tocar código (prueba manual cronometrada). | CP-22 |
| RNF-07 | Modularidad | Módulos independientes: captura, detección, conteo, decisión, visualización, persistencia (revisión de dependencias, CLAUDE.md §2). | CP-23 |
| RNF-08 | Portabilidad | Instalación limpia en Windows 11 con entorno virtual y `requirements.txt`. | CP-24 |
| RNF-09 | Integridad | `conteo` y `evento_fase` de solo inserción; la base bloquea UPDATE/DELETE; re-ejecutar crea registros nuevos. | CP-25 |
| RNF-10 | Interoperabilidad | CSV abre en planilla de cálculo sin perder estructura ni tildes. | CP-26 |

## Reglas de negocio

| Cód. | Regla | Descripción |
|---|---|---|
| RN-01 | Origen de datos | Solo videos pregrabados mp4 de la intersección de estudio: uno por carril (3 en total), grabados en el mismo lapso de tiempo. |
| RN-02 | Clases admitidas | Solo auto, moto y camión. **Camión agrupa a todos los pesados, incluidos los ómnibus.** Otra categoría se descarta y no suma demanda. |
| RN-03 | Unicidad del conteo | Un vehículo en una zona cuenta una sola vez por intervalo (ocupación en el cuadro de cierre). |
| RN-04 | Asignación de prioridad | Prioridad al carril con mayor demanda que además **supere** el umbral. |
| RN-05 | Verde acotado | Todo verde tiene duración mínima y máxima. Nadie conserva el verde más allá del máximo aunque tenga la mayor demanda; **al cumplirse, el verde pasa al siguiente carril del ciclo fijo** (evita la inanición). |
| RN-06 | Transición segura | Verde → amarillo (duración fija) → rojo. Nunca dos carriles conflictivos en verde a la vez. |
| RN-07 | Empates | A igual demanda, gana el carril con más tiempo acumulado en rojo. |
| RN-08 | Ciclo de tiempos fijos | Si ningún carril supera el umbral, el plan recomendado aplica el ciclo fijo: recorre los carriles por posición 1 → 2 → 3, cada uno con `verde_max` seguido del amarillo. Aplicado durante todo el análisis es el **plan FIJO** de comparación (RF-17). |
| RN-09 | Trazabilidad | Todo conteo lleva id de ejecución, zona y marca de tiempo del video. Todo evento de fase lleva id de ejecución, **tipo de plan**, zona e instante del plan en **segundos de simulación**. |
| RN-10 | Independencia de la validación | Los videos de validación no pueden estar en el entrenamiento. |
| RN-11 | Reproducción según el estado semafórico (**nueva**) | En la demostración, el video de un carril avanza solo en verde o amarillo y se detiene en el último cuadro en rojo. Para generar el plan, la demanda de un carril en rojo es la ocupación registrada en el instante en que su video quedó detenido. |

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

### HU-08 · Registro persistente de conteos — **Sprint 1** · 3 pts · RF-11 · RN-09 · CP-11, CP-25
Se adelanta al Sprint 1 porque la persistencia ya existe por HU-02; se prueba con **conteos simulados** (aún no hay detector).
- CA-01: al cierre de cada intervalo se guarda un registro por zona y clase con la marca de tiempo del video.
- CA-02: todo registro lleva id de ejecución y zona.
- CA-03: NO se sobrescriben ejecuciones anteriores; re-ejecutar los mismos videos crea registros nuevos.
- CA-04: si el proceso se interrumpe, lo ya guardado se conserva.

### HU-03 · Detección y clasificación — Sprint 2 · 8 pts · RF-04, RF-05 · RN-02, RN-10 · CP-04, CP-05, CP-17, CP-20
- CA-01: por cada cuadro se obtienen cajas con su nivel de confianza.
- CA-02: cada detección es auto, moto o camión; NO se contabilizan otros objetos.
- CA-03: detecciones con confianza menor al umbral se descartan y no suman demanda.
- CA-04: el modelo alcanza mAP50 ≥ 80 % en el conjunto de prueba independiente.

### HU-04 · Conteo de demanda por zona — Sprint 2 · 8 pts · RF-06 · RN-03 · CP-06, CP-18
- CA-01: dadas las detecciones válidas de un cuadro del video de un carril, se evalúan contra la zona **de ese video**; se cuenta lo que está dentro y se descarta lo demás.
- CA-02: el conteo se consolida por zona y por clase al cierre de cada intervalo.
- CA-03: un vehículo que permanece en la zona en cuadros consecutivos NO se cuenta más de una vez en el intervalo.
- CA-04: precisión ≥ 90 % frente al conteo manual en los videos de validación.

### HU-05 · Asignación de prioridad según demanda — Sprint 3 · 5 pts · RF-07 · RN-04, RN-07, RN-08, RN-11 · CP-07
Se ejecuta **una vez terminado el análisis**, sobre la demanda registrada.
- CA-01: dado el conteo registrado de cada carril **en el instante de su video**, al cierre de cada intervalo de evaluación son candidatos los carriles cuya demanda supera el umbral.
- CA-02: recibe prioridad el candidato de mayor demanda.
- CA-03: empate → gana el de mayor tiempo acumulado en rojo.
- CA-04: si nadie supera el umbral → ciclo de tiempos fijos (línea base de comparación).

### HU-06 · Generación del plan semafórico — Sprint 3 · 8 pts · RF-08 · RN-05, RN-06, RN-11 · CP-08
- CA-01: el plan registra para cada carril uno de los estados verde, amarillo o rojo.
- CA-02: nadie conserva el verde más allá del máximo; ninguna transición antes del mínimo.
- CA-03: verde → rojo siempre pasa por amarillo de duración fija.
- CA-04: NO hay dos carriles conflictivos en verde al mismo tiempo.
- CA-05: el plan termina cuando el tiempo de simulación alcanza la duración del tramo analizado.

### RF-12 · Registro de eventos de fase — Sprint 3 · CP-12
- Cada cambio de estado de cada plan se inserta en `evento_fase` con tipo de plan, carril, estado, instante (s de simulación), duración y demanda asociada (la del carril en el instante de su video, RN-11).

### HU-07 · Visualización del análisis — Sprint 4 · 5 pts · RF-09 · RN-02 · CP-09
- CA-01: durante el análisis, cajas con la clase de cada vehículo en cada cuadro de salida.
- CA-02: contorno de cada zona y su conteo vigente.
- CA-03: los tres videos se muestran en simultáneo, cada uno en la tarjeta de su carril.

### HU-09 · Demostración y comparación del plan semafórico (**nueva**) — Sprint 4 · 5 pts · RF-16, RF-17 · RN-06, RN-08, RN-11 · CP-16, CP-27
- CA-01: dado un plan generado, al iniciar la demostración el video de cada carril avanza en verde o amarillo y se detiene en el último cuadro en rojo.
- CA-02: cada tarjeta muestra video, zona virtual, conteo y semáforo de su carril, y refleja cada cambio de fase en el momento en que ocurre.
- CA-03: reproducir, pausar, detener y velocidad normal o doble. Pausar o detener NO modifica los registros guardados.
- CA-04: antes de iniciar, el operador elige entre el plan RECOMENDADO y el FIJO.
- CA-05: se muestran, para ambos planes, el tiempo de verde sin demanda y la espera acumulada por carril y en total.

### RF-13 · Registro de parámetros de ejecución — Cierre · CP-13
- Cada ejecución guarda los tres videos (con su posición), umbrales, intervalo, tiempos de fase, versión del modelo y estado.

### Cierre: RF-13, RF-14 (CSV), RF-15 (métricas de validación)
- RF-15: precisión = (1 − Σ|Ca − Cm| / ΣCm) × 100 por zona y clase; error = Σ|Ca − Cm|. Ca = conteo automático, Cm = manual. El conteo manual sigue el **mismo criterio** que el sistema (presentes en la zona en el cuadro de cierre del intervalo).

## Métricas de comparación de planes (RF-17, glosario §2.6.1 del TFG)

- **Tiempo de verde sin demanda** (s): segundos en que un carril está en verde con ocupación cero en su zona.
- **Espera acumulada** (vehículos·s): suma, por cada segundo en rojo, de la ocupación del carril.
- Se calculan sobre la **ocupación registrada** (no sobre la imagen), por carril y en total, para RECOMENDADO y FIJO. Menor es mejor.
- Las calcula `validacion.py`; CP-27 exige que coincidan con un cálculo manual sobre conteos conocidos y que ambos planes duren lo mismo.

## Casos de prueba (Tabla 33 del TFG)

| CP | Módulo | Verifica |
|---|---|---|
| CP-01 | Captura | RF-01: tres mp4 válidos, .avi, mp4 corrupto, fps distintos |
| CP-21 | Captura | RNF-05: inexistente/corrupto/no admitido → mensaje controlado |
| CP-02 | Configuración | RF-02: polígonos de 2 y 4 vértices, nombres repetidos, edición y eliminación |
| CP-03 | Configuración, Persistencia | RF-03: la zona se recupera al reabrir el video |
| CP-10 | Configuración | RF-10: parámetros válidos e inválidos |
| CP-22 | Configuración | RNF-06: manual cronometrada, ≤ 10 min |
| CP-04 | Detección | RF-04: cajas con confianza, filtro por umbral |
| CP-05 | Detección | RF-05: solo tres clases |
| CP-17 | Detección | RNF-01: mAP50 ≥ 80 % |
| CP-20 | Detección | RNF-04: RAM ≤ 8 GB |
| CP-06 | Conteo | RF-06: detecciones simuladas dentro/fuera, una vez por intervalo |
| CP-18 | Conteo | RNF-02: precisión ≥ 90 % |
| CP-07 | Motor de decisión | RF-07: sobre/bajo umbral, empates, ciclo fijo |
| CP-08 | Controlador de fases | RF-08: secuencias completas de demanda registrada; verde mín/máx, amarillo, nunca dos verdes, duración = análisis |
| CP-12 | Controlador, Persistencia | RF-12: cada cambio con tipo de plan, carril, instante, duración y demanda |
| CP-09 | Visualización | RF-09: cajas, zonas y conteos de los tres videos |
| CP-16 | Núcleo, Captura, Visualización | RF-16, RN-11: avanza solo en verde/amarillo; controles y velocidad; registros intactos |
| CP-11 | Persistencia | RF-11: registros por zona y clase; se conservan tras interrupción |
| CP-13 | Persistencia | RF-13: tres videos, umbrales, tiempos, modelo |
| CP-14 | Persistencia | RF-14: CSV generado |
| CP-25 | Persistencia | RNF-09: UPDATE/DELETE bloqueados; ejecuciones independientes |
| CP-26 | Persistencia | RNF-10: CSV sin pérdida de estructura ni acentos |
| CP-15 | Validación | RF-15: error y precisión correctos |
| CP-27 | Decisión, Validación | RF-17: ambos planes misma duración; métricas = cálculo manual |
| CP-19 | Todos | RNF-03: análisis ≤ 2 × duración |
| CP-23 | Todos | RNF-07: reglas de dependencia |
| CP-24 | Todos | RNF-08: instalación limpia |
