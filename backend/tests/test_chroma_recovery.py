import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.api.routes.rag import _require_chroma_available
from app.core.config import settings
from app.services import vector_service


class ChromaRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.previous_status = vector_service._CHROMA_STATUS
        vector_service._CHROMA_STATUS = "unknown"

    def tearDown(self):
        vector_service._CHROMA_STATUS = self.previous_status

    def test_validation_runs_collection_query_and_reports_healthy(self):
        collection = Mock()
        client = Mock()
        client.list_collections.return_value = [
            SimpleNamespace(name=vector_service.COLLECTION_NAME)
        ]
        client.get_collection.return_value = collection
        with patch.object(vector_service, "get_chroma_client", return_value=client), patch.object(
            vector_service, "CHROMA_HOST", "chroma"
        ):
            self.assertEqual(vector_service.validate_chroma_storage(), "healthy")
        collection.count.assert_called_once()
        collection.query.assert_called_once()

    def test_query_failure_marks_chroma_degraded_and_blocks_rag(self):
        collection = Mock()
        collection.query.side_effect = RuntimeError("corrupt collection")
        client = Mock()
        client.list_collections.return_value = [
            SimpleNamespace(name=vector_service.COLLECTION_NAME)
        ]
        client.get_collection.return_value = collection
        with patch.object(vector_service, "get_chroma_client", return_value=client), patch.object(
            vector_service, "CHROMA_HOST", "chroma"
        ):
            with self.assertRaisesRegex(RuntimeError, "corrupt collection"):
                vector_service.validate_chroma_storage()
        self.assertEqual(vector_service.chroma_status(), "degraded")
        with self.assertRaises(HTTPException) as unavailable:
            _require_chroma_available()
        self.assertEqual(unavailable.exception.status_code, 503)

    def test_production_startup_does_not_crash_when_chroma_is_unavailable(self):
        from app.main import validate_startup_dependencies

        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        with patch.object(settings, "ENVIRONMENT", "production"), patch(
            "app.main.engine.connect", return_value=connection
        ), patch(
            "app.main.validate_chroma_storage",
            side_effect=RuntimeError("Chroma unavailable"),
        ):
            validate_startup_dependencies()
        self.assertEqual(vector_service.chroma_status(), "unknown")


if __name__ == "__main__":
    unittest.main()
