import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import hybrid_retrieval_service
from app.services import keyword_search_service
from app.services import vector_service


class HybridRetrievalTests(unittest.TestCase):
    def test_chroma_client_uses_configured_http_service(self):
        original_client = vector_service._chroma_client
        original_host = vector_service.CHROMA_HOST
        original_port = vector_service.CHROMA_PORT
        original_ssl = vector_service.CHROMA_SSL
        expected_client = object()
        try:
            vector_service._chroma_client = None
            vector_service.CHROMA_HOST = "chroma-service"
            vector_service.CHROMA_PORT = 8123
            vector_service.CHROMA_SSL = True
            with patch.object(
                vector_service.chromadb,
                "HttpClient",
                return_value=expected_client,
            ) as http_client:
                self.assertIs(vector_service.get_chroma_client(), expected_client)
            http_client.assert_called_once_with(
                host="chroma-service",
                port=8123,
                ssl=True,
            )
        finally:
            vector_service._chroma_client = original_client
            vector_service.CHROMA_HOST = original_host
            vector_service.CHROMA_PORT = original_port
            vector_service.CHROMA_SSL = original_ssl

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.index_path_patcher = patch.object(
            keyword_search_service,
            "KEYWORD_INDEX_PATH",
            Path(self.temp_dir.name) / "keyword.sqlite3",
        )
        self.index_path_patcher.start()
        keyword_search_service.replace_material_chunks(
            material_id=1,
            chunks=[
                "ACID properties ensure reliable database transactions. "
                "BCNF is a normal form used in database normalization.",
            ],
            title="DBMS Notes",
            subject_id=10,
            subject_name="DBMS",
        )
        keyword_search_service.replace_material_chunks(
            material_id=2,
            chunks=[
                "FCFS is a CPU scheduling algorithm that serves processes "
                "in arrival order.",
            ],
            title="Operating Systems Notes",
            subject_id=20,
            subject_name="Operating Systems",
        )
        keyword_search_service.replace_material_chunks(
            material_id=3,
            chunks=[
                "TCP provides reliable transport while UDP provides "
                "connectionless datagrams.",
            ],
            title="Computer Networks Notes",
            subject_id=30,
            subject_name="Computer Networks",
        )

    def tearDown(self):
        self.index_path_patcher.stop()
        self.temp_dir.cleanup()

    def test_acronym_query_finds_exact_technical_term(self):
        results = keyword_search_service.search_keywords("What is ACID?")

        self.assertTrue(results)
        self.assertEqual(results[0]["metadata"]["material_id"], 1)

    def test_semantic_style_query_matches_normalization_terms(self):
        results = keyword_search_service.search_keywords(
            "Explain database normalization"
        )

        self.assertEqual(results[0]["metadata"]["subject_name"], "DBMS")

    def test_subject_filter_excludes_other_materials(self):
        results = keyword_search_service.search_keywords(
            "Explain database normalization",
            subject_id=20,
        )

        self.assertEqual(results, [])

    def test_reindexing_material_replaces_previous_chunks(self):
        keyword_search_service.replace_material_chunks(
            material_id=1,
            chunks=["Updated transaction recovery notes."],
            title="Updated DBMS Notes",
            subject_id=10,
            subject_name="DBMS",
        )

        self.assertEqual(
            keyword_search_service.search_keywords("ACID"),
            [],
        )
        updated = keyword_search_service.search_keywords("recovery")
        self.assertEqual(updated[0]["metadata"]["title"], "Updated DBMS Notes")

    def test_ambiguous_scheduling_query_returns_os_material(self):
        results = keyword_search_service.search_keywords("What is scheduling?")

        self.assertTrue(results)
        self.assertEqual(
            results[0]["metadata"]["subject_name"],
            "Operating Systems",
        )

    def test_rrf_fuses_duplicate_chunk_and_marks_hybrid_source(self):
        vector_results = [
            {
                "id": "1_0",
                "document": "ACID properties",
                "metadata": {"material_id": 1, "title": "DBMS Notes"},
                "similarity": 0.9,
                "source": "vector",
            }
        ]
        keyword_results = [
            {
                "id": "1_0",
                "document": "ACID properties",
                "metadata": {"material_id": 1, "title": "DBMS Notes"},
                "score": 4.2,
                "source": "keyword",
            },
            {
                "id": "2_0",
                "document": "FCFS scheduling",
                "metadata": {"material_id": 2, "title": "OS Notes"},
                "score": 2.1,
                "source": "keyword",
            },
        ]

        contributions = hybrid_retrieval_service.fuse_results(
            vector_results,
            keyword_results,
            rrf_k=60,
        )
        fused = hybrid_retrieval_service.deduplicate_results(contributions)

        self.assertEqual(len(fused), 2)
        self.assertEqual(fused[0]["id"], "1_0")
        self.assertEqual(fused[0]["source"], "hybrid")
        self.assertAlmostEqual(
            fused[0]["score"],
            1 / 61 + 1 / 61,
        )
        self.assertEqual(fused[0]["metadata"]["material_id"], 1)


if __name__ == "__main__":
    unittest.main()
