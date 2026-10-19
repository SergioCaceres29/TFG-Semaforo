# TFG-Semaforo
Este es repositorio oficial del desarrollo de mi TFG a desarrollarse entre octubre a diciembre del 2026

## Puesta a punto (Windows, PowerShell, desde la raíz)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

1. Copiar `best.pt` (entrenado en Colab) a `modelos/` y `data.yaml` a `dataset/`.
2. Verificar: `python herramientas/verificar_modelo.py`
3. Videos mp4 en `datos/videos/` (no se versionan).

## Estructura

```
src/semaforo/    paquete de la aplicación (python -m semaforo)
tests/           pruebas unittest (test_cpXX_...)
modelos/         best.pt (no versionado)
dataset/         data.yaml (imágenes no versionadas)
datos/videos/    videos de entrada
datos/db/        base SQLite
datos/exportaciones/  CSV (RF-14)
docs/specs/      requisitos.md y diseno.md
.claude/rules/   reglas de la IA por módulo (decisión, persistencia, pruebas)
notebooks/       entrenamiento_colab.ipynb
herramientas/    scripts auxiliares (verificar modelo, extraer cuadros, dividir dataset)
tests/datos/     mp4 corto, mp4 corrupto y .avi para las pruebas
```
