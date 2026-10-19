---
paths:
  - "src/semaforo/decision.py"
  - "src/semaforo/control_fases.py"
  - "tests/test_decision.py"
  - "tests/test_control_fases.py"
---

# Reglas del motor de decisión y del controlador de fases (RN-04 a RN-08)

- Python puro: sin `cv2`, sin `time.time()`, sin base de datos. El tiempo llega como parámetro en segundos del video.
- Orden de evaluación fijo: umbral (RN-04) → mayor demanda → desempate por tiempo en rojo (RN-07) → ciclo fijo si nadie supera el umbral (RN-08).
- La demanda debe SUPERAR el umbral (`>`), no igualarlo.
- Máquina de estados: ver `docs/specs/diseno.md` sección 3. Prohibido VERDE → ROJO directo.
- Un solo carril en verde a la vez. Verde dentro de [`verde_min`, `verde_max`]. Amarillo de duración fija.
- Cada transición devuelve los datos del evento (carril, estado, marca_tiempo, duración, demanda) para que el núcleo lo persista (RF-12); este módulo no guarda nada por sí mismo.
- Pruebas obligatorias (CP-07, CP-08): umbral no superado → ciclo fijo; mayor demanda gana; empate resuelto por rojo; no cambia antes de `verde_min`; cede al llegar a `verde_max` aunque tenga la mayor demanda; siempre pasa por amarillo; nunca dos verdes. Simular secuencias de tiempo completas, no solo llamadas sueltas.
