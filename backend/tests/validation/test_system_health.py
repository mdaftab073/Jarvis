import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import system_health_service


class SystemHealthTests(unittest.TestCase):
    def test_health_reports_all_dependencies_healthy(self):
        with (
            patch.object(system_health_service.engine, "connect") as connect,
            patch.object(system_health_service, "get_collection") as collection,
            patch.object(system_health_service, "_migration_state", return_value="up_to_date"),
        ):
            connect.return_value.__enter__.return_value.execute.return_value = None
            collection.return_value.count.return_value = 0
            health = system_health_service.get_system_health()

        self.assertEqual(health["database"], "healthy")
        self.assertEqual(health["chroma"], "healthy")
        self.assertEqual(health["migrations"], "up_to_date")
        self.assertEqual(health["overall"], "healthy")

    def test_health_reports_degraded_when_dependency_unavailable(self):
        with (
            patch.object(system_health_service.engine, "connect", side_effect=OSError("down")),
            patch.object(system_health_service, "get_collection", side_effect=OSError("down")),
            patch.object(system_health_service, "_migration_state", side_effect=OSError("down")),
        ):
            health = system_health_service.get_system_health()

        self.assertEqual(health["database"], "unhealthy")
        self.assertEqual(health["chroma"], "unhealthy")
        self.assertEqual(health["migrations"], "unknown")
        self.assertEqual(health["overall"], "degraded")

    def test_preproduction_validation_passes_when_all_checks_are_satisfied(self):
        class Inspector:
            def get_table_names(self):
                return list(system_health_service.Base.metadata.tables)

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
            patch.object(system_health_service, "_migration_state", return_value="up_to_date"),
        ):
            connect.return_value.__enter__.return_value.execute.return_value = None
            result = system_health_service.validate_system()

        self.assertTrue(result["success"])
        self.assertTrue(result["agent_registry"])
        self.assertTrue(result["api_routes"])

    def test_preproduction_validation_fails_for_missing_schema(self):
        class Inspector:
            def get_table_names(self):
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
        ):
            connect.return_value.__enter__.return_value.execute.return_value = None
            result = system_health_service.validate_system()

        self.assertFalse(result["success"])
        self.assertFalse(result["required_tables"])
        self.assertFalse(result["alembic_head"])


if __name__ == "__main__":
    unittest.main()