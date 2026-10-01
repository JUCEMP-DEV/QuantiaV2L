from typing import Any


GEMINI_SPACE_LOCALIZATION_SCHEMA: dict[str, Any] = {
    "type": "object",

    "properties": {
        "pagina": {
            "type": "integer",
            "minimum": 1,
        },

        "niveles": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {
                    "nombre": {
                        "type": "string",
                    },

                    "localizado": {
                        "type": "boolean",
                    },

                    "bbox_normalizado": {
                        "type": [
                            "object",
                            "null",
                        ],

                        "properties": {
                            "x_min": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },

                            "y_min": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },

                            "x_max": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },

                            "y_max": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                        },

                        "required": [
                            "x_min",
                            "y_min",
                            "x_max",
                            "y_max",
                        ],

                        "additionalProperties": False,
                    },

                    "confianza": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },

                    "espacios": {
                        "type": "array",

                        "items": {
                            "type": "object",

                            "properties": {
                                "id_propuesto": {
                                    "type": "string",
                                },

                                "nombre": {
                                    "type": "string",
                                },

                                "localizado": {
                                    "type": "boolean",
                                },

                                "bbox_normalizado": {
                                    "type": [
                                        "object",
                                        "null",
                                    ],

                                    "properties": {
                                        "x_min": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },

                                        "y_min": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },

                                        "x_max": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },

                                        "y_max": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                    },

                                    "required": [
                                        "x_min",
                                        "y_min",
                                        "x_max",
                                        "y_max",
                                    ],

                                    "additionalProperties": False,
                                },

                                "confianza": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },

                                "evidencia": {
                                    "type": "array",

                                    "items": {
                                        "type": "string",
                                    },
                                },

                                "motivo_no_localizado": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                            },

                            "required": [
                                "id_propuesto",
                                "nombre",
                                "localizado",
                                "bbox_normalizado",
                                "confianza",
                                "evidencia",
                                "motivo_no_localizado",
                            ],

                            "additionalProperties": False,
                        },
                    },
                },

                "required": [
                    "nombre",
                    "localizado",
                    "bbox_normalizado",
                    "confianza",
                    "espacios",
                ],

                "additionalProperties": False,
            },
        },
    },

    "required": [
        "pagina",
        "niveles",
    ],

    "additionalProperties": False,
}


def get_gemini_space_localization_schema() -> dict[str, Any]:
    """
    Schema compacto utilizado únicamente para localizar
    regiones visuales en una página.

    Las coordenadas están normalizadas entre 0 y 1.

    NO representan:
    - metros;
    - dimensiones constructivas;
    - geometría confirmada.

    Son únicamente propuestas de ubicación visual que
    posteriormente se transformarán al sistema de
    coordenadas PDF y se validarán contra los trazos
    vectoriales de PyMuPDF.
    """

    return GEMINI_SPACE_LOCALIZATION_SCHEMA