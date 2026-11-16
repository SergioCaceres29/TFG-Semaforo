"""Pruebas de configuracion.py: validación de zonas virtuales (HU-02, RF-02)."""

import unittest

from semaforo.configuracion import validar_zona
from semaforo.modelos import ErrorConfiguracion, Zona

TRIANGULO = ((0, 0), (100, 0), (50, 80))


class TestValidarZona(unittest.TestCase):
    def test_cp02_ca02_rechaza_poligono_de_menos_de_3_vertices(self):
        """HU-02 CA-02 / RF-02: un polígono necesita al menos 3 vértices."""
        with self.assertRaisesRegex(ErrorConfiguracion, "3 vértices"):
            validar_zona(Zona("Norte", ((0, 0), (100, 0))), [])

    def test_cp02_ca02_rechaza_nombre_de_carril_repetido(self):
        """HU-02 CA-02: dos carriles no pueden llamarse igual (sin distinguir mayúsculas)."""
        with self.assertRaisesRegex(ErrorConfiguracion, "Norte"):
            validar_zona(Zona(" norte ", TRIANGULO), ["Sur", "Norte"])

    def test_cp02_ca01_exige_nombre_del_carril(self):
        """HU-02 CA-01: el sistema pide el nombre del carril; vacío no se acepta."""
        with self.assertRaisesRegex(ErrorConfiguracion, "nombre"):
            validar_zona(Zona("   ", TRIANGULO), [])

    def test_cp02_acepta_zona_valida_y_limpia_el_nombre(self):
        """HU-02 CA-01: zona de 3 o más vértices con nombre único."""
        zona = validar_zona(Zona("  Ruta 14  ", TRIANGULO), ["Sur"])
        self.assertEqual(zona, Zona("Ruta 14", TRIANGULO))


if __name__ == "__main__":
    unittest.main()
