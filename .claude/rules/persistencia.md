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
- Todo registro de resultados lleva `id_ejecucion` e `id_zona` (RN-09). `conteo` y `conteo_manual` usan segundos del video; `evento_fase` lleva además `tipo_plan` (RECOMENDADO/FIJO) y `marca_tiempo` en **segundos de simulación**.
- Cambios del Word (nov/2026): `ejecucion.estado` sin `Pausada` ya aplicado (HU-08). `evento_fase.tipo_plan` pendiente: aplicarlo al empezar RF-12, avisando; recrear la base de desarrollo.
- La ejecución nace `Creada` (`insertar_ejecucion`); `actualizar_estado_ejecucion` es el único UPDATE permitido sobre resultados. Cada intervalo se inserta en una sola transacción (las 3 clases juntas).
- La demostración solo **lee** (`consultar_plan`, `consultar_conteos`); nunca escribe.
- Consultas siempre parametrizadas (`?`), nunca armadas con f-strings.
- `commit` al cierre de cada intervalo para no perder datos ante una interrupción (HU-08 CA-04).
- CSV (RF-14): módulo `csv` estándar, `encoding="utf-8-sig"`, `newline=""`, separador `;` si se abrirá en Excel en español (confirmar).
- Pruebas: usar una base en memoria (`":memory:"`) o un archivo temporal; nunca la base real `datos/db/semaforo.db`.
