from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.legacy.quantia_spatial.space_pdf_coordinate_mapper import (
    MappedLevelLocalization,
    MappedSpaceLocalization,
    NormalizedBBox,
    RasterBBox,
)


@dataclass(slots=True)
class SpaceRasterCoordinateMapping:
    page: int

    image_width_px: int
    image_height_px: int

    levels: list[
        MappedLevelLocalization
    ] = field(
        default_factory=list
    )

    spaces: list[
        MappedSpaceLocalization
    ] = field(
        default_factory=list
    )

    notes: list[str] = field(
        default_factory=list
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


class SpaceRasterCoordinateMapper:
    """
    Mapea bbox Gemini directamente al raster canónico.

    Ruta:

        JPG / PNG / croquis
            ↓
        raster canónico
            ↓
        Gemini bbox 0..1
            ↓
        bbox en píxeles

    No existe transformación PDF en esta ruta.
    """

    def map(
        self,
        *,
        localization_payload: dict[str, Any],
        image_width_px: int,
        image_height_px: int,
    ) -> SpaceRasterCoordinateMapping:
        if not isinstance(
            localization_payload,
            dict,
        ):
            raise ValueError(
                "La localización Gemini debe ser "
                "un objeto JSON."
            )

        width = self._positive_int(
            image_width_px,
            "image_width_px",
        )

        height = self._positive_int(
            image_height_px,
            "image_height_px",
        )

        page = self._page_number(
            localization_payload.get(
                "pagina",
                1,
            )
        )

        levels_payload = (
            localization_payload.get(
                "niveles"
            )
        )

        if not isinstance(
            levels_payload,
            list,
        ):
            raise ValueError(
                "El campo niveles no es una lista."
            )

        mapped_levels: list[
            MappedLevelLocalization
        ] = []

        mapped_spaces: list[
            MappedSpaceLocalization
        ] = []

        for level in levels_payload:
            if not isinstance(
                level,
                dict,
            ):
                continue

            name = str(
                level.get(
                    "nombre",
                    "",
                )
            ).strip()

            if not name:
                continue

            requested = (
                level.get(
                    "localizado"
                )
                is True
            )

            normalized_bbox = None
            raster_bbox = None
            reason = self._nullable_text(
                level.get(
                    "motivo_no_localizado"
                )
            )

            localized = False

            if requested:
                try:
                    normalized_bbox = (
                        self._parse_bbox(
                            level.get(
                                "bbox_normalizado"
                            )
                        )
                    )

                    raster_bbox = (
                        self._to_raster(
                            normalized_bbox,
                            width,
                            height,
                        )
                    )

                    localized = True

                except ValueError as exc:
                    reason = str(
                        exc
                    )

            mapped_levels.append(
                MappedLevelLocalization(
                    nombre=
                        name,

                    localizado=
                        localized,

                    confianza=
                        self._confidence(
                            level.get(
                                "confianza"
                            )
                        ),

                    bbox_normalizado=
                        normalized_bbox,

                    bbox_raster=
                        raster_bbox,

                    bbox_pdf=
                        None,

                    motivo_no_localizado=
                        reason,
                )
            )

            spaces_payload = (
                level.get(
                    "espacios"
                )
            )

            if not isinstance(
                spaces_payload,
                list,
            ):
                continue

            for space in spaces_payload:
                if not isinstance(
                    space,
                    dict,
                ):
                    continue

                space_id = str(
                    space.get(
                        "id_propuesto",
                        "",
                    )
                ).strip()

                if not space_id:
                    continue

                requested_space = (
                    space.get(
                        "localizado"
                    )
                    is True
                )

                normalized_space = None
                raster_space = None

                reason_space = (
                    self._nullable_text(
                        space.get(
                            "motivo_no_localizado"
                        )
                    )
                )

                localized_space = False

                if requested_space:
                    try:
                        normalized_space = (
                            self._parse_bbox(
                                space.get(
                                    "bbox_normalizado"
                                )
                            )
                        )

                        raster_space = (
                            self._to_raster(
                                normalized_space,
                                width,
                                height,
                            )
                        )

                        localized_space = True

                    except ValueError as exc:
                        reason_space = str(
                            exc
                        )

                mapped_spaces.append(
                    MappedSpaceLocalization(
                        nivel=
                            name,

                        id_propuesto=
                            space_id,

                        nombre=
                            str(
                                space.get(
                                    "nombre",
                                    "",
                                )
                            ).strip(),

                        localizado=
                            localized_space,

                        confianza=
                            self._confidence(
                                space.get(
                                    "confianza"
                                )
                            ),

                        bbox_normalizado=
                            normalized_space,

                        bbox_raster=
                            raster_space,

                        bbox_pdf=
                            None,

                        evidencia=
                            self._string_list(
                                space.get(
                                    "evidencia"
                                )
                            ),

                        motivo_no_localizado=
                            reason_space,
                    )
                )

        return SpaceRasterCoordinateMapping(
            page=
                page,

            image_width_px=
                width,

            image_height_px=
                height,

            levels=
                mapped_levels,

            spaces=
                mapped_spaces,

            notes=[
                (
                    "Las localizaciones Gemini fueron "
                    "mapeadas directamente al raster "
                    "canónico."
                ),
                (
                    "Los bbox continúan siendo regiones "
                    "aproximadas y no geometría final."
                ),
            ],
        )

    @staticmethod
    def _parse_bbox(
        value: Any,
    ) -> NormalizedBBox:
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "bbox_normalizado inválido."
            )

        try:
            x_min = float(
                value["x_min"]
            )

            y_min = float(
                value["y_min"]
            )

            x_max = float(
                value["x_max"]
            )

            y_max = float(
                value["y_max"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "bbox_normalizado inválido."
            ) from exc

        if not (
            0.0
            <= x_min
            < x_max
            <= 1.0
        ):
            raise ValueError(
                "Coordenadas X inválidas."
            )

        if not (
            0.0
            <= y_min
            < y_max
            <= 1.0
        ):
            raise ValueError(
                "Coordenadas Y inválidas."
            )

        return NormalizedBBox(
            x_min=
                x_min,

            y_min=
                y_min,

            x_max=
                x_max,

            y_max=
                y_max,
        )

    @staticmethod
    def _to_raster(
        bbox: NormalizedBBox,
        width: int,
        height: int,
    ) -> RasterBBox:
        return RasterBBox(
            x_min=
                bbox.x_min
                * width,

            y_min=
                bbox.y_min
                * height,

            x_max=
                bbox.x_max
                * width,

            y_max=
                bbox.y_max
                * height,
        )

    @staticmethod
    def _positive_int(
        value: Any,
        name: str,
    ) -> int:
        try:
            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"{name} inválido."
            ) from exc

        if number <= 0:
            raise ValueError(
                f"{name} debe ser mayor que cero."
            )

        return number

    @staticmethod
    def _page_number(
        value: Any,
    ) -> int:
        if isinstance(
            value,
            bool,
        ):
            raise ValueError(
                "Número de página inválido."
            )

        try:
            page = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Número de página inválido."
            ) from exc

        if page <= 0:
            raise ValueError(
                "Número de página inválido."
            )

        return page

    @staticmethod
    def _confidence(
        value: Any,
    ) -> float:
        if isinstance(
            value,
            bool,
        ):
            return 0.0

        if not isinstance(
            value,
            (int, float),
        ):
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                float(
                    value
                ),
            ),
        )

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            text
            for text
            in (
                str(
                    item or ""
                ).strip()
                for item
                in value
            )
            if text
        ]

    @staticmethod
    def _nullable_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(
            value
        ).strip()

        return (
            text
            if text
            else None
        )


def get_space_raster_coordinate_mapper(
) -> SpaceRasterCoordinateMapper:
    return SpaceRasterCoordinateMapper()