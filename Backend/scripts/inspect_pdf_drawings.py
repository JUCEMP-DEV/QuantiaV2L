import argparse
import collections
import sys
from pathlib import Path

import pymupdf


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inspecciona la estructura vectorial real "
            "de un PDF para Quantia V2."
        )
    )

    parser.add_argument(
        "pdf",
        help="Ruta al PDF original.",
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    ).expanduser().resolve()

    if not pdf_path.exists():
        print(
            "ERROR: no existe el PDF:"
        )
        print(
            pdf_path
        )
        return 1

    try:
        document = pymupdf.open(
            pdf_path
        )

    except Exception as exc:
        print(
            "ERROR abriendo PDF:"
        )
        print(
            f"{type(exc).__name__}: {exc}"
        )
        return 2

    try:
        print()
        print(
            "========================================"
        )
        print(
            "QUANTIA V2 — PDF DRAWING INSPECTION"
        )
        print(
            "========================================"
        )

        print(
            f"Páginas: {document.page_count}"
        )

        print()

        for page_index in range(
            document.page_count
        ):
            page = document.load_page(
                page_index
            )

            drawings = page.get_drawings()

            command_counter = (
                collections.Counter()
            )

            path_type_counter = (
                collections.Counter()
            )

            width_counter = (
                collections.Counter()
            )

            fill_count = 0
            stroke_count = 0
            closed_count = 0

            rectangle_items = []
            quad_items = []
            curve_items = []
            line_items = []

            print(
                "----------------------------------------"
            )

            print(
                f"PÁGINA {page_index + 1}"
            )

            print(
                f"rotation        : {page.rotation}"
            )

            print(
                f"rect            : {page.rect}"
            )

            print(
                f"cropbox         : {page.cropbox}"
            )

            print(
                f"paths           : {len(drawings)}"
            )

            for path_index, drawing in enumerate(
                drawings
            ):
                if not isinstance(
                    drawing,
                    dict,
                ):
                    continue

                path_type = drawing.get(
                    "type"
                )

                path_type_counter[
                    str(path_type)
                ] += 1

                width = drawing.get(
                    "width"
                )

                if isinstance(
                    width,
                    (int, float),
                ):
                    width_counter[
                        round(
                            float(width),
                            4,
                        )
                    ] += 1

                if drawing.get(
                    "fill"
                ) is not None:
                    fill_count += 1

                if drawing.get(
                    "color"
                ) is not None:
                    stroke_count += 1

                if drawing.get(
                    "closePath"
                ) is True:
                    closed_count += 1

                items = drawing.get(
                    "items",
                    []
                )

                if not isinstance(
                    items,
                    list,
                ):
                    continue

                for item_index, item in enumerate(
                    items
                ):
                    if (
                        not isinstance(
                            item,
                            tuple,
                        )
                        or not item
                    ):
                        continue

                    command = str(
                        item[0]
                    )

                    command_counter[
                        command
                    ] += 1

                    reference = {
                        "path_index":
                            path_index,
                        "item_index":
                            item_index,
                        "command":
                            command,
                        "item":
                            item,
                        "path_type":
                            path_type,
                        "width":
                            width,
                        "fill":
                            drawing.get(
                                "fill"
                            ),
                        "color":
                            drawing.get(
                                "color"
                            ),
                        "closePath":
                            drawing.get(
                                "closePath"
                            ),
                    }

                    if command == "re":
                        rectangle_items.append(
                            reference
                        )

                    elif command == "qu":
                        quad_items.append(
                            reference
                        )

                    elif command == "c":
                        curve_items.append(
                            reference
                        )

                    elif command == "l":
                        line_items.append(
                            reference
                        )

            print()

            print(
                "COMANDOS:"
            )

            for command, count in (
                command_counter
                .most_common()
            ):
                print(
                    f"  {command:<8} {count}"
                )

            print()

            print(
                "TIPOS DE PATH:"
            )

            for path_type, count in (
                path_type_counter
                .most_common()
            ):
                print(
                    f"  {path_type:<12} {count}"
                )

            print()

            print(
                "ATRIBUTOS:"
            )

            print(
                f"  con fill      : {fill_count}"
            )

            print(
                f"  con stroke    : {stroke_count}"
            )

            print(
                f"  closePath=True: {closed_count}"
            )

            print()

            print(
                "ANCHOS DE TRAZO:"
            )

            for width, count in sorted(
                width_counter.items(),
                key=lambda item:
                    item[0],
            ):
                print(
                    f"  {width:<10} {count}"
                )

            print()

            print(
                "CONTEOS DIRECTOS:"
            )

            print(
                f"  líneas l      : "
                f"{len(line_items)}"
            )

            print(
                f"  rectángulos re: "
                f"{len(rectangle_items)}"
            )

            print(
                f"  quads qu      : "
                f"{len(quad_items)}"
            )

            print(
                f"  curvas c      : "
                f"{len(curve_items)}"
            )

            print()

            # =================================================
            # MUESTRA DE RECTÁNGULOS
            # =================================================

            if rectangle_items:
                print(
                    "PRIMEROS RECTÁNGULOS:"
                )

                for item in (
                    rectangle_items[:15]
                ):
                    print(
                        "  path=",
                        item["path_index"],
                        "| width=",
                        item["width"],
                        "| type=",
                        item["path_type"],
                        "| fill=",
                        item["fill"],
                        "| close=",
                        item["closePath"],
                        "| item=",
                        item["item"],
                    )

                print()

            # =================================================
            # MUESTRA PATHS CERRADOS
            # =================================================

            closed_examples = []

            for path_index, drawing in enumerate(
                drawings
            ):
                if (
                    isinstance(
                        drawing,
                        dict,
                    )
                    and drawing.get(
                        "closePath"
                    ) is True
                ):
                    closed_examples.append(
                        (
                            path_index,
                            drawing,
                        )
                    )

            if closed_examples:
                print(
                    "PRIMEROS PATHS CERRADOS:"
                )

                for (
                    path_index,
                    drawing,
                ) in closed_examples[:10]:
                    print(
                        f"  path={path_index} "
                        f"type={drawing.get('type')} "
                        f"width={drawing.get('width')} "
                        f"fill={drawing.get('fill')} "
                        f"color={drawing.get('color')} "
                        f"rect={drawing.get('rect')} "
                        f"items={len(drawing.get('items', []))}"
                    )

                print()

    finally:
        document.close()

    print(
        "========================================"
    )
    print(
        "FIN DE INSPECCIÓN"
    )
    print(
        "========================================"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )