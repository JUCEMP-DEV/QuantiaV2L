import {
  closestPointOnSegment,
  dist,
  pointIsFinite,
} from "./geometry";

export function snapToGrid(point, gridSizeM) {
  const size = Number(gridSizeM);
  if (!pointIsFinite(point) || !Number.isFinite(size) || size <= 0) {
    return null;
  }

  return {
    x: Math.round(Number(point.x) / size) * size,
    y: Math.round(Number(point.y) / size) * size,
  };
}

export function snapToVertices(point, vertices = [], toleranceM) {
  const tolerance = Number(toleranceM);
  if (!pointIsFinite(point) || !Number.isFinite(tolerance) || tolerance < 0) {
    return null;
  }

  let best = null;

  for (const candidate of vertices) {
    if (!pointIsFinite(candidate)) continue;
    const distance = dist(point, candidate);

    if (distance <= tolerance && (!best || distance < best.distanceM)) {
      best = {
        applied: true,
        type: "vertex",
        point: { x: Number(candidate.x), y: Number(candidate.y) },
        distanceM: distance,
        targetEntityId: candidate.entityId ?? candidate.id ?? null,
      };
    }
  }

  return best;
}

export function snapToEdges(point, edges = [], toleranceM) {
  const tolerance = Number(toleranceM);
  if (!pointIsFinite(point) || !Number.isFinite(tolerance) || tolerance < 0) {
    return null;
  }

  let best = null;

  for (const edge of edges) {
    if (!pointIsFinite(edge?.start) || !pointIsFinite(edge?.end)) continue;

    const closest = closestPointOnSegment(point, edge.start, edge.end);
    const distance = dist(point, closest);

    if (distance <= tolerance && (!best || distance < best.distanceM)) {
      best = {
        applied: true,
        type: "edge",
        point: { x: closest.x, y: closest.y },
        distanceM: distance,
        t: closest.t,
        targetEntityId: edge.entityId ?? edge.id ?? null,
      };
    }
  }

  return best;
}

export function snapOrthogonal(point, anchor, toleranceM) {
  const tolerance = Number(toleranceM);
  if (
    !pointIsFinite(point) ||
    !pointIsFinite(anchor) ||
    !Number.isFinite(tolerance) ||
    tolerance < 0
  ) {
    return null;
  }

  const dx = Math.abs(Number(point.x) - Number(anchor.x));
  const dy = Math.abs(Number(point.y) - Number(anchor.y));

  if (dx <= tolerance && dx <= dy) {
    return {
      applied: true,
      type: "vertical",
      point: { x: Number(anchor.x), y: Number(point.y) },
      distanceM: dx,
      targetEntityId: null,
    };
  }

  if (dy <= tolerance) {
    return {
      applied: true,
      type: "horizontal",
      point: { x: Number(point.x), y: Number(anchor.y) },
      distanceM: dy,
      targetEntityId: null,
    };
  }

  return null;
}

export function snapAngle(point, anchor, incrementDeg) {
  if (!pointIsFinite(point) || !pointIsFinite(anchor)) return null;

  const increment = Number(incrementDeg);
  if (!Number.isFinite(increment) || increment <= 0 || increment > 180) {
    return null;
  }

  const dx = Number(point.x) - Number(anchor.x);
  const dy = Number(point.y) - Number(anchor.y);
  const radius = Math.hypot(dx, dy);
  if (radius === 0) return { ...point };

  const angle = Math.atan2(dy, dx);
  const step = (increment * Math.PI) / 180;
  const snappedAngle = Math.round(angle / step) * step;

  return {
    x: Number(anchor.x) + Math.cos(snappedAngle) * radius,
    y: Number(anchor.y) + Math.sin(snappedAngle) * radius,
  };
}

/**
 * Convierte una tolerancia visual a metros.
 * El caller debe proporcionar pixelsPerMeter y zoom reales del viewport.
 */
export function worldToleranceFromScreen({
  screenTolerancePx,
  pixelsPerMeter,
  zoom,
}) {
  const px = Number(screenTolerancePx);
  const ppm = Number(pixelsPerMeter);
  const scale = Number(zoom);

  if (
    !Number.isFinite(px) ||
    !Number.isFinite(ppm) ||
    !Number.isFinite(scale) ||
    px < 0 ||
    ppm <= 0 ||
    scale <= 0
  ) {
    return null;
  }

  return px / (ppm * scale);
}

/**
 * Orden canónico:
 * 1) vértice
 * 2) arista
 * 3) ortogonal
 * 4) grid
 */
export function resolveSnap({
  point,
  vertices = [],
  edges = [],
  anchor = null,
  toleranceM,
  gridSizeM,
  enableVertices = true,
  enableEdges = true,
  enableOrthogonal = true,
  enableGrid = true,
}) {
  if (!pointIsFinite(point)) {
    return {
      applied: false,
      type: "none",
      point: null,
      targetEntityId: null,
    };
  }

  if (enableVertices) {
    const result = snapToVertices(point, vertices, toleranceM);
    if (result) return result;
  }

  if (enableEdges) {
    const result = snapToEdges(point, edges, toleranceM);
    if (result) return result;
  }

  if (enableOrthogonal && anchor) {
    const result = snapOrthogonal(point, anchor, toleranceM);
    if (result) return result;
  }

  if (enableGrid) {
    const snapped = snapToGrid(point, gridSizeM);
    if (snapped) {
      return {
        applied: true,
        type: "grid",
        point: snapped,
        targetEntityId: null,
      };
    }
  }

  return {
    applied: false,
    type: "none",
    point: { x: Number(point.x), y: Number(point.y) },
    targetEntityId: null,
  };
}
