import {
  DEFAULT_EDITOR_SETTINGS,
  DEFAULT_VIEWPORT,
} from "./editorDefaults";

export const EDITOR_SCHEMA_VERSION = "quantia-editor-1.0";
export const EDITOR_UNITS = "m";

export const CANONICAL_LEVEL_KEYS = Object.freeze([
  "planta_baja",
  "segunda_planta",
  "tercera_planta",
  "planta_azotea",
]);

export const SOURCE_TYPES = Object.freeze([
  "manual",
  "document",
  "ai",
  "rule",
  "import",
]);

export const SOURCE_STATES = Object.freeze([
  "DETECTADO",
  "INFERIDO",
  "NO_IDENTIFICADO",
  "CONFLICTO",
  "MANUAL",
]);

export const GEOMETRY_TYPES = Object.freeze(["rectangle", "polygon"]);
export const WALL_TYPES = Object.freeze(["exterior", "interior", "uncertain"]);

export function createEntityId(prefix = "entity") {
  const safePrefix = String(prefix || "entity")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_");

  const cryptoApi = globalThis?.crypto;
  if (cryptoApi?.randomUUID) {
    return `${safePrefix}_${cryptoApi.randomUUID()}`;
  }

  const random = Math.random().toString(36).slice(2, 10);
  return `${safePrefix}_${Date.now().toString(36)}_${random}`;
}

export function nowIso() {
  return new Date().toISOString();
}

export function createSourceInfo(overrides = {}) {
  const type = SOURCE_TYPES.includes(overrides.type)
    ? overrides.type
    : "manual";

  const state = SOURCE_STATES.includes(overrides.state)
    ? overrides.state
    : type === "manual"
      ? "MANUAL"
      : "NO_IDENTIFICADO";

  return {
    type,
    documentId: overrides.documentId ?? null,
    documentName: overrides.documentName ?? null,
    page: Number.isInteger(overrides.page) ? overrides.page : null,
    confidence: finiteOrNull(
      overrides.confidence,
    ),
    state,
    note: overrides.note ?? null,
  };
}

export function createEmptyValidation() {
  return {
    isValid: true,
    conflicts: [],
    warnings: [],
  };
}

export function createLevel(overrides = {}) {
  return {
    id: overrides.id || createEntityId("level"),
    key: String(overrides.key || "").trim(),
    name: String(overrides.name || "").trim(),
    order: Number.isInteger(overrides.order) ? overrides.order : 0,
    elevationM: finiteOrNull(overrides.elevationM),
    heightM: finiteOrNull(overrides.heightM),
    slabThicknessM: finiteOrNull(overrides.slabThicknessM),
    visible: overrides.visible !== false,
    locked: Boolean(overrides.locked),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
  };
}

export function createTerrain(overrides = {}) {
  return {
    id: overrides.id || createEntityId("terrain"),
    shape: overrides.shape === "polygon" ? "polygon" : "rectangle",
    geometry: overrides.geometry ?? null,
    widthM: finiteOrNull(overrides.widthM),
    lengthM: finiteOrNull(overrides.lengthM),
    orientationDeg: finiteOrNull(overrides.orientationDeg),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
  };
}

export function createSpace(overrides = {}) {
  return {
    finishes: cloneEditorState(overrides.finishes || []),
    intervention: overrides.intervention || "UNKNOWN",
    id: overrides.id || createEntityId("space"),
    name: String(overrides.name || "").trim(),
    usageCode: String(overrides.usageCode || "").trim(),
    usageLabel: String(overrides.usageLabel || "").trim(),
    category: String(overrides.category || "").trim(),
    levelId: String(overrides.levelId || "").trim(),
    geometry: overrides.geometry ?? null,
    areaM2: finiteOrZero(overrides.areaM2),
    perimeterM: finiteOrZero(overrides.perimeterM),
    doubleHeight: Boolean(overrides.doubleHeight),
    heightM: finiteOrNull(overrides.heightM),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
    wallIds: uniqueStrings(overrides.wallIds),
    doorIds: uniqueStrings(overrides.doorIds),
    windowIds: uniqueStrings(overrides.windowIds),
    validation: normalizeValidation(overrides.validation),
  };
}

export function createWall(overrides = {}) {
  return {
    material: overrides.material || "UNKNOWN",
    structuralRole: overrides.structuralRole || (overrides.loadBearing === true ? "LOAD_BEARING" : overrides.loadBearing === false ? "PARTITION" : "UNKNOWN"),
    finishes: cloneEditorState(overrides.finishes || []),
    id: overrides.id || createEntityId("wall"),
    levelId: String(overrides.levelId || "").trim(),
    start: normalizePoint(overrides.start),
    end: normalizePoint(overrides.end),
    lengthM: finiteOrZero(overrides.lengthM),
    thicknessM: finiteOrNull(overrides.thicknessM),
    heightM: finiteOrNull(overrides.heightM),
    type: WALL_TYPES.includes(overrides.type)
      ? overrides.type
      : "uncertain",
    spaceAId: overrides.spaceAId || null,
    spaceBId: overrides.spaceBId || null,
    doorIds: uniqueStrings(overrides.doorIds),
    windowIds: uniqueStrings(overrides.windowIds),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
    validation: normalizeValidation(overrides.validation),
  };
}

export function createDoor(overrides = {}) {
  return {
    kind: overrides.kind === "GARAGE_DOOR" ? "GARAGE_DOOR" : "DOOR",
    usage: overrides.usage || "UNKNOWN",
    material: overrides.material || "UNKNOWN",
    operation: overrides.operation || "UNKNOWN",
    glazing: overrides.glazing || "UNKNOWN",
    leafCount: finiteOrNull(overrides.leafCount),
    id: overrides.id || createEntityId("door"),
    levelId: String(overrides.levelId || "").trim(),
    wallId: String(overrides.wallId || "").trim(),
    position: finiteOrNull(overrides.position),
    widthM: finiteOrNull(overrides.widthM),
    heightM: finiteOrNull(overrides.heightM),
    swingDirection: overrides.swingDirection || "unknown",
    flipSide: Boolean(overrides.flipSide),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
    validation: normalizeValidation(overrides.validation),
  };
}

export function createWindow(overrides = {}) {
  return {
    kind: "WINDOW",
    material: overrides.material || "UNKNOWN",
    operation: overrides.operation || "UNKNOWN",
    glazing: overrides.glazing || "UNKNOWN",
    id: overrides.id || createEntityId("window"),
    levelId: String(overrides.levelId || "").trim(),
    wallId: String(overrides.wallId || "").trim(),
    position: finiteOrNull(overrides.position),
    widthM: finiteOrNull(overrides.widthM),
    heightM: finiteOrNull(overrides.heightM),
    sillHeightM: finiteOrNull(overrides.sillHeightM),
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
    validation: normalizeValidation(overrides.validation),
  };
}

export function createStair(overrides = {}) {
  return {
    hasSlabVoid: Boolean(overrides.hasSlabVoid),
    railingSide: overrides.railingSide || "UNKNOWN",
    railingMaterial: overrides.railingMaterial || "UNKNOWN",
    system: overrides.system || "UNKNOWN",
    flights: cloneEditorState(overrides.flights || []),
    landings: cloneEditorState(overrides.landings || []),
    slabVoidIds: uniqueStrings(overrides.slabVoidIds),
    railingIds: uniqueStrings(overrides.railingIds),
    id: overrides.id || createEntityId("stair"),
    levelFromId: String(overrides.levelFromId || "").trim(),
    levelToId: String(overrides.levelToId || "").trim(),
    position: normalizePoint(overrides.position),
    rotationDeg: finiteOrZero(overrides.rotationDeg),
    widthM: finiteOrNull(overrides.widthM),
    geometry: overrides.geometry ?? null,
    type: overrides.type || "unknown",
    confirmed: Boolean(overrides.confirmed),
    source: createSourceInfo(overrides.source),
  };
}

export function createAnnotation(overrides = {}) {
  return {
    id: overrides.id || createEntityId("annotation"),
    levelId: String(overrides.levelId || "").trim(),
    position: normalizePoint(overrides.position),
    text: String(overrides.text || ""),
    linkedEntityType: overrides.linkedEntityType || null,
    linkedEntityId: overrides.linkedEntityId || null,
  };
}

export function createEmptyEditorState(overrides = {}) {
  const timestamp = nowIso();

  return {
    schemaVersion: EDITOR_SCHEMA_VERSION,
    projectId: overrides.projectId ?? null,
    units: EDITOR_UNITS,
    activeLevelId: overrides.activeLevelId ?? null,
    viewport: {
      ...DEFAULT_VIEWPORT,
      ...(overrides.viewport || {}),
    },
    editorSettings: {
      ...DEFAULT_EDITOR_SETTINGS,
      ...(overrides.editorSettings || {}),
    },
    terrain: overrides.terrain ?? null,
    levels: Array.isArray(overrides.levels) ? overrides.levels : [],
    spaces: Array.isArray(overrides.spaces) ? overrides.spaces : [],
    walls: Array.isArray(overrides.walls) ? overrides.walls : [],
    doors: Array.isArray(overrides.doors) ? overrides.doors : [],
    windows: Array.isArray(overrides.windows) ? overrides.windows : [],
    stairs: Array.isArray(overrides.stairs) ? overrides.stairs : [],
    elements: cloneEditorState(overrides.elements || []),
    completeness: { ...(overrides.completeness || {}) },
    annotations: Array.isArray(overrides.annotations)
      ? overrides.annotations
      : [],
    validation: {
      isValid: true,
      conflicts: [],
      warnings: [],
      lastValidatedAt: null,
      ...(overrides.validation || {}),
    },
    metadata: {
      sourceMode: overrides.metadata?.sourceMode === "plan"
        ? "plan"
        : "manual",
      createdAt: overrides.metadata?.createdAt || timestamp,
      updatedAt: overrides.metadata?.updatedAt || timestamp,
    },
  };
}

export function cloneEditorState(value) {
  return clonePlainValue(
    value,
    new WeakMap(),
  );
}

function clonePlainValue(
  value,
  seen,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return value;
  }

  const valueType =
    typeof value;

  if (
    valueType === "string" ||
    valueType === "number" ||
    valueType === "boolean" ||
    valueType === "bigint"
  ) {
    return value;
  }

  if (
    valueType === "function" ||
    valueType === "symbol"
  ) {
    return undefined;
  }

  if (
    value instanceof Date
  ) {
    return new Date(
      value.getTime(),
    );
  }

  if (
    value instanceof RegExp
  ) {
    return new RegExp(
      value.source,
      value.flags,
    );
  }

  if (
    seen.has(value)
  ) {
    return seen.get(value);
  }

  if (
    Array.isArray(value)
  ) {
    const output = [];
    seen.set(
      value,
      output,
    );

    for (
      const item of value
    ) {
      output.push(
        clonePlainValue(
          item,
          seen,
        ),
      );
    }

    return output;
  }

  // El estado puede venir de Pinia/Vue como Proxy reactivo.
  // Leer sus propiedades una a una produce un objeto plano clonable
  // sin depender de Vue ni de toRaw().
  const output = {};
  seen.set(
    value,
    output,
  );

  for (
    const key of Object.keys(value)
  ) {
    const cloned =
      clonePlainValue(
        value[key],
        seen,
      );

    if (
      cloned !== undefined
    ) {
      output[key] =
        cloned;
    }
  }

  return output;
}

function normalizePoint(value) {
  return {
    x: Number.isFinite(Number(value?.x)) ? Number(value.x) : 0,
    y: Number.isFinite(Number(value?.y)) ? Number(value.y) : 0,
  };
}

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function finiteOrZero(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function uniqueStrings(value) {
  if (!Array.isArray(value)) return [];
  return [...new Set(
    value
      .map((item) => String(item || "").trim())
      .filter(Boolean),
  )];
}

function normalizeValidation(value) {
  return {
    ...createEmptyValidation(),
    ...(value || {}),
    conflicts: Array.isArray(value?.conflicts) ? value.conflicts : [],
    warnings: Array.isArray(value?.warnings) ? value.warnings : [],
  };
}
