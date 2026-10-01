import unittest
from types import SimpleNamespace

from app.prompts.quantia_extraction_prompt import (
    QUANTIA_EXTRACTION_PROMPT,
)
from app.prompts.quantia_space_localization_prompt import (
    build_quantia_space_localization_prompt,
)


class QuantiaExtractionPromptTests(unittest.TestCase):
    def test_requires_complete_dimension_chains_before_space_assignment(self):
        self.assertIn(
            "Una cota parcial NUNCA representa por sí sola",
            QUANTIA_EXTRACTION_PROMPT,
        )
        self.assertIn(
            "están presentes TODOS los tramos intermedios",
            QUANTIA_EXTRACTION_PROMPT,
        )
        self.assertIn(
            '"<nivel> | <horizontal o vertical> | eje <inicio>→<fin>',
            QUANTIA_EXTRACTION_PROMPT,
        )

    def test_requires_independent_opening_passes(self):
        self.assertIn(
            "pasada visual independiente\ny completa por CADA nivel para buscar puertas",
            QUANTIA_EXTRACTION_PROMPT,
        )
        self.assertIn(
            "pasada visual independiente y completa por CADA nivel\npara ventanas",
            QUANTIA_EXTRACTION_PROMPT,
        )
        self.assertIn(
            "No dupliques la misma puerta en dos espacios",
            QUANTIA_EXTRACTION_PROMPT,
        )


class QuantiaLocalizationPromptTests(unittest.TestCase):
    def test_irregular_circulation_cannot_cover_closed_rooms(self):
        extraction = SimpleNamespace(
            niveles=[
                SimpleNamespace(
                    nombre="Planta Alta",
                    espacios=[
                        SimpleNamespace(
                            id_propuesto="pa_pasillo",
                            nombre="Pasillo de circulación",
                        )
                    ],
                )
            ]
        )

        prompt = build_quantia_space_localization_prompt(extraction)

        self.assertIn("id_propuesto: pa_pasillo", prompt)
        self.assertIn(
            "NO expandas un único rectángulo hasta incluir recámaras",
            prompt,
        )
        self.assertIn(
            "El mobiliario y las\netiquetas sirven para reconocer el recinto",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
