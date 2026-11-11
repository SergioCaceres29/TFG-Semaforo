"""Configuración: zonas virtuales (HU-02, RF-02) y parámetros del ciclo (RF-10)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import fields, replace

from semaforo.modelos import ErrorConfiguracion, Parametros, Zona

MIN_VERTICES = 3

ETIQUETAS_PARAMETROS: dict[str, str] = {
    "umbral_demanda": "Umbral de demanda (vehículos)",
    "umbral_confianza": "Umbral de confianza (0 a 1)",
    "intervalo_seg": "Intervalo de evaluación (s)",
    "verde_min": "Verde mínimo (s)",
    "verde_max": "Verde máximo (s)",
    "amarillo": "Amarillo (s)",
}

PARAMETROS_INICIALES = Parametros(umbral_demanda=5, umbral_confianza=0.5, intervalo_seg=10,
                                  verde_min=10, verde_max=28, amarillo=3)
"""Valores con los que arranca el formulario (A CONFIRMAR con el autor).

verde_max 28 s + amarillo 3 s por carril da un ciclo fijo de 93 s, cercano al ciclo de
92 s de la línea base (§1.2 del TFG). El operador puede cambiarlos antes de ejecutar.
"""


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


def leer_parametros(textos: Mapping[str, str]) -> Parametros:
    """RF-10: convierte los textos del formulario en Parametros válidos.

    Acepta coma o punto decimal en el umbral de confianza. Ante cualquier valor
    faltante, no numérico o fuera de rango lanza ErrorConfiguracion nombrando el campo.
    """
    valores = {}
    for campo in fields(Parametros):
        convertir = int if campo.type in (int, "int") else float
        valores[campo.name] = _convertir(campo.name, textos.get(campo.name, ""), convertir)
    return validar_parametros(Parametros(**valores))


def validar_parametros(parametros: Parametros) -> Parametros:
    """RF-10: reglas de rango (las mismas restricciones CHECK de la tabla ejecucion)."""
    reglas: tuple[tuple[str, bool, str], ...] = (
        ("umbral_demanda", parametros.umbral_demanda >= 0, "debe ser 0 o mayor"),
        ("umbral_confianza", 0 <= parametros.umbral_confianza <= 1, "debe estar entre 0 y 1"),
        ("intervalo_seg", parametros.intervalo_seg > 0, "debe ser mayor que 0"),
        ("verde_min", parametros.verde_min > 0, "debe ser mayor que 0"),
        ("verde_max", parametros.verde_max >= parametros.verde_min,
         "debe ser mayor o igual que el verde mínimo"),
        ("amarillo", parametros.amarillo > 0, "debe ser mayor que 0"),
    )
    for campo, cumple, motivo in reglas:
        if not cumple:
            raise ErrorConfiguracion(f"{_nombre(campo)}: {motivo}.")
    return parametros


def _convertir(campo: str, texto: str, convertir: Callable[[str], int | float]) -> int | float:
    limpio = texto.strip().replace(",", ".")
    if not limpio:
        raise ErrorConfiguracion(f"{_nombre(campo)}: ingresá un valor.")
    try:
        return convertir(limpio)
    except ValueError as error:
        tipo = "un número entero" if convertir is int else "un número"
        raise ErrorConfiguracion(f"{_nombre(campo)}: «{texto.strip()}» no es {tipo}.") from error


def _nombre(campo: str) -> str:
    """Etiqueta del campo sin la unidad entre paréntesis, para los mensajes."""
    return ETIQUETAS_PARAMETROS[campo].split(" (")[0]
