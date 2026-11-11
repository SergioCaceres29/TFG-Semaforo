"""Pruebas de configuracion.py: zonas virtuales (HU-02, RF-02) y parámetros (RF-10)."""

import unittest
from dataclasses import asdict

from semaforo.configuracion import PARAMETROS_INICIALES, leer_parametros, validar_zona
from semaforo.modelos import ErrorConfiguracion, Parametros, Zona

TRIANGULO = ((0, 0), (100, 0), (50, 80))
TEXTOS_VALIDOS = {"umbral_demanda": "5", "umbral_confianza": "0,5", "intervalo_seg": "10",
                  "verde_min": "10", "verde_max": "60", "amarillo": "3"}


def con(**cambios: str) -> dict[str, str]:
    """Textos válidos del formulario con algunos campos cambiados."""
    return {**TEXTOS_VALIDOS, **cambios}


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


class TestParametros(unittest.TestCase):
    def test_cp10_acepta_parametros_validos(self):
        """RF-10: valores válidos se convierten en Parametros (coma o punto decimal)."""
        self.assertEqual(leer_parametros(TEXTOS_VALIDOS), Parametros(5, 0.5, 10, 10, 60, 3))
        self.assertEqual(leer_parametros(con(umbral_confianza="0.75")).umbral_confianza, 0.75)

    def test_cp10_acepta_limites(self):
        """RF-10: umbral de demanda 0, confianza 0 y 1, y verde máximo igual al mínimo."""
        for cambios in ({"umbral_demanda": "0"}, {"umbral_confianza": "0"},
                        {"umbral_confianza": "1"}, {"verde_max": "10"}):
            with self.subTest(cambios=cambios):
                leer_parametros(con(**cambios))

    def test_cp10_rechaza_valores_fuera_de_rango(self):
        """RF-10: cada regla de rango se rechaza con un mensaje que nombra el campo."""
        casos = {
            "umbral_demanda": ("-1", "Umbral de demanda"),
            "umbral_confianza": ("1,2", "Umbral de confianza"),
            "intervalo_seg": ("0", "Intervalo"),
            "verde_min": ("0", "Verde mínimo"),
            "verde_max": ("9", "Verde máximo"),
            "amarillo": ("0", "Amarillo"),
        }
        for campo, (valor, etiqueta) in casos.items():
            with self.subTest(campo=campo), self.assertRaisesRegex(ErrorConfiguracion, etiqueta):
                leer_parametros(con(**{campo: valor}))

    def test_cp10_rechaza_texto_no_numerico_o_decimal_en_enteros(self):
        """RF-10: los campos enteros no aceptan decimales ni texto; ninguno acepta vacío."""
        for campo, valor in (("intervalo_seg", "2,5"), ("verde_min", "diez"),
                             ("amarillo", ""), ("umbral_confianza", "alto")):
            with self.subTest(campo=campo), self.assertRaises(ErrorConfiguracion):
                leer_parametros(con(**{campo: valor}))

    def test_cp10_rechaza_campo_faltante(self):
        """RF-10: el formulario debe traer los seis parámetros."""
        textos = con()
        del textos["amarillo"]
        with self.assertRaisesRegex(ErrorConfiguracion, "Amarillo"):
            leer_parametros(textos)

    def test_parametros_iniciales_son_validos(self):
        """RF-10: los valores iniciales del formulario pasan la validación."""
        textos = {campo: str(valor) for campo, valor in asdict(PARAMETROS_INICIALES).items()}
        self.assertEqual(leer_parametros(textos), PARAMETROS_INICIALES)


if __name__ == "__main__":
    unittest.main()
