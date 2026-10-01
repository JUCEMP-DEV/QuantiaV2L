import {
  closestPointOnSegment,
  distToSegment,
  segmentLength,
} from "./geometry";
import {
  createDoor,
  createWindow,
} from "./editorSchema";
import { validateOpening } from "./constraints";

export function wallPointAtPosition(wall, position) {
  const t = clamp01(position);

  return {
    x: Number(wall.start.x) + (Number(wall.end.x) - Number(wall.start.x)) * t,
    y: Number(wall.start.y) + (Number(wall.end.y) - Number(wall.start.y)) * t,
  };
}

export function positionOnWallFromPoint(wall, point) {
  return closestPointOnSegment(point, wall.start, wall.end).t;
}

export function createDoorOnWall({
  wall,
  point = null,
  position = null,
  data = {},
  walls = [],
  doors = [],
  windows = [],
}) {
  if (!wall?.id) {
    return failure("DOOR_WITHOUT_WALL", "No existe un muro válido para la puerta.");
  }

  const resolvedPosition = position != null && position !== "" && Number.isFinite(Number(position))
    ? clamp01(position)
    : point
      ? positionOnWallFromPoint(wall, point)
      : null;

  const door = createDoor({
    ...data,
    levelId: wall.levelId,
    wallId: wall.id,
    position: resolvedPosition,
  });

  const validation = validateOpening({
    opening: door,
    walls: walls.length ? walls : [wall],
    doors: [...doors, door],
    windows,
  });

  if (!validation.isValid) {
    return {
      ok: false,
      entity: door,
      validation,
    };
  }

  return {
    ok: true,
    entity: door,
    validation,
  };
}

export function createWindowOnWall({
  wall,
  point = null,
  position = null,
  data = {},
  walls = [],
  doors = [],
  windows = [],
}) {
  if (!wall?.id) {
    return failure(
      "WINDOW_WITHOUT_WALL",
      "No existe un muro válido para la ventana.",
    );
  }

  const resolvedPosition = position != null && position !== "" && Number.isFinite(Number(position))
    ? clamp01(position)
    : point
      ? positionOnWallFromPoint(wall, point)
      : null;

  const window = createWindow({
    ...data,
    levelId: wall.levelId,
    wallId: wall.id,
    position: resolvedPosition,
  });

  const validation = validateOpening({
    opening: window,
    walls: walls.length ? walls : [wall],
    doors,
    windows: [...windows, window],
  });

  if (!validation.isValid) {
    return {
      ok: false,
      entity: window,
      validation,
    };
  }

  return {
    ok: true,
    entity: window,
    validation,
  };
}

export function moveOpeningAlongWall({
  opening,
  wall,
  point = null,
  position = null,
  walls = [],
  doors = [],
  windows = [],
}) {
  if (!opening || !wall) {
    return failure("OPENING_INVALID", "El vano o muro no es válido.");
  }

  const nextPosition = position != null && position !== "" && Number.isFinite(Number(position))
    ? clamp01(position)
    : point
      ? positionOnWallFromPoint(wall, point)
      : opening.position;

  const next = {
    ...opening,
    wallId: wall.id,
    levelId: wall.levelId,
    position: nextPosition,
  };

  const validation = validateOpening({
    opening: next,
    walls: walls.length ? walls : [wall],
    doors: isWindow(next)
      ? doors
      : doors.map((item) => item.id === next.id ? next : item),
    windows: isWindow(next)
      ? windows.map((item) => item.id === next.id ? next : item)
      : windows,
  });

  return {
    ok: validation.isValid,
    entity: next,
    validation,
  };
}

export function cascadeRemoveOpeningsForWalls({
  wallIds = [],
  doors = [],
  windows = [],
}) {
  const removed = new Set(wallIds);

  return {
    doors: doors.filter((door) => !removed.has(door.wallId)),
    windows: windows.filter((window) => !removed.has(window.wallId)),
    removedDoorIds: doors
      .filter((door) => removed.has(door.wallId))
      .map((door) => door.id),
    removedWindowIds: windows
      .filter((window) => removed.has(window.wallId))
      .map((window) => window.id),
  };
}

/**
 * Remapea vanos cuando un muro fue dividido/reconciliado.
 * Si el wallId original desaparece, conserva el punto geométrico del centro
 * y busca el nuevo segmento compatible.
 */
export function remapOpeningsAfterWallReconcile({
  openings = [],
  oldWalls = [],
  newWalls = [],
  toleranceM = 1e-6,
}) {
  const oldWallMap = new Map(oldWalls.map((wall) => [wall.id, wall]));
  const newWallMap = new Map(newWalls.map((wall) => [wall.id, wall]));

  const remapped = [];
  const unresolved = [];

  for (const opening of openings) {
    if (newWallMap.has(opening.wallId)) {
      remapped.push({ ...opening });
      continue;
    }

    const oldWall = oldWallMap.get(opening.wallId);
    if (!oldWall) {
      unresolved.push(opening.id);
      remapped.push({ ...opening, confirmed: false });
      continue;
    }

    const center = wallPointAtPosition(oldWall, opening.position);

    const candidates = newWalls
      .filter((wall) => wall.levelId === opening.levelId)
      .map((wall) => ({
        wall,
        distance: distToSegment(center, wall.start, wall.end),
      }))
      .filter((item) => item.distance <= toleranceM)
      .sort((a, b) => a.distance - b.distance);

    const match = candidates.length === 1 ? candidates[0].wall : null;
    if (!match) {
      unresolved.push(opening.id);
      remapped.push({ ...opening, confirmed: false });
      continue;
    }

    remapped.push({
      ...opening,
      wallId: match.id,
      position: positionOnWallFromPoint(match, center),
    });
  }

  return {
    openings: remapped,
    unresolvedIds: unresolved,
  };
}

export function openingIntervalOnWall(opening, wall) {
  const length = segmentLength(wall.start, wall.end);
  const width = Number(opening?.widthM);
  const position = Number(opening?.position);

  if (
    !Number.isFinite(length) ||
    length <= 0 ||
    !Number.isFinite(width) ||
    width <= 0 ||
    !Number.isFinite(position)
  ) {
    return null;
  }

  const half = width / (2 * length);
  return {
    min: position - half,
    max: position + half,
  };
}

function clamp01(value) {
  return Math.max(0, Math.min(1, Number(value)));
}

function isWindow(opening) {
  return Object.prototype.hasOwnProperty.call(opening || {}, "sillHeightM");
}

function failure(code, message) {
  return {
    ok: false,
    entity: null,
    validation: {
      isValid: false,
      conflicts: [{
        id: code,
        code,
        entityType: "opening",
        entityId: null,
        severity: "error",
        message,
        relatedEntityIds: [],
      }],
      warnings: [],
    },
  };
}
