"""Detección y clasificación de vehículos con el modelo YOLO26n propio (HU-03, RF-04, RF-05).

Único módulo que importa `ultralytics` y `torch` (CLAUDE.md §2). Se importan al cargar el modelo para
que el resto del programa arranque sin esperar a PyTorch.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from semaforo.modelos import Clase, Deteccion, ErrorConfiguracion

registro = logging.getLogger(__name__)

RUTA_PESOS = Path("modelos") / "best.pt"

Caja = Sequence[float]


class Detector:
    """RF-04, RF-05: detecta en lote los cuadros de los tres carriles y filtra por clase y confianza."""

    def __init__(self, umbral_confianza: float) -> None:
        self._umbral_confianza = umbral_confianza
        self._modelo = None
        self._dispositivo: int | str = "cpu"

    @property
    def nombres_modelo(self) -> dict[int, str]:
        """RN-02: índice → nombre de clase del modelo cargado (vacío si no hay modelo)."""
        if self._modelo is None:
            return {}
        return {int(indice): nombre.lower() for indice, nombre in self._modelo.names.items()}

    def cargar_modelo(self, pesos: Path = RUTA_PESOS) -> None:
        """RF-04, RNF-05: carga los pesos y verifica que sus clases sean las de RN-02.

        Usa la GPU si está disponible; si no, la CPU.
        """
        if not pesos.is_file():
            raise ErrorConfiguracion(f"No se encontró el modelo en «{pesos}».")
        import torch
        from ultralytics import YOLO

        try:
            self._modelo = YOLO(str(pesos))
        except Exception as error:  # el formato de los pesos lo valida Ultralytics
            raise ErrorConfiguracion(f"No se pudo cargar el modelo «{pesos.name}»: {error}") from error
        esperado = {clase.value: clase.descripcion for clase in Clase}
        if self.nombres_modelo != esperado:
            encontrado = self.nombres_modelo
            self._modelo = None
            raise ErrorConfiguracion(f"El modelo tiene las clases {encontrado}; se esperaba {esperado} (RN-02).")
        self._dispositivo = 0 if torch.cuda.is_available() else "cpu"
        registro.info("Modelo %s cargado en %s", pesos.name, "GPU" if self._dispositivo == 0 else "CPU")

    def detectar(self, cuadros: Sequence[np.ndarray]) -> list[list[Deteccion]]:
        """RF-04: una lista de detecciones válidas por cuadro, en el mismo orden (un cuadro por carril)."""
        if self._modelo is None:
            raise ErrorConfiguracion("Hay que cargar el modelo antes de detectar.")
        resultados = self._modelo.predict(list(cuadros), conf=self._umbral_confianza,
                                          device=self._dispositivo, verbose=False)
        return [self.filtrar_por_clase(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())
                for r in resultados]

    def filtrar_por_clase(self, cajas: Sequence[Caja], indices: Sequence[float],
                          confianzas: Sequence[float]) -> list[Deteccion]:
        """RF-05, RN-02, HU-03 CA-03: solo auto, moto o camión con confianza ≥ umbral."""
        clases_validas = {clase.value for clase in Clase}
        return [Deteccion(Clase(int(indice)), float(confianza), *map(float, caja))
                for caja, indice, confianza in zip(cajas, indices, confianzas, strict=True)
                if int(indice) in clases_validas and confianza >= self._umbral_confianza]
