import tempfile
import unittest
from pathlib import Path
import os
from unittest.mock import Mock, patch

from app.services.ocr_service import OCRDependencyError, OCRProcessingError, OCRService


class OCRServiceTests(unittest.TestCase):
    def test_process_plain_text_document(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "sample.txt"
            temp_path.write_text("Linea uno\n\nLinea dos", encoding="utf-8")

            result = OCRService().process_document(temp_path)

            self.assertEqual(result["text"], "Linea uno\n\nLinea dos")
            self.assertEqual(result["metadata"]["file_name"], "sample.txt")
            self.assertEqual(result["metadata"]["page_count"], 1)

    def test_process_unsupported_document_returns_empty_text(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "sample.xyz"
            temp_path.write_text("contenido", encoding="utf-8")

            result = OCRService().process_document(temp_path)

            self.assertEqual(result["text"], "")
            self.assertEqual(result["metadata"]["extension"], ".xyz")
            self.assertEqual(result["metadata"]["page_count"], 0)

    def test_clean_text_normalizes_spaces_and_control_characters(self):
        service = OCRService()

        text = "  Total\t\t de\x00 obra   \n\n\n  Costo   directo  "

        self.assertEqual(service._clean_text(text), "Total de obra\n\nCosto directo")

    def test_clean_text_preserves_paragraph_lines(self):
        service = OCRService()

        text = "Parrafo uno linea uno  \n  linea dos\n\n\nParrafo dos"

        self.assertEqual(service._clean_text(text), "Parrafo uno linea uno\nlinea dos\n\nParrafo dos")

    def test_process_missing_document_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            OCRService().process_document("missing.pdf")

    def test_supported_document_without_text_raises_processing_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "empty.txt"
            temp_path.write_text("   \n", encoding="utf-8")

            with self.assertRaises(OCRProcessingError):
                OCRService().process_document(temp_path)

    def test_missing_tesseract_path_raises_dependency_error(self):
        service = OCRService(tesseract_cmd="missing-tesseract.exe")

        with self.assertRaises(OCRDependencyError):
            service._extract_text_from_image_object(Mock())

    def test_tesseract_receives_language_and_data_directory(self):
        import pytesseract

        service = OCRService(
            language="spa",
            tesseract_cmd=Path(__file__),
            tesseract_data_dir=Path(__file__).parent,
        )

        with (
            patch.dict(os.environ, {}, clear=False),
            patch.object(pytesseract.pytesseract, "tesseract_cmd", "tesseract"),
            patch.object(pytesseract, "image_to_string", return_value="texto") as image_to_string,
        ):
            result = service._extract_text_from_image_object(Mock())

        self.assertEqual(result, "texto")
        image_to_string.assert_called_once_with(
            unittest.mock.ANY,
            lang="spa",
        )
        self.assertNotEqual(os.environ.get("TESSDATA_PREFIX"), str(Path(__file__).parent))

    def test_scanned_pdf_receives_poppler_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            poppler_path = Path(tmp_dir)
            (poppler_path / "pdftoppm.exe").touch()
            service = OCRService(poppler_path=poppler_path)
            pdf_path = poppler_path / "sample.pdf"
            pdf_path.touch()

            with (
                patch("pdf2image.convert_from_path", return_value=[Mock()]) as convert,
                patch.object(service, "_extract_text_from_image_object", return_value="texto"),
            ):
                result = service._extract_scanned_pdf_text(pdf_path)

        self.assertEqual(result, ["texto"])
        convert.assert_called_once_with(str(pdf_path), poppler_path=str(poppler_path))


if __name__ == "__main__":
    unittest.main()


