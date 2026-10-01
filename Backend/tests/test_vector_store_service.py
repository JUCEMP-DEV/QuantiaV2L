import unittest

from app.services.vector_store_service import LocalVectorStore, VectorChunk


class LocalVectorStoreTests(unittest.TestCase):
    def test_upsert_and_list_chunks(self):
        store = LocalVectorStore()
        chunk = VectorChunk(
            document_id="doc-1",
            chunk_id="doc-1-0",
            content="contenido",
            embedding=[1.0, 0.0],
            metadata={"source": "test"},
        )

        store.upsert_chunks([chunk])

        self.assertEqual(store.list_chunks(), [chunk])
        self.assertEqual(store.list_chunks(document_id="doc-1"), [chunk])
        self.assertEqual(store.list_chunks(document_id="doc-2"), [])

    def test_similarity_search_orders_by_cosine_similarity(self):
        store = LocalVectorStore()
        first = VectorChunk("doc", "a", "primero", [1.0, 0.0], {})
        second = VectorChunk("doc", "b", "segundo", [0.0, 1.0], {})
        store.upsert_chunks([second, first])

        results = store.similarity_search([1.0, 0.0], top_k=1)

        self.assertEqual(results[0][0], first)
        self.assertEqual(results[0][1], 1.0)

    def test_upsert_rejects_invalid_chunk(self):
        store = LocalVectorStore()
        chunk = VectorChunk("", "chunk", "contenido", [1.0], {})

        with self.assertRaises(ValueError):
            store.upsert_chunks([chunk])


if __name__ == "__main__":
    unittest.main()
