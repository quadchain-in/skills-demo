import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class ExampleQueriesRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment_patcher = patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "test-key",
            },
        )
        cls.supabase_patcher = patch("supabase.create_client")
        cls.genai_patcher = patch("google.genai.Client")
        cls.environment_patcher.start()
        cls.supabase_patcher.start()
        cls.genai_patcher.start()
        api = importlib.import_module("rag_chat_api")
        cls.client = TestClient(api.app)

    @classmethod
    def tearDownClass(cls):
        cls.genai_patcher.stop()
        cls.supabase_patcher.stop()
        cls.environment_patcher.stop()

    def test_examples_route_returns_structured_query_strings(self):
        response = self.client.get("/examples")

        self.assertEqual(response.status_code, 200)
        examples = response.json()["examples"]
        self.assertTrue(examples)
        self.assertTrue(all(isinstance(example, str) for example in examples))

    def test_examples_route_is_documented_in_openapi(self):
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("/examples", response.json()["paths"])
