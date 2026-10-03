import unittest

from app.services.connector_adapters import (
    ConnectorAdapter,
    create_connector_adapter,
    register_connector_adapter,
)


class GenericAdapterTests(unittest.TestCase):
    def test_registered_adapter_factory_is_used(self):
        class ExampleAdapter(ConnectorAdapter):
            def __init__(self, endpoint_url, configuration):
                self.endpoint_url = endpoint_url
                self.configuration = configuration

            def fetch(self, credentials):
                return {"endpoint_url": self.endpoint_url, "credentials": credentials}

        register_connector_adapter("example_test", ExampleAdapter)
        adapter = create_connector_adapter(
            "example_test",
            "https://example.test",
            {"resource": "/data"},
        )

        self.assertEqual(adapter.endpoint_url, "https://example.test")
        self.assertEqual(adapter.configuration, {"resource": "/data"})
        self.assertEqual(adapter.fetch({"token": "secret"}), {
            "endpoint_url": "https://example.test",
            "credentials": {"token": "secret"},
        })


if __name__ == "__main__":
    unittest.main()
