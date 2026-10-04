import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import system_health_service


class SystemHealthTests(unittest.TestCase):
    def test_health_reports_all_dependencies_healthy(self):
        with (
            patch.object(system_health_service.engine, "connect") as connect,
            patch.object(system_health_service, "validate_rag_storage", return_value="healthy"),
            patch.object(system_health_service, "_migration_state", return_value="up_to_date"),
            patch.object(
                system_health_service,
                "get_worker_health",
                return_value={
                    "status": "healthy",
                    "last_heartbeat": "2026-10-04T12:00:00",
                    "pending_jobs": 0,
                },
            ),
        ):
            connect.return_value.__enter__.return_value.execute.return_value = None
            health = system_health_service.get_system_health()

        self.assertEqual(health["database"], "healthy")
        self.assertEqual(health["chroma"], "healthy")
        self.assertEqual(health["migrations"], "up_to_date")
        self.assertEqual(health["worker"]["status"], "healthy")
        self.assertEqual(health["overall"], "healthy")

    def test_health_reports_degraded_when_dependency_unavailable(self):
        with (
            patch.object(system_health_service.engine, "connect", side_effect=OSError("down")),
            patch.object(system_health_service, "validate_rag_storage", side_effect=OSError("down")),
            patch.object(system_health_service, "_migration_state", side_effect=OSError("down")),
            patch.object(
                system_health_service,
                "get_worker_health",
                return_value={
                    "status": "unhealthy",
                    "last_heartbeat": None,
                    "pending_jobs": 0,
                },
            ),
        ):
            health = system_health_service.get_system_health()

        self.assertEqual(health["database"], "unhealthy")
        self.assertEqual(health["chroma"], "degraded")
        self.assertEqual(health["migrations"], "unknown")
        self.assertEqual(health["overall"], "degraded")

    def test_preproduction_validation_passes_when_all_checks_are_satisfied(self):
        class Inspector:
            def get_table_names(self):
                return list(system_health_service.models.Base.metadata.tables)

            def get_indexes(self, table_name):
                return [
                    {
                        "name": index.name,
                        "column_names": [column.name for column in index.columns],
                    }
                    for index in system_health_service.models.Base.metadata.tables[table_name].indexes
                    if tuple(column.name for column in index.columns)
                    != tuple(self.get_pk_constraint(table_name)["constrained_columns"])
                ]

            def get_pk_constraint(self, table_name):
                primary_key = system_health_service.models.Base.metadata.tables[table_name].primary_key
                return {"constrained_columns": [column.name for column in primary_key.columns]}

            def get_foreign_keys(self, table_name):
                return [
                    {
                        "constrained_columns": [foreign_key.parent.name],
                        "referred_table": foreign_key.column.table.name,
                        "referred_columns": [foreign_key.column.name],
                    }
                    for foreign_key in system_health_service.models.Base.metadata.tables[table_name].foreign_keys
                ]

        with (
            patch.object(system_health_service.engine, "connect") as connect,
            patch.object(system_health_service, "inspect", return_value=Inspector()),
            patch.object(
                system_health_service,
                "get_chroma_client",
                return_value=SimpleNamespace(
                    list_collections=lambda: [SimpleNamespace(name="study_materials")]
                ),
            ),
            patch.object(
                system_health_service,
                "get_collection",
                return_value=SimpleNamespace(count=lambda: 12),
            ),
            patch.object(system_health_service, "_migration_state", return_value="up_to_date"),
            patch.object(
                system_health_service,
                "_migration_details",
                return_value={
                    "current_revisions": ["head"],
                    "latest_heads": ["head"],
                    "status": "up_to_date",
                },
            ),
        ):
            connect.return_value.__enter__.return_value.execute.return_value.scalar_one.return_value = 0
            result = system_health_service.validate_system()

        self.assertTrue(result["success"])
        self.assertTrue(result["agent_registry"])
        self.assertTrue(result["api_routes"])
        self.assertTrue(result["index_integrity"])
        self.assertTrue(result["foreign_key_integrity"])
        self.assertEqual(result["chroma_items"], 12)

    def test_preproduction_validation_fails_for_missing_schema(self):
        class Inspector:
            def get_table_names(self):
                return []

            def get_indexes(self, _table_name):
                return []

            def get_foreign_keys(self, _table_name):
                return []

        with (
            patch.object(system_health_service.engine, "connect") as connect,
            patch.object(system_health_service, "inspect", return_value=Inspector()),
            patch.object(
                system_health_service,
                "get_chroma_client",
                return_value=SimpleNamespace(
                    list_collections=lambda: [SimpleNamespace(name="study_materials")]
                ),
            ),
            patch.object(system_health_service, "_migration_state", return_value="pending"),
            patch.object(
                system_health_service,
                "_migration_details",
                return_value={
                    "current_revisions": ["old"],
                    "latest_heads": ["head"],
                    "status": "pending",
                },
            ),
        ):
            connect.return_value.__enter__.return_value.execute.return_value.scalar_one.return_value = 0
            result = system_health_service.validate_system()

        self.assertFalse(result["success"])
        self.assertFalse(result["required_tables"])
        self.assertFalse(result["alembic_head"])
        self.assertFalse(result["index_integrity"])
        self.assertFalse(result["foreign_key_integrity"])


if __name__ == "__main__":
    unittest.main()