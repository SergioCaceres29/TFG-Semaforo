---
paths:
  - "tests/**/*.py"
---

# Reglas de pruebas (Etapa 4, IEEE 829)

- Un archivo por módulo: `tests/test_<modulo>.py`.
- Nombre de cada prueba = caso de prueba + criterio: `test_cp01_rechaza_extension_no_mp4`. Docstring con HU, CA y RF/RN.
- Cada CA de `docs/specs/requisitos.md` tiene al menos una prueba. Si un CA no se puede automatizar (ej. RNF-06), dejar una prueba marcada como manual (`skip`) con el procedimiento en el docstring.
- Datos de prueba pequeños en `tests/datos/` (un mp4 de pocos segundos, un archivo .mp4 corrupto, un .avi). Nunca usar videos de validación ni el dataset.
- Las pruebas de `deteccion.py` que necesitan `best.pt` se saltan automáticamente si el archivo no existe.
- No borrar ni debilitar una prueba para que pase. Si una prueba parece incorrecta, avisar y explicar por qué.
- Al terminar una HU, mostrar la salida real de las pruebas (cantidad de aprobadas/fallidas).
