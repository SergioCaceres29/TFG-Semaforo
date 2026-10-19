# modelos/

Colocar aquí los pesos entrenados en Colab:

- `best.pt` — YOLO26n, 3 clases: `0 = auto`, `1 = moto`, `2 = camion` (deben coincidir con `dataset/data.yaml`).

Los `.pt` no se versionan (ver `.gitignore`). Tras copiarlo, verificar con:

```powershell
python herramientas/verificar_modelo.py
```
