import {
  CANONICAL_LEVEL_KEYS,
  createLevel,
} from "./editorSchema";

const ALIASES = Object.freeze({
  "1": "planta_baja",
  pb: "planta_baja",
  nivel_1: "planta_baja",
  planta_baja: "planta_baja",

  "2": "segunda_planta",
  pa: "segunda_planta",
  nivel_2: "segunda_planta",
  planta_alta: "segunda_planta",
  segunda_planta: "segunda_planta",

  "3": "tercera_planta",
  nivel_3: "tercera_planta",
  tercera_planta: "tercera_planta",

  "4": "planta_azotea",
  azotea: "planta_azotea",
  planta_azotea: "planta_azotea",
});

export function normalizeLevelKey(value) {
  const key = normalizeToken(value);
  return ALIASES[key] || key;
}

export function isCanonicalLevelKey(value) {
  return CANONICAL_LEVEL_KEYS.includes(normalizeLevelKey(value));
}

export function normalizeLevels(levels = []) {
  return levels
    .map((level, index) =>
      createLevel({
        ...level,
        key: normalizeLevelKey(level.key || level.name),
        order: Number.isInteger(level.order) ? level.order : index,
      }),
    )
    .sort((a, b) => a.order - b.order)
    .map((level, index) => ({
      ...level,
      order: index,
    }));
}

export function buildLevelsFromProject(sourceLevels = []) {
  if (!Array.isArray(sourceLevels)) return [];
  return normalizeLevels(sourceLevels);
}

export function addLevel(levels = [], data = {}) {
  const next = createLevel({
    ...data,
    key: normalizeLevelKey(data.key || data.name),
    order: levels.length,
  });

  return normalizeLevels([...levels, next]);
}

export function updateLevel(levels = [], levelId, patch = {}) {
  return normalizeLevels(
    levels.map((level) =>
      level.id === levelId
        ? {
            ...level,
            ...patch,
            key: patch.key != null
              ? normalizeLevelKey(patch.key)
              : level.key,
          }
        : level,
    ),
  );
}

export function canRemoveLevel({
  levelId,
  levels = [],
  spaces = [],
  walls = [],
  doors = [],
  windows = [],
  stairs = [],
}) {
  const level = levels.find((item) => item.id === levelId);
  if (!level) {
    return {
      allowed: false,
      requiresConfirmation: false,
      reason: "El nivel no existe.",
      relatedEntityIds: [],
    };
  }

  const related = [
    ...spaces.filter((item) => item.levelId === levelId).map((item) => item.id),
    ...walls.filter((item) => item.levelId === levelId).map((item) => item.id),
    ...doors.filter((item) => item.levelId === levelId).map((item) => item.id),
    ...windows.filter((item) => item.levelId === levelId).map((item) => item.id),
    ...stairs
      .filter(
        (item) =>
          item.levelFromId === levelId ||
          item.levelToId === levelId,
      )
      .map((item) => item.id),
  ];

  return {
    allowed: true,
    requiresConfirmation: related.length > 0,
    reason: related.length
      ? "El nivel contiene elementos y requiere confirmación antes de eliminarse."
      : null,
    relatedEntityIds: related,
  };
}

export function removeLevelCascade({
  levelId,
  levels = [],
  spaces = [],
  walls = [],
  doors = [],
  windows = [],
  stairs = [],
  annotations = [],
}) {
  return {
    levels: normalizeLevels(levels.filter((item) => item.id !== levelId)),
    spaces: spaces.filter((item) => item.levelId !== levelId),
    walls: walls.filter((item) => item.levelId !== levelId),
    doors: doors.filter((item) => item.levelId !== levelId),
    windows: windows.filter((item) => item.levelId !== levelId),
    stairs: stairs.filter(
      (item) =>
        item.levelFromId !== levelId &&
        item.levelToId !== levelId,
    ),
    annotations: annotations.filter((item) => item.levelId !== levelId),
  };
}

export function validateLevelHeightsForCalculation({
  levels = [],
  spaces = [],
}) {
  const usedLevelIds = new Set(
    spaces.map((space) => space.levelId).filter(Boolean),
  );

  const missing = levels
    .filter((level) => usedLevelIds.has(level.id))
    .filter((level) => {
      const value = Number(level.heightM);
      return !Number.isFinite(value) || value <= 0;
    });

  return {
    isValid: missing.length === 0,
    missingLevelIds: missing.map((level) => level.id),
  };
}

export function getLevelByKey(levels = [], key) {
  const normalized = normalizeLevelKey(key);
  return levels.find((level) => normalizeLevelKey(level.key) === normalized) || null;
}

export function getActiveLevel(levels = [], activeLevelId) {
  return levels.find((level) => level.id === activeLevelId) || null;
}

function normalizeToken(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\s-]+/g, "_");
}
