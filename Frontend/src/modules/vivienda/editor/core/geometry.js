const DEFAULT_EPSILON = 1e-9;

export function isFiniteNumber(value) {
  return Number.isFinite(Number(value));
}

export function normalizePoint(point) {
  return {
    x: Number(point?.x),
    y: Number(point?.y),
  };
}

export function pointIsFinite(point) {
  return isFiniteNumber(point?.x) && isFiniteNumber(point?.y);
}

export function almostEqual(a, b, epsilon = DEFAULT_EPSILON) {
  return Math.abs(Number(a) - Number(b)) <= epsilon;
}

export function pointsEqual(a, b, epsilon = DEFAULT_EPSILON) {
  return (
    pointIsFinite(a) &&
    pointIsFinite(b) &&
    almostEqual(a.x, b.x, epsilon) &&
    almostEqual(a.y, b.y, epsilon)
  );
}

export function dist2(a, b) {
  const dx = Number(b.x) - Number(a.x);
  const dy = Number(b.y) - Number(a.y);
  return dx * dx + dy * dy;
}

export function dist(a, b) {
  return Math.sqrt(dist2(a, b));
}

export function midpoint(a, b) {
  return {
    x: (Number(a.x) + Number(b.x)) / 2,
    y: (Number(a.y) + Number(b.y)) / 2,
  };
}

export function segmentLength(a, b) {
  return dist(a, b);
}

export function segmentAngle(a, b) {
  return Math.atan2(Number(b.y) - Number(a.y), Number(b.x) - Number(a.x));
}

export function segmentNormal(a, b) {
  const length = segmentLength(a, b);
  if (length <= DEFAULT_EPSILON) return { x: 0, y: 0 };

  return {
    x: -(Number(b.y) - Number(a.y)) / length,
    y: (Number(b.x) - Number(a.x)) / length,
  };
}

export function closestPointOnSegment(point, start, end) {
  const ax = Number(start.x);
  const ay = Number(start.y);
  const bx = Number(end.x);
  const by = Number(end.y);
  const px = Number(point.x);
  const py = Number(point.y);

  const dx = bx - ax;
  const dy = by - ay;
  const denom = dx * dx + dy * dy;

  if (denom <= DEFAULT_EPSILON) {
    return { x: ax, y: ay, t: 0 };
  }

  const rawT = ((px - ax) * dx + (py - ay) * dy) / denom;
  const t = Math.max(0, Math.min(1, rawT));

  return {
    x: ax + dx * t,
    y: ay + dy * t,
    t,
  };
}

export function distToSegment(point, start, end) {
  const closest = closestPointOnSegment(point, start, end);
  return dist(point, closest);
}

export function pointOnSegment(point, start, end, epsilon = 1e-8) {
  if (![point, start, end].every(pointIsFinite)) return false;
  return distToSegment(point, start, end) <= epsilon;
}

export function signedPolygonArea(vertices = []) {
  if (!Array.isArray(vertices) || vertices.length < 3) return 0;

  let sum = 0;
  for (let i = 0; i < vertices.length; i += 1) {
    const a = vertices[i];
    const b = vertices[(i + 1) % vertices.length];
    sum += Number(a.x) * Number(b.y) - Number(b.x) * Number(a.y);
  }

  return sum / 2;
}

export function polygonArea(vertices = []) {
  return Math.abs(signedPolygonArea(vertices));
}

export function polygonPerimeter(vertices = []) {
  if (!Array.isArray(vertices) || vertices.length < 2) return 0;

  let sum = 0;
  for (let i = 0; i < vertices.length; i += 1) {
    sum += dist(vertices[i], vertices[(i + 1) % vertices.length]);
  }
  return sum;
}

export function polygonCentroid(vertices = []) {
  if (!Array.isArray(vertices) || vertices.length < 3) {
    return averagePoint(vertices);
  }

  const area2 = signedPolygonArea(vertices) * 2;
  if (Math.abs(area2) <= DEFAULT_EPSILON) {
    return averagePoint(vertices);
  }

  let cx = 0;
  let cy = 0;

  for (let i = 0; i < vertices.length; i += 1) {
    const a = vertices[i];
    const b = vertices[(i + 1) % vertices.length];
    const cross = Number(a.x) * Number(b.y) - Number(b.x) * Number(a.y);
    cx += (Number(a.x) + Number(b.x)) * cross;
    cy += (Number(a.y) + Number(b.y)) * cross;
  }

  return {
    x: cx / (3 * area2),
    y: cy / (3 * area2),
  };
}

export function boundingBox(vertices = []) {
  const valid = vertices.filter(pointIsFinite);
  if (!valid.length) {
    return {
      minX: 0,
      minY: 0,
      maxX: 0,
      maxY: 0,
      width: 0,
      height: 0,
    };
  }

  const xs = valid.map((point) => Number(point.x));
  const ys = valid.map((point) => Number(point.y));
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const maxX = Math.max(...xs);
  const maxY = Math.max(...ys);

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

export function verticesFromRect({ x, y, widthM, lengthM }) {
  const x0 = Number(x);
  const y0 = Number(y);
  const width = Number(widthM);
  const length = Number(lengthM);

  if (
    ![x0, y0, width, length].every(Number.isFinite) ||
    width <= 0 ||
    length <= 0
  ) {
    return [];
  }

  return [
    { x: x0, y: y0 },
    { x: x0 + width, y: y0 },
    { x: x0 + width, y: y0 + length },
    { x: x0, y: y0 + length },
  ];
}

export function rectFromXYWH({ x, y, widthM, lengthM }) {
  const vertices = verticesFromRect({ x, y, widthM, lengthM });
  return geometryFromVertices(vertices, {
    type: "rectangle",
    x: Number(x),
    y: Number(y),
    widthM: Number(widthM),
    lengthM: Number(lengthM),
  });
}

export function geometryFromVertices(vertices = [], options = {}) {
  const normalized = vertices
    .filter(pointIsFinite)
    .map((point) => ({ x: Number(point.x), y: Number(point.y) }));

  const bbox = boundingBox(normalized);
  const type = options.type === "rectangle" ? "rectangle" : "polygon";

  return {
    type,
    ...(type === "rectangle"
      ? {
          x: Number.isFinite(Number(options.x)) ? Number(options.x) : bbox.minX,
          y: Number.isFinite(Number(options.y)) ? Number(options.y) : bbox.minY,
          widthM: Number.isFinite(Number(options.widthM))
            ? Number(options.widthM)
            : bbox.width,
          lengthM: Number.isFinite(Number(options.lengthM))
            ? Number(options.lengthM)
            : bbox.height,
        }
      : {}),
    vertices: normalized,
    edges: buildEdges(normalized),
    areaM2: polygonArea(normalized),
    perimeterM: polygonPerimeter(normalized),
    bbox,
  };
}

export function normalizeGeometry(geometry) {
  if (!geometry || typeof geometry !== "object") return null;

  if (geometry.type === "rectangle") {
    const rect = rectFromXYWH({
      x: geometry.x,
      y: geometry.y,
      widthM: geometry.widthM,
      lengthM: geometry.lengthM,
    });

    if (rect.vertices.length === 4) return rect;
  }

  return geometryFromVertices(geometry.vertices || [], {
    type: "polygon",
  });
}

export function translateGeometry(geometry, dx, dy) {
  const offsetX = Number(dx);
  const offsetY = Number(dy);

  if (!Number.isFinite(offsetX) || !Number.isFinite(offsetY)) {
    return normalizeGeometry(geometry);
  }

  const normalized = normalizeGeometry(geometry);
  if (!normalized) return null;

  if (normalized.type === "rectangle") {
    return rectFromXYWH({
      x: normalized.x + offsetX,
      y: normalized.y + offsetY,
      widthM: normalized.widthM,
      lengthM: normalized.lengthM,
    });
  }

  return geometryFromVertices(
    normalized.vertices.map((point) => ({
      x: point.x + offsetX,
      y: point.y + offsetY,
    })),
    { type: "polygon" },
  );
}

export function buildEdges(vertices = []) {
  if (!Array.isArray(vertices) || vertices.length < 2) return [];

  return vertices.map((point, index) => {
    const nextIndex = (index + 1) % vertices.length;
    const next = vertices[nextIndex];

    return {
      id: `edge_${index}`,
      startVertexIndex: index,
      endVertexIndex: nextIndex,
      start: { x: Number(point.x), y: Number(point.y) },
      end: { x: Number(next.x), y: Number(next.y) },
      lengthM: dist(point, next),
    };
  });
}

export function orientation(a, b, c, epsilon = DEFAULT_EPSILON) {
  const value =
    (Number(b.x) - Number(a.x)) * (Number(c.y) - Number(a.y)) -
    (Number(b.y) - Number(a.y)) * (Number(c.x) - Number(a.x));

  if (Math.abs(value) <= epsilon) return 0;
  return value > 0 ? 1 : -1;
}

export function segmentIntersection(a1, a2, b1, b2, epsilon = 1e-9) {
  const x1 = Number(a1.x);
  const y1 = Number(a1.y);
  const x2 = Number(a2.x);
  const y2 = Number(a2.y);
  const x3 = Number(b1.x);
  const y3 = Number(b1.y);
  const x4 = Number(b2.x);
  const y4 = Number(b2.y);

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);

  if (Math.abs(denom) <= epsilon) {
    return null;
  }

  const t =
    ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
  const u =
    -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom;

  if (t < -epsilon || t > 1 + epsilon || u < -epsilon || u > 1 + epsilon) {
    return null;
  }

  return {
    x: x1 + t * (x2 - x1),
    y: y1 + t * (y2 - y1),
    t,
    u,
  };
}

export function segmentsIntersect(a1, a2, b1, b2, epsilon = 1e-9) {
  const o1 = orientation(a1, a2, b1, epsilon);
  const o2 = orientation(a1, a2, b2, epsilon);
  const o3 = orientation(b1, b2, a1, epsilon);
  const o4 = orientation(b1, b2, a2, epsilon);

  if (o1 !== o2 && o3 !== o4) return true;

  if (o1 === 0 && pointOnSegment(b1, a1, a2, epsilon)) return true;
  if (o2 === 0 && pointOnSegment(b2, a1, a2, epsilon)) return true;
  if (o3 === 0 && pointOnSegment(a1, b1, b2, epsilon)) return true;
  if (o4 === 0 && pointOnSegment(a2, b1, b2, epsilon)) return true;

  return false;
}

export function segmentsProperlyIntersect(a1, a2, b1, b2, epsilon = 1e-9) {
  const hit = segmentIntersection(a1, a2, b1, b2, epsilon);
  if (!hit) return false;

  return (
    hit.t > epsilon &&
    hit.t < 1 - epsilon &&
    hit.u > epsilon &&
    hit.u < 1 - epsilon
  );
}

export function polygonSelfIntersects(vertices = [], epsilon = 1e-9) {
  if (vertices.length < 4) return false;

  for (let i = 0; i < vertices.length; i += 1) {
    const a1 = vertices[i];
    const a2 = vertices[(i + 1) % vertices.length];

    for (let j = i + 1; j < vertices.length; j += 1) {
      const nextI = (i + 1) % vertices.length;
      const nextJ = (j + 1) % vertices.length;

      if (i === j || nextI === j || nextJ === i) continue;
      if (i === 0 && nextJ === 0) continue;

      const b1 = vertices[j];
      const b2 = vertices[nextJ];

      if (segmentsIntersect(a1, a2, b1, b2, epsilon)) return true;
    }
  }

  return false;
}

export function pointInPolygon(point, vertices = [], includeBoundary = true) {
  if (!pointIsFinite(point) || vertices.length < 3) return false;

  if (
    includeBoundary &&
    buildEdges(vertices).some((edge) =>
      pointOnSegment(point, edge.start, edge.end, 1e-8))
  ) {
    return true;
  }

  let inside = false;

  for (let i = 0, j = vertices.length - 1; i < vertices.length; j = i++) {
    const xi = Number(vertices[i].x);
    const yi = Number(vertices[i].y);
    const xj = Number(vertices[j].x);
    const yj = Number(vertices[j].y);
    const px = Number(point.x);
    const py = Number(point.y);

    const intersects =
      yi > py !== yj > py &&
      px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;

    if (intersects) inside = !inside;
  }

  return inside;
}

export function polygonContainsPolygon(container, candidate) {
  if (!Array.isArray(container) || !Array.isArray(candidate)) return false;
  if (container.length < 3 || candidate.length < 3) return false;

  if (!candidate.every((point) => pointInPolygon(point, container, true))) {
    return false;
  }

  const containerEdges = buildEdges(container);
  const candidateEdges = buildEdges(candidate);

  for (const a of candidateEdges) {
    for (const b of containerEdges) {
      if (segmentsProperlyIntersect(a.start, a.end, b.start, b.end)) {
        return false;
      }
    }
  }

  return true;
}

/**
 * Determina solape interior con área positiva.
 * El contacto por punto o borde NO cuenta como solape.
 */
export function polygonsOverlapInterior(a, b, epsilon = 1e-9) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length < 3 || b.length < 3) {
    return false;
  }

  if (polygonSelfIntersects(a, epsilon) || polygonSelfIntersects(b, epsilon)) {
    return false;
  }

  const trianglesA = triangulatePolygon(a, epsilon);
  const trianglesB = triangulatePolygon(b, epsilon);

  for (const triA of trianglesA) {
    for (const triB of trianglesB) {
      const clipped = clipConvexPolygon(triA, triB, epsilon);
      if (polygonArea(clipped) > epsilon) return true;
    }
  }

  return false;
}

export function triangulatePolygon(vertices = [], epsilon = 1e-9) {
  const polygon = vertices
    .filter(pointIsFinite)
    .map((point) => ({ x: Number(point.x), y: Number(point.y) }));

  if (polygon.length < 3) return [];
  if (polygon.length === 3) return [polygon];

  const ccw = signedPolygonArea(polygon) > 0;
  const indices = polygon.map((_, index) => index);
  const triangles = [];
  let guard = 0;

  while (indices.length > 3 && guard < polygon.length * polygon.length) {
    guard += 1;
    let earFound = false;

    for (let i = 0; i < indices.length; i += 1) {
      const prevIndex = indices[(i - 1 + indices.length) % indices.length];
      const currIndex = indices[i];
      const nextIndex = indices[(i + 1) % indices.length];

      const a = polygon[prevIndex];
      const b = polygon[currIndex];
      const c = polygon[nextIndex];

      const turn = orientation(a, b, c, epsilon);
      if ((ccw && turn <= 0) || (!ccw && turn >= 0)) continue;

      const containsOther = indices.some((index) => {
        if ([prevIndex, currIndex, nextIndex].includes(index)) return false;
        return pointInTriangle(polygon[index], a, b, c, epsilon);
      });

      if (containsOther) continue;

      triangles.push([a, b, c]);
      indices.splice(i, 1);
      earFound = true;
      break;
    }

    if (!earFound) break;
  }

  if (indices.length === 3) {
    triangles.push(indices.map((index) => polygon[index]));
  }

  return triangles;
}

export function clipConvexPolygon(subject, clip, epsilon = 1e-9) {
  let output = subject.map((point) => ({ ...point }));
  if (!output.length || clip.length < 3) return [];

  const clipIsCcw = signedPolygonArea(clip) >= 0;

  for (let i = 0; i < clip.length; i += 1) {
    const a = clip[i];
    const b = clip[(i + 1) % clip.length];
    const input = output;
    output = [];
    if (!input.length) break;

    let previous = input[input.length - 1];

    for (const current of input) {
      const currentInside = isInsideHalfPlane(
        current,
        a,
        b,
        clipIsCcw,
        epsilon,
      );
      const previousInside = isInsideHalfPlane(
        previous,
        a,
        b,
        clipIsCcw,
        epsilon,
      );

      if (currentInside) {
        if (!previousInside) {
          const intersection = infiniteLineIntersection(previous, current, a, b);
          if (intersection) output.push(intersection);
        }
        output.push(current);
      } else if (previousInside) {
        const intersection = infiniteLineIntersection(previous, current, a, b);
        if (intersection) output.push(intersection);
      }

      previous = current;
    }
  }

  return output;
}

function pointInTriangle(point, a, b, c, epsilon) {
  const o1 = orientation(a, b, point, epsilon);
  const o2 = orientation(b, c, point, epsilon);
  const o3 = orientation(c, a, point, epsilon);

  const hasPositive = o1 > 0 || o2 > 0 || o3 > 0;
  const hasNegative = o1 < 0 || o2 < 0 || o3 < 0;

  return !(hasPositive && hasNegative);
}

function isInsideHalfPlane(point, a, b, clipIsCcw, epsilon) {
  const cross =
    (Number(b.x) - Number(a.x)) * (Number(point.y) - Number(a.y)) -
    (Number(b.y) - Number(a.y)) * (Number(point.x) - Number(a.x));

  return clipIsCcw ? cross >= -epsilon : cross <= epsilon;
}

function infiniteLineIntersection(p1, p2, q1, q2) {
  const x1 = Number(p1.x);
  const y1 = Number(p1.y);
  const x2 = Number(p2.x);
  const y2 = Number(p2.y);
  const x3 = Number(q1.x);
  const y3 = Number(q1.y);
  const x4 = Number(q2.x);
  const y4 = Number(q2.y);

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (Math.abs(denom) <= DEFAULT_EPSILON) return null;

  const det1 = x1 * y2 - y1 * x2;
  const det2 = x3 * y4 - y3 * x4;

  return {
    x: (det1 * (x3 - x4) - (x1 - x2) * det2) / denom,
    y: (det1 * (y3 - y4) - (y1 - y2) * det2) / denom,
  };
}

function averagePoint(vertices = []) {
  if (!vertices.length) return { x: 0, y: 0 };

  const total = vertices.reduce(
    (acc, point) => ({
      x: acc.x + Number(point.x || 0),
      y: acc.y + Number(point.y || 0),
    }),
    { x: 0, y: 0 },
  );

  return {
    x: total.x / vertices.length,
    y: total.y / vertices.length,
  };
}
