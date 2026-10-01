from __future__ import annotations

import importlib.util
import os
import re
import shutil
from threading import Lock
from pathlib import Path
from typing import Any

from app.core.config import settings


class OCRServiceError(RuntimeError):
    pass


class OCRDependencyError(OCRServiceError):
    pass


class OCRProcessingError(OCRServiceError):
    pass


class OCRService:
    text_extensions = {".txt", ".md", ".json"}
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    _tesseract_environment_lock = Lock()

    def __init__(
        self,
        engine: str | None = None,
        language: str | None = None,
        tesseract_cmd: str | Path | None = None,
        tesseract_data_dir: str | Path | None = None,
        poppler_path: str | Path | None = None,
    ):
        self.engine = (engine or settings.ocr_engine).lower().strip()
        self.language = (language or settings.tesseract_language).strip()
        self.tesseract_cmd = self._optional_path(tesseract_cmd, settings.tesseract_cmd)
        self.tesseract_data_dir = self._optional_path(tesseract_data_dir, settings.tesseract_data_dir)
        self.poppler_path = self._optional_path(poppler_path, settings.poppler_path)

    def process_document(self, file_path: str | Path) -> dict[str, Any]:
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {source_path}")

        extension = source_path.suffix.lower()
        if extension in self.text_extensions:
            pages = [self._read_text(source_path)]
        elif extension == ".pdf":
            pages = self._extract_from_pdf(source_path)
        elif extension in self.image_extensions:
            pages = [self._extract_from_image(source_path)]
        else:
            pages = [""]

        clean_pages = []
        for page in pages:
            clean_page = self._clean_text(page)
            if clean_page:
                clean_pages.append(clean_page)
        text = "\n\n".join(clean_pages)
        supported = extension in self.text_extensions or extension == ".pdf" or extension in self.image_extensions
        if supported and not text:
            raise OCRProcessingError("No se pudo extraer texto del documento.")
        return {
            "text": text,
            "metadata": {
                "file_name": source_path.name,
                "extension": extension,
                "ocr_engine": self.engine,
                "ocr_language": self.language,
                "page_count": len(clean_pages),
            },
        }

    def _read_text(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")

    def _extract_from_pdf(self, file_path: Path) -> list[str]:
        embedded_text = self._extract_embedded_pdf_text(file_path)
        if embedded_text:
            return embedded_text
        return self._extract_scanned_pdf_text(file_path)

    def _extract_embedded_pdf_text(self, file_path: Path) -> list[str]:
        if importlib.util.find_spec("pypdf") is None:
            return []

        try:
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            pages_text = []
            for page in reader.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    pages_text.append(extracted)
            return pages_text
        except Exception as exc:  # pragma: no cover - defensive path
            raise OCRProcessingError(f"Error al procesar PDF: {exc}") from exc

    def _extract_scanned_pdf_text(self, file_path: Path) -> list[str]:
        if self.engine != "tesseract":
            raise OCRDependencyError(f"OCR no disponible: motor no soportado ({self.engine}).")
        if importlib.util.find_spec("pdf2image") is None:
            raise OCRDependencyError("OCR no disponible: pdf2image no esta instalado.")
        if self.poppler_path is not None:
            if not (self.poppler_path / "pdftoppm.exe").exists() and not (self.poppler_path / "pdftoppm").exists():
                raise OCRDependencyError(f"Poppler no esta disponible en {self.poppler_path}.")
        elif shutil.which("pdftoppm") is None:
            raise OCRDependencyError("Poppler no esta instalado o pdftoppm no esta disponible en PATH.")

        try:
            from pdf2image import convert_from_path

            images = convert_from_path(
                str(file_path),
                poppler_path=str(self.poppler_path) if self.poppler_path is not None else None,
            )
            return [self._extract_text_from_image_object(image) for image in images]
        except Exception as exc:  # pragma: no cover - depends on Poppler/local files
            if isinstance(exc, OCRServiceError):
                raise
            raise OCRProcessingError(f"Error al procesar PDF escaneado: {exc}") from exc

    def _extract_from_image(self, file_path: Path) -> str:
        if self.engine != "tesseract":
            raise OCRDependencyError(f"OCR no disponible: motor no soportado ({self.engine}).")
        if importlib.util.find_spec("PIL") is None:
            raise OCRDependencyError("OCR no disponible: Pillow no esta instalado.")

        try:
            from PIL import Image

            with Image.open(file_path) as image:
                return self._extract_text_from_image_object(image)
        except Exception as exc:  # pragma: no cover - defensive path
            if isinstance(exc, OCRServiceError):
                raise
            raise OCRProcessingError(f"Error al procesar imagen: {exc}") from exc

    def _extract_text_from_image_object(self, image: Any) -> str:
        if importlib.util.find_spec("pytesseract") is None:
            raise OCRDependencyError("OCR no disponible: pytesseract no esta instalado.")

        try:
            import pytesseract

            if self.tesseract_cmd is not None:
                if not self.tesseract_cmd.is_file():
                    raise OCRDependencyError(f"Tesseract no esta disponible en {self.tesseract_cmd}.")
                pytesseract.pytesseract.tesseract_cmd = str(self.tesseract_cmd)
            if self.tesseract_data_dir is not None:
                if not self.tesseract_data_dir.is_dir():
                    raise OCRDependencyError(f"El directorio tessdata no existe: {self.tesseract_data_dir}.")
                with self._tesseract_environment_lock:
                    previous_tessdata = os.environ.get("TESSDATA_PREFIX")
                    os.environ["TESSDATA_PREFIX"] = str(self.tesseract_data_dir)
                    try:
                        return pytesseract.image_to_string(image, lang=self.language)
                    finally:
                        if previous_tessdata is None:
                            os.environ.pop("TESSDATA_PREFIX", None)
                        else:
                            os.environ["TESSDATA_PREFIX"] = previous_tessdata
            return pytesseract.image_to_string(image, lang=self.language)
        except OCRServiceError:
            raise
        except pytesseract.TesseractNotFoundError as exc:  # pragma: no cover - depends on local Tesseract
            raise OCRDependencyError("Tesseract no esta instalado o no esta disponible en PATH.") from exc
        except pytesseract.TesseractError as exc:  # pragma: no cover - depends on local Tesseract data
            detail = str(exc)
            if "Failed loading language" in detail or "Error opening data file" in detail:
                raise OCRDependencyError(f"Tesseract no pudo cargar el idioma {self.language}.") from exc
            raise OCRProcessingError(f"Error al ejecutar OCR: {exc}") from exc
        except Exception as exc:  # pragma: no cover - depends on local Tesseract
            raise OCRProcessingError(f"Error al ejecutar OCR: {exc}") from exc

    @staticmethod
    def _optional_path(value: str | Path | None, default: Path | None) -> Path | None:
        resolved = value if value is not None else default
        if resolved is None or not str(resolved).strip():
            return None
        return Path(resolved).expanduser()

    def _clean_text(self, text: str) -> str:
        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", normalized)
        normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
        normalized = re.sub(r" *\n *", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        paragraphs = []
        for paragraph in normalized.split("\n\n"):
            lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
            if lines:
                paragraphs.append("\n".join(lines))
        return "\n\n".join(paragraphs).strip()


