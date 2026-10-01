from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "ocr_real"
SOURCE_PATH = FIXTURE_DIR / "documento_control.txt"


def _pdf_escape(value: str) -> bytes:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("cp1252")


def _write_embedded_pdf(lines: list[str], output_path: Path) -> None:
    commands = [b"BT", b"/F1 14 Tf", b"72 730 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append(b"0 -24 Td")
        commands.append(b"(" + _pdf_escape(line) + b") Tj")
    commands.append(b"ET")
    stream = b"\n".join(commands) + b"\n"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode("ascii"))
        document.extend(obj)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    output_path.write_bytes(document)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _render_page(lines: list[str], page_number: int) -> Image.Image:
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(52)
    body_font = _font(40)
    small_font = _font(30)
    draw.rectangle((90, 90, 1564, 2249), outline="black", width=4)
    draw.text((150, 150), lines[0], fill="black", font=title_font)
    y = 280
    for line in lines[1:]:
        y += 34 if not line else 0
        draw.text((150, y), line, fill="black", font=body_font)
        y += 72
    draw.text((1400, 2170), f"Página {page_number}", fill="black", font=small_font)
    return image


def main() -> None:
    lines = SOURCE_PATH.read_text(encoding="utf-8").splitlines()
    _write_embedded_pdf(lines, FIXTURE_DIR / "documento_texto_embebido.pdf")

    page_one = _render_page(lines[:7], page_number=1)
    page_two = _render_page([lines[0], *lines[7:]], page_number=2)
    page_one.save(FIXTURE_DIR / "imagen_escaneada.png", format="PNG")
    page_one.save(
        FIXTURE_DIR / "documento_escaneado.pdf",
        format="PDF",
        resolution=200,
        save_all=True,
        append_images=[page_two],
    )


if __name__ == "__main__":
    main()
