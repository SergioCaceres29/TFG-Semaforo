"""Ayudas de prueba para auditar las reglas de dependencia de CLAUDE.md §2."""

import ast
from pathlib import Path
from types import ModuleType

PROHIBIDOS_EN_PURO = {"cv2", "numpy", "sqlite3", "time", "datetime", "ultralytics", "torch", "pathlib", "os"}
"""Módulos que no pueden usar decision.py ni control_fases.py (Python puro: sin imagen, I/O, base ni reloj)."""


def modulos_importados(modulo: ModuleType) -> set[str]:
    """Nombres completos de los módulos que importa el archivo fuente de `modulo`."""
    arbol = ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))
    importados = {alias.name for nodo in ast.walk(arbol) if isinstance(nodo, ast.Import) for alias in nodo.names}
    return importados | {nodo.module for nodo in ast.walk(arbol) if isinstance(nodo, ast.ImportFrom)}
