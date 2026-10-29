"""
test_app.py - Suite de pruebas unitarias para el MVP de Abstención Electoral INE.
Verifica la integridad de datos, lógica de clasificación de riesgo, filtros territoriales
y funciones del API.
"""

import unittest
from data_loader import DataLoader
import app

class TestMVPAbstencion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dl = app.data_loader

    def test_01_data_loader_integrity(self):
        """Verifica que DataLoader haya cargado exactamente 70,751 secciones."""
        self.assertIsNotNone(self.dl.df_secciones)
        self.assertEqual(len(self.dl.df_secciones), 70751)
        self.assertEqual(len(self.dl.df_estados), 32)
        self.assertEqual(len(self.dl.df_municipios), 2477)

    def test_02_global_stats(self):
        """Verifica que las estadísticas globales calculen los valores correctos."""
        stats = app.get_stats()
        self.assertEqual(stats["total_secciones"], 70751)
        self.assertEqual(stats["total_estados"], 32)
        self.assertEqual(stats["total_municipios"], 2477)
        self.assertAlmostEqual(stats["promedio_abstencion"], 46.77, places=1)
        
        # Verificar cuantiles
        self.assertIn("umbrales", stats)
        umbrales = stats["umbrales"]
        self.assertEqual(umbrales["q33"], 0.4231)
        self.assertEqual(umbrales["q66"], 0.5099)
        self.assertEqual(stats["secciones_alto_riesgo"], 23584)
        self.assertEqual(stats["secciones_medio_riesgo"], 23583)
        self.assertEqual(stats["secciones_bajo_riesgo"], 23584)

    def test_03_estados_list(self):
        """Verifica que get_estados devuelva las 32 entidades con métricas."""
        estados = app.get_estados()
        self.assertEqual(len(estados), 32)
        self.assertEqual(estados[0]["EDOCVE"], 1)
        self.assertEqual(estados[0]["EDONOM"], "AGUASCALIENTES")
        self.assertGreater(estados[0]["total_secciones"], 0)

    def test_04_municipios_filter(self):
        """Verifica el filtrado de municipios por estado."""
        mpios_ags = app.get_municipios(edocve=1)
        self.assertGreater(len(mpios_ags), 0)
        for m in mpios_ags:
            self.assertEqual(m["EDOCVE"], 1)

    def test_05_secciones_filtering(self):
        """Verifica consulta de secciones con filtros combinados."""
        # Filtrar por EDOCVE 1 y riesgo ALTO
        data = app.get_secciones(edocve=1, riesgo="ALTO", limit=10, offset=0)
        self.assertGreater(data["total"], 0)
        self.assertLessEqual(len(data["results"]), 10)
        for sec in data["results"]:
            self.assertEqual(sec["EDOCVE"], 1)
            self.assertEqual(sec["RIESGO"], "ALTO")
            self.assertGreater(sec["PREDICCION_ABSTENCION"], 0.5098)

    def test_06_seccion_detalle(self):
        """Verifica la consulta directa de una sección por ID_TERRITORIO."""
        sec = app.get_seccion_detalle("10010001")
        self.assertEqual(sec["ID_TERRITORIO"], 10010001)
        self.assertEqual(sec["SECCION"], 1)
        self.assertEqual(sec["EDONOM"], "AGUASCALIENTES")
        self.assertEqual(sec["RIESGO"], "BAJO")

    def test_07_resumen_tablas(self):
        """Verifica los resúmenes por estado y municipio."""
        res_edo = app.get_resumen_estados()
        self.assertEqual(len(res_edo), 32)

        res_mpio = app.get_resumen_municipios(edocve=1)
        self.assertGreater(len(res_mpio), 0)

    def test_08_geo_status(self):
        """Verifica que el estado de la capa geográfica sea informativo."""
        status = app.get_geo_status()
        self.assertFalse(status["capa_secciones_disponible"])
        self.assertTrue(status["capa_estatal_referencia"])
        self.assertIn("centroides", status["mensaje"].lower())

if __name__ == "__main__":
    unittest.main()
