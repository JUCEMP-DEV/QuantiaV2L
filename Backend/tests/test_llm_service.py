import unittest
from unittest.mock import Mock, patch

import requests

from app.services.llm_service import LLMService, LLMServiceError


class LLMServiceTests(unittest.TestCase):
    def test_generate_answer_calls_ollama(self):
        service = LLMService(
            model="llama3.2:3b",
            host="http://localhost:11434",
            context_length=2048,
        )

        with patch.object(service, "_call_ollama", return_value="Respuesta desde Ollama") as call:
            answer = service.generate_answer("Contexto de prueba", "Que se puede decir?")

        self.assertEqual(answer, "Respuesta desde Ollama")
        self.assertIn("Contexto de prueba", call.call_args.args[0])
        self.assertIn("Que se puede decir?", call.call_args.args[0])

    def test_generate_from_prompt_calls_ollama(self):
        service = LLMService()

        with patch.object(service, "_call_ollama", return_value="Respuesta") as call:
            answer = service.generate_from_prompt("Prompt listo")

        self.assertEqual(answer, "Respuesta")
        call.assert_called_once_with("Prompt listo")

    def test_generate_from_prompt_rejects_empty_prompt(self):
        service = LLMService()

        with self.assertRaises(LLMServiceError):
            service.generate_from_prompt("   ")

    def test_generate_answer_rejects_empty_query(self):
        service = LLMService()

        with self.assertRaises(LLMServiceError):
            service.generate_answer("Contexto de prueba", "")

    def test_call_ollama_returns_response_text(self):
        service = LLMService(
            model="llama3.2:3b",
            host="http://localhost:11434",
            context_length=2048,
        )
        response = Mock()
        response.json.return_value = {"response": "Respuesta generada"}

        with patch("app.services.llm_service.requests.post", return_value=response) as post:
            answer = service._call_ollama("Prompt")

        self.assertEqual(answer, "Respuesta generada")
        post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": "Prompt",
                "stream": False,
                "options": {
                    "temperature": service.temperature,
                    "num_ctx": 2048,
                    "num_predict": service.max_tokens,
                },
            },
            timeout=service.timeout,
        )

    def test_call_ollama_raises_on_connection_error(self):
        service = LLMService()

        with patch("app.services.llm_service.requests.post", side_effect=requests.ConnectionError):
            with self.assertRaises(LLMServiceError):
                service._call_ollama("Prompt")

    def test_health_reports_available_model(self):
        service = LLMService(model="llama3.1:8b", host="http://localhost:11434")
        response = Mock()
        response.json.return_value = {"models": [{"name": "llama3.1:8b"}]}

        with patch("app.services.llm_service.requests.get", return_value=response):
            health = service.health()

        self.assertTrue(health["available"])
        self.assertTrue(health["model_available"])

    def test_ensure_ready_passes_when_model_is_available(self):
        service = LLMService(model="llama3.1:8b")

        with patch.object(service, "health", return_value={"available": True, "model_available": True}):
            service.ensure_ready()

    def test_ensure_ready_raises_when_model_is_missing(self):
        service = LLMService(model="llama3.1:8b")

        with patch.object(service, "health", return_value={"available": True, "model_available": False}):
            with self.assertRaises(LLMServiceError) as error:
                service.ensure_ready()

        self.assertIn("ollama pull llama3.1:8b", str(error.exception))


if __name__ == "__main__":
    unittest.main()
