"""Sprint 0: verifica el entorno y los pesos traídos de Colab (modelos/best.pt).

Herramienta de puesta a punto, fuera del paquete `semaforo`. Comprueba:
- versiones de Python, PyTorch y OpenCV, y disponibilidad de CUDA;
- que `modelos/best.pt` exista y cargue;
- que el mapeo de clases sea 0 = auto, 1 = moto, 2 = camion (RN-02, CLAUDE.md §6).
"""

import logging
import sys
from pathlib import Path

RUTA_MODELO = Path(__file__).resolve().parent.parent / "modelos" / "best.pt"
CLASES_ESPERADAS = {0: "auto", 1: "moto", 2: "camion"}

logger = logging.getLogger(__name__)


def verificar_entorno() -> None:
    """Informa versiones y si la GPU está disponible (si no, se usa CPU)."""
    import cv2
    import torch

    logger.info("Python %s", sys.version.split()[0])
    logger.info("PyTorch %s | OpenCV %s", torch.__version__, cv2.__version__)
    if torch.cuda.is_available():
        logger.info("CUDA disponible: %s", torch.cuda.get_device_name(0))
    else:
        logger.warning("CUDA no disponible: la inferencia usará CPU")


def verificar_modelo(ruta: Path = RUTA_MODELO) -> bool:
    """Carga el modelo y compara su mapeo de clases con el esperado."""
    from ultralytics import YOLO

    if not ruta.is_file():
        logger.error("No se encontró el modelo en %s", ruta)
        return False
    nombres = {int(k): v.lower() for k, v in YOLO(str(ruta)).names.items()}
    if nombres != CLASES_ESPERADAS:
        logger.error("Mapeo de clases %s; se esperaba %s", nombres, CLASES_ESPERADAS)
        return False
    logger.info("Modelo correcto: %s", nombres)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    verificar_entorno()
    sys.exit(0 if verificar_modelo() else 1)
