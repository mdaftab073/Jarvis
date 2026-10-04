import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import chromadb

from app.services import vector_service
from app.services.study_material_processing import process_pdf_material


class SafeReindexTests(unittest.TestCase):
    def setUp(self):
        self.material = SimpleNamespace(
            id=17,
            file_path="uploads/material.pdf",
            title="Notes",
            subject=SimpleNamespace(id=4, name="Systems"),
            material_type="NOTES",
            embedding_status="pending",
        )
        self.db = Mock()
        self.vectors = Mock()
        self.vectors.stage_material_chunks.return_value = {
            "ids": ["17_new_0", "17_new_1"],
            "previous_ids": ["17_old_0"],
        }
        self.dependencies = {
            "extract_text": Mock(return_value="document text"),
            "chunk_text": Mock(return_value=["new one", "new two"]),
            "vector_service": self.vectors,
            "replace_material_chunks": Mock(),
            "analyze_pyq_material": Mock(return_value=[]),
        }

    def run_processing(self):
        with patch(
            "app.services.study_material_processing.get_material",
            return_value=self.material,
        ), patch(
            "app.services.study_material_processing.validate_uploaded_file_path",
            side_effect=lambda path: path,
        ):
            return process_pdf_material(
                17, db=self.db, dependencies=self.dependencies
            )

    def test_success_activates_then_retires_previous_chunks(self):
        result = self.run_processing()

        self.assertEqual(result["chunks_stored"], 2)
        self.vectors.stage_material_chunks.assert_called_once()
        self.vectors.activate_staged_material_chunks.assert_called_once_with(
            ["17_new_0", "17_new_1"]
        )
        self.dependencies["replace_material_chunks"].assert_called_once()
        self.vectors.retire_previous_material_chunks.assert_called_once_with(
            ["17_old_0"]
        )
        self.vectors.discard_staged_material_chunks.assert_not_called()
        self.assertEqual(self.material.embedding_status, "embedded")

    def test_embedding_failure_preserves_old_chunks(self):
        self.vectors.stage_material_chunks.side_effect = TimeoutError(
            "temporary embedding failure"
        )

        with self.assertRaisesRegex(TimeoutError, "temporary embedding"):
            self.run_processing()

        self.vectors.stage_material_chunks.assert_called_once()
        self.vectors.retire_previous_material_chunks.assert_not_called()
        self.dependencies["replace_material_chunks"].assert_not_called()

    def test_chunking_failure_preserves_old_chunks(self):
        self.dependencies["chunk_text"].side_effect = ValueError(
            "invalid PDF content"
        )

        with self.assertRaisesRegex(ValueError, "invalid PDF content"):
            self.run_processing()

        self.vectors.stage_material_chunks.assert_not_called()
        self.vectors.retire_previous_material_chunks.assert_not_called()

    def test_partial_stage_write_failure_preserves_old_chunks(self):
        self.vectors.stage_material_chunks.side_effect = RuntimeError(
            "partial vector write"
        )

        with self.assertRaisesRegex(RuntimeError, "partial vector write"):
            self.run_processing()

        self.vectors.activate_staged_material_chunks.assert_not_called()
        self.vectors.retire_previous_material_chunks.assert_not_called()
        self.dependencies["replace_material_chunks"].assert_not_called()

    def test_keyword_write_failure_discards_new_generation(self):
        self.dependencies["replace_material_chunks"].side_effect = RuntimeError(
            "keyword index write failed"
        )

        with self.assertRaisesRegex(RuntimeError, "keyword index write failed"):
            self.run_processing()

        self.vectors.discard_staged_material_chunks.assert_called_once_with(
            ["17_new_0", "17_new_1"]
        )
        self.vectors.retire_previous_material_chunks.assert_not_called()


class VectorStagingTests(unittest.TestCase):
    def setUp(self):
        self.previous_client = vector_service._chroma_client
        self.client = chromadb.EphemeralClient()
        vector_service._chroma_client = self.client
        self.collection = vector_service.get_collection()
        self.collection.add(
            ids=["41_old_0"],
            embeddings=[[0.0] * 384],
            documents=["old searchable content"],
            metadatas=[{"material_id": 41, "subject_id": 9}],
        )

    def tearDown(self):
        vector_service._chroma_client = self.previous_client

    def test_new_generation_stays_hidden_until_activated_and_replaces_old(self):
        with patch.object(vector_service, "generate_embedding", return_value=[0.1] * 384):
            staged = vector_service.stage_material_chunks(
                41, ["replacement content"], "Notes", 9, "Systems"
            )

        self.assertEqual(
            self.collection.query(
                query_embeddings=[[0.1] * 384],
                n_results=5,
                where={"indexing_state": {"$ne": "staged"}},
            )["ids"],
            [["41_old_0"]],
        )
        vector_service.activate_staged_material_chunks(staged["ids"])
        visible = self.collection.query(
            query_embeddings=[[0.1] * 384],
            n_results=5,
            where={
                "$and": [
                    {"indexing_state": {"$ne": "staged"}},
                    {"indexing_state": {"$ne": "retired"}},
                ]
            },
        )["ids"][0]
        self.assertCountEqual(visible, ["41_old_0", staged["ids"][0]])

        vector_service.retire_previous_material_chunks(staged["previous_ids"])
        final = self.collection.query(
            query_embeddings=[[0.1] * 384],
            n_results=5,
            where={
                "$and": [
                    {"indexing_state": {"$ne": "staged"}},
                    {"indexing_state": {"$ne": "retired"}},
                ]
            },
        )["ids"][0]
        self.assertEqual(final, staged["ids"])

    def test_embedding_failure_leaves_old_vector_untouched(self):
        with patch.object(
            vector_service,
            "generate_embedding",
            side_effect=TimeoutError("embedding model unavailable"),
        ):
            with self.assertRaises(TimeoutError):
                vector_service.stage_material_chunks(
                    41, ["replacement content"], "Notes", 9, "Systems"
                )
        self.assertEqual(self.collection.get()["ids"], ["41_old_0"])

    def test_old_generation_lookup_failure_discards_staged_vectors(self):
        collection = Mock()
        collection.get.side_effect = [
            {"ids": ["staged"], "metadatas": [{"indexing_state": "staged"}]},
            RuntimeError("old generation lookup failed"),
        ]
        with patch.object(
            vector_service, "get_collection", return_value=collection
        ), patch.object(
            vector_service, "generate_embedding", return_value=[0.1] * 384
        ):
            with self.assertRaisesRegex(RuntimeError, "old generation lookup"):
                vector_service.stage_material_chunks(
                    41, ["replacement content"], "Notes", 9, "Systems"
                )

        collection.delete.assert_called_once_with(
            ids=collection.add.call_args.kwargs["ids"]
        )


if __name__ == "__main__":
    unittest.main()

    def test_partial_chroma_write_is_removed_without_deleting_old_vector(self):
        original_add = self.collection.add

        def write_one_then_fail(*, ids, embeddings, documents, metadatas):
            original_add(
                ids=ids[:1],
                embeddings=embeddings[:1],
                documents=documents[:1],
                metadatas=metadatas[:1],
            )
            raise RuntimeError("simulated partial Chroma write")

        with patch.object(vector_service, "generate_embedding", return_value=[0.2] * 384), patch.object(
            self.collection, "add", side_effect=write_one_then_fail
        ):
            with self.assertRaisesRegex(RuntimeError, "partial Chroma"):
                vector_service.stage_material_chunks(
                    41, ["first", "second"], "Notes", 9, "Systems"
                )
        self.assertEqual(self.collection.get()["ids"], ["41_old_0"])
