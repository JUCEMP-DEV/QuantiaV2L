import unittest

from app.services.embedding_service import EmbeddingService, EmbeddingServiceError


class FakeEmbeddingModel:
    def __init__(self):
        self.received_texts = None

    def encode(self, texts, convert_to_numpy=False, normalize_embeddings=True):
        self.received_texts = texts
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


class EmbeddingServiceTests(unittest.TestCase):
    def test_embed_text_returns_single_vector(self):
        model = FakeEmbeddingModel()
        service = EmbeddingService(model=model)

        vector = service.embed_text(" texto   con   espacios ")

        self.assertEqual(vector, [18.0, 0.0])
        self.assertEqual(model.received_texts, ["texto con espacios"])

    def test_embed_texts_returns_one_vector_per_text(self):
        service = EmbeddingService(model=FakeEmbeddingModel())

        vectors = service.embed_texts(["uno", "dos palabras"])

        self.assertEqual(vectors, [[3.0, 0.0], [12.0, 1.0]])

    def test_embed_texts_rejects_empty_text(self):
        service = EmbeddingService(model=FakeEmbeddingModel())

        with self.assertRaises(EmbeddingServiceError):
            service.embed_texts(["contenido", "   "])

    def test_embed_texts_returns_empty_for_empty_input(self):
        service = EmbeddingService(model=FakeEmbeddingModel())

        self.assertEqual(service.embed_texts([]), [])

    def test_hashing_backend_is_deterministic_and_normalized(self):
        service = EmbeddingService(backend="hashing", dimension=16)

        first = service.embed_text("Cimentacion con concreto y acero")
        second = service.embed_text("Cimentacion con concreto y acero")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_hashing_backend_rejects_unknown_backend(self):
        with self.assertRaises(EmbeddingServiceError):
            EmbeddingService(backend="desconocido")


if __name__ == "__main__":
    unittest.main()

