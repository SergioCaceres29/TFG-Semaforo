"""Pruebas de los tipos compartidos (modelos.py)."""

import unittest

from semaforo.modelos import POSICIONES_CARRIL, ActualizacionCarril, Clase


class TestModelos(unittest.TestCase):
    def test_mapeo_clases_coincide_con_indices_del_modelo(self):
        """RN-02 / CLAUDE.md §6: índice 0 = auto, 1 = moto, 2 = camión."""
        self.assertEqual([(c.value, c.descripcion) for c in Clase],
                         [(0, "auto"), (1, "moto"), (2, "camion")])

    def test_tres_carriles_en_posiciones_1_a_3(self):
        """RN-01: un video por carril, 3 carriles."""
        self.assertEqual(POSICIONES_CARRIL, (1, 2, 3))

    def test_demanda_es_suma_de_las_tres_clases(self):
        """CLAUDE.md §6: demanda de un carril = suma de las tres clases."""
        actualizacion = ActualizacionCarril(1, {Clase.AUTO: 4, Clase.MOTO: 2, Clase.CAMION: 1})
        self.assertEqual(actualizacion.demanda, 7)


if __name__ == "__main__":
    unittest.main()
