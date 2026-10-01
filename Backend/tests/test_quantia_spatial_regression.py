import unittest
from types import SimpleNamespace

from scripts.test_quantia_spatial_miguel_h import (
    is_bedroom_contract_space,
)


class QuantiaSpatialRegressionHelperTests(unittest.TestCase):
    def test_identifies_bedrooms_without_depending_on_generated_ids(self):
        spaces = [
            SimpleNamespace(
                id="PA_ESP_01",
                nombre="Recámara 1",
                tipo="Recamara",
            ),
            SimpleNamespace(
                id="dynamic-room-id",
                nombre="Dormitorio principal",
                tipo=None,
            ),
            SimpleNamespace(
                id="another-id",
                nombre="Cuarto principal",
                tipo="Habitación",
            ),
        ]

        self.assertTrue(is_bedroom_contract_space(spaces[0]))
        self.assertTrue(is_bedroom_contract_space(spaces[1]))
        self.assertTrue(is_bedroom_contract_space(spaces[2]))

    def test_rejects_non_bedroom_circulation(self):
        space = SimpleNamespace(
            id="PA_ESP_03",
            nombre="Pasillo de distribución",
            tipo="Circulación",
        )

        self.assertFalse(is_bedroom_contract_space(space))


if __name__ == "__main__":
    unittest.main()
