"""Tests for the raw HTTP model client — the one piece with real I/O.

Every network shape is mocked; the point is that each failure mode maps to a
ModelError whose message tells the operator which setting to check.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from bare_agent.models import ModelError, OpenAIChatClient


def _response(body: dict) -> mock.MagicMock:
    raw = json.dumps(body).encode("utf-8")
    response = mock.MagicMock()
    response.read.return_value = raw
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


class OpenAIChatClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = OpenAIChatClient(api_key="test-key", model="test-model")
        self.messages = [{"role": "user", "content": "hi"}]

    def test_happy_path_returns_message_content(self) -> None:
        body = {"choices": [{"message": {"content": '{"type":"final"}'}}]}
        with mock.patch("urllib.request.urlopen", return_value=_response(body)) as urlopen:
            result = self.client.complete(self.messages)

        self.assertEqual(result, '{"type":"final"}')
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"], self.messages)

    def test_http_error_names_the_settings_to_check(self) -> None:
        error = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error": {"message": "bad key"}}'),
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ModelError) as ctx:
                self.client.complete(self.messages)

        message = str(ctx.exception)
        self.assertIn("HTTP 401", message)
        self.assertIn("OPENAI_MODEL", message)
        self.assertIn("bad key", message)

    def test_network_failure_points_at_base_url(self) -> None:
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("refused")
        ):
            with self.assertRaises(ModelError) as ctx:
                self.client.complete(self.messages)

        self.assertIn("OPENAI_BASE_URL", str(ctx.exception))

    def test_unexpected_response_shape_is_a_model_error(self) -> None:
        with mock.patch(
            "urllib.request.urlopen", return_value=_response({"unexpected": True})
        ):
            with self.assertRaises(ModelError) as ctx:
                self.client.complete(self.messages)

        self.assertIn("Unexpected LLM response shape", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
