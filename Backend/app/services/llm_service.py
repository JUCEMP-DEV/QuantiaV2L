from __future__ import annotations

from typing import Any

import requests

from app.core.config import settings


class LLMServiceError(RuntimeError):
    pass


class LLMService:
    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        context_length: int | None = None,
        max_tokens: int | None = None,
    ):
        self.model = model or settings.ollama_model
        self.host = (host or settings.ollama_host).rstrip("/")
        self.context_length = (
            context_length if context_length is not None else settings.ollama_context_length
        )
        self.max_tokens = max_tokens if max_tokens is not None else settings.ollama_max_tokens
        self.timeout = settings.ollama_timeout_seconds
        self.temperature = settings.ollama_temperature

    def health(self) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "model_available": False,
                "error": f"No se pudo conectar con Ollama: {exc}",
            }

        models = payload.get("models", [])
        model_names = {str(item.get("name", "")) for item in models if isinstance(item, dict)}
        return {
            "available": True,
            "host": self.host,
            "model": self.model,
            "model_available": self.model in model_names,
            "models": sorted(name for name in model_names if name),
        }

    def ensure_ready(self) -> None:
        status = self.health()
        if not status["available"]:
            raise LLMServiceError(status.get("error") or "Ollama no esta disponible.")
        if not status["model_available"]:
            raise LLMServiceError(
                f"El modelo {self.model} no esta disponible en Ollama. Ejecuta: ollama pull {self.model}"
            )
    def generate_answer(self, context: str, query: str) -> str:
        if not context or not context.strip():
            return "No se encontro contexto suficiente para responder."
        if not query or not query.strip():
            raise LLMServiceError("La pregunta no puede estar vacia.")

        prompt = self._build_prompt(context=context, query=query)
        return self.generate_from_prompt(prompt)

    def generate_from_prompt(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise LLMServiceError("El prompt no puede estar vacio.")
        return self._call_ollama(prompt.strip())

    def _build_prompt(self, context: str, query: str) -> str:
        return (
            "Eres un asistente de Quantia especializado en responder con documentos cargados.\n"
            "Usa unicamente el contexto proporcionado.\n"
            "Si el contexto no contiene la respuesta, indica que no hay informacion suficiente.\n"
            "Responde en espanol, de forma breve, clara y sin inventar datos.\n\n"
            f"Contexto:\n{context.strip()}\n\n"
            f"Pregunta:\n{query.strip()}\n\n"
            "Respuesta:"
        )

    def _call_ollama(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_ctx": self.context_length,
                        "num_predict": self.max_tokens,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout as exc:
            raise LLMServiceError("Ollama tardo demasiado en responder.") from exc
        except requests.ConnectionError as exc:
            raise LLMServiceError("Ollama no esta disponible. Verifica que el servicio este activo.") from exc
        except requests.HTTPError as exc:
            raise LLMServiceError(f"Ollama rechazo la solicitud: {exc}") from exc
        except requests.RequestException as exc:
            raise LLMServiceError(f"Error al comunicarse con Ollama: {exc}") from exc
        except ValueError as exc:
            raise LLMServiceError("Ollama devolvio una respuesta invalida.") from exc

        answer = str(payload.get("response", "")).strip()
        if not answer:
            raise LLMServiceError("Ollama devolvio una respuesta vacia.")
        return answer

