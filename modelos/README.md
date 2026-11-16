# modelos/

Colocar aquí los pesos entrenados en Colab:

- `best.pt` — YOLO26n, 3 clases: `0 = auto`, `1 = camion`, `2 = moto` (deben coincidir con `dataset/data.yaml`).

Los `.pt` no se versionan (ver `.gitignore`). Tras copiarlo, verificar con:

```powershell
python herramientas/verificar_modelo.py
```
