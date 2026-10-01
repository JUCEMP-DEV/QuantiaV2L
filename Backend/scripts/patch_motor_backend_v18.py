
from __future__ import annotations

import argparse
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

    container = str(
        requirement.get("container")
        or "serviciosInstalaciones"
    )
    key = str(requirement.get("key") or "")
    required_value = requirement.get("required_value", True)
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
            "status": str(
                requirement.get("false_state")
                or "NOT_APPLICABLE"
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
                        f"serviciosInstalaciones.{expected_key}"
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


def replace_function(source: str, name: str, replacement: str) -> str:
    marker = f"def {name}("
    start = source.find(marker)
    if start < 0:
        raise RuntimeError(f"No se encontró {name}().")

    next_start = source.find("\ndef ", start + len(marker))
    if next_start < 0:
        end = len(source)
    else:
        end = next_start + 1

    return source[:start] + replacement.rstrip() + "\n\n\n" + source[end:]


def insert_service_helper(source: str) -> str:
    if "def _evaluate_service_requirement(" in source:
        return source

    marker = "def _evaluate_activation_rule("
    pos = source.find(marker)
    if pos < 0:
        raise RuntimeError("No se encontró _evaluate_activation_rule().")

    return (
        source[:pos]
        + SERVICE_HELPER
        + "\n\n\n"
        + source[pos:]
    )


def inject_service_evaluation(source: str) -> str:
    if "service_evaluation = (" in source:
        return source

    fn_pos = source.find("def _evaluate_activation_rule(")
    if fn_pos < 0:
        raise RuntimeError("No se encontró _evaluate_activation_rule().")

    next_fn = source.find("\ndef ", fn_pos + 1)
    fn_end = len(source) if next_fn < 0 else next_fn
    block = source[fn_pos:fn_end]

    needle = "    context_evaluation = (\n"
    rel = block.find(needle)
    if rel < 0:
        raise RuntimeError(
            "No se encontró context_evaluation dentro de "
            "_evaluate_activation_rule()."
        )

    insertion = '''    service_evaluation = (
        _evaluate_service_requirement(
            condition,
            context,
        )
    )

    if not service_evaluation.get("active", True):
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

'''

    absolute = fn_pos + rel
    return source[:absolute] + insertion + source[absolute:]


def fix_available_concepts_loop(source: str) -> str:
    if "for concept in concepts_concepts:" not in source:
        if (
            "ordered_concepts = sorted(" in source
            and "for concept in ordered_concepts:" in source
        ):
            return source
        raise RuntimeError(
            "No se encontró concepts_concepts ni el patrón corregido."
        )

    lines = source.splitlines()

    loop_idx = next(
        i
        for i, line in enumerate(lines)
        if line.strip() == "for concept in concepts_concepts:"
    )

    sorted_idx = loop_idx + 1
    if "ordered_concepts = sorted(" not in lines[sorted_idx]:
        raise RuntimeError(
            "Estructura inesperada después de concepts_concepts."
        )

    balance = 0
    end_idx = None
    for i in range(sorted_idx, len(lines)):
        line = lines[i]
        balance += line.count("(")
        balance -= line.count(")")
        if balance == 0:
            end_idx = i
            break

    if end_idx is None:
        raise RuntimeError("No se pudo localizar cierre de sorted().")

    del lines[loop_idx]
    sorted_idx -= 1
    end_idx -= 1

    for i in range(sorted_idx, end_idx + 1):
        if lines[i].startswith("        "):
            lines[i] = lines[i][4:]

    lines.insert(
        end_idx + 1,
        "    for concept in ordered_concepts:",
    )

    return "\n".join(lines) + ("\n" if source.endswith("\n") else "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parche Backend Quantia V1.8 para activación declarativa."
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

    original = target.read_text(
        encoding="utf-8",
        errors="strict",
    )

    updated = original
    updated = insert_service_helper(updated)
    updated = inject_service_evaluation(updated)
    updated = replace_function(
        updated,
        "_audit_instalaciones_activation_rules",
        AUDIT_INSTALLATIONS,
    )
    updated = replace_function(
        updated,
        "_filter_instalaciones_by_services",
        FILTER_INSTALLATIONS,
    )
    updated = fix_available_concepts_loop(updated)

    if updated == original:
        print("Sin cambios: el archivo parece estar ya parcheado.")
        py_compile.compile(str(target), doraise=True)
        print("Sintaxis: OK")
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
        print("ERROR: se restauró automáticamente el backup.")
        raise

    print("Parche aplicado correctamente.")
    print(f"Archivo: {target}")
    print(f"Backup:  {backup}")
    print("Sintaxis: OK")
    print("")
    print("Cambios:")
    print("- service_requirement tri-state evaluado por activation rules")
    print("- activationCoverage de Instalaciones usa service_requirement")
    print("- fallback no asume servicios=True cuando faltan")
    print("- corregido concepts_concepts / orden execution_priority")
    print("- eliminado bloque legacy inaccesible con _estimate_quantity")


if __name__ == "__main__":
    main()
