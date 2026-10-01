import {
  createLevel,
  createSourceInfo,
  createTerrain,
} from "../core/editorSchema";
import {
  rectFromXYWH,
} from "../core/geometry";
import {
  normalizeLevels,
} from "../core/levels";

/**
 * Traduce datosGeneralesObra al subconjunto de configuración que necesita
 * el editor 04.
 *
 * Reglas:
 * - terreno es opcional;
 * - solo se crea terreno si existen ancho Y largo válidos;
 * - no se inventan alturas;
 * - alturaPromedioM NO se reparte automáticamente entre niveles;
 * - no se crea azotea automáticamente por el simple hecho de existir N niveles;
 * - niveles superiores a 3 usan keys abiertas nivel_4, nivel_5, etc.
 */
export function extractProjectEditorConfig(
  datosGeneralesObra = {},
  currentSpatial = {},
) {
  const storedLevels = Array.isArray(currentSpatial?.niveles)
    ? currentSpatial.niveles
    : [];

  const levels = storedLevels.length
    ? normalizeLevels(storedLevels)
    : buildLevelsFromDatosGenerales(datosGeneralesObra);

  const terrain =
    normalizeStoredTerrain(currentSpatial?.terreno) ||
    buildTerrainFromDatosGenerales(datosGeneralesObra);

  return {
    levels,
    terrain,
    source: "datosGeneralesObra",
  };
}

export function buildLevelsFromDatosGenerales(
  datosGeneralesObra = {},
) {
  const count = positiveIntegerOrZero(
    datosGeneralesObra.niveles,
  );

  if (!count) return [];

  const levels = [];

  for (let index = 0; index < count; index += 1) {
    const number = index + 1;

    levels.push(
      createLevel({
        key: levelKeyFromNumber(number),
        name: levelNameFromNumber(number),
        order: index,

        // No derivamos elevaciones sin un contrato explícito
        // de entrepisos/losas.
        elevationM:
          number === 1
            ? 0
            : null,

        heightM:
          explicitHeightForLevel(
            datosGeneralesObra,
            number,
          ),

        visible: true,
        locked: false,
        confirmed:
          explicitHeightForLevel(
            datosGeneralesObra,
            number,
          ) != null,

        source: createSourceInfo({
          type: "manual",
          state: "MANUAL",
          note: "datosGeneralesObra",
        }),
      }),
    );
  }

  return normalizeLevels(levels);
}

export function buildTerrainFromDatosGenerales(
  datosGeneralesObra = {},
) {
  const widthM = positiveNumberOrNull(
    datosGeneralesObra.anchoTerrenoM,
  );

  const lengthM = positiveNumberOrNull(
    datosGeneralesObra.largoTerrenoM,
  );

  if (widthM == null || lengthM == null) {
    return null;
  }

  const geometry = rectFromXYWH({
    x: 0,
    y: 0,
    widthM,
    lengthM,
  });

  return createTerrain({
    shape: "rectangle",
    geometry,
    widthM,
    lengthM,
    orientationDeg: null,
    confirmed: true,
    source: createSourceInfo({
      type: "manual",
      state: "MANUAL",
      note: "datosGeneralesObra",
    }),
  });
}

/**
 * Completa únicamente información ausente en EditorState.
 * Nunca reemplaza niveles/geometría ya editados en 04.
 */
export function mergeProjectConfigIntoEditorState(
  editorState,
  datosGeneralesObra = {},
  currentSpatial = {},
) {
  const config = extractProjectEditorConfig(
    datosGeneralesObra,
    currentSpatial,
  );

  const hasLevels =
    Array.isArray(editorState?.levels) &&
    editorState.levels.length > 0;

  return {
    ...editorState,

    terrain:
      editorState?.terrain ??
      config.terrain ??
      null,

    levels:
      hasLevels
        ? editorState.levels
        : config.levels,

    activeLevelId:
      editorState?.activeLevelId ||
      (
        hasLevels
          ? editorState.levels[0]?.id
          : config.levels[0]?.id
      ) ||
      null,
  };
}

export function getMissingRequiredLevelHeights(
  levels = [],
  spaces = [],
) {
  const usedLevelIds = new Set(
    spaces
      .map((space) => space?.levelId)
      .filter(Boolean),
  );

  return levels
    .filter((level) =>
      usedLevelIds.has(level.id),
    )
    .filter((level) => {
      const height = Number(level.heightM);
      return !Number.isFinite(height) || height <= 0;
    });
}

export function levelKeyFromNumber(number) {
  switch (Number(number)) {
    case 1:
      return "planta_baja";
    case 2:
      return "segunda_planta";
    case 3:
      return "tercera_planta";
    default:
      return `nivel_${Number(number)}`;
  }
}

export function levelNameFromNumber(number) {
  switch (Number(number)) {
    case 1:
      return "Planta Baja";
    case 2:
      return "Segunda Planta";
    case 3:
      return "Tercera Planta";
    default:
      return `Nivel ${Number(number)}`;
  }
}

function explicitHeightForLevel(
  datosGeneralesObra,
  number,
) {
  const fields = {
    1: "alturaNivel1M",
    2: "alturaNivel2M",
    3: "alturaNivel3M",
  };

  const field = fields[number];
  if (!field) return null;

  return positiveNumberOrNull(
    datosGeneralesObra[field],
  );
}

function normalizeStoredTerrain(value) {
  if (!value || typeof value !== "object") return null;

  if (!value.geometry && !value.geometria) {
    return null;
  }

  return value;
}

function positiveNumberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : null;
}

function positiveIntegerOrZero(value) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 0;
  }

  return Math.floor(parsed);
}
