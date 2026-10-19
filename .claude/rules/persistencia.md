---
paths:
  - "src/semaforo/persistencia.py"
  - "src/semaforo/esquema.sql"
  - "src/semaforo/validacion.py"
---

# Reglas de persistencia (RNF-09, RN-09, HU-08)

- Este es el ÚNICO módulo que importa `sqlite3`. Abrir con `PRAGMA foreign_keys = ON`.
- El esquema es el de `docs/specs/diseno.md` sección 5. No agregar ni renombrar columnas sin aprobación.
- `conteo` y `evento_fase`: solo `INSERT`. Nunca `UPDATE`, `DELETE`, `INSERT OR REPLACE` ni `UPSERT`. Los triggers lo bloquean; no desactivarlos.
- Todo registro de resultados lleva `id_ejecucion`, `id_zona` y marca de tiempo en segundos del video (RN-09).
- Consultas siempre parametrizadas (`?`), nunca armadas con f-strings.
- `commit` al cierre de cada intervalo para no perder datos ante una interrupción (HU-08 CA-04).
- CSV (RF-14): módulo `csv` estándar, `encoding="utf-8-sig"`, `newline=""`, separador `;` si se abrirá en Excel en español (confirmar).
- Pruebas: usar una base en memoria (`":memory:"`) o un archivo temporal; nunca la base real `datos/db/semaforo.db`.
