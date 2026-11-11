---
paths:
  - "src/semaforo/decision.py"
  - "src/semaforo/control_fases.py"
  - "tests/test_decision.py"
  - "tests/test_control_fases.py"
---

# Reglas del motor de decisión y del controlador de fases (RN-04 a RN-08, RN-11)

- Python puro: sin `cv2`, sin `time.time()`, sin base de datos. Reciben la **demanda registrada** (conteos por carril e intervalo) y la duración del análisis como parámetros.
- Se ejecutan **después del análisis**, no dentro del bucle de cuadros. Generan dos planes con la misma duración: `RECOMENDADO` y `FIJO`.
- Tiempo: el plan corre en **segundos de simulación** (`t_sim`). Cada carril lleva su `t_video[p]`, que avanza solo en VERDE/AMARILLO y queda congelado en ROJO (RN-11). La demanda de un carril es la ocupación registrada en su `t_video[p]`.
- Orden de evaluación fijo: umbral (RN-04) → mayor demanda → desempate por tiempo en rojo (RN-07) → ciclo fijo si nadie supera el umbral (RN-08).
- La demanda debe SUPERAR el umbral (`>`), no igualarlo.
- RN-05: al llegar a `verde_max` el carril cede aunque tenga la mayor demanda, y el verde pasa **al siguiente carril del ciclo fijo** (1 → 2 → 3).
- Plan FIJO (RN-08): rotación 1 → 2 → 3, cada carril con `verde_max` + amarillo, durante toda la duración.
- Máquina de estados: ver `docs/specs/diseno.md` §3. Prohibido VERDE → ROJO directo.
- Un solo carril en verde a la vez. Verde dentro de [`verde_min`, `verde_max`]. Amarillo de duración fija.
- El plan termina cuando `t_sim` alcanza la duración del tramo analizado (HU-06 CA-05).
- Cada evento devuelto lleva: tipo de plan, carril, estado, `marca_tiempo` (s de simulación), duración y demanda asociada, para que el núcleo lo persista (RF-12); este módulo no guarda nada.
- Puntos abiertos (preguntar, no decidir): `docs/specs/diseno.md` §4.1.
- Pruebas obligatorias (CP-07, CP-08, CP-27): umbral no superado → ciclo fijo; mayor demanda gana; empate resuelto por rojo; no cambia antes de `verde_min`; cede al llegar a `verde_max` al siguiente del ciclo; siempre pasa por amarillo; nunca dos verdes; `t_video` congelado en rojo; ambos planes duran lo mismo que el análisis. Simular secuencias de demanda completas, no solo llamadas sueltas.
