import { workflowConstructionContext } from "./spatialWorkflowContract.js";
import {
  createDoor,
  createEmptyEditorState,
  createSourceInfo,
  createSpace,
  createStair,
  createWall,
  createWindow,
} from "../core/editorSchema";
import {
  normalizeGeometry,
} from "../core/geometry";
import {
  normalizeLevels,
  normalizeLevelKey,
} from "../core/levels";
import {
  normalizeEditorState,
} from "../core/serialization";
import {
  reconcileWallGraph,
  updateSpaceWallRelations,
} from "../core/wallGraph";
import {
  extractProjectEditorConfig,
} from "./projectConfigAdapter";

/**
 * Convierte el estado actual de viviendaStore a EditorState canónico.
 *
 * Este adaptador:
 * - NO modifica el store.
 * - conserva compatibilidad con estructuraEspacial legacy.
 * - deriva muros desde espacios únicamente cuando el store todavía no los tiene.
 * - no inventa puertas/ventanas a partir de flags legacy sin geometría suficiente.
 */
export function editorStateFromViviendaStore(viviendaStore) {
  const spatial = viviendaStore?.estructuraEspacial || {};
  const project = viviendaStore?.datosGeneralesObra || {};

  const projectConfig = extractProjectEditorConfig(project, spatial);

  const levels = resolveLevels(spatial, projectConfig);
  const levelIdByKey = new Map(
    levels.map((level) => [normalizeLevelKey(level.key), level.id]),
  );

  const spaces = (Array.isArray(spatial.espacios) ? spatial.espacios : [])
    .map((space) => legacySpaceToEditorSpace(space, levels, levelIdByKey))
    .filter(Boolean);

  let walls = normalizeWalls(spatial.muros, levels);
  let doors = normalizeDoors(spatial.puertas, levels, walls);
  let windows = normalizeWindows(spatial.ventanas, levels, walls);
  const stairs = normalizeStairs(spatial.escaleras, levels);
  const annotations = normalizeAnnotations(spatial.anotaciones, levels);

  // Compatibilidad con estructuraEspacial anterior:
  // si existen espacios con geometría pero aún no hay muros canónicos,
  // derivamos el grafo básico sin inventar espesores/alturas.
  if (!walls.length && spaces.some((space) => space.geometry)) {
    const reconciled = reconcileWallGraph({
      spaces,
      existingWalls: [],
    });
    walls = reconciled.walls;
  }

  const spacesWithWalls = updateSpaceWallRelations(spaces, walls);

  // Limpieza defensiva: no mantener vanos cuyo muro ya no existe.
  const wallIds = new Set(walls.map((wall) => wall.id));
  doors = doors.map(door => wallIds.has(door.wallId) ? door : {...door, confirmed:false});
  windows = windows.map(window => wallIds.has(window.wallId) ? window : {...window, confirmed:false});

  const activeLevelId = resolveActiveLevelId(
    spatial.activeLevelId,
    levels,
    spacesWithWalls,
  );

  const editorState = createEmptyEditorState({
    projectId:
      spatial.projectId ??
      viviendaStore?.registro?.proyecto?.folio ??
      null,

    activeLevelId,

    terrain:
      normalizeTerrain(spatial.terreno) ??
      projectConfig.terrain ??
      null,

    levels,
    spaces: spacesWithWalls,
    walls,
    doors,
    windows,
    stairs,
    elements: spatial.elementos || [],
    completeness: spatial.completeness || {},
    annotations,

    validation:
      spatial.validacion && typeof spatial.validacion === "object"
        ? spatial.validacion
        : undefined,

    metadata: {
      sourceMode:
        spatial.sourceMode === "plan" ||
        spatial.metadata?.sourceMode === "plan"
          ? "plan"
          : "manual",

      createdAt:
        spatial.metadata?.createdAt ||
        undefined,

      updatedAt:
        spatial.metadata?.updatedAt ||
        undefined,
    },
  });

  return normalizeEditorState(editorState);
}

/**
 * Convierte EditorState canónico a la forma persistida en estructuraEspacial.
 *
 * Además de los campos canónicos, conserva alias legacy usados por vistas
 * existentes mientras se completa la migración:
 * - nivel
 * - geometria
 * - dobleAltura
 * - origen
 * - confianzaIA
 *
 * También preserva campos legacy desconocidos del espacio cuando comparte id.
 */
export function estructuraEspacialFromEditorState(
  editorState,
  currentSpatial = {},
) {
  const normalized = normalizeEditorState(editorState);

  const levelsById = new Map(
    normalized.levels.map((level) => [level.id, level]),
  );

  const existingSpacesById = new Map(
    (Array.isArray(currentSpatial?.espacios)
      ? currentSpatial.espacios
      : []
    ).map((space) => [space.id, space]),
  );

  const spaces = normalized.spaces.map((space) => {
    const previous = existingSpacesById.get(space.id) || {};
    const level = levelsById.get(space.levelId) || null;
    const source = sourceInfoToLegacy(space.source);

    return {
      ...previous,

      id: space.id,
      nombre: space.name,

      // Mantener tipo si ya existe; si no, usar código de uso canónico.
      tipo:
        space.usageCode ||
        previous.tipo ||
        "",

      usageCode: space.usageCode,
      usageLabel: space.usageLabel,
      category: space.category,

      levelId: space.levelId,
      nivel:
        level?.key ||
        previous.nivel ||
        "",

      geometry: space.geometry,
      geometria: space.geometry,

      areaM2: space.areaM2,
      perimetroM: space.perimeterM,

      doubleHeight: space.doubleHeight,
      dobleAltura: space.doubleHeight,

      heightM: space.heightM,
      finishes: space.finishes || [],
      intervention: space.intervention || "UNKNOWN",

      confirmed: space.confirmed,

      source: space.source,
      origen: source.origen,
      confianzaIA: source.confianzaIA,

      wallIds: [...(space.wallIds || [])],
      doorIds: [...(space.doorIds || [])],
      windowIds: [...(space.windowIds || [])],

      validation: space.validation,
    };
  });

  return {
    ...currentSpatial,

    schemaVersion: normalized.schemaVersion,
    projectId: normalized.projectId ?? currentSpatial.projectId ?? null,
    activeLevelId: normalized.activeLevelId,

    sourceMode: normalized.metadata?.sourceMode || "manual",
    metadata: {
      ...(currentSpatial.metadata || {}),
      ...normalized.metadata,
    },

    terreno: normalized.terrain,
    niveles: normalized.levels,
    espacios: spaces,
    muros: normalized.walls,
    puertas: normalized.doors,
    ventanas: normalized.windows,
    escaleras: normalized.stairs,
    elementos: normalized.elements,
    completeness: normalized.completeness,
    units: "m",
    revision: normalized.metadata.updatedAt,
    anotaciones: normalized.annotations,

    validacion: normalized.validation,

    // Compatibilidad: se conservan explícitamente campos existentes
    // que pertenecen al motor y no al editor.
    observaciones: currentSpatial.observaciones ?? "",
    engineInputs:
      currentSpatial.engineInputs &&
      typeof currentSpatial.engineInputs === "object"
        ? currentSpatial.engineInputs
        : {},
    engineInputsByConcept:
      currentSpatial.engineInputsByConcept &&
      typeof currentSpatial.engineInputsByConcept === "object"
        ? currentSpatial.engineInputsByConcept
        : {},
  };
}

/**
 * Aplica EditorState al viviendaStore.
 *
 * useStoreAction=true:
 *   usa setEstructuraEspacial(), por lo que conserva la semántica actual
 *   de invalidar/resetear estados downstream.
 *
 * useStoreAction=false:
 *   asigna directamente estructuraEspacial. Úsese únicamente para
 *   sincronización interna controlada; no es el modo recomendado al confirmar.
 */
export function applyEditorStateToViviendaStore(
  viviendaStore,
  editorState,
  options = {},
) {
  if (!viviendaStore) {
    return {
      ok: false,
      error: "ViviendaStore no disponible.",
      payload: null,
    };
  }

  const payload = estructuraEspacialFromEditorState(
    editorState,
    options.currentSpatial || viviendaStore.estructuraEspacial || {},
  );

  payload.context01 = {proyecto: viviendaStore.registro?.proyecto || {}, clasificacion:viviendaStore.clasificacion || {}, alcance:viviendaStore.alcance || {}};
  payload.context02 = workflowConstructionContext(viviendaStore);
  const useStoreAction = options.useStoreAction !== false;

  if (
    useStoreAction &&
    typeof viviendaStore.setEstructuraEspacial === "function"
  ) {
    viviendaStore.setEstructuraEspacial(payload);
  } else {
    viviendaStore.estructuraEspacial = payload;
  }

  return {
    ok: true,
    payload,
  };
}

/**
 * Solo construye el payload; útil para autosave/debounce o pruebas.
 */
export function buildEstructuraEspacialPayload(
  viviendaStore,
  editorState,
) {
  return estructuraEspacialFromEditorState(
    editorState,
    viviendaStore?.estructuraEspacial || {},
  );
}

function resolveLevels(spatial, projectConfig) {
  const storedLevels = Array.isArray(spatial?.niveles)
    ? spatial.niveles
    : [];

  if (storedLevels.length) {
    return normalizeLevels(storedLevels);
  }

  return normalizeLevels(projectConfig.levels || []);
}

function resolveActiveLevelId(
  requestedLevelId,
  levels,
  spaces,
) {
  if (levels.some((level) => level.id === requestedLevelId)) {
    return requestedLevelId;
  }

  const firstSpaceLevelId = spaces
    .map((space) => space.levelId)
    .find((levelId) =>
      levels.some((level) => level.id === levelId),
    );

  return firstSpaceLevelId || levels[0]?.id || null;
}

function legacySpaceToEditorSpace(
  legacy,
  levels,
  levelIdByKey,
) {
  if (!legacy || typeof legacy !== "object") return null;

  const originalGeometry = legacy.geometry || legacy.geometria || null;
  const geometry = normalizeGeometry(originalGeometry?.metrica || originalGeometry);

  if (!geometry) return null;

  const levelId = resolveSpaceLevelId(
    legacy,
    levels,
    levelIdByKey,
  );

  const source = legacySourceToSourceInfo(legacy);

  return createSpace({
    finishes: legacy.finishes || [],
    intervention: legacy.intervention || "UNKNOWN",
    id: legacy.id || undefined,
    name:
      legacy.name ??
      legacy.nombre ??
      "",
    usageCode:
      legacy.usageCode ??
      legacy.tipo ??
      "",
    usageLabel:
      legacy.usageLabel ??
      legacy.nombreUso ??
      legacy.tipo ??
      "",
    category:
      legacy.category ??
      "",
    levelId,

    geometry,
    areaM2: geometry.areaM2,
    perimeterM: geometry.perimeterM,

    doubleHeight:
      legacy.doubleHeight === true ||
      legacy.dobleAltura === true,

    heightM:
      legacy.heightM ??
      legacy.alturaM ??
      null,

    confirmed: Boolean(legacy.confirmed),

    source,

    wallIds:
      Array.isArray(legacy.wallIds)
        ? legacy.wallIds
        : [],

    doorIds:
      Array.isArray(legacy.doorIds)
        ? legacy.doorIds
        : [],

    windowIds:
      Array.isArray(legacy.windowIds)
        ? legacy.windowIds
        : [],

    validation:
      legacy.validation &&
      typeof legacy.validation === "object"
        ? legacy.validation
        : undefined,
  });
}

function resolveSpaceLevelId(
  legacy,
  levels,
  levelIdByKey,
) {
  if (
    legacy.levelId &&
    levels.some((level) => level.id === legacy.levelId)
  ) {
    return legacy.levelId;
  }

  const legacyKey = normalizeLevelKey(
    legacy.nivel ??
    legacy.level ??
    "planta_baja",
  );

  const matched = levelIdByKey.get(legacyKey);
  if (matched) return matched;

  return levels[0]?.id || "";
}

function normalizeWalls(value, levels) {
  if (!Array.isArray(value)) return [];
  const levelIds = new Set(levels.map((level) => level.id));

  return value
    .filter((wall) => wall && typeof wall === "object")
    .map((wall) =>
      createWall({
        ...wall,
        levelId:
          levelIds.has(wall.levelId)
            ? wall.levelId
            : resolveLevelIdByLegacyKey(
                wall.nivel,
                levels,
              ),
        source: legacySourceToSourceInfo(wall),
      }),
    );
}

function normalizeDoors(value, levels, walls) {
  if (!Array.isArray(value)) return [];
  const wallMap = new Map(walls.map((wall) => [wall.id, wall]));

  return value
    .filter((door) => door && typeof door === "object")
    .map((door) => {
      const wall = wallMap.get(door.wallId) || {};

      return createDoor({
        ...door,
        levelId:
          door.levelId ||
          wall.levelId ||
          resolveLevelIdByLegacyKey(
            door.nivel,
            levels,
          ),
        source: legacySourceToSourceInfo(door),
      });
    });
}

function normalizeWindows(value, levels, walls) {
  if (!Array.isArray(value)) return [];
  const wallMap = new Map(walls.map((wall) => [wall.id, wall]));

  return value
    .filter((window) =>
      window && typeof window === "object",
    )
    .map((window) => {
      const wall = wallMap.get(window.wallId) || {};

      return createWindow({
        ...window,
        levelId:
          window.levelId ||
          wall.levelId ||
          resolveLevelIdByLegacyKey(
            window.nivel,
            levels,
          ),
        source: legacySourceToSourceInfo(window),
      });
    });
}

function normalizeStairs(value, levels) {
  if (!Array.isArray(value)) return [];

  return value
    .filter((stair) => stair && typeof stair === "object")
    .map((stair) =>
      createStair({
        ...stair,
        levelFromId:
          stair.levelFromId ||
          resolveLevelIdByLegacyKey(
            stair.nivelOrigen,
            levels,
          ),
        levelToId:
          stair.levelToId ||
          resolveLevelIdByLegacyKey(
            stair.nivelDestino,
            levels,
          ),
        source: legacySourceToSourceInfo(stair),
      }),
    );
}

function normalizeAnnotations(value, levels) {
  if (!Array.isArray(value)) return [];

  return value
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      ...item,
      levelId:
        item.levelId ||
        resolveLevelIdByLegacyKey(
          item.nivel,
          levels,
        ),
    }));
}

function resolveLevelIdByLegacyKey(value, levels) {
  const normalized = normalizeLevelKey(value);
  return (
    levels.find((level) =>
      normalizeLevelKey(level.key) === normalized,
    )?.id ||
    levels[0]?.id ||
    ""
  );
}

function normalizeTerrain(value) {
  if (!value || typeof value !== "object") return null;

  const geometry = normalizeGeometry(
    value.geometry ||
    value.geometria ||
    null,
  );

  if (!geometry) return null;

  return {
    ...value,
    geometry,
    shape:
      geometry.type === "polygon"
        ? "polygon"
        : "rectangle",
    widthM:
      value.widthM ??
      geometry.widthM ??
      null,
    lengthM:
      value.lengthM ??
      geometry.lengthM ??
      null,
    confirmed: Boolean(value.confirmed),
    source: legacySourceToSourceInfo(value),
  };
}

function legacySourceToSourceInfo(value) {
  if (
    value?.source &&
    typeof value.source === "object"
  ) {
    return createSourceInfo(value.source);
  }

  const origin =
    value?.origen &&
    typeof value.origen === "object"
      ? value.origen
      : {};

  const hasAiEvidence =
    value?.confianzaIA != null ||
    origin.documento ||
    origin.pagina != null ||
    origin.fuente;

  return createSourceInfo({
    type:
      hasAiEvidence
        ? "ai"
        : "manual",

    documentId:
      origin.documentId ??
      null,

    documentName:
      origin.documento ??
      origin.documentName ??
      null,

    page:
      Number.isInteger(origin.pagina)
        ? origin.pagina
        : null,

    confidence:
      value?.confianzaIA ??
      value?.confidence ??
      null,

    state:
      value?.estado ||
      value?.state ||
      (hasAiEvidence
        ? "DETECTADO"
        : "MANUAL"),

    note:
      origin.fuente ??
      null,
  });
}

function sourceInfoToLegacy(source) {
  const safe = createSourceInfo(source);

  return {
    origen: {
      documentId: safe.documentId,
      documento: safe.documentName,
      pagina: safe.page,
      fuente: safe.note,
    },
    confianzaIA: safe.confidence,
  };
}
