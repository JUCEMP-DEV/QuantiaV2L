from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.catalogos import execute_catalog_query


EXPECTED_TOTAL = 101
EXPECTED_ACTIVE = 99
EXPECTED_INACTIVE_CODES = {"EST-008", "EST-010"}
EXPECTED_CIM003A_ID = "c1497b86-9857-4170-b01b-f47b7fab5b56"

EXPECTED_CORRECTIONS: dict[str, tuple[str, str, str]] = {
    "ACA-001": ("M2", "por_area", "F_M2_DIRECTA"),
    "ACA-003": ("M2", "por_area", "F_M2_DIRECTA"),
    "CAN-001": ("M2", "por_area", "F_M2_DIRECTA"),
    "CIM-002": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "CIM-003": ("PZA", "por_pieza", "F_PZA_DIRECTA"),
    "CIM-004": ("PZA", "por_pieza", "F_PZA_DIRECTA"),
    "CIM-005": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "CIM-006": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "COM-001": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "COM-002": ("M2", "por_area", "F_M2_DIRECTA"),
    "EST-001": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "EST-002": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "EST-005": ("M2", "por_area", "F_M2_DIRECTA"),
    "EST-006": ("M2", "por_area", "F_M2_DIRECTA"),
    "EST-007": ("M2", "por_area", "F_M2_DIRECTA"),
    "HER-002": ("ML", "por_perimetro", "F_ML_DIRECTA"),
    "HID-007": ("PZA", "por_pieza", "F_PZA_DIRECTA"),
    "SAN-006": ("PZA", "por_pieza", "F_PZA_DIRECTA"),
}

BOOL_FIELDS = {
    "applies_private_housing",
    "is_optional",
    "requires_space_context",
    "requires_system_context",
    "requires_normative_validation",
    "is_active",
}

NULLABLE_TEXT_FIELDS = {
    "partida_id",
    "subalcance_id",
    "unit_id",
    "technical_description",
    "official_description",
    "finish_level",
    "default_formula_code",
    "notes",
}

ALL_FIELDS = [
    "id",
    "partida_id",
    "subalcance_id",
    "unit_id",
    "code",
    "technical_description",
    "official_description",
    "finish_level",
    "applies_private_housing",
    "is_optional",
    "requires_space_context",
    "requires_system_context",
    "requires_normative_validation",
    "quantification_mode",
    "default_formula_code",
    "is_active",
    "notes",
    "metadata_json",
    "created_at",
    "updated_at",
]

WRITE_ENABLED = os.getenv("QUANTIA_CATALOG_V18_WRITE", "0") == "1"


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "si", "sí"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Booleano inválido: {value!r}")


def parse_row(raw: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {}

    for field in ALL_FIELDS:
        value: Any = raw.get(field)

        if field in BOOL_FIELDS:
            value = parse_bool(value)

        elif field == "metadata_json":
            text = (value or "").strip()
            value = json.loads(text) if text else {}

        elif field in NULLABLE_TEXT_FIELDS:
            text = (value or "").strip()
            value = text if text else None

        else:
            if isinstance(value, str):
                value = value.strip()

        row[field] = value

    return row


def load_migration(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV de migración: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)

        missing_columns = [field for field in ALL_FIELDS if field not in (reader.fieldnames or [])]
        if missing_columns:
            raise RuntimeError(
                "El CSV no tiene todas las columnas requeridas: "
                + ", ".join(missing_columns)
            )

        rows = [parse_row(raw) for raw in reader]

    return rows


def fetch_table(table: str, select_fields: str = "*") -> list[dict[str, Any]]:
    return execute_catalog_query(
        lambda client: (
            client.table(table)
            .select(select_fields)
            .execute()
            .data
            or []
        ),
        operation=f"audit_{table}",
        critical=True,
    )


def normalize_for_compare(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if value == "":
        return None
    return value


def changed_fields(
    current: dict[str, Any],
    source: dict[str, Any],
) -> list[str]:
    # created_at se preserva para registros ya existentes.
    fields = [field for field in ALL_FIELDS if field != "created_at"]
    changed: list[str] = []

    for field in fields:
        a = normalize_for_compare(current.get(field))
        b = normalize_for_compare(source.get(field))
        if a != b:
            changed.append(field)

    return changed


def validate_source(
    rows: list[dict[str, Any]],
    units: list[dict[str, Any]],
    partidas: list[dict[str, Any]],
) -> None:
    errors: list[str] = []

    if len(rows) != EXPECTED_TOTAL:
        errors.append(f"Se esperaban {EXPECTED_TOTAL} conceptos y hay {len(rows)}.")

    ids = [str(row["id"]) for row in rows]
    codes = [str(row["code"]) for row in rows]

    if len(ids) != len(set(ids)):
        errors.append("Hay UUID duplicados en el CSV.")

    if len(codes) != len(set(codes)):
        errors.append("Hay claves duplicadas en el CSV.")

    active = [row for row in rows if row["is_active"]]
    inactive_codes = {str(row["code"]) for row in rows if not row["is_active"]}

    if len(active) != EXPECTED_ACTIVE:
        errors.append(
            f"Se esperaban {EXPECTED_ACTIVE} conceptos activos y hay {len(active)}."
        )

    if inactive_codes != EXPECTED_INACTIVE_CODES:
        errors.append(
            "Los inactivos no coinciden. "
            f"Esperados={sorted(EXPECTED_INACTIVE_CODES)}, "
            f"obtenidos={sorted(inactive_codes)}"
        )

    by_code = {str(row["code"]): row for row in rows}

    cim003a = by_code.get("CIM-003A")
    if not cim003a:
        errors.append("Falta CIM-003A.")
    elif str(cim003a["id"]) != EXPECTED_CIM003A_ID:
        errors.append(
            "UUID incorrecto en CIM-003A: "
            f"{cim003a['id']} != {EXPECTED_CIM003A_ID}"
        )

    unit_by_id = {str(row["id"]): row for row in units}
    partida_by_id = {str(row["id"]): row for row in partidas}

    referenced_unit_ids = {
        str(row["unit_id"]) for row in rows if row.get("unit_id")
    }
    referenced_partida_ids = {
        str(row["partida_id"]) for row in rows if row.get("partida_id")
    }

    missing_units = sorted(referenced_unit_ids - set(unit_by_id))
    missing_partidas = sorted(referenced_partida_ids - set(partida_by_id))

    if missing_units:
        errors.append(
            "Hay unit_id del maestro que no existen en catalog_units: "
            + ", ".join(missing_units)
        )

    if missing_partidas:
        errors.append(
            "Hay partida_id del maestro que no existen en catalog_partidas: "
            + ", ".join(missing_partidas)
        )

    for code, (expected_unit, expected_mode, expected_formula) in EXPECTED_CORRECTIONS.items():
        row = by_code.get(code)
        if not row:
            errors.append(f"Falta concepto normalizado requerido: {code}")
            continue

        unit = unit_by_id.get(str(row["unit_id"]))
        actual_unit = str(unit.get("code", "")).upper() if unit else ""

        if actual_unit != expected_unit:
            errors.append(
                f"{code}: unidad {actual_unit or 'DESCONOCIDA'}; "
                f"esperada {expected_unit}."
            )

        if row.get("quantification_mode") != expected_mode:
            errors.append(
                f"{code}: quantification_mode={row.get('quantification_mode')}; "
                f"esperado={expected_mode}."
            )

        if row.get("default_formula_code") != expected_formula:
            errors.append(
                f"{code}: default_formula_code={row.get('default_formula_code')}; "
                f"esperado={expected_formula}."
            )

    if cim003a:
        unit = unit_by_id.get(str(cim003a["unit_id"]))
        actual_unit = str(unit.get("code", "")).upper() if unit else ""
        if actual_unit != "PZA":
            errors.append(
                f"CIM-003A apunta a unidad {actual_unit or 'DESCONOCIDA'}; "
                "debe apuntar a PZA."
            )

    if errors:
        raise RuntimeError(
            "Validación del maestro V1.8 falló:\n- " + "\n- ".join(errors)
        )


def audit_current(
    source_rows: list[dict[str, Any]],
    current_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], list[str]]], list[dict[str, Any]]]:
    source_by_id = {str(row["id"]): row for row in source_rows}
    source_by_code = {str(row["code"]): row for row in source_rows}
    current_by_id = {str(row["id"]): row for row in current_rows}
    current_by_code = {str(row["code"]): row for row in current_rows}

    collisions: list[str] = []

    for code, source in source_by_code.items():
        current = current_by_code.get(code)
        if current and str(current["id"]) != str(source["id"]):
            collisions.append(
                f"Clave {code}: BD id={current['id']} / maestro id={source['id']}"
            )

    for row_id, source in source_by_id.items():
        current = current_by_id.get(row_id)
        if current and str(current["code"]) != str(source["code"]):
            collisions.append(
                f"UUID {row_id}: BD code={current['code']} / maestro code={source['code']}"
            )

    if collisions:
        raise RuntimeError(
            "Se detectaron colisiones UUID/clave. No se permite migrar:\n- "
            + "\n- ".join(collisions)
        )

    inserts: list[dict[str, Any]] = []
    updates: list[tuple[dict[str, Any], list[str]]] = []
    unchanged: list[dict[str, Any]] = []

    for source in source_rows:
        current = current_by_id.get(str(source["id"]))

        if not current:
            inserts.append(source)
            continue

        fields = changed_fields(current, source)
        if fields:
            updates.append((source, fields))
        else:
            unchanged.append(source)

    extra_rows = [
        row
        for row in current_rows
        if str(row["id"]) not in source_by_id
    ]

    return inserts, updates, extra_rows


def print_plan(
    inserts: list[dict[str, Any]],
    updates: list[tuple[dict[str, Any], list[str]]],
    extra_rows: list[dict[str, Any]],
) -> None:
    print("\n--- PLAN DE MIGRACIÓN ---")
    print(f"INSERT:    {len(inserts)}")
    print(f"UPDATE:    {len(updates)}")
    print(f"EXTRAS BD: {len(extra_rows)}")

    if inserts:
        print("\nAltas:")
        for row in inserts:
            print(f"  + {row['code']}  {row['id']}")

    if updates:
        print("\nCambios:")
        for row, fields in updates:
            print(f"  ~ {row['code']}: {', '.join(fields)}")

    if extra_rows:
        print("\nRegistros existentes en BD que NO pertenecen al maestro V1.8:")
        for row in sorted(extra_rows, key=lambda r: str(r.get("code", ""))):
            print(f"  ! {row.get('code')}  {row.get('id')}")


def update_existing(row: dict[str, Any]) -> None:
    payload = {
        field: row[field]
        for field in ALL_FIELDS
        if field not in {"id", "created_at"}
    }

    execute_catalog_query(
        lambda client, row_id=row["id"], payload=payload: (
            client.table("catalog_concepts")
            .update(payload)
            .eq("id", row_id)
            .execute()
            .data
            or []
        ),
        operation=f"update_catalog_concept_{row['code']}",
        critical=True,
    )


def insert_new(row: dict[str, Any]) -> None:
    payload = {field: row[field] for field in ALL_FIELDS}

    execute_catalog_query(
        lambda client, payload=payload: (
            client.table("catalog_concepts")
            .insert(payload)
            .execute()
            .data
            or []
        ),
        operation=f"insert_catalog_concept_{row['code']}",
        critical=True,
    )


def verify_final(
    source_rows: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> None:
    current = fetch_table("catalog_concepts", "*")
    source_by_id = {str(row["id"]): row for row in source_rows}
    current_by_id = {str(row["id"]): row for row in current}

    errors: list[str] = []

    if len(current) != EXPECTED_TOTAL:
        errors.append(
            f"catalog_concepts total={len(current)}; esperado={EXPECTED_TOTAL}."
        )

    active = [row for row in current if bool(row.get("is_active"))]
    inactive = {
        str(row.get("code"))
        for row in current
        if not bool(row.get("is_active"))
    }

    if len(active) != EXPECTED_ACTIVE:
        errors.append(
            f"Activos={len(active)}; esperado={EXPECTED_ACTIVE}."
        )

    if inactive != EXPECTED_INACTIVE_CODES:
        errors.append(
            f"Inactivos={sorted(inactive)}; "
            f"esperados={sorted(EXPECTED_INACTIVE_CODES)}."
        )

    if len({str(row.get("id")) for row in current}) != len(current):
        errors.append("UUID duplicados en catalog_concepts.")

    if len({str(row.get("code")) for row in current}) != len(current):
        errors.append("Claves duplicadas en catalog_concepts.")

    for row_id, source in source_by_id.items():
        actual = current_by_id.get(row_id)
        if not actual:
            errors.append(f"Falta UUID {row_id} ({source['code']}).")
            continue

        fields = changed_fields(actual, source)
        if fields:
            errors.append(
                f"{source['code']} difiere del maestro en: {', '.join(fields)}"
            )

    unit_by_id = {str(row["id"]): row for row in units}
    current_by_code = {str(row["code"]): row for row in current}

    for code, (expected_unit, expected_mode, expected_formula) in EXPECTED_CORRECTIONS.items():
        row = current_by_code.get(code)
        if not row:
            errors.append(f"Falta {code} en verificación final.")
            continue

        unit = unit_by_id.get(str(row.get("unit_id")))
        unit_code = str(unit.get("code", "")).upper() if unit else ""

        if (
            unit_code != expected_unit
            or row.get("quantification_mode") != expected_mode
            or row.get("default_formula_code") != expected_formula
        ):
            errors.append(
                f"{code}: ({unit_code}, {row.get('quantification_mode')}, "
                f"{row.get('default_formula_code')}) != "
                f"({expected_unit}, {expected_mode}, {expected_formula})"
            )

    cim003a = current_by_code.get("CIM-003A")
    if not cim003a:
        errors.append("CIM-003A no existe después de migración.")
    else:
        unit = unit_by_id.get(str(cim003a.get("unit_id")))
        unit_code = str(unit.get("code", "")).upper() if unit else ""
        if str(cim003a.get("id")) != EXPECTED_CIM003A_ID:
            errors.append("CIM-003A tiene UUID incorrecto.")
        if unit_code != "PZA":
            errors.append(f"CIM-003A tiene unidad {unit_code}; debe ser PZA.")

    if errors:
        raise RuntimeError(
            "La verificación posterior a la migración falló:\n- "
            + "\n- ".join(errors)
        )

    print("\n--- VERIFICACIÓN FINAL ---")
    print(f"Conceptos: {len(current)}/{EXPECTED_TOTAL}")
    print(f"Activos:   {len(active)}/{EXPECTED_ACTIVE}")
    print(f"Inactivos: {', '.join(sorted(inactive))}")
    print("UUID únicos: 101/101")
    print("Claves únicas: 101/101")
    print("Correcciones V1.8: 18/18")
    print("CIM-003A: UUID definitivo + PZA + por_pieza + F_PZA_DIRECTA")
    print("Catálogo Maestro V1.8 migrado correctamente.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración controlada de catalog_concepts a Quantia V1.8."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Ruta a catalog_concepts_V1_8_migracion.csv",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()

    print("Migración Catálogo Maestro Quantia V1.8")
    print(f"Archivo: {csv_path}")
    print("Modo:", "ESCRITURA" if WRITE_ENABLED else "DRY-RUN")

    source_rows = load_migration(csv_path)

    units = fetch_table(
        "catalog_units",
        "id,code,name,symbol,is_active",
    )
    partidas = fetch_table(
        "catalog_partidas",
        "id,code,name,is_active",
    )

    validate_source(source_rows, units, partidas)

    current_rows = fetch_table("catalog_concepts", "*")

    inserts, updates, extra_rows = audit_current(
        source_rows,
        current_rows,
    )

    print_plan(inserts, updates, extra_rows)

    if extra_rows:
        raise RuntimeError(
            "La BD contiene registros fuera del Maestro V1.8. "
            "No se realizará escritura hasta revisarlos."
        )

    if not WRITE_ENABLED:
        print("\nDRY-RUN correcto. No se modificó Supabase.")
        print(
            "Para escribir, establece QUANTIA_CATALOG_V18_WRITE=1 "
            "y vuelve a ejecutar el mismo comando."
        )
        return

    print("\n--- ESCRITURA ---")

    for row in inserts:
        insert_new(row)
        print(f"Creado:     {row['code']}")

    for row, _fields in updates:
        update_existing(row)
        print(f"Actualizado: {row['code']}")

    verify_final(source_rows, units)


if __name__ == "__main__":
    main()
