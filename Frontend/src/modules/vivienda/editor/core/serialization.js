import {
  EDITOR_SCHEMA_VERSION,
  createEmptyEditorState,
  cloneEditorState,
  nowIso,
} from "./editorSchema";
import {
  normalizeGeometry,
  segmentLength,
} from "./geometry";
import { validateReadyForCalculation } from "./constraints";

export function exportEditorState(state, options = {}) {
  const normalized = normalizeEditorState(state);

  return {
    schemaVersion: EDITOR_SCHEMA_VERSION,
    exportedAt: nowIso(),
    project: normalized,
    ...(options.includeValidation === true
      ? { readiness: validateReadyForCalculation(normalized) }
      : {}),
  };
}

export function exportEditorStateJson(state, options = {}) {
  return JSON.stringify(
    exportEditorState(state, options),
    null,
    options.pretty === false ? 0 : 2,
  );
}

export function importEditorState(input) {
  let parsed = input;

  if (typeof input === "string") {
    try {
      parsed = JSON.parse(input);
    } catch (error) {
      return {
        ok: false,
        state: null,
        errors: [`JSON inválido: ${error.message}`],
      };
    }
  }

  const project = parsed?.project || parsed;
  const validation = validateSerializedState(project);

  if (!validation.isValid) {
    return {
      ok: false,
      state: null,
      errors: validation.errors,
    };
  }

  return {
    ok: true,
    state: normalizeEditorState(project),
    errors: [],
  };
}

export function validateSerializedState(state) {
  const errors = [];

  if (!state || typeof state !== "object") {
    return {
      isValid: false,
      errors: ["El estado del editor debe ser un objeto."],
    };
  }

  if (state.schemaVersion !== EDITOR_SCHEMA_VERSION) {
    errors.push(
      `Versión incompatible: se esperaba ${EDITOR_SCHEMA_VERSION}.`,
    );
  }

  const arrays = [
    "levels",
    "spaces",
    "walls",
    "doors",
    "windows",
    "stairs",
    "annotations",
  ];

  for (const key of arrays) {
    if (!Array.isArray(state[key])) {
      errors.push(`El campo ${key} debe ser un arreglo.`);
    }
  }

  const allEntities = arrays.flatMap((key) =>
    Array.isArray(state[key]) ? state[key] : [],
  );

  const ids = new Set();
  for (const entity of allEntities) {
    if (!entity?.id) {
      errors.push("Se encontró una entidad sin id.");
      continue;
    }
    if (ids.has(entity.id)) {
      errors.push(`ID duplicado: ${entity.id}.`);
    }
    ids.add(entity.id);
  }

  const levelIds = new Set((state.levels || []).map((item) => item.id));
  const wallIds = new Set((state.walls || []).map((item) => item.id));
  const spaceIds = new Set((state.spaces || []).map((item) => item.id));

  for (const space of state.spaces || []) {
    if (!levelIds.has(space.levelId)) {
      errors.push(`Espacio ${space.id} referencia un levelId inexistente.`);
    }
    const geometry = normalizeGeometry(space.geometry);
    if (!geometry || geometry.vertices.length < 3) {
      errors.push(`Espacio ${space.id} tiene geometría inválida.`);
    }
  }

  for (const wall of state.walls || []) {
    if (!levelIds.has(wall.levelId)) {
      errors.push(`Muro ${wall.id} referencia un levelId inexistente.`);
    }
    if (wall.spaceAId && !spaceIds.has(wall.spaceAId)) {
      errors.push(`Muro ${wall.id} referencia spaceAId inexistente.`);
    }
    if (wall.spaceBId && !spaceIds.has(wall.spaceBId)) {
      errors.push(`Muro ${wall.id} referencia spaceBId inexistente.`);
    }
  }

  for (const door of state.doors || []) {
    validateOpeningReference(door, "Puerta", levelIds, wallIds, errors);
  }

  for (const window of state.windows || []) {
    validateOpeningReference(window, "Ventana", levelIds, wallIds, errors);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function normalizeEditorState(state) {
  const base = createEmptyEditorState(state || {});
  const normalized = cloneEditorState(base);

  normalized.schemaVersion = EDITOR_SCHEMA_VERSION;

  normalized.spaces = (state?.spaces || []).map((space) => {
    const geometry = normalizeGeometry(space.geometry);

    return {
      ...space,
      geometry,
      areaM2: geometry?.areaM2 ?? 0,
      perimeterM: geometry?.perimeterM ?? 0,
      wallIds: uniqueStrings(space.wallIds),
      doorIds: uniqueStrings(space.doorIds),
      windowIds: uniqueStrings(space.windowIds),
    };
  });

  normalized.walls = (state?.walls || []).map((wall) => ({
    ...wall,
    lengthM: wall?.start && wall?.end
      ? segmentLength(wall.start, wall.end)
      : 0,
    doorIds: uniqueStrings(wall.doorIds),
    windowIds: uniqueStrings(wall.windowIds),
  }));

  normalized.doors = (state?.doors || []).map((door) => ({
    ...door,
    position: finiteOrNull(door.position),
    widthM: finiteOrNull(door.widthM),
    heightM: finiteOrNull(door.heightM),
  }));

  normalized.windows = (state?.windows || []).map((window) => ({
    ...window,
    position: finiteOrNull(window.position),
    widthM: finiteOrNull(window.widthM),
    heightM: finiteOrNull(window.heightM),
    sillHeightM: finiteOrNull(window.sillHeightM),
  }));

  normalized.metadata = {
    ...normalized.metadata,
    updatedAt: nowIso(),
  };

  return normalized;
}

function validateOpeningReference(
  opening,
  label,
  levelIds,
  wallIds,
  errors,
) {
  if (!levelIds.has(opening.levelId)) {
    errors.push(`${label} ${opening.id} referencia un levelId inexistente.`);
  }

  if (!wallIds.has(opening.wallId)) {
    errors.push(`${label} ${opening.id} referencia un wallId inexistente.`);
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
    errors.push(`${label} ${opening.id} tiene position fuera de 0..1.`);
  }
}

function uniqueStrings(value) {
  if (!Array.isArray(value)) return [];
  return [...new Set(
    value.map((item) => String(item || "").trim()).filter(Boolean),
  )];
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
