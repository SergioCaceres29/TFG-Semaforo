"""Configuración (HU-02, RF-02): reglas de las zonas virtuales trazadas por el operador."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from semaforo.modelos import ErrorConfiguracion, Zona

MIN_VERTICES = 3


def validar_zona(zona: Zona, nombres_otros_carriles: Iterable[str]) -> Zona:
    """HU-02 CA-01, CA-02: ≥ 3 vértices y nombre de carril no vacío ni repetido.

    Devuelve la zona con el nombre sin espacios sobrantes. La comparación de nombres
    no distingue mayúsculas para que «Norte» y «norte» cuenten como el mismo carril.
    """
    if len(zona.vertices) < MIN_VERTICES:
        raise ErrorConfiguracion(f"La zona necesita al menos {MIN_VERTICES} vértices; "
                                 f"tiene {len(zona.vertices)}.")
    nombre = zona.nombre_carril.strip()
    if not nombre:
        raise ErrorConfiguracion("Ingresá el nombre del carril.")
    for otro in nombres_otros_carriles:
        if otro.strip().casefold() == nombre.casefold():
            raise ErrorConfiguracion(f"Ya hay otro carril llamado «{otro.strip()}».")
    return replace(zona, nombre_carril=nombre)
