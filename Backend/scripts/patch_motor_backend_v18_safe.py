
from __future__ import annotations

import argparse
import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SERVICE_HELPER = r'''
def _evaluate_service_requirement(
    condition: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    requirement = (
        condition.get("service_requirement")
        if isinstance(condition.get("service_requirement"), dict)
        else {}
    )

    if not requirement:
        return {
            "active": True,
            "status": None,
            "alerts": [],
            "missingInputs": [],
        }

    container = _to_text(
        requirement.get("container"),
        "serviciosInstalaciones",
    )
    key = _to_text(
        requirement.get("key"),
        "",
    )
    required_value = requirement.get(
        "required_value",
        True,
    )

    path = f"{container}.{key}" if key else container
    values = context.get(container)

    if (
        not key
        or not isinstance(values, dict)
        or key not in values
        or values.get(key) is None
    ):
        return {
            "active": False,
            "status": "BLOCKED_MISSING_INPUT",
            "alerts": [
                {
                    "code": "MISSING_SERVICE_CONTEXT",
                    "field": path,
                    "severity": "blocking",
                }
            ],
            "missingInputs": [path],
        }

    actual = values.get(key)

    if not isinstance(actual, bool):
        return {
            "active": False,
            "status": "BLOCKED_CONFLICT",
            "alerts": [
                {
                    "code": "INVALID_SERVICE_CONTEXT",
                    "field": path,
                    "value": actual,
                    "severity": "blocking",
                }
            ],
            "missingInputs": [],
        }

    if actual != required_value:
        return {
            "active": False,
            "status": _to_text(
                requirement.get("false_state"),
                "NOT_APPLICABLE",
            ),
            "alerts": [
                {
                    "code": "SERVICE_NOT_APPLICABLE",
                    "field": path,
                    "severity": "info",
                }
            ],
            "missingInputs": [],
        }

    return {
        "active": True,
        "status": None,
        "alerts": [],
        "missingInputs": [],
    }
'''.strip()


AUDIT_INSTALLATIONS = r'''
def _audit_instalaciones_activation_rules(
    concepts: list[dict[str, Any]],
) -> dict[str, Any]:
    required_service_by_partida = {
        "HID": "agua",
        "ELE": "energia",
        "SAN": "drenaje",
        "PLU": "drenaje",
        "GAS": "gas",
    }

    checked = 0
    missing_conditions: list[dict[str, str]] = []

    for concept in concepts:
        partida_code = _to_text(
            concept.get("partida_code"),
            "",
        ).upper()

        expected_key = required_service_by_partida.get(
            partida_code
        )

        if not expected_key:
            continue

        checked += 1

        activation = (
            concept.get("activation_rule")
            if isinstance(
                concept.get("activation_rule"),
                dict,
            )
            else {}
        )

        condition = (
            activation.get("condition_json")
            if isinstance(
                activation.get("condition_json"),
                dict,
            )
            else {}
        )

        requirement = (
            condition.get("service_requirement")
            if isinstance(
                condition.get("service_requirement"),
                dict,
            )
            else {}
        )

        valid = (
            requirement.get("container")
            == "serviciosInstalaciones"
            and requirement.get("key")
            == expected_key
            and requirement.get("required_value")
            is True
        )

        if not valid:
            missing_conditions.append(
                {
                    "code": _to_text(
                        concept.get("code"),
                        "",
                    ).upper(),
                    "partida": partida_code,
                    "field": (
                        "service_requirement:"
                        "serviciosInstalaciones."
                        f"{expected_key}"
                    ),
                }
            )

    return {
        "ready": (
            checked > 0
            and not missing_conditions
        ),
        "checkedConcepts": checked,
        "missingConditions": missing_conditions,
    }
'''.strip()


FILTER_INSTALLATIONS = r'''
def _filter_instalaciones_by_services(
    concepts: list[dict[str, Any]],
    services: dict[str, Any],
) -> list[dict[str, Any]]:
    agua = services.get("agua") is True
    energia = services.get("energia") is True
    drenaje = services.get("drenaje") is True
    gas = services.get("gas") is True

    filtered: list[dict[str, Any]] = []

    for concept in concepts:
        partida_code = _to_text(
            concept.get("partida_code"),
            "",
        ).upper()

        if partida_code == "HID" and not agua:
            continue
        if partida_code == "ELE" and not energia:
            continue
        if (
            partida_code in {"SAN", "PLU"}
            and not drenaje
        ):
            continue
        if partida_code == "GAS" and not gas:
            continue

        filtered.append(concept)

    return filtered
'''.strip()


SERVICE_EVAL_BLOCK = r'''
    # Servicio de Instalaciones — tri-state V1.8
    service_evaluation = (
        _evaluate_service_requirement(
            condition,
            context,
        )
    )

    if not service_evaluation.get(
        "active",
        True,
    ):
        return {
            "active": False,
            "status": service_evaluation.get(
                "status",
                "BLOCKED_MISSING_INPUT",
            ),
            "alerts": service_evaluation.get(
                "alerts",
                [],
            ),
            "missingInputs": service_evaluation.get(
                "missingInputs",
                [],
            ),
            "requiresProjectDefinition": bool(
                condition.get(
                    "requires_project_definition",
                    spec.get(
                        "requires_project_definition",
                        False,
                    ),
                )
            ),
        }

'''.lstrip("\n")


BUILD_AVAILABLE_PROLOGUE = r'''
    ordered_concepts = sorted(
        concepts,
        key=lambda item: (
            int(
                (
                    item.get("engine_spec")
                    if isinstance(
                        item.get("engine_spec"),
                        dict,
                    )
                    else {}
                ).get(
                    "execution_priority",
                    9999,
                )
                or 9999
            ),
            _to_text(
                item.get("code"),
                "",
            ),
        ),
    )

    for concept in ordered_concepts:
'''.lstrip("\n")


def parse_functions(source: str) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def replace_top_level_function(
    source: str,
    name: str,
    replacement: str,
) -> str:
    functions = parse_functions(source)
    node = functions.get(name)
    if node is None:
        raise RuntimeError(f"No se encontró función top-level {name}().")

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    lines[start:end] = [replacement.rstrip() + "\n\n\n"]
    return "".join(lines)


def insert_helper_before_activation(source: str) -> str:
    if "def _evaluate_service_requirement(" in source:
        return source

    functions = parse_functions(source)
    node = functions.get("_evaluate_activation_rule")
    if node is None:
        raise RuntimeError("No se encontró _evaluate_activation_rule().")

    lines = source.splitlines(keepends=True)
    index = node.lineno - 1
    lines[index:index] = [SERVICE_HELPER.rstrip() + "\n\n\n"]
    return "".join(lines)


def inject_service_evaluation(source: str) -> str:
    if "Servicio de Instalaciones — tri-state V1.8" in source:
        return source

    functions = parse_functions(source)
    node = functions.get("_evaluate_activation_rule")
    if node is None:
        raise RuntimeError("No se encontró _evaluate_activation_rule().")

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    block = "".join(lines[start:end])

    needle = "    context_evaluation = (\n"
    pos = block.find(needle)
    if pos < 0:
        raise RuntimeError(
            "No se encontró context_evaluation dentro de "
            "_evaluate_activation_rule()."
        )

    block = block[:pos] + SERVICE_EVAL_BLOCK + block[pos:]
    lines[start:end] = [block]
    return "".join(lines)


def fix_build_available_concepts(source: str) -> str:
    functions = parse_functions(source)
    node = functions.get("_build_available_concepts")
    if node is None:
        raise RuntimeError("No se encontró _build_available_concepts().")

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    block = "".join(lines[start:end])

    if "for concept in concepts_concepts:" not in block:
        if "for concept in ordered_concepts:" in block:
            return source
        raise RuntimeError("No se encontró el patrón concepts_concepts.")

    start_marker = "    for concept in concepts_concepts:\n"
    end_marker = "        code = _to_text(\n"

    p1 = block.find(start_marker)
    p2 = block.find(end_marker, p1)

    if p1 < 0 or p2 < 0:
        raise RuntimeError(
            "No se pudo aislar el prólogo defectuoso de "
            "_build_available_concepts()."
        )

    block = (
        block[:p1]
        + BUILD_AVAILABLE_PROLOGUE
        + block[p2:]
    )

    lines[start:end] = [block]
    return "".join(lines)


def validate_expected_state(source: str) -> None:
    ast.parse(source)

    required = [
        "def _evaluate_service_requirement(",
        "def _audit_instalaciones_activation_rules(",
        "for concept in ordered_concepts:",
        "def _filter_instalaciones_by_services(",
        "Servicio de Instalaciones — tri-state V1.8",
    ]

    missing = [token for token in required if token not in source]
    if missing:
        raise RuntimeError(
            "Validación incompleta: " + ", ".join(missing)
        )

    if "for concept in concepts_concepts:" in source:
        raise RuntimeError("Todavía existe concepts_concepts.")

    functions = parse_functions(source)
    filter_node = functions["_filter_instalaciones_by_services"]
    lines = source.splitlines(keepends=True)
    filter_block = "".join(
        lines[filter_node.lineno - 1:filter_node.end_lineno]
    )

    if "_estimate_quantity(" in filter_block:
        raise RuntimeError(
            "El legacy _estimate_quantity sigue dentro "
            "del filtro de Instalaciones."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Parche seguro Backend Quantia V1.8 "
            "para activación declarativa."
        )
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(
            "app/services/motor_simulation_service.py"
        ),
    )
    args = parser.parse_args()

    target = args.file.resolve()
    if not target.exists():
        raise FileNotFoundError(target)

    # El original debe compilar ANTES de tocarlo.
    try:
        py_compile.compile(str(target), doraise=True)
    except Exception as exc:
        raise RuntimeError(
            "El archivo original ya tiene un error de sintaxis. "
            "No se aplicó ningún cambio."
        ) from exc

    original = target.read_text(encoding="utf-8")
    updated = original

    updated = insert_helper_before_activation(updated)
    ast.parse(updated)

    updated = inject_service_evaluation(updated)
    ast.parse(updated)

    updated = replace_top_level_function(
        updated,
        "_audit_instalaciones_activation_rules",
        AUDIT_INSTALLATIONS,
    )
    ast.parse(updated)

    updated = replace_top_level_function(
        updated,
        "_filter_instalaciones_by_services",
        FILTER_INSTALLATIONS,
    )
    ast.parse(updated)

    updated = fix_build_available_concepts(updated)
    ast.parse(updated)

    validate_expected_state(updated)

    if updated == original:
        print("Sin cambios: el archivo ya parece actualizado.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_suffix(
        target.suffix + f".bak_{timestamp}"
    )

    shutil.copy2(target, backup)
    target.write_text(updated, encoding="utf-8")

    try:
        py_compile.compile(str(target), doraise=True)
    except Exception:
        shutil.copy2(backup, target)
        print("ERROR: validación final falló; backup restaurado.")
        raise

    print("Parche aplicado correctamente.")
    print(f"Archivo: {target}")
    print(f"Backup:  {backup}")
    print("Sintaxis: OK")
    print("")
    print("Cambios validados:")
    print("- service_requirement tri-state en activation rules")
    print("- activationCoverage Instalaciones lee service_requirement")
    print("- fallback sin defaults True")
    print("- _build_available_concepts ordena por execution_priority")
    print("- eliminado legacy inaccesible del filtro de Instalaciones")


if __name__ == "__main__":
    main()
