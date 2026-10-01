import {
  buildEdges,
  closestPointOnSegment,
  dist,
  normalizeGeometry,
  pointOnSegment,
  pointsEqual,
  segmentLength,
} from "./geometry";
import {
  createEntityId,
  createSourceInfo,
  createWall,
} from "./editorSchema";

const DEFAULT_EPSILON = 1e-8;

export function reconcileWallGraph({
  spaces = [],
  existingWalls = [],
  levelId = null,
  epsilon = DEFAULT_EPSILON,
}) {
  const scopedSpaces = levelId
    ? spaces.filter((space) => space.levelId === levelId)
    : spaces;

  const rawEdges = collectSpaceEdges(scopedSpaces);
  const splitEdges = splitEdgesAtSharedPoints(rawEdges, epsilon);
  const groups = groupEquivalentSegments(splitEdges, epsilon);

  const usedWallIds = new Set();
  const walls = groups.map((group) => {
    const owners = [...new Set(group.owners)].filter(Boolean).slice(0, 2);
    const existing = findBestExistingWall(
      group,
      existingWalls,
      usedWallIds,
      epsilon,
    );

    const id = existing?.id || createEntityId("wall");
    usedWallIds.add(id);

    const wall = createWall({
      ...existing,
      id,
      levelId: group.levelId,
      start: group.start,
      end: group.end,
      lengthM: segmentLength(group.start, group.end),
      type:
        existing?.type ||
        (owners.length === 2 ? "interior" : "uncertain"),
      spaceAId: owners[0] || null,
      spaceBId: owners[1] || null,
      doorIds: existing?.doorIds || [],
      windowIds: existing?.windowIds || [],
      source: existing?.source || createSourceInfo({ type: "manual" }),
    });

    return wall;
  });

  return {
    walls,
    removedWallIds: existingWalls
      .map((wall) => wall.id)
      .filter((id) => !walls.some((wall) => wall.id === id)),
  };
}

export function translateExclusiveWallsForSpace(
  walls = [],
  spaceId,
  dx,
  dy,
) {
  const offsetX = Number(dx);
  const offsetY = Number(dy);

  if (!Number.isFinite(offsetX) || !Number.isFinite(offsetY)) {
    return walls.map((wall) => ({ ...wall }));
  }

  return walls.map((wall) => {
    const owners = [wall.spaceAId, wall.spaceBId].filter(Boolean);
    const isExclusive = owners.length === 1 && owners[0] === spaceId;

    if (!isExclusive) return { ...wall };

    return {
      ...wall,
      start: {
        x: Number(wall.start.x) + offsetX,
        y: Number(wall.start.y) + offsetY,
      },
      end: {
        x: Number(wall.end.x) + offsetX,
        y: Number(wall.end.y) + offsetY,
      },
    };
  });
}

export function updateSpaceWallRelations(spaces = [], walls = []) {
  const map = new Map(
    spaces.map((space) => [
      space.id,
      {
        ...space,
        wallIds: [],
      },
    ]),
  );

  for (const wall of walls) {
    for (const spaceId of [wall.spaceAId, wall.spaceBId]) {
      if (!spaceId || !map.has(spaceId)) continue;
      map.get(spaceId).wallIds.push(wall.id);
    }
  }

  return [...map.values()];
}

export function removeSpaceAndReconcile({
  spaces = [],
  walls = [],
  spaceId,
  levelId = null,
}) {
  const nextSpaces = spaces.filter((space) => space.id !== spaceId);
  const provisionalWalls = walls.filter((wall) => {
    const owners = [wall.spaceAId, wall.spaceBId].filter(Boolean);
    if (!owners.includes(spaceId)) return true;

    // Exclusivo del espacio eliminado → se elimina.
    if (owners.length === 1) return false;

    // Compartido → permanece y pierde la relación con el espacio eliminado.
    return true;
  }).map((wall) => ({
    ...wall,
    spaceAId: wall.spaceAId === spaceId ? null : wall.spaceAId,
    spaceBId: wall.spaceBId === spaceId ? null : wall.spaceBId,
  }));

  const reconciled = reconcileWallGraph({
    spaces: nextSpaces,
    existingWalls: provisionalWalls,
    levelId,
  });

  return {
    spaces: updateSpaceWallRelations(nextSpaces, reconciled.walls),
    walls: reconciled.walls,
    removedWallIds: reconciled.removedWallIds,
  };
}

export function wallContainsPoint(wall, point, epsilon = DEFAULT_EPSILON) {
  return pointOnSegment(point, wall.start, wall.end, epsilon);
}

export function wallContainsSegment(wall, start, end, epsilon = DEFAULT_EPSILON) {
  return (
    pointOnSegment(start, wall.start, wall.end, epsilon) &&
    pointOnSegment(end, wall.start, wall.end, epsilon)
  );
}

export function projectPointToWall(point, wall) {
  return closestPointOnSegment(point, wall.start, wall.end);
}

function collectSpaceEdges(spaces) {
  const result = [];

  for (const space of spaces) {
    const geometry = normalizeGeometry(space.geometry);
    if (!geometry) continue;

    for (const edge of buildEdges(geometry.vertices)) {
      if (edge.lengthM <= DEFAULT_EPSILON) continue;

      result.push({
        levelId: space.levelId,
        ownerId: space.id,
        start: edge.start,
        end: edge.end,
      });
    }
  }

  return result;
}

function splitEdgesAtSharedPoints(edges, epsilon) {
  const result = [];

  for (const edge of edges) {
    const points = [
      { ...edge.start },
      { ...edge.end },
    ];

    for (const other of edges) {
      if (other === edge || other.levelId !== edge.levelId) continue;

      for (const point of [other.start, other.end]) {
        if (
          pointOnSegment(point, edge.start, edge.end, epsilon) &&
          !points.some((candidate) => pointsEqual(candidate, point, epsilon))
        ) {
          points.push({ ...point });
        }
      }
    }

    const ordered = points
      .map((point) => ({
        point,
        t: closestPointOnSegment(point, edge.start, edge.end).t,
      }))
      .sort((a, b) => a.t - b.t);

    for (let i = 0; i < ordered.length - 1; i += 1) {
      const start = ordered[i].point;
      const end = ordered[i + 1].point;
      if (dist(start, end) <= epsilon) continue;

      result.push({
        levelId: edge.levelId,
        ownerId: edge.ownerId,
        start,
        end,
      });
    }
  }

  return result;
}

function groupEquivalentSegments(segments, epsilon) {
  const groups = [];

  for (const segment of segments) {
    let group = groups.find((candidate) =>
      sameUndirectedSegment(candidate, segment, epsilon),
    );

    if (!group) {
      group = {
        levelId: segment.levelId,
        start: { ...segment.start },
        end: { ...segment.end },
        owners: [],
      };
      groups.push(group);
    }

    group.owners.push(segment.ownerId);
  }

  return groups;
}

function sameUndirectedSegment(a, b, epsilon) {
  if (a.levelId !== b.levelId) return false;

  return (
    (
      pointsEqual(a.start, b.start, epsilon) &&
      pointsEqual(a.end, b.end, epsilon)
    ) ||
    (
      pointsEqual(a.start, b.end, epsilon) &&
      pointsEqual(a.end, b.start, epsilon)
    )
  );
}

function findBestExistingWall(
  segment,
  existingWalls,
  usedWallIds,
  epsilon,
) {
  const exact = existingWalls.find((wall) => (
    !usedWallIds.has(wall.id) &&
    wall.levelId === segment.levelId &&
    sameUndirectedSegment(wall, segment, epsilon)
  ));

  if (exact) return exact;

  return existingWalls.find((wall) => (
    !usedWallIds.has(wall.id) &&
    wall.levelId === segment.levelId &&
    wallContainsSegment(wall, segment.start, segment.end, epsilon)
  )) || null;
}
