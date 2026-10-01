import {
  buildEdges,
  normalizeGeometry,
  pointOnSegment,
  polygonContainsPolygon,
  polygonSelfIntersects,
  polygonsOverlapInterior,
  segmentLength,
} from "./geometry";

export const VALIDATION_CODES = Object.freeze({
  SPACE_OVERLAP: "SPACE_OVERLAP",
  SPACE_OUTSIDE_TERRAIN: "SPACE_OUTSIDE_TERRAIN",
  SPACE_SELF_INTERSECTION: "SPACE_SELF_INTERSECTION",
  SPACE_ZERO_AREA: "SPACE_ZERO_AREA",
  SPACE_INVALID_GEOMETRY: "SPACE_INVALID_GEOMETRY",
  WALL_DUPLICATED: "WALL_DUPLICATED",
  WALL_ZERO_LENGTH: "WALL_ZERO_LENGTH",
  WALL_ORPHAN: "WALL_ORPHAN",
  WALL_SPACE_RELATION_CONFLICT: "WALL_SPACE_RELATION_CONFLICT",
  DOOR_WITHOUT_WALL: "DOOR_WITHOUT_WALL",
  DOOR_OUTSIDE_WALL: "DOOR_OUTSIDE_WALL",
  DOOR_OVERLAP: "DOOR_OVERLAP",
  WINDOW_WITHOUT_WALL: "WINDOW_WITHOUT_WALL",
  WINDOW_OUTSIDE_WALL: "WINDOW_OUTSIDE_WALL",
  WINDOW_OVERLAP: "WINDOW_OVERLAP",
  OPENING_INVALID_POSITION: "OPENING_INVALID_POSITION",
  OPENING_INVALID_WIDTH: "OPENING_INVALID_WIDTH",
  LEVEL_MISSING_HEIGHT: "LEVEL_MISSING_HEIGHT",
  LEVEL_INVALID_HEIGHT: "LEVEL_INVALID_HEIGHT",
  LEVEL_INVALID_ELEVATION: "LEVEL_INVALID_ELEVATION",
  GEOMETRY_INVALID: "GEOMETRY_INVALID",
});

export function validateGeometry(geometry) {
  const normalized = normalizeGeometry(geometry);
  const conflicts = [];

  if (!normalized || normalized.vertices.length < 3) {
    conflicts.push(conflict(
      VALIDATION_CODES.SPACE_INVALID_GEOMETRY,
      "space",
      null,
      "La geometría requiere al menos tres vértices válidos.",
    ));
    return validationResult(conflicts);
  }

  if (normalized.areaM2 <= 0) {
    conflicts.push(conflict(
      VALIDATION_CODES.SPACE_ZERO_AREA,
      "space",
      null,
      "La geometría debe tener un área mayor que cero.",
    ));
  }

  if (polygonSelfIntersects(normalized.vertices)) {
    conflicts.push(conflict(
      VALIDATION_CODES.SPACE_SELF_INTERSECTION,
      "space",
      null,
      "La geometría no puede cruzarse sobre sí misma.",
    ));
  }

  return validationResult(conflicts);
}

export function validateSpaceCandidate({
  space,
  spaces = [],
  terrain = null,
  ignoreSpaceId = null,
}) {
  const conflicts = [];
  const geometry = normalizeGeometry(space?.geometry);

  const geometryValidation = validateGeometry(geometry);
  conflicts.push(
    ...geometryValidation.conflicts.map((item) => ({
      ...item,
      entityId: space?.id || null,
    })),
  );

  if (!geometry || !geometryValidation.isValid) {
    return validationResult(conflicts);
  }

  for (const other of spaces) {
    if (!other?.geometry) continue;
    if (other.id === ignoreSpaceId || other.id === space?.id) continue;
    if (String(other.levelId || "") !== String(space?.levelId || "")) continue;

    const otherGeometry = normalizeGeometry(other.geometry);
    if (!otherGeometry) continue;

    if (polygonsOverlapInterior(
      geometry.vertices,
      otherGeometry.vertices,
    )) {
      conflicts.push(conflict(
        VALIDATION_CODES.SPACE_OVERLAP,
        "space",
        space?.id || null,
        "El espacio se superpone con otro espacio del mismo nivel.",
        [other.id],
      ));
    }
  }

  if (terrain?.geometry) {
    const terrainGeometry = normalizeGeometry(terrain.geometry);

    if (
      terrainGeometry &&
      !polygonContainsPolygon(
        terrainGeometry.vertices,
        geometry.vertices,
      )
    ) {
      conflicts.push(conflict(
        VALIDATION_CODES.SPACE_OUTSIDE_TERRAIN,
        "space",
        space?.id || null,
        "El espacio queda fuera del terreno definido.",
      ));
    }
  }

  return validationResult(conflicts);
}

export function canApplySpaceGeometry(args) {
  return validateSpaceCandidate(args);
}

export function validateWall(wall) {
  const conflicts = [];

  if (!wall?.start || !wall?.end || segmentLength(wall.start, wall.end) <= 0) {
    conflicts.push(conflict(
      VALIDATION_CODES.WALL_ZERO_LENGTH,
      "wall",
      wall?.id || null,
      "El muro debe tener una longitud mayor que cero.",
    ));
  }

  if (!wall?.spaceAId && !wall?.spaceBId) {
    conflicts.push(conflict(
      VALIDATION_CODES.WALL_ORPHAN,
      "wall",
      wall?.id || null,
      "El muro no está relacionado con ningún espacio.",
      [],
      "warning",
    ));
  }

  if (
    wall?.spaceAId &&
    wall?.spaceBId &&
    wall.spaceAId === wall.spaceBId
  ) {
    conflicts.push(conflict(
      VALIDATION_CODES.WALL_SPACE_RELATION_CONFLICT,
      "wall",
      wall?.id || null,
      "Un muro no puede tener el mismo espacio en ambos lados.",
    ));
  }

  return validationResult(conflicts);
}

export function validateOpening({
  opening,
  walls = [],
  doors = [],
  windows = [],
  levels = [],
  requireComplete = false,
}) {
  const conflicts = [];
  const wall = walls.find((item) => item.id === opening?.wallId);

  if (!wall) {
    conflicts.push(conflict(
      openingKindCode(opening, "withoutWall"),
      openingKind(opening),
      opening?.id || null,
      "El vano debe estar asociado a un muro existente.",
    ));
    return validationResult(conflicts);
  }

  const hasPosition =
    opening.position !== null &&
    opening.position !== undefined &&
    opening.position !== "";

  const position =
    hasPosition
      ? Number(opening.position)
      : Number.NaN;

  if (!Number.isFinite(position) || position < 0 || position > 1) {
    conflicts.push(conflict(
      VALIDATION_CODES.OPENING_INVALID_POSITION,
      openingKind(opening),
      opening?.id || null,
      "La posición del vano debe estar entre 0 y 1 sobre el muro.",
    ));
  }

  const width = Number(opening.widthM);
  if (opening.widthM != null && (!Number.isFinite(width) || width <= 0)) {
    conflicts.push(conflict(
      VALIDATION_CODES.OPENING_INVALID_WIDTH,
      openingKind(opening),
      opening?.id || null,
      "El ancho del vano debe ser mayor que cero.",
    ));
  }

  const known = (v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v));
  const isWindow = opening.kind === "WINDOW" || Object.hasOwn(opening, "sillHeightM");
  const sill = isWindow ? opening.sillHeightM : 0;
  const height = opening.heightM;
  const wallHeight = wall.heightM ?? levels.find((l) => l.id === wall.levelId)?.heightM;
  const add = (code, message) => conflicts.push(conflict(code, openingKind(opening), opening.id, message));
  if (opening.levelId !== wall.levelId) add("OPENING_LEVEL_MISMATCH", "El vano y su muro deben pertenecer al mismo nivel.");
  if (known(height) && Number(height) <= 0) add("OPENING_HEIGHT", "La altura debe ser positiva.");
  if (known(sill) && Number(sill) < 0) add("OPENING_SILL", "El antepecho no puede ser negativo.");
  if (known(height) && known(sill) && known(wallHeight) && Number(sill) + Number(height) > Number(wallHeight) + 1e-6)
    add("OPENING_VERTICAL_BOUNDS", "El vano excede la altura del muro.");
  if (requireComplete && (!known(opening.widthM) || !known(height) || !known(sill) || !known(wallHeight)))
    add("OPENING_MISSING_DIMENSIONS", "Define ancho, alto, antepecho y altura del muro antes de confirmar el vano.");
  const wallLength = segmentLength(wall.start, wall.end);

  if (
    Number.isFinite(position) &&
    Number.isFinite(width) &&
    width > 0 &&
    wallLength > 0
  ) {
    const halfSpan = width / (2 * wallLength);
    const min = position - halfSpan;
    const max = position + halfSpan;

    if (min < 0 || max > 1) {
      conflicts.push(conflict(
        openingKindCode(opening, "outsideWall"),
        openingKind(opening),
        opening?.id || null,
        "El vano no cabe completamente dentro del muro.",
      ));
    }

    const allOpenings = [...doors, ...windows].filter(
      (item) =>
        item?.id !== opening?.id &&
        item?.wallId === opening.wallId &&
        item.position !== null &&
        item.position !== undefined &&
        item.position !== "" &&
        item.widthM !== null &&
        item.widthM !== undefined &&
        item.widthM !== "" &&
        Number.isFinite(Number(item.position)) &&
        Number.isFinite(Number(item.widthM)) &&
        Number(item.widthM) > 0,
    );

    for (const other of allOpenings) {
      const otherHalf = Number(other.widthM) / (2 * wallLength);
      const otherMin = Number(other.position) - otherHalf;
      const otherMax = Number(other.position) + otherHalf;

      const otherSill = other.kind === "WINDOW" || Object.hasOwn(other, "sillHeightM") ? other.sillHeightM : 0;
      const separatedVertically = known(sill) && known(height) && known(otherSill) && known(other.heightM)
        && (Number(sill) + Number(height) <= Number(otherSill) + 1e-6 || Number(otherSill) + Number(other.heightM) <= Number(sill) + 1e-6);
      if (!separatedVertically && Math.max(min, otherMin) < Math.min(max, otherMax) - 1e-8) {
        conflicts.push(conflict(
          openingKindCode(opening, "overlap"),
          openingKind(opening),
          opening?.id || null,
          "El vano se superpone con otro vano del mismo muro.",
          [other.id],
        ));
      }
    }
  }

  return validationResult(conflicts);
}

export function validateReadyForCalculation(state) {
  const conflicts = [];
  const usedLevelIds = new Set(
    (state?.spaces || [])
      .map((space) => space?.levelId)
      .filter(Boolean),
  );

  for (const level of state?.levels || []) {
    if (!usedLevelIds.has(level.id)) continue;

    const height = Number(level.heightM);
    if (!Number.isFinite(height) || height <= 0) {
      conflicts.push(conflict(
        VALIDATION_CODES.LEVEL_MISSING_HEIGHT,
        "level",
        level.id,
        `El nivel "${level.name || level.key || level.id}" requiere altura para continuar al cálculo.`,
      ));
    }
  }

  for (const space of state?.spaces || []) {
    const result = validateSpaceCandidate({
      space,
      spaces: state.spaces,
      terrain: state.terrain,
      ignoreSpaceId: space.id,
    });
    conflicts.push(...result.conflicts);
  }

  for (const wall of state?.walls || []) {
    conflicts.push(...validateWall(wall).conflicts);
  }

  for (const door of state?.doors || []) {
    conflicts.push(...validateOpening({
      opening: door,
      levels: state.levels,
      walls: state.walls,
      doors: state.doors,
      windows: state.windows,
    }).conflicts);
  }

  for (const window of state?.windows || []) {
    conflicts.push(...validateOpening({
      opening: window,
      levels: state.levels,
      walls: state.walls,
      doors: state.doors,
      windows: state.windows,
    }).conflicts);
  }

  return validationResult(deduplicateConflicts(conflicts));
}

export function validateTerrainIsOptional(state) {
  return {
    terrainRequired: false,
    terrainPresent: Boolean(state?.terrain),
  };
}

export function geometryTouchesWall(geometry, wall, epsilon = 1e-8) {
  const normalized = normalizeGeometry(geometry);
  if (!normalized || !wall?.start || !wall?.end) return false;

  return buildEdges(normalized.vertices).some(
    (edge) =>
      pointOnSegment(edge.start, wall.start, wall.end, epsilon) &&
      pointOnSegment(edge.end, wall.start, wall.end, epsilon),
  );
}

function openingKind(opening) {
  return Object.prototype.hasOwnProperty.call(opening || {}, "sillHeightM")
    ? "window"
    : "door";
}

function openingKindCode(opening, kind) {
  const isWindow = openingKind(opening) === "window";
  const map = {
    withoutWall: isWindow
      ? VALIDATION_CODES.WINDOW_WITHOUT_WALL
      : VALIDATION_CODES.DOOR_WITHOUT_WALL,
    outsideWall: isWindow
      ? VALIDATION_CODES.WINDOW_OUTSIDE_WALL
      : VALIDATION_CODES.DOOR_OUTSIDE_WALL,
    overlap: isWindow
      ? VALIDATION_CODES.WINDOW_OVERLAP
      : VALIDATION_CODES.DOOR_OVERLAP,
  };
  return map[kind];
}

function conflict(
  code,
  entityType,
  entityId,
  message,
  relatedEntityIds = [],
  severity = "error",
) {
  return {
    id: `${code}:${entityType}:${entityId ?? "unknown"}:${relatedEntityIds.join(",")}`,
    code,
    entityType,
    entityId,
    severity,
    message,
    relatedEntityIds,
  };
}

function validationResult(conflicts) {
  return {
    isValid: !conflicts.some((item) => item.severity === "error"),
    conflicts,
    warnings: conflicts.filter((item) => item.severity === "warning"),
  };
}

function deduplicateConflicts(conflicts) {
  const map = new Map();
  for (const item of conflicts) {
    map.set(item.id, item);
  }
  return [...map.values()];
}
