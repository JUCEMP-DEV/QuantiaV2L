"""Move the reviewed historical test set, verifying paths and SHA256 before/after.

This is a one-time archival operation. No reconstruction code is changed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


def io_path(path: Path) -> Path:
    # Windows legacy MAX_PATH also applies to compiled historical test names.
    absolute = str(path.absolute())
    return Path("\\\\?\\" + absolute) if os.name == "nt" and not absolute.startswith("\\\\?\\") else path


def digest(path: Path) -> str:
    with io_path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    workspace = Path(__file__).resolve().parents[2]
    source = (workspace / "Backend/app/quantia_spatialV1").resolve()
    plan_path = source / "documentation/ARCHIVE_TESTS_2026-09-28.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["status"] == "PLANNED", "This archive has already been processed"
    assert Path(plan["source_root"]).resolve() == source
    authorized = Path(
        r"D:\03 INGENIEIRA SISTEMAS\03 RESIDENCIAS PROFESIONALES"
        r"\REFERENCIAS Y ANEXOS Quantia General"
    ).resolve(strict=True)
    archive = Path(plan["archive_root"]).resolve()
    assert archive.is_relative_to(authorized) and archive != authorized
    assert not archive.exists(), "Refusing to overwrite an existing archive"
    entries = plan["entries"]
    paths = [(source / name).resolve(strict=True) for name in entries]
    for name, path in zip(entries, paths):
        assert path.is_relative_to(source) and path != source
        assert not (source / name).is_symlink()
        assert name.startswith(("tests/", "documentation/history"))
        assert not name.startswith(("tests/data", "tests/output/canonical_", "tests/output/quantia_spatial_v1_process"))
        target = (archive / "quantia_spatialV1" / name).resolve()
        assert target.is_relative_to(archive) and target != archive
        for child in path.rglob("*") if path.is_dir() else ():
            assert not child.is_symlink() and child.resolve().is_relative_to(source)
    assert all(not a.is_relative_to(b) for a in paths for b in paths if a != b)
    for item in plan["files"]:
        path = (source / item["relative_path"]).resolve(strict=True)
        assert path.is_relative_to(source)
        assert any(path == entry or path.is_relative_to(entry) for entry in paths)
        assert digest(path) == item["sha256"], f"Source changed since review: {path}"

    archive.mkdir(parents=True)
    (archive / "manifest.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    support = archive / "support_snapshot"
    support.mkdir()
    loader = source / "tests/quantia_case_loader.py"
    shutil.copy2(loader, support / loader.name)
    (archive / "README.md").write_text(
        "# Archivo historico de pruebas Quantia Spatial V1\n\n"
        "Las ocho pruebas de primer nivel y documentation/history se retiraron del arbol activo.\n"
        "Los resultados historicos asociados conservan su estructura relativa bajo quantia_spatialV1/.\n"
        "manifest.json identifica cada origen, tamano y SHA256; no se ha eliminado evidencia.\n\n"
        "## Restauracion\n\n"
        "Usar el checkout/checkpoint compatible y restaurar las rutas de quantia_spatialV1/ "
        "en Backend/app/quantia_spatialV1/, comprobando primero que no existan colisiones.\n"
        "Los probes conservan imports y rutas originales: este archivo NO es una suite autonoma.\n"
        "quantia_case_loader.py se incluye como copia de referencia en support_snapshot/. "
        "Los datos/replays vigentes permanecen en tests/data del proyecto.\n"
        "Los checkpoints del motor permanecen en documentation/checkpoints.\n\n"
        f"Proyecto de origen: {source}\n",
        encoding="utf-8",
    )
    moved = []
    try:
        for name, path in zip(entries, paths):
            target = archive / "quantia_spatialV1" / name
            io_path(target.parent).mkdir(parents=True, exist_ok=True)
            shutil.move(str(io_path(path)), str(io_path(target)))
            moved.append((path, target))
        for item in plan["files"]:
            assert digest(archive / "quantia_spatialV1" / item["relative_path"]) == item["sha256"]
            assert not (source / item["relative_path"]).exists()
    except BaseException:
        for original, target in reversed(moved):
            assert original.resolve().is_relative_to(source)
            assert target.resolve().is_relative_to(archive)
            assert not original.exists(), f"Rollback collision: {original}"
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(io_path(target)), str(io_path(original)))
        raise
    plan["status"] = "ARCHIVED_SHA256_VERIFIED"
    plan["support_snapshot"] = {loader.name: digest(support / loader.name)}
    if plan.get("previous_attempt_archive_root"):
        previous = Path(plan["previous_attempt_archive_root"]).resolve(strict=True)
        assert previous.is_relative_to(authorized) and previous != authorized
        assert previous != archive and not archive.is_relative_to(previous)
        shutil.move(str(io_path(previous)), str(io_path(archive / "previous_attempt_rolled_back")))
    text = json.dumps(plan, indent=2, ensure_ascii=False)
    (archive / "manifest.json").write_text(text, encoding="utf-8")
    plan_path.write_text(text, encoding="utf-8")
    print(f"Archived {plan['file_count']} files ({plan['total_bytes']} bytes)")
    print(archive)


if __name__ == "__main__":
    main()
