from __future__ import annotations

import time
import base64
import json
from typing import Any

import requests

from app.core.config import settings
from app.services.vision_provider import (
    VisionProvider,
    VisionProviderError,
    VisionResult,
)

# ============================================================
# ERROR INTERNO HTTP
# ============================================================


class _GeminiHTTPError(VisionProviderError):
    """
    Error interno que conserva el código HTTP.

    Permite distinguir:

    - error de formato/schema;
    - saturación;
    - rate limit;
    - error temporal del proveedor.

    No forma parte de la interfaz pública.
    """

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
    ) -> None:
        super().__init__(message)

        self.status_code = int(status_code)


# ============================================================
# PROVEEDOR
# ============================================================


class GeminiVisionProvider(VisionProvider):
    """
    Proveedor multimodal Gemini para Quantia V2.

    Modelos configurados:

        1. Gemini principal
        2. Gemini fallback

    En el estado actual de Quantia:

        gemini-3.7-flash
        gemini-3.5-flash

    Este servicio recibe una IMAGEN CANÓNICA preparada
    previamente por PlanDocumentAnalyzer.

    Flujo esperado:

        PDF
          ↓
        render PNG
          ↓
        GeminiVisionProvider

    o:

        JPG / PNG
          ↓
        normalización PNG
          ↓
        GeminiVisionProvider


    IMPORTANTE:

    Este proveedor:

    - interpreta semántica visual;
    - NO convierte automáticamente bbox en geometría final;
    - NO decide muros definitivos;
    - NO sustituye OpenCV;
    - NO sustituye OCR;
    - NO realiza reconciliación geométrica.

    Su salida es EVIDENCIA SEMÁNTICA para el reconciliador.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/" "v1beta/models"

    SUPPORTED_MEDIA_MIME_TYPES = {
        "image/png",
        "image/jpeg",
    }

    # Errores temporales:
    #
    # no tiene sentido cambiar el formato de structured output
    # y repetir inmediatamente sobre el mismo modelo.
    #
    # Se pasa al modelo fallback.

    TRANSIENT_HTTP_STATUS = {
        408,
        429,
        500,
        502,
        503,
        504,
    }
    MAX_ATTEMPTS_PER_MODEL = 3

    # Errores donde sí puede existir incompatibilidad
    # con el formato de structured output.

    FORMAT_HTTP_STATUS = {
        400,
        422,
    }

    MAX_ATTEMPTS_PER_MODEL = 3
    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        *,
        api_key: str | None = None,
        primary_model: str | None = None,
        fallback_model: str | None = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else settings.gemini_api_key
        ).strip()

        self.primary_model = (primary_model or settings.gemini_primary_model).strip()

        self.fallback_model = (fallback_model or settings.gemini_fallback_model).strip()

        self.models = self._build_model_order()

    @staticmethod
    def _validate_required_fields(
        *,
        data: Any,
        schema: dict[str, Any],
    ) -> None:
        """
        Validación mínima del contrato de transporte.

        La validación completa sigue correspondiendo
        posteriormente a los modelos Pydantic de Quantia.

        Aquí únicamente impedimos aceptar como válida
        una respuesta JSON que omita campos marcados
        como required por el schema solicitado.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise VisionProviderError(
                "Gemini devolvió JSON, pero la raíz " "de la respuesta no es un objeto."
            )

        required = schema.get(
            "required",
            [],
        )

        if not isinstance(
            required,
            list,
        ):
            return

        missing = [field for field in required if field not in data]

        if missing:
            raise VisionProviderError(
                "Gemini devolvió JSON que incumple "
                "el schema solicitado. "
                "Campos requeridos ausentes: "
                + ", ".join(str(field) for field in missing)
            )

    # ========================================================
    # API PÚBLICA
    # ========================================================

    def analyze(
        self,
        *,
        prompt: str,
        media_bytes: bytes,
        media_mime_type: str,
        response_json_schema: dict[str, Any] | None = None,
    ) -> VisionResult:
        """
        Ejecuta análisis multimodal.

        Cuando existe schema:

        1. intenta structured output moderno Gemini 3;
        2. si el modelo rechaza el formato, intenta
           structured output legacy;
        3. si vuelve a rechazarlo, pide JSON sin schema;
        4. si el modelo está saturado / rate limited,
           pasa directamente al siguiente modelo.

        Esto evita que una incompatibilidad del transporte
        structured output inutilice toda la extracción.
        """

        normalized_media_mime = self._normalize_mime_type(media_mime_type)

        self._validate_request(
            prompt=prompt,
            media_bytes=media_bytes,
            media_mime_type=normalized_media_mime,
        )

        errors: list[str] = []

        for model_index, model in enumerate(self.models):
            fallback_used = model_index > 0

            modes = self._build_output_modes(response_json_schema)

            model_errors: list[str] = []

            for mode in modes:
                try:
                    return self._generate_once(
                        model=model,
                        prompt=prompt,
                        media_bytes=media_bytes,
                        media_mime_type=normalized_media_mime,
                        response_json_schema=response_json_schema,
                        output_mode=mode,
                        fallback_used=fallback_used,
                    )

                except _GeminiHTTPError as exc:
                    model_errors.append(f"{mode}: {exc}")

                    # ----------------------------------------
                    # ERROR TEMPORAL
                    # ----------------------------------------
                    #
                    # No insistimos sobre el mismo modelo.
                    # Pasamos al siguiente configurado.
                    # ----------------------------------------

                    if exc.status_code in self.TRANSIENT_HTTP_STATUS:
                        break

                    # ----------------------------------------
                    # INCOMPATIBILIDAD DE FORMATO
                    # ----------------------------------------

                    if exc.status_code in self.FORMAT_HTTP_STATUS:
                        continue

                    # Cualquier otro HTTP se considera
                    # fallo real de ese modelo.

                    break

                except VisionProviderError as exc:
                    model_errors.append(f"{mode}: {exc}")

                    # JSON inválido o respuesta inesperada:
                    #
                    # si tenemos otro modo disponible,
                    # permitimos degradación.

                    continue

            errors.append(f"{model}: " + " | ".join(model_errors))

        raise VisionProviderError(
            "Todos los modelos Gemini configurados fallaron. " + " || ".join(errors)
        )

    # ========================================================
    # MODOS DE SALIDA
    # ========================================================

    @staticmethod
    def _build_output_modes(
        response_json_schema: dict[str, Any] | None,
    ) -> tuple[str, ...]:
        """
        Orden de transporte para generateContent.

        Con schema:
            1. responseMimeType + responseJsonSchema
            2. JSON MIME sin schema
            3. respuesta plain

        Sin schema:
            respuesta plain.
        """

        if response_json_schema:
            return (
                "response_json_schema",
                "json_only",
                "plain",
            )

        return ("plain",)

    # ========================================================
    # GENERACIÓN
    # ========================================================

    def _generate_once(
        self,
        *,
        model: str,
        prompt: str,
        media_bytes: bytes,
        media_mime_type: str,
        response_json_schema: dict[str, Any] | None,
        output_mode: str,
        fallback_used: bool,
    ) -> VisionResult:
        encoded_media = base64.b64encode(media_bytes).decode("utf-8")

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt,
                        },
                        {
                            "inlineData": {
                                "mimeType": media_mime_type,
                                "data": encoded_media,
                            }
                        },
                    ],
                }
            ]
        }

        generation_config = self._build_generation_config(
            output_mode=output_mode,
            response_json_schema=response_json_schema,
        )

        if generation_config:
            payload["generationConfig"] = generation_config

        url = f"{self.BASE_URL}/" f"{model}:generateContent"

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        response = None

        for attempt in range(
            1,
            self.MAX_ATTEMPTS_PER_MODEL + 1,
        ):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )

            except requests.RequestException as exc:
                if attempt == self.MAX_ATTEMPTS_PER_MODEL:
                    raise VisionProviderError(
                        "No fue posible conectar con Gemini: " f"{exc}"
                    ) from exc

                time.sleep(2 ** (attempt - 1))
                continue

            if response.ok:
                break

            status_code = response.status_code

            # Errores no temporales:
            # se devuelven al analyze() para decidir
            # si corresponde degradar el formato.
            if status_code not in self.TRANSIENT_HTTP_STATUS:
                raise _GeminiHTTPError(
                    status_code=status_code,
                    message=self._http_error_message(response),
                )

            # Error temporal agotó reintentos.
            if attempt == self.MAX_ATTEMPTS_PER_MODEL:
                raise _GeminiHTTPError(
                    status_code=status_code,
                    message=self._http_error_message(response),
                )

            retry_after = response.headers.get("Retry-After")

            try:
                delay = float(retry_after)

            except (
                TypeError,
                ValueError,
            ):
                delay = float(2 ** (attempt - 1))

            time.sleep(
                max(
                    0.0,
                    delay,
                )
            )

        if response is None:
            raise VisionProviderError("Gemini no produjo una respuesta HTTP.")
        try:
            raw = response.json()

        except ValueError as exc:
            raise VisionProviderError(
                "Gemini devolvió una respuesta HTTP " "que no contiene JSON válido."
            ) from exc

        text = self._extract_text(raw)

        if not text:
            raise VisionProviderError(self._empty_response_message(raw))

        parsed_data = None

        # Si se solicitó un schema, incluso cuando tuvimos
        # que degradar a JSON sin schema, la respuesta sigue
        # teniendo que ser JSON parseable.
        #
        # La validación Pydantic completa ocurre después.

        if response_json_schema:
            parsed_data = self._parse_json(text)

            self._validate_required_fields(
                data=parsed_data,
                schema=response_json_schema,
            )

        return VisionResult(
            provider="gemini",
            model=model,
            text=text,
            data=parsed_data,
            fallback_used=fallback_used,
            raw=raw,
        )

    # ========================================================
    # GENERATION CONFIG
    # ========================================================

    def _build_generation_config(
        self,
        *,
        output_mode: str,
        response_json_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Construye únicamente configuración relacionada con
        formato de salida.

        No fijamos aquí:

        - temperature;
        - topP;
        - topK;
        - maxOutputTokens;

        porque Quantia no debe introducir valores arbitrarios
        que alteren el comportamiento sin haberlos validado
        experimentalmente.
        """

        if output_mode == "plain":
            return {}

        if output_mode == "json_only":
            return {
                "responseMimeType": "application/json",
            }

        if not response_json_schema:
            return {}

        gemini_schema = self._prepare_schema_for_gemini(response_json_schema)

        # ====================================================
        # GEMINI 3 — FORMATO ACTUAL
        # ====================================================

        if output_mode == "plain":
            return {}

        if output_mode == "json_only":
            return {
                "responseMimeType": "application/json",
            }

        if not response_json_schema:
            return {}

        gemini_schema = self._prepare_schema_for_gemini(response_json_schema)

        if output_mode == "response_json_schema":
            return {
                "responseMimeType": "application/json",
                "responseJsonSchema": gemini_schema,
            }

        raise VisionProviderError(
            "Modo de salida Gemini desconocido: " f"{output_mode}"
        )

        # ====================================================
        # COMPATIBILIDAD LEGACY
        # ====================================================

        if output_mode == "response_json_schema":
            return {
                "responseMimeType": "application/json",
                "responseJsonSchema": gemini_schema,
            }

        raise VisionProviderError(
            "Modo de salida Gemini desconocido: " f"{output_mode}"
        )

    # ========================================================
    # PREPARACIÓN JSON SCHEMA
    # ========================================================

    @classmethod
    def _prepare_schema_for_gemini(
        cls,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Limpia el JSON Schema generado por Pydantic antes de
        enviarlo a Gemini.

        IMPORTANTE:

        Esta transformación NO sustituye la validación Pydantic.

        Flujo correcto:

            Pydantic JSON Schema
                    ↓
            schema compatible Gemini
                    ↓
                 Gemini
                    ↓
              JSON recibido
                    ↓
            validación Pydantic real

        Se eliminan únicamente restricciones conocidas por
        causar incompatibilidades de transporte y que no son
        necesarias para describir la forma básica de la salida.
        """

        unsupported_keys = {
            "$schema",
            "default",
            "examples",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "readOnly",
            "writeOnly",
        }

        def clean(
            value: Any,
        ) -> Any:
            if isinstance(
                value,
                list,
            ):
                return [clean(item) for item in value]

            if not isinstance(
                value,
                dict,
            ):
                return value

            result: dict[
                str,
                Any,
            ] = {}

            for key, item in value.items():
                if key in unsupported_keys:
                    continue

                result[key] = clean(item)

            return result

        prepared = clean(schema)

        if not isinstance(
            prepared,
            dict,
        ):
            raise VisionProviderError(
                "El JSON Schema preparado para Gemini " "no es un objeto válido."
            )

        return prepared

    # ========================================================
    # EXTRACCIÓN DEL TEXTO
    # ========================================================

    @staticmethod
    def _extract_text(
        response: dict[str, Any],
    ) -> str:
        candidates = response.get("candidates")

        if (
            not isinstance(
                candidates,
                list,
            )
            or not candidates
        ):
            return ""

        candidate = candidates[0]

        if not isinstance(
            candidate,
            dict,
        ):
            return ""

        content = candidate.get("content")

        if not isinstance(
            content,
            dict,
        ):
            return ""

        parts = content.get("parts")

        if not isinstance(
            parts,
            list,
        ):
            return ""

        texts: list[str] = []

        for part in parts:
            if not isinstance(
                part,
                dict,
            ):
                continue

            text = part.get("text")

            if (
                isinstance(
                    text,
                    str,
                )
                and text.strip()
            ):
                texts.append(text.strip())

        return "\n".join(texts).strip()

    # ========================================================
    # PARSEO JSON
    # ========================================================

    @staticmethod
    def _parse_json(
        text: str,
    ) -> dict[str, Any] | list[Any]:
        """
        Convierte la salida Gemini en estructura Python.

        Structured output debería devolver JSON puro.

        Las defensas contra ```json permanecen porque el modo
        degradado puede devolver fences inesperadamente.
        """

        cleaned = str(text or "").strip()

        if not cleaned:
            raise VisionProviderError("Gemini devolvió una respuesta JSON vacía.")

        # ----------------------------------------------------
        # MARKDOWN FENCE
        # ----------------------------------------------------

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines:
                first = lines[0].strip().lower()

                if first in {
                    "```",
                    "```json",
                }:
                    lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise VisionProviderError(
                "Gemini respondió, pero no entregó "
                "JSON válido conforme al formato solicitado."
            ) from exc

        if not isinstance(
            parsed,
            (dict, list),
        ):
            raise VisionProviderError(
                "La respuesta estructurada de Gemini "
                "no es un objeto ni una lista JSON."
            )

        return parsed

    # ========================================================
    # ERRORES HTTP
    # ========================================================

    @staticmethod
    def _http_error_message(
        response: requests.Response,
    ) -> str:
        try:
            payload = response.json()

        except ValueError:
            payload = None

        if isinstance(
            payload,
            dict,
        ):
            error = payload.get("error")

            if isinstance(
                error,
                dict,
            ):
                message = error.get("message")

                status = error.get("status")

                details = error.get("details")

                parts = [f"Gemini HTTP " f"{response.status_code}"]

                if status:
                    parts.append(str(status))

                if message:
                    parts.append(str(message))

                if details:
                    parts.append(f"details={details}")

                return ": ".join(parts)

        response_text = str(response.text or "")

        return f"Gemini HTTP " f"{response.status_code}: " f"{response_text[:1500]}"

    # ========================================================
    # RESPUESTA VACÍA
    # ========================================================

    @staticmethod
    def _empty_response_message(
        response: dict[str, Any],
    ) -> str:
        prompt_feedback = response.get("promptFeedback") or {}

        block_reason = prompt_feedback.get("blockReason")

        candidates = response.get("candidates")

        finish_reason = None

        if (
            isinstance(
                candidates,
                list,
            )
            and candidates
            and isinstance(
                candidates[0],
                dict,
            )
        ):
            finish_reason = candidates[0].get("finishReason")

        parts = ["Gemini no devolvió " "contenido utilizable."]

        if block_reason:
            parts.append(f"blockReason=" f"{block_reason}")

        if finish_reason:
            parts.append(f"finishReason=" f"{finish_reason}")

        return " ".join(parts)

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    def _validate_request(
        self,
        *,
        prompt: str,
        media_bytes: bytes,
        media_mime_type: str,
    ) -> None:
        if not self.api_key:
            raise VisionProviderError("GEMINI_API_KEY no está configurada.")

        if not self.models:
            raise VisionProviderError("No existen modelos Gemini configurados.")

        if (
            not isinstance(
                prompt,
                str,
            )
            or not prompt.strip()
        ):
            raise VisionProviderError("El prompt de análisis está vacío.")

        if not media_bytes:
            raise VisionProviderError("No se recibió contenido para analizar.")

        if media_mime_type not in self.SUPPORTED_MEDIA_MIME_TYPES:
            raise VisionProviderError(
                "GeminiVisionProvider debe recibir "
                "el raster canónico de Quantia. "
                "MIME recibido: "
                f"{media_mime_type or 'desconocido'}"
            )

    # ========================================================
    # MIME
    # ========================================================

    @staticmethod
    def _normalize_mime_type(
        value: str,
    ) -> str:
        return str(value or "").strip().lower()

    # ========================================================
    # ORDEN DE MODELOS
    # ========================================================

    def _build_model_order(
        self,
    ) -> tuple[str, ...]:
        models: list[str] = []

        for model in (
            self.primary_model,
            self.fallback_model,
        ):
            normalized = str(model or "").strip()

            if normalized and normalized not in models:
                models.append(normalized)

        return tuple(models)


# ============================================================
# DEPENDENCY FACTORY
# ============================================================


def get_gemini_vision_provider() -> GeminiVisionProvider:
    return GeminiVisionProvider()
