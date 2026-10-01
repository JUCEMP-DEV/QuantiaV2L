from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.ocr_service import OCRService


class DocumentService:
    def __init__(self, storage_dir: str | None = None, ocr_service: OCRService | None = None):
        self.storage_dir = Path(storage_dir) if storage_dir is not None else settings.upload_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_service = ocr_service or OCRService()

    def process_file(self, file_path: str | Path) -> dict[str, Any]:
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {source_path}")

        dest_path = self.storage_dir / source_path.name
        if dest_path.resolve() != source_path.resolve():
            shutil.copy2(source_path, dest_path)

        result = self.ocr_service.process_document(dest_path)
        return {
            "status": "processed",
            "file_name": source_path.name,
            "stored_path": str(dest_path),
            "text": result["text"],
            "metadata": result["metadata"],
        }
