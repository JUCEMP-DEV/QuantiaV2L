from typing import Any


EXTRACTION_STATES = [
    "DETECTADO",
    "INFERIDO",
    "NO_IDENTIFICADO",
    "CONFLICTO",
]


GEMINI_EXTRACTION_TRANSPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resumen": {
            "type": "string",
        },

        "documento": {
            "type": "object",
            "properties": {
                "titulo": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "tipo_plano": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "escala": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "orientacion": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
            },
            "required": [
                "titulo",
                "tipo_plano",
                "escala",
                "orientacion",
            ],
            "additionalProperties": False,
        },

        "predio": {
            "type": "object",
            "properties": {
                "ancho_m": {
                    "type": [
                        "number",
                        "null",
                    ],
                },
                "fondo_m": {
                    "type": [
                        "number",
                        "null",
                    ],
                },
                "area_m2": {
                    "type": [
                        "number",
                        "null",
                    ],
                },
                "acceso_principal": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "orientacion": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "colindancias": {
                    "type": "object",
                    "properties": {
                        "norte": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "sur": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "este": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "oeste": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                    },
                    "required": [
                        "norte",
                        "sur",
                        "este",
                        "oeste",
                    ],
                    "additionalProperties": False,
                },
                "estado": {
                    "type": "string",
                    "enum": EXTRACTION_STATES,
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
            },
            "required": [
                "ancho_m",
                "fondo_m",
                "area_m2",
                "acceso_principal",
                "orientacion",
                "colindancias",
                "estado",
                "confianza",
                "evidencia",
            ],
            "additionalProperties": False,
        },

        "niveles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
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
                                "tipo": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "ancho_m": {
                                    "type": [
                                        "number",
                                        "null",
                                    ],
                                },
                                "largo_m": {
                                    "type": [
                                        "number",
                                        "null",
                                    ],
                                },
                                "area_m2": {
                                    "type": [
                                        "number",
                                        "null",
                                    ],
                                },
                                "ubicacion": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "comunica_con": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "comparte_muro_con": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "puertas": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "hacia": {
                                                "type": [
                                                    "string",
                                                    "null",
                                                ],
                                            },
                                            "ancho_m": {
                                                "type": [
                                                    "number",
                                                    "null",
                                                ],
                                            },
                                            "alto_m": {
                                                "type": [
                                                    "number",
                                                    "null",
                                                ],
                                            },
                                            "ubicacion": {
                                                "type": [
                                                    "string",
                                                    "null",
                                                ],
                                            },
                                            "estado": {
                                                "type": "string",
                                                "enum": EXTRACTION_STATES,
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
                                        },
                                        "required": [
                                            "hacia",
                                            "ancho_m",
                                            "alto_m",
                                            "ubicacion",
                                            "estado",
                                            "confianza",
                                            "evidencia",
                                        ],
                                        "additionalProperties": False,
                                    },
                                },
                                "ventanas": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "ancho_m": {
                                                "type": [
                                                    "number",
                                                    "null",
                                                ],
                                            },
                                            "alto_m": {
                                                "type": [
                                                    "number",
                                                    "null",
                                                ],
                                            },
                                            "ubicacion": {
                                                "type": [
                                                    "string",
                                                    "null",
                                                ],
                                            },
                                            "estado": {
                                                "type": "string",
                                                "enum": EXTRACTION_STATES,
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
                                        },
                                        "required": [
                                            "ancho_m",
                                            "alto_m",
                                            "ubicacion",
                                            "estado",
                                            "confianza",
                                            "evidencia",
                                        ],
                                        "additionalProperties": False,
                                    },
                                },
                                "bbox_normalizado": {
                                    "type": [
                                        "array",
                                        "null",
                                    ],
                                    "items": {
                                        "type": "number",
                                    },
                                },
                                "estado": {
                                    "type": "string",
                                    "enum": EXTRACTION_STATES,
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
                            },
                            "required": [
                                "id_propuesto",
                                "nombre",
                                "tipo",
                                "ancho_m",
                                "largo_m",
                                "area_m2",
                                "ubicacion",
                                "comunica_con",
                                "comparte_muro_con",
                                "puertas",
                                "ventanas",
                                "bbox_normalizado",
                                "estado",
                                "confianza",
                                "evidencia",
                            ],
                            "additionalProperties": False,
                        },
                    },

                    "escaleras": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ubicacion": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "sentido": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "comunica_con": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "estado": {
                                    "type": "string",
                                    "enum": EXTRACTION_STATES,
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
                            },
                            "required": [
                                "ubicacion",
                                "sentido",
                                "comunica_con",
                                "estado",
                                "confianza",
                                "evidencia",
                            ],
                            "additionalProperties": False,
                        },
                    },

                    "cotas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "texto": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "valor_m": {
                                    "type": [
                                        "number",
                                        "null",
                                    ],
                                },
                                "referencia": {
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "estado": {
                                    "type": "string",
                                    "enum": EXTRACTION_STATES,
                                },
                                "confianza": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                            },
                            "required": [
                                "texto",
                                "valor_m",
                                "referencia",
                                "estado",
                                "confianza",
                            ],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "nombre",
                    "espacios",
                    "escaleras",
                    "cotas",
                ],
                "additionalProperties": False,
            },
        },

        "informacion_constructiva": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "campo": {
                        "type": "string",
                    },
                    "valor": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "estado": {
                        "type": "string",
                        "enum": EXTRACTION_STATES,
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
                },
                "required": [
                    "campo",
                    "valor",
                    "estado",
                    "confianza",
                    "evidencia",
                ],
                "additionalProperties": False,
            },
        },

        "conflictos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "descripcion": {
                        "type": "string",
                    },
                    "elementos": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "evidencia": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "required": [
                    "descripcion",
                    "elementos",
                    "evidencia",
                ],
                "additionalProperties": False,
            },
        },

        "datos_no_identificados": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "confirmaciones_requeridas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "elemento": {
                        "type": "string",
                    },
                    "motivo": {
                        "type": "string",
                    },
                },
                "required": [
                    "elemento",
                    "motivo",
                ],
                "additionalProperties": False,
            },
        },
    },

    "required": [
        "resumen",
        "documento",
        "predio",
        "niveles",
        "informacion_constructiva",
        "conflictos",
        "datos_no_identificados",
        "confirmaciones_requeridas",
    ],

    "additionalProperties": False,
}


def get_gemini_extraction_transport_schema() -> dict[str, Any]:
    return GEMINI_EXTRACTION_TRANSPORT_SCHEMA