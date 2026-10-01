<template>
  <section ref="containerRef" class="quantia-plan-editor" :class="{
    'is-plan-mode': mode === 'plan',
    'is-readonly': readonly,
  }">
    <div v-if="mode === 'plan' && !hasPlanWorld" class="empty-state">
      <strong>No hay geometría o plano base disponible.</strong>
      <span>
        Carga un plano base o un modelo espacial para iniciar la revisión.
      </span>
    </div>

    <v-stage v-else ref="stageRef" :config="stageConfig" @wheel="onWheel" @mousedown="onPointerDown"
      @mousemove="onPointerMove" @mouseup="onPointerUp" @mouseleave="onPointerLeave" @click="onStageClick"
      @tap="onStageClick" @dragend="onStageDragEnd">
      <!-- =========================================================
           CAPA BASE: plano / grid / terreno
           ========================================================= -->
      <v-layer :config="{ listening: false }">
        <v-image v-if="
          mode === 'plan' &&
          baseImage &&
          layerVisible('planoBase')
        " :config="baseImageConfig" />

        <template v-if="
          mode === 'manual' &&
          layerVisible('grid')
        ">
          <v-line v-for="line in gridLines" :key="line.key" :config="line.config" />
        </template>

        <v-line v-if="
          mode === 'manual' &&
          terrainPolygon &&
          layerVisible('terreno')
        " :config="terrainShapeConfig" />
      </v-layer>

      <!-- =========================================================
           CAPA ESPACIOS
           ========================================================= -->
      <v-layer v-if="layerVisible('espacios')">
        <template v-for="space in renderedSpaces" :key="space.id">
          <v-line :config="space.shape" @click="selectCanvasEntity($event, 'space', space.id)"
            @tap="selectCanvasEntity($event, 'space', space.id)" @dragstart="onSpaceDragStart(space, $event)"
            @dragend="onSpaceDragEnd(space, $event)" />

          <v-text :config="space.label" @click="selectCanvasEntity($event, 'space', space.id)"
            @tap="selectCanvasEntity($event, 'space', space.id)" />
        </template>
      </v-layer>

      <!-- =========================================================
           CAPA MUROS
           ========================================================= -->
      <v-layer v-if="layerVisible('muros')">
        <v-line v-for="wall in renderedWalls" :key="wall.id" :config="wall.shape"
          @click="selectCanvasEntity($event, 'wall', wall.wallId)" @tap="selectCanvasEntity($event, 'wall', wall.wallId)" /> </v-layer>

      <!-- =========================================================
           CAPA COTAS GROUNDED
           ========================================================= -->
      <v-layer v-if="layerVisible('cotas')" :config="{ listening: false }">
        <template v-for="dimension in renderedDimensions" :key="dimension.id">
          <v-line :config="dimension.shape" />
          <v-text :config="dimension.label" />
        </template>
      </v-layer>

      <!-- =========================================================
           CAPA VANOS
           ========================================================= -->
      <v-layer>
        <template v-if="layerVisible('puertas')">
          <template v-for="door in renderedDoors" :key="door.id">
            <v-line :config="door.opening" @click="selectCanvasEntity($event, 'door', door.id)"
              @tap="selectCanvasEntity($event, 'door', door.id)" />
            <v-line v-if="door.leaf" :config="door.leaf" @click="selectCanvasEntity($event, 'door', door.id)"
              @tap="selectCanvasEntity($event, 'door', door.id)" />
          </template>
        </template>

        <template v-if="layerVisible('ventanas')">
          <v-line v-for="windowItem in renderedWindows" :key="windowItem.id" :config="windowItem.shape"
            @click="selectCanvasEntity($event, 'window', windowItem.id)" @tap="selectCanvasEntity($event, 'window', windowItem.id)" />
        </template>
      </v-layer>

      <v-layer v-if="mode === 'manual'">
        <template v-for="stair in renderedStairs" :key="stair.id">
          <v-line :config="stair.shape" @click="selectCanvasEntity($event, 'stair', stair.id)" @tap="selectCanvasEntity($event, 'stair', stair.id)" />
          <v-line v-for="(line,i) in stair.lines" :key="i" :config="line" />
          <v-text :config="stair.label" @click="selectCanvasEntity($event, 'stair', stair.id)" />
        </template>
      </v-layer>

      <!-- =========================================================
           CAPA DIBUJO / PREVIEW / MEDICIÓN
           ========================================================= -->
      <v-layer :config="{ listening: false }">
        <v-line v-if="rectanglePreview" :config="rectanglePreview" />

        <v-line v-if="wallPreview" :config="wallPreview" />

        <template v-if="polygonDraft.length">
          <v-line :config="polygonPreview" />

          <v-circle v-for="(point, index) in polygonDraft" :key="`draft-${index}`"
            :config="draftNode(point, index === 0)" />
        </template>

        <template v-if="measurementPreview">
          <v-line :config="measurementPreview.line" />
          <v-text :config="measurementPreview.label" />
        </template>

        <v-circle v-if="snapIndicator" :config="snapIndicator" />
      </v-layer>

      <!-- =========================================================
           CAPA NODOS DE EDICIÓN
           ========================================================= -->
      <v-layer v-if="
        selectedRenderedSpace &&
        canEditNodes
      ">
        <v-circle v-for="(point, index) in selectedRenderedSpace.points"
          :key="`node-${selectedRenderedSpace.id}-${index}`" :config="nodeConfig(point)"
          @dragmove="onNodeDrag(index, $event)" @dragend="onNodeDragEnd(index, $event)" />
      </v-layer>
    </v-stage>

    <div v-if="editorMessage" class="editor-message" :class="`is-${editorMessage.type}`">
      {{ editorMessage.text }}
    </div>

    <div v-if="
      mode === 'manual' ||
      hasPlanWorld
    " class="status-bar">
      <span>
        {{ mode === "manual" ? "Métrico" : "Raster" }}
      </span>

      <span>{{ zoomPercent }}%</span>

      <span v-if="mode === 'manual'">
        Grid {{ effectiveGridLabel }}
      </span>

      <span v-if="pointerWorld">
        X {{ formatCoord(pointerWorld.x) }}
        ·
        Y {{ formatCoord(pointerWorld.y) }}
      </span>
    </div>
  </section>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import {
  Circle as VCircle,
  Image as VImage,
  Layer as VLayer,
  Line as VLine,
  Stage as VStage,
  Text as VText,
} from "vue-konva";

import {
  boundingBox,
  buildEdges,
  closestPointOnSegment,
  dist,
  geometryFromVertices,
  midpoint,
  normalizeGeometry,
  pointIsFinite,
  polygonArea,
  polygonCentroid,
  polygonPerimeter,
  rectFromXYWH,
  segmentLength,
  segmentNormal,
  translateGeometry,
} from "@/modules/vivienda/editor/core/geometry";

import {
  resolveSnap,
} from "@/modules/vivienda/editor/core/snap";

import {
  validateSpaceCandidate,
} from "@/modules/vivienda/editor/core/constraints";

import {
  normalizeLevelKey,
} from "@/modules/vivienda/editor/core/levels";

const props = defineProps({
  mode: {
    type: String,
    default: "manual",
    validator: (value) =>
      ["manual", "plan"].includes(value),
  },

  /**
   * Acepta:
   * - estructura legacy: { espacios, ... }
   * - estructura canónica: { levels, spaces, walls, doors, windows, terrain }
   * - estructuraEspacial con aliases en español.
   */
  spatialModel: {
    type: Object,
    default: () => ({}),
  },

  /**
   * Compatibilidad legacy.
   * Puede ser key (planta_baja) o id de nivel.
   */
  activeLevel: {
    type: String,
    default: "planta_baja",
  },

  /**
   * Nuevo contrato canónico.
   */
  activeLevelId: {
    type: String,
    default: null,
  },

  /**
   * Compatibilidad con vista actual:
   * { anchoM, largoM }
   */
  terrain: {
    type: Object,
    default: () => ({
      anchoM: null,
      largoM: null,
    }),
  },

  baseLayerUrl: {
    type: String,
    default: null,
  },

  activeTool: {
    type: String,
    default: "select",
  },

  selectedId: {
    type: String,
    default: null,
  },

  selectedType: {
    type: String,
    default: null,
  },

  gridSizeM: {
    type: Number,
    default: 0.5,
  },

  showGrid: {
    type: Boolean,
    default: true,
  },

  snapToGrid: {
    type: Boolean,
    default: true,
  },

  snapEnabled: {
    type: Boolean,
    default: true,
  },

  readonly: {
    type: Boolean,
    default: false,
  },

  /**
   * Escala visual inicial.
   * Es UI, no dato constructivo.
   */
  initialPixelsPerMeter: {
    type: Number,
    default: 50,
  },

  /**
   * Tolerancia visual de snap.
   * Es UI, no dato constructivo.
   */
  snapTolerancePx: {
    type: Number,
    default: 12,
  },

  layers: {
    type: Object,
    default: () => ({
      planoBase: true,
      terreno: true,
      grid: true,
      espacios: true,
      muros: true,
      puertas: true,
      ventanas: true,
      cotas: true,
      anotaciones: true,
    }),
  },
});

function selectCanvasEntity(event, type, id) {
  // Drawing tools must receive the stage click even when it hits an existing wall.
  if (!SELECT_TOOLS.has(props.activeTool)) return;
  event.cancelBubble = true;
  selectEntity(type, id);
}

const emit = defineEmits([
  // Compatibilidad actual.
  "select",
  "create-space",
  "update-space-geometry",
  "viewport-change",

  // Contrato nuevo.
  "select-entity",
  "move-space",
  "create-wall",
  "create-door",
  "create-window",
  "measure",
  "validation-error",
]);

const containerRef = ref(null);
const stageRef = ref(null);

const viewportWidth = ref(900);
const viewportHeight = ref(620);

const stageScale = ref(
  normalizeVisualScale(props.initialPixelsPerMeter),
);
const stageX = ref(48);
const stageY = ref(48);

const pointerWorld = ref(null);
const localSelectedId = ref(props.selectedId);
const localSelectedType = ref(
  props.selectedType ||
  (props.selectedId ? "space" : null),
);

const rectangleStart = ref(null);
const rectangleEnd = ref(null);

const polygonDraft = ref([]);

const wallStart = ref(null);
const wallEnd = ref(null);

const measureStart = ref(null);
const measureEnd = ref(null);

const editedSpaceId = ref(null);
const editedVertices = ref(null);

const draggingSpace = ref(null);

const currentSnap = ref(null);
const editorMessage = ref(null);

const baseImage = ref(null);

let resizeObserver = null;
let messageTimer = null;

const RECT_TOOLS = new Set([
  "stair",
  "rectangle",
  "rect",
  "space-rect",
]);

const POLYGON_TOOLS = new Set([
  "polygon",
  "space-polygon",
]);

const SELECT_TOOLS = new Set([
  "select",
  "edit",
]);

const PAN_TOOLS = new Set([
  "pan",
  "hand",
]);

const WALL_TOOLS = new Set([
  "wall",
  "muro",
]);

const DOOR_TOOLS = new Set([
  "garage",
  "door",
  "puerta",
]);

const WINDOW_TOOLS = new Set([
  "window",
  "ventana",
]);

const MEASURE_TOOLS = new Set([
  "measure",
  "medir",
]);

const FIT_TOOLS = new Set([
  "fit",
  "fit-view",
  "ajustar-vista",
]);

const MIN_SCALE = 0.02;
const MAX_SCALE = 300;
const EPS = 1e-9;

/* =========================================================
   MODELO NORMALIZADO
   ========================================================= */

const modelLevels = computed(() => {
  const source =
    props.spatialModel?.levels ||
    props.spatialModel?.niveles ||
    [];

  return Array.isArray(source)
    ? source
    : [];
});

const modelSpaces = computed(() => {
  const source =
    props.spatialModel?.spaces ||
    props.spatialModel?.espacios ||
    [];

  return Array.isArray(source)
    ? source
    : [];
});

const modelWalls = computed(() => {
  const source =
    props.spatialModel?.walls ||
    props.spatialModel?.muros ||
    [];

  return Array.isArray(source)
    ? source
    : [];
});

const modelDoors = computed(() => {
  const source =
    props.spatialModel?.doors ||
    props.spatialModel?.puertas ||
    [];

  return Array.isArray(source)
    ? source
    : [];
});

const modelWindows = computed(() => {
  const source =
    props.spatialModel?.windows ||
    props.spatialModel?.ventanas ||
    [];

  return Array.isArray(source)
    ? source
    : [];
});

const modelAxes = computed(() => {
  const source =
    props.spatialModel?.axes ||
    props.spatialModel?.ejes ||
    [];

  return Array.isArray(source) ? source : [];
});

const modelDimensions = computed(() => {
  const source =
    props.spatialModel?.dimensions ||
    props.spatialModel?.cotas ||
    [];

  return Array.isArray(source) ? source : [];
});

const resolvedActiveLevelId = computed(() => {
  const requested =
    props.activeLevelId ||
    props.activeLevel ||
    null;

  if (
    requested &&
    modelLevels.value.some(
      (level) => level.id === requested,
    )
  ) {
    return requested;
  }

  const requestedKey =
    normalizeLevelKey(requested || "planta_baja");

  const matched = modelLevels.value.find(
    (level) =>
      normalizeLevelKey(
        level.key ||
        level.name,
      ) === requestedKey,
  );

  return (
    matched?.id ||
    requestedKey ||
    null
  );
});

const resolvedActiveLevelKey = computed(() => {
  const level = modelLevels.value.find(
    (item) =>
      item.id === resolvedActiveLevelId.value,
  );

  return normalizeLevelKey(
    level?.key ||
    props.activeLevel ||
    "planta_baja",
  );
});

const terrainGeometry = computed(() => {
  const canonical =
    props.spatialModel?.terrain ||
    props.spatialModel?.terreno ||
    null;

  const canonicalGeometry =
    canonical?.geometry ||
    canonical?.geometria ||
    null;

  if (canonicalGeometry) {
    const normalized =
      normalizeGeometry(canonicalGeometry);

    if (normalized?.vertices?.length >= 3) {
      return normalized;
    }
  }

  const width =
    numberOrNull(
      props.terrain?.anchoM ??
      props.terrain?.widthM ??
      canonical?.widthM ??
      canonical?.anchoM ??
      props.spatialModel
        ?.datosGeneralesObra
        ?.anchoTerrenoM,
    );

  const length =
    numberOrNull(
      props.terrain?.largoM ??
      props.terrain?.lengthM ??
      canonical?.lengthM ??
      canonical?.largoM ??
      props.spatialModel
        ?.datosGeneralesObra
        ?.largoTerrenoM,
    );

  if (
    width > 0 &&
    length > 0
  ) {
    return rectFromXYWH({
      x: 0,
      y: 0,
      widthM: width,
      lengthM: length,
    });
  }

  return null;
});

const terrainPolygon = computed(() =>
  terrainGeometry.value?.vertices || null,
);

const normalizedSpaces = computed(() =>
  modelSpaces.value
    .map((space) =>
      normalizeSpaceRecord(space),
    )
    .filter(Boolean),
);

const activeSpaces = computed(() =>
  normalizedSpaces.value.filter(
    (space) =>
      spaceMatchesActiveLevel(space.raw),
  ),
);

const activeWalls = computed(() =>
  modelWalls.value.filter(
    (wall) =>
      wallMatchesActiveLevel(wall),
  ),
);

const activeDoors = computed(() =>
  modelDoors.value.filter(
    (door) =>
      openingMatchesActiveLevel(door),
  ),
);

const activeWindows = computed(() =>
  modelWindows.value.filter(
    (windowItem) =>
      openingMatchesActiveLevel(windowItem),
  ),
);

/* =========================================================
   PLAN MODE / IMAGEN BASE
   ========================================================= */

const baseImageSource = computed(() =>
  props.baseLayerUrl ||
  props.spatialModel
    ?.planoBase
    ?.referencia ||
  props.spatialModel
    ?.planoBase
    ?.url ||
  null,
);

const planWorldSize = computed(() => {
  const width =
    numberOrNull(
      props.spatialModel
        ?.planoBase
        ?.anchoPx ??
      props.spatialModel
        ?.planoBase
        ?.widthPx ??
      props.spatialModel
        ?.planoBase
        ?.width_px,
    );

  const height =
    numberOrNull(
      props.spatialModel
        ?.planoBase
        ?.altoPx ??
      props.spatialModel
        ?.planoBase
        ?.heightPx ??
      props.spatialModel
        ?.planoBase
        ?.height_px,
    );

  if (width > 0 && height > 0) {
    return {
      width,
      height,
    };
  }

  const points =
    modelSpaces.value.flatMap(
      (space) =>
        rasterVertices(space),
    );

  if (!points.length) {
    return {
      width: 0,
      height: 0,
    };
  }

  const bbox = boundingBox(points);

  return {
    width: Math.max(
      bbox.maxX,
      bbox.width,
    ),
    height: Math.max(
      bbox.maxY,
      bbox.height,
    ),
  };
});

const hasPlanWorld = computed(() =>
  Boolean(
    baseImageSource.value ||
    (
      planWorldSize.value.width > 0 &&
      planWorldSize.value.height > 0
    ),
  ),
);

const baseImageConfig = computed(() => ({
  x: 0,
  y: 0,
  width: planWorldSize.value.width,
  height: planWorldSize.value.height,
  image: baseImage.value,
  listening: false,
}));

/* =========================================================
   VIEWPORT / STAGE
   ========================================================= */

const stageConfig = computed(() => ({
  width: viewportWidth.value,
  height: viewportHeight.value,
  x: stageX.value,
  y: stageY.value,
  scaleX: stageScale.value,
  scaleY: stageScale.value,
  draggable:
    !props.readonly &&
    PAN_TOOLS.has(props.activeTool),
}));

const zoomPercent = computed(() =>
  Math.round(
    (
      stageScale.value /
      normalizeVisualScale(
        props.initialPixelsPerMeter,
      )
    ) * 100,
  ),
);

const visibleWorldBounds = computed(() => {
  const scale =
    Math.max(
      stageScale.value,
      MIN_SCALE,
    );

  const left =
    (0 - stageX.value) / scale;

  const top =
    (0 - stageY.value) / scale;

  const right =
    (
      viewportWidth.value -
      stageX.value
    ) / scale;

  const bottom =
    (
      viewportHeight.value -
      stageY.value
    ) / scale;

  return {
    left,
    top,
    right,
    bottom,
  };
});

const contentBounds = computed(() => {
  if (props.mode === "plan") {
    if (
      planWorldSize.value.width > 0 &&
      planWorldSize.value.height > 0
    ) {
      return {
        minX: 0,
        minY: 0,
        maxX:
          planWorldSize.value.width,
        maxY:
          planWorldSize.value.height,
      };
    }

    return null;
  }

  const points = [];

  if (terrainPolygon.value) {
    points.push(
      ...terrainPolygon.value,
    );
  }

  for (const space of activeSpaces.value) {
    points.push(
      ...space.points,
    );
  }

  for (const wall of activeWalls.value) {
    if (
      pointIsFinite(wall.start) &&
      pointIsFinite(wall.end)
    ) {
      points.push(
        wall.start,
        wall.end,
      );
    }
  }

  if (!points.length) {
    return null;
  }

  const bbox = boundingBox(points);

  return {
    minX: bbox.minX,
    minY: bbox.minY,
    maxX: bbox.maxX,
    maxY: bbox.maxY,
  };
});

/* =========================================================
   GRID / TERRENO
   ========================================================= */

const effectiveGridStep = computed(() => {
  const requested =
    positiveNumberOrFallback(
      props.gridSizeM,
      0.5,
    );

  let step = requested;

  while (
    step * stageScale.value < 12
  ) {
    step *= 2;
  }

  return step;
});

const effectiveGridLabel = computed(() =>
  `${effectiveGridStep.value.toFixed(2)} m`,
);

const gridLines = computed(() => {
  if (
    props.mode !== "manual" ||
    !props.showGrid ||
    !layerVisible("grid")
  ) {
    return [];
  }

  const bounds =
    visibleWorldBounds.value;

  const step =
    effectiveGridStep.value;

  const majorStep =
    Math.max(
      1,
      step,
    );

  const startX =
    Math.floor(bounds.left / step) *
    step;

  const endX =
    Math.ceil(bounds.right / step) *
    step;

  const startY =
    Math.floor(bounds.top / step) *
    step;

  const endY =
    Math.ceil(bounds.bottom / step) *
    step;

  const strokeWidth =
    1 /
    Math.max(
      stageScale.value,
      0.001,
    );

  const lines = [];
  const maxLines = 500;

  let counter = 0;

  for (
    let x = startX;
    x <= endX + EPS &&
    counter < maxLines;
    x += step
  ) {
    const isMajor =
      isMultipleOf(
        x,
        majorStep,
      );

    lines.push({
      key: `gx-${x.toFixed(6)}`,
      config: {
        points: [
          x,
          startY,
          x,
          endY,
        ],
        stroke:
          isMajor
            ? "#cbd5e1"
            : "#e8edf3",
        strokeWidth:
          isMajor
            ? strokeWidth * 1.25
            : strokeWidth,
        listening: false,
      },
    });

    counter += 1;
  }

  for (
    let y = startY;
    y <= endY + EPS &&
    counter < maxLines;
    y += step
  ) {
    const isMajor =
      isMultipleOf(
        y,
        majorStep,
      );

    lines.push({
      key: `gy-${y.toFixed(6)}`,
      config: {
        points: [
          startX,
          y,
          endX,
          y,
        ],
        stroke:
          isMajor
            ? "#cbd5e1"
            : "#e8edf3",
        strokeWidth:
          isMajor
            ? strokeWidth * 1.25
            : strokeWidth,
        listening: false,
      },
    });

    counter += 1;
  }

  if (
    bounds.left <= 0 &&
    bounds.right >= 0
  ) {
    lines.push({
      key: "axis-y",
      config: {
        points: [
          0,
          startY,
          0,
          endY,
        ],
        stroke: "#94a3b8",
        strokeWidth:
          strokeWidth * 1.6,
        listening: false,
      },
    });
  }

  if (
    bounds.top <= 0 &&
    bounds.bottom >= 0
  ) {
    lines.push({
      key: "axis-x",
      config: {
        points: [
          startX,
          0,
          endX,
          0,
        ],
        stroke: "#94a3b8",
        strokeWidth:
          strokeWidth * 1.6,
        listening: false,
      },
    });
  }

  return lines;
});

const terrainShapeConfig = computed(() => ({
  points: flatten(
    terrainPolygon.value || [],
  ),
  closed: true,
  fill: "rgba(255,255,255,.72)",
  stroke: "#475569",
  strokeWidth:
    2 /
    Math.max(
      stageScale.value,
      0.001,
    ),
  dash: [
    8 / stageScale.value,
    5 / stageScale.value,
  ],
  listening: false,
}));

/* =========================================================
   ESPACIOS RENDER
   ========================================================= */

const renderedSpaces = computed(() =>
  activeSpaces.value
    .map((space) => {
      const id =
        String(
          space.id || "",
        );

      const selected =
        id ===
        localSelectedId.value &&
        localSelectedType.value ===
        "space";

      const center =
        polygonCentroid(
          space.points,
        );

      const bounds = boundingBox(space.points);
      const labelVisible =
        selected ||
        (
          bounds.width * stageScale.value >= 90 &&
          bounds.height * stageScale.value >= 36
        );

      const name =
        space.raw?.name ||
        space.raw?.nombre ||
        space.raw?.usageLabel ||
        space.raw?.label ||
        space.raw?.tipo ||
        "Espacio";

      const area =
        props.mode === "manual"
          ? polygonArea(space.points)
          : null;

      const draggable =
        props.mode === "manual" &&
        !props.readonly &&
        SELECT_TOOLS.has(
          props.activeTool,
        );

      return {
        id,
        raw: space.raw,
        geometry: space.geometry,
        points: space.points,

        shape: {
          points: flatten(
            space.points,
          ),
          closed: true,
          fill:
            selected
              ? "rgba(37,99,235,.18)"
              : "rgba(14,116,144,.10)",
          stroke:
            selected
              ? "#2563eb"
              : "#0f766e",
          strokeWidth:
            (
              selected
                ? 2.5
                : 1.5
            ) /
            Math.max(
              stageScale.value,
              0.001,
            ),
          hitStrokeWidth:
            12 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          draggable,
        },

        label: {
          x: center.x,
          y: center.y,
          text:
            `${name}` +
            (
              area > 0
                ? ` · ${area.toFixed(2)} m²`
                : ""
            ),
          fontSize:
            13 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          fill: "#0f172a",
          align: "center",
          width:
            140 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          offsetX:
            70 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          offsetY:
            7 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          listening: true,
          visible: labelVisible,
        },
      };
    })
    .filter(
      (space) =>
        space.points.length >= 3,
    ),
);

const selectedRenderedSpace = computed(() =>
  renderedSpaces.value.find(
    (space) =>
      space.id ===
      localSelectedId.value &&
      localSelectedType.value ===
      "space",
  ) || null,
);

const canEditNodes = computed(() =>
  !props.readonly &&
  props.mode === "manual" &&
  SELECT_TOOLS.has(
    props.activeTool,
  ) &&
  Boolean(
    selectedRenderedSpace.value,
  ),
);

/* =========================================================
   MUROS / PUERTAS / VENTANAS
   ========================================================= */

const renderedWalls = computed(() => {
  const rendered = [];

  for (const wall of activeWalls.value) {
    const selected =
      wall.id === localSelectedId.value &&
      localSelectedType.value === "wall";

    const stroke =
      selected
        ? "#2563eb"
        : "#334155";

    // ----------------------------------------------------------
    // MODO PLAN:
    // prioriza los segmentos raster del contrato 03.2.
    // No convierte píxeles a metros.
    // ----------------------------------------------------------
    if (props.mode === "plan") {
      const segments =
        Array.isArray(wall?.segmentos)
          ? wall.segmentos
          : [];

      for (
        let index = 0;
        index < segments.length;
        index += 1
      ) {
        const segment =
          segments[index];

        const vertices =
          segment?.geometria
            ?.raster
            ?.vertices;

        if (
          !Array.isArray(vertices) ||
          vertices.length < 2
        ) {
          continue;
        }

        const points = vertices
          .map((point) => ({
            x: Number(point?.x),
            y: Number(point?.y),
          }))
          .filter(pointIsFinite);

        if (points.length < 2) {
          continue;
        }

        rendered.push({
          id:
            `${wall.id}::${segment.id || index}`,

          wallId:
            wall.id,

          raw:
            wall,

          segmentRaw:
            segment,

          shape: {
            points:
              flatten(points),

            stroke,

            strokeWidth:
              (
                selected
                  ? 3
                  : 2
              ) /
              Math.max(
                stageScale.value,
                0.001,
              ),

            lineCap:
              "square",

            lineJoin:
              "round",

            hitStrokeWidth:
              14 /
              Math.max(
                stageScale.value,
                0.001,
              ),
          },
        });
      }

      continue;
    }

    // ----------------------------------------------------------
    // MODO MANUAL:
    // conserva el comportamiento existente start/end.
    // ----------------------------------------------------------
    if (
      !pointIsFinite(wall.start) ||
      !pointIsFinite(wall.end)
    ) {
      continue;
    }

    const thickness =
      numberOrNull(
        wall.thicknessM ??
        wall.espesorM,
      );

    const visualThickness =
      thickness > 0
        ? thickness
        : 0.06;

    rendered.push({
      id:
        wall.id,

      wallId:
        wall.id,

      raw:
        wall,

      shape: {
        points: [
          Number(wall.start.x),
          Number(wall.start.y),
          Number(wall.end.x),
          Number(wall.end.y),
        ],

        stroke,

        strokeWidth:
          Math.max(
            visualThickness,
            2.5 /
            Math.max(
              stageScale.value,
              0.001,
            ),
          ),

        lineCap:
          "square",

        hitStrokeWidth:
          14 /
          Math.max(
            stageScale.value,
            0.001,
          ),
      },
    });
  }

  return rendered;
});

const renderedDimensions = computed(() => {
  const axes = new Map(
    modelAxes.value.map((axis) => [axis.id, axis]),
  );
  const rendered = [];
  const seen = new Set();

  for (const dimension of modelDimensions.value) {
    if (!dimensionMatchesActiveLevel(dimension)) continue;

    const value = numberOrNull(dimension?.valorM ?? dimension?.valueM);
    if (!(value > 0)) continue;

    const startAxis = axes.get(
      dimension?.ejeInicioId ?? dimension?.startAxisId,
    );
    const endAxis = axes.get(
      dimension?.ejeFinId ?? dimension?.endAxisId,
    );
    const start = numberOrNull(
      startAxis?.coordenadaPx ?? startAxis?.coordinatePx,
    );
    const end = numberOrNull(
      endAxis?.coordenadaPx ?? endAxis?.coordinatePx,
    );

    if (start === null || end === null || start === end) continue;

    const evidence = Array.isArray(dimension?.evidencia)
      ? dimension.evidencia.find((item) => item?.bboxRaster)
      : null;
    const bbox = evidence?.bboxRaster;
    if (!bbox) continue;

    const direction = String(
      dimension?.direccion ?? dimension?.direction ?? "",
    ).toLowerCase();
    let points;
    let labelX;
    let labelY;

    if (direction === "horizontal") {
      const y = (Number(bbox.yMin) + Number(bbox.yMax)) / 2;
      if (!Number.isFinite(y)) continue;
      points = [start, y, end, y];
      labelX = (start + end) / 2;
      labelY = y;
    } else if (direction === "vertical") {
      const x = (Number(bbox.xMin) + Number(bbox.xMax)) / 2;
      if (!Number.isFinite(x)) continue;
      points = [x, start, x, end];
      labelX = x;
      labelY = (start + end) / 2;
    } else {
      continue;
    }

    const levelKey = normalizeLevelKey(dimension?.nivel || dimension?.level);
    const dedupeKey = [levelKey, direction, start, end, value].join("|");
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);

    const scale = Math.max(stageScale.value, 0.001);
    rendered.push({
      id: String(dimension.id || dedupeKey),
      shape: {
        points,
        stroke: "#b45309",
        strokeWidth: 1.25 / scale,
        dash: [5 / scale, 3 / scale],
      },
      label: {
        x: labelX,
        y: labelY,
        text: `${value.toFixed(2)} m`,
        fontSize: 11 / scale,
        fill: "#92400e",
        width: 72 / scale,
        offsetX: 36 / scale,
        offsetY: 14 / scale,
        align: "center",
      },
    });
  }

  return rendered;
});

const wallMap = computed(
  () =>
    new Map(
      activeWalls.value.map(
        (wall) => [
          wall.id,
          wall,
        ],
      ),
    ),
);

const renderedDoors = computed(() =>
  activeDoors.value
    .map((door) =>
      renderDoor(door),
    )
    .filter(Boolean),
);

const renderedStairs = computed(() => (props.spatialModel?.stairs || props.spatialModel?.escaleras || [])
  .filter(s => s.levelFromId === resolvedActiveLevelId.value || s.levelToId === resolvedActiveLevelId.value)
  .filter(s => s.geometry?.vertices?.length)
  .map(s => {
    const scale=Math.max(stageScale.value,0.001), lines=[];
    for(const f of s.flights || []) {
      const [a,b]=f.pathM || []; if(!a || !b)continue;
      lines.push({points:[a.x,a.y,b.x,b.y],stroke:'#7c3aed',strokeWidth:2/scale,listening:false});
      const length=Math.hypot(b.x-a.x,b.y-a.y), n=Number(f.riserCount);
      if(length>0 && Number(f.widthM)>0 && n>=2 && n<=200) for(let i=0;i<n;i++) {
        const t=i/(n-1), x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t,dx=-(b.y-a.y)/length*f.widthM/2,dy=(b.x-a.x)/length*f.widthM/2;
        lines.push({points:[x-dx,y-dy,x+dx,y+dy],stroke:'#7c3aed',strokeWidth:1/scale,listening:false});
      }
    }
    for(const l of s.landings || []) lines.push({points:flatten(l.outer || []),closed:true,stroke:'#a855f7',strokeWidth:1/scale,listening:false});
    return {id:s.id,shape:{points:flatten(s.geometry.vertices),closed:true,fill:'rgba(124,58,237,.12)',stroke:s.id===localSelectedId.value?'#2563eb':'#7c3aed',strokeWidth:2/scale},lines,
      label:{x:s.geometry.vertices[0].x,y:s.geometry.vertices[0].y,text:'Escalera '+(s.type || ''),fontSize:12/scale,fill:'#6d28d9'}};
  }));

const renderedWindows = computed(() =>
  activeWindows.value
    .map((windowItem) =>
      renderWindow(windowItem),
    )
    .filter(Boolean),
);

/* =========================================================
   PREVIEWS
   ========================================================= */

const rectanglePreview = computed(() => {
  if (
    !rectangleStart.value ||
    !rectangleEnd.value
  ) {
    return null;
  }

  const geometry =
    rectangleGeometry(
      rectangleStart.value,
      rectangleEnd.value,
    );

  if (!geometry) return null;

  return {
    points: flatten(
      geometry.vertices,
    ),
    closed: true,
    fill: "rgba(37,99,235,.10)",
    stroke: "#2563eb",
    strokeWidth:
      2 /
      Math.max(
        stageScale.value,
        0.001,
      ),
    dash: [
      8 / stageScale.value,
      5 / stageScale.value,
    ],
  };
});

const polygonPreview = computed(() => ({
  points: flatten(
    polygonDraft.value,
  ),
  closed: false,
  stroke: "#2563eb",
  strokeWidth:
    2 /
    Math.max(
      stageScale.value,
      0.001,
    ),
  dash: [
    8 / stageScale.value,
    5 / stageScale.value,
  ],
}));

const wallPreview = computed(() => {
  if (
    !wallStart.value ||
    !wallEnd.value
  ) {
    return null;
  }

  return {
    points: [
      wallStart.value.x,
      wallStart.value.y,
      wallEnd.value.x,
      wallEnd.value.y,
    ],
    stroke: "#7c3aed",
    strokeWidth:
      2 /
      Math.max(
        stageScale.value,
        0.001,
      ),
    dash: [
      8 / stageScale.value,
      5 / stageScale.value,
    ],
  };
});

const measurementPreview = computed(() => {
  if (
    !measureStart.value ||
    !measureEnd.value
  ) {
    return null;
  }

  const start =
    measureStart.value;

  const end =
    measureEnd.value;

  const center =
    midpoint(
      start,
      end,
    );

  const length =
    dist(
      start,
      end,
    );

  return {
    line: {
      points: [
        start.x,
        start.y,
        end.x,
        end.y,
      ],
      stroke: "#f97316",
      strokeWidth:
        1.5 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      dash: [
        6 / stageScale.value,
        4 / stageScale.value,
      ],
    },

    label: {
      x: center.x,
      y: center.y,
      text:
        props.mode === "manual"
          ? `${length.toFixed(2)} m`
          : `${length.toFixed(0)} px`,
      fill: "#c2410c",
      fontSize:
        12 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      offsetY:
        18 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      listening: false,
    },
  };
});

const snapIndicator = computed(() => {
  const result =
    currentSnap.value;

  if (
    !result?.applied ||
    !pointIsFinite(result.point)
  ) {
    return null;
  }

  const colors = {
    vertex: "#dc2626",
    edge: "#7c3aed",
    horizontal: "#0891b2",
    vertical: "#0891b2",
    grid: "#2563eb",
  };

  return {
    x: result.point.x,
    y: result.point.y,
    radius:
      4 /
      Math.max(
        stageScale.value,
        0.001,
      ),
    fill:
      colors[result.type] ||
      "#2563eb",
    stroke: "#ffffff",
    strokeWidth:
      1.5 /
      Math.max(
        stageScale.value,
        0.001,
      ),
  };
});

/* =========================================================
   STAGE HELPERS
   ========================================================= */

function stageNode() {
  return (
    stageRef.value?.getNode?.() ||
    null
  );
}

function screenToWorld() {
  const stage =
    stageNode();

  const pointer =
    stage?.getPointerPosition?.();

  if (!pointer) return null;

  return {
    x:
      (
        pointer.x -
        stageX.value
      ) /
      stageScale.value,

    y:
      (
        pointer.y -
        stageY.value
      ) /
      stageScale.value,
  };
}

function currentPoint(options = {}) {
  const raw =
    options.point ||
    screenToWorld();

  if (!raw) return null;

  if (
    props.mode !== "manual" ||
    !props.snapEnabled
  ) {
    currentSnap.value = null;

    return {
      x: Number(raw.x),
      y: Number(raw.y),
    };
  }

  const tolerance =
    Math.max(
      2,
      numberOrNull(
        props.snapTolerancePx,
      ) || 12,
    ) /
    Math.max(
      stageScale.value,
      0.001,
    );

  const result =
    resolveSnap({
      point: raw,
      vertices:
        collectSnapVertices(),
      edges:
        collectSnapEdges(),
      anchor:
        options.anchor ||
        null,
      toleranceM:
        tolerance,
      gridSizeM:
        positiveNumberOrFallback(
          props.gridSizeM,
          0.5,
        ),
      enableVertices: true,
      enableEdges: true,
      enableOrthogonal:
        Boolean(
          options.anchor,
        ),
      enableGrid:
        props.snapToGrid,
    });

  currentSnap.value =
    result?.applied
      ? result
      : null;

  return (
    result?.point ||
    raw
  );
}

function collectSnapVertices() {
  const result = [];

  for (const space of activeSpaces.value) {
    for (const point of space.points) {
      result.push({
        ...point,
        entityId: space.id,
      });
    }
  }

  for (const wall of activeWalls.value) {
    if (pointIsFinite(wall.start)) {
      result.push({
        ...wall.start,
        entityId: wall.id,
      });
    }

    if (pointIsFinite(wall.end)) {
      result.push({
        ...wall.end,
        entityId: wall.id,
      });
    }
  }

  return result;
}

function collectSnapEdges() {
  const result = [];

  for (const space of activeSpaces.value) {
    for (
      const edge of buildEdges(
        space.points,
      )
    ) {
      result.push({
        ...edge,
        entityId: space.id,
      });
    }
  }

  for (const wall of activeWalls.value) {
    if (
      pointIsFinite(wall.start) &&
      pointIsFinite(wall.end)
    ) {
      result.push({
        id: `wall-edge-${wall.id}`,
        entityId: wall.id,
        start: wall.start,
        end: wall.end,
      });
    }
  }

  return result;
}

/* =========================================================
   VIEWPORT
   ========================================================= */

function fitViewport() {
  const bounds =
    contentBounds.value;

  if (!bounds) {
    if (props.mode === "manual") {
      resetManualViewport();
    }
    return;
  }

  const width =
    bounds.maxX -
    bounds.minX;

  const height =
    bounds.maxY -
    bounds.minY;

  if (
    width <= 0 ||
    height <= 0
  ) {
    return;
  }

  const padding = 52;

  const scale = Math.min(
    Math.max(
      viewportWidth.value -
      padding * 2,
      1,
    ) / width,

    Math.max(
      viewportHeight.value -
      padding * 2,
      1,
    ) / height,
  );

  stageScale.value =
    clamp(
      scale,
      MIN_SCALE,
      MAX_SCALE,
    );

  stageX.value =
    padding -
    bounds.minX *
    stageScale.value +
    (
      (
        viewportWidth.value -
        padding * 2
      ) -
      width *
      stageScale.value
    ) / 2;

  stageY.value =
    padding -
    bounds.minY *
    stageScale.value +
    (
      (
        viewportHeight.value -
        padding * 2
      ) -
      height *
      stageScale.value
    ) / 2;

  emitViewport();
}

function resetManualViewport() {
  stageScale.value =
    normalizeVisualScale(
      props.initialPixelsPerMeter,
    );

  stageX.value = 48;
  stageY.value = 48;

  emitViewport();
}

function emitViewport() {
  emit("viewport-change", {
    x: stageX.value,
    y: stageY.value,
    scale: stageScale.value,
  });
}

function onWheel(event) {
  event.evt.preventDefault();

  const stage =
    stageNode();

  const pointer =
    stage?.getPointerPosition?.();

  if (!pointer) return;

  const oldScale =
    stageScale.value;

  const worldPoint = {
    x:
      (
        pointer.x -
        stageX.value
      ) /
      oldScale,

    y:
      (
        pointer.y -
        stageY.value
      ) /
      oldScale,
  };

  const factor = 1.08;

  const next =
    event.evt.deltaY > 0
      ? oldScale / factor
      : oldScale * factor;

  stageScale.value =
    clamp(
      next,
      MIN_SCALE,
      MAX_SCALE,
    );

  stageX.value =
    pointer.x -
    worldPoint.x *
    stageScale.value;

  stageY.value =
    pointer.y -
    worldPoint.y *
    stageScale.value;

  emitViewport();
}

function onStageDragEnd() {
  const stage =
    stageNode();

  if (!stage) return;

  stageX.value =
    stage.x();

  stageY.value =
    stage.y();

  emitViewport();
}

/* =========================================================
   EVENTOS DE POINTER
   ========================================================= */

function onPointerDown(event) {
  pointerWorld.value =
    screenToWorld();

  if (
    props.readonly ||
    props.mode !== "manual" ||
    (event.target !== event.target.getStage() && SELECT_TOOLS.has(props.activeTool))
  ) {
    return;
  }

  if (
    RECT_TOOLS.has(
      props.activeTool,
    )
  ) {
    const point =
      currentPoint();

    if (!point) return;

    rectangleStart.value =
      point;

    rectangleEnd.value =
      point;

    return;
  }

  if (
    WALL_TOOLS.has(
      props.activeTool,
    )
  ) {
    const point =
      currentPoint();

    if (!point) return;

    wallStart.value =
      point;

    wallEnd.value =
      point;
  }
}

function onPointerMove() {
  pointerWorld.value =
    screenToWorld();

  if (
    rectangleStart.value &&
    RECT_TOOLS.has(
      props.activeTool,
    )
  ) {
    const point =
      currentPoint({
        anchor:
          rectangleStart.value,
      });

    if (point) {
      rectangleEnd.value =
        point;
    }

    return;
  }

  if (
    wallStart.value &&
    WALL_TOOLS.has(
      props.activeTool,
    )
  ) {
    const point =
      currentPoint({
        anchor:
          wallStart.value,
      });

    if (point) {
      wallEnd.value =
        point;
    }

    return;
  }

  if (
    measureStart.value &&
    MEASURE_TOOLS.has(
      props.activeTool,
    )
  ) {
    const point =
      currentPoint({
        anchor:
          measureStart.value,
      });

    if (point) {
      measureEnd.value =
        point;
    }

    return;
  }

  if (
    props.mode === "manual" &&
    props.snapEnabled
  ) {
    currentPoint();
  } else {
    currentSnap.value = null;
  }
}

function onPointerUp() {
  if (
    rectangleStart.value &&
    rectangleEnd.value &&
    RECT_TOOLS.has(
      props.activeTool,
    )
  ) {
    finishRectangle();
    return;
  }

  if (
    wallStart.value &&
    wallEnd.value &&
    WALL_TOOLS.has(
      props.activeTool,
    )
  ) {
    finishWall();
  }
}

function onPointerLeave() {
  currentSnap.value = null;
}

/* =========================================================
   STAGE CLICK TOOLS
   ========================================================= */

function onStageClick(event) {
  if (
    event.target !==
    event.target.getStage() && SELECT_TOOLS.has(props.activeTool)
  ) {
    return;
  }

  if (
    SELECT_TOOLS.has(
      props.activeTool,
    )
  ) {
    selectEntity(null, null);
    return;
  }

  if (
    props.readonly ||
    props.mode !== "manual"
  ) {
    return;
  }

  if (
    POLYGON_TOOLS.has(
      props.activeTool,
    )
  ) {
    addPolygonPoint();
    return;
  }

  if (
    DOOR_TOOLS.has(
      props.activeTool,
    )
  ) {
    createOpeningFromPointer(
      "door",
    );
    return;
  }

  if (
    WINDOW_TOOLS.has(
      props.activeTool,
    )
  ) {
    createOpeningFromPointer(
      "window",
    );
    return;
  }

  if (
    MEASURE_TOOLS.has(
      props.activeTool,
    )
  ) {
    measureClick();
  }
}

/* =========================================================
   CREACIÓN RECTÁNGULO
   ========================================================= */

function finishRectangle() {
  const start =
    rectangleStart.value;

  const end =
    rectangleEnd.value;

  rectangleStart.value = null;
  rectangleEnd.value = null;

  const geometry =
    rectangleGeometry(
      start,
      end,
    );

  if (!geometry) return;
  if (props.activeTool === "stair") { emit("create-space", {geometry}); return; }

  const validation =
    validateNewSpaceGeometry(
      geometry,
    );

  if (!validation.isValid) {
    showValidation(
      validation,
    );
    return;
  }

  const payload = {
    source: "manual",
    levelId:
      resolvedActiveLevelId.value,
    nivel:
      resolvedActiveLevelKey.value,

    xM: geometry.x,
    yM: geometry.y,
    anchoM:
      geometry.widthM,
    largoM:
      geometry.lengthM,

    areaM2:
      geometry.areaM2,
    perimetroM:
      geometry.perimeterM,

    confirmed: false,

    geometry,
    geometria:
      canonicalGeometryToLegacy(
        geometry,
      ),
  };

  emit(
    "create-space",
    payload,
  );
}

function rectangleGeometry(
  start,
  end,
) {
  if (!start || !end) {
    return null;
  }

  const minX =
    Math.min(
      start.x,
      end.x,
    );

  const maxX =
    Math.max(
      start.x,
      end.x,
    );

  const minY =
    Math.min(
      start.y,
      end.y,
    );

  const maxY =
    Math.max(
      start.y,
      end.y,
    );

  const width =
    maxX - minX;

  const length =
    maxY - minY;

  if (
    width <= EPS ||
    length <= EPS
  ) {
    return null;
  }

  return rectFromXYWH({
    x: minX,
    y: minY,
    widthM: width,
    lengthM: length,
  });
}

/* =========================================================
   CREACIÓN POLÍGONO
   ========================================================= */

function addPolygonPoint() {
  const point =
    currentPoint({
      anchor:
        polygonDraft.value[
        polygonDraft.value.length - 1
        ] || null,
    });

  if (!point) return;

  if (
    polygonDraft.value.length >= 3 &&
    nearFirstDraftPoint(point)
  ) {
    finishPolygon();
    return;
  }

  polygonDraft.value = [
    ...polygonDraft.value,
    point,
  ];
}

function finishPolygon() {
  if (
    polygonDraft.value.length < 3
  ) {
    return;
  }

  const geometry =
    geometryFromVertices(
      polygonDraft.value,
      {
        type: "polygon",
      },
    );

  const validation =
    validateNewSpaceGeometry(
      geometry,
    );

  if (!validation.isValid) {
    showValidation(
      validation,
    );
    return;
  }

  polygonDraft.value = [];

  emit("create-space", {
    source: "manual",
    levelId:
      resolvedActiveLevelId.value,
    nivel:
      resolvedActiveLevelKey.value,

    areaM2:
      geometry.areaM2,
    perimetroM:
      geometry.perimeterM,

    confirmed: false,

    geometry,
    geometria:
      canonicalGeometryToLegacy(
        geometry,
      ),
  });
}

function nearFirstDraftPoint(point) {
  const first =
    polygonDraft.value[0];

  if (!first) return false;

  const tolerance =
    Math.max(
      8,
      props.snapTolerancePx,
    ) /
    Math.max(
      stageScale.value,
      0.001,
    );

  return (
    dist(
      point,
      first,
    ) <= tolerance
  );
}

/* =========================================================
   CREACIÓN MURO
   ========================================================= */

function finishWall() {
  const start =
    wallStart.value;

  const end =
    wallEnd.value;

  wallStart.value = null;
  wallEnd.value = null;

  if (
    !start ||
    !end ||
    segmentLength(
      start,
      end,
    ) <= EPS
  ) {
    return;
  }

  emit("create-wall", {
    levelId:
      resolvedActiveLevelId.value,
    nivel:
      resolvedActiveLevelKey.value,
    start: { ...start },
    end: { ...end },
    lengthM:
      segmentLength(
        start,
        end,
      ),
    thicknessM: null,
    heightM: null,
    type: "uncertain",
    confirmed: false,
    source: {
      type: "manual",
      state: "MANUAL",
    },
  });
}

/* =========================================================
   PUERTAS / VENTANAS
   ========================================================= */

function createOpeningFromPointer(
  kind,
) {
  const raw =
    screenToWorld();

  if (!raw) return;

  const match =
    nearestWallToPoint(raw);

  if (!match) {
    showMessage(
      "Selecciona un punto sobre un muro.",
      "error",
    );
    return;
  }

  const tolerance =
    Math.max(
      8,
      props.snapTolerancePx,
    ) /
    Math.max(
      stageScale.value,
      0.001,
    );

  if (
    match.distance >
    tolerance
  ) {
    showMessage(
      "La puerta o ventana debe colocarse sobre un muro.",
      "error",
    );
    return;
  }

  const closest =
    closestPointOnSegment(
      raw,
      match.wall.start,
      match.wall.end,
    );

  const payload = {
    levelId:
      match.wall.levelId ||
      resolvedActiveLevelId.value,

    nivel:
      resolvedActiveLevelKey.value,

    wallId:
      match.wall.id,

    position:
      closest.t,

    widthM: null,
    heightM: null,

    confirmed: false,

    source: {
      type: "manual",
      state: "MANUAL",
    },
  };

  if (kind === "door") {
    emit(
      "create-door",
      {
        ...payload,
        swingDirection:
          "unknown",
      },
    );
  } else {
    emit(
      "create-window",
      {
        ...payload,
        sillHeightM: null,
      },
    );
  }
}

function nearestWallToPoint(point) {
  let best = null;

  for (
    const wall of activeWalls.value
  ) {
    if (
      !pointIsFinite(wall.start) ||
      !pointIsFinite(wall.end)
    ) {
      continue;
    }

    const closest =
      closestPointOnSegment(
        point,
        wall.start,
        wall.end,
      );

    const distance =
      dist(
        point,
        closest,
      );

    if (
      !best ||
      distance <
      best.distance
    ) {
      best = {
        wall,
        closest,
        distance,
      };
    }
  }

  return best;
}

/* =========================================================
   MEDICIÓN
   ========================================================= */

function measureClick() {
  const point =
    currentPoint({
      anchor:
        measureStart.value,
    });

  if (!point) return;

  if (!measureStart.value) {
    measureStart.value =
      point;

    measureEnd.value =
      point;

    return;
  }

  measureEnd.value =
    point;

  const payload = {
    start: {
      ...measureStart.value,
    },

    end: {
      ...measureEnd.value,
    },

    distance:
      dist(
        measureStart.value,
        measureEnd.value,
      ),

    units:
      props.mode === "manual"
        ? "m"
        : "px",
  };

  emit(
    "measure",
    payload,
  );

  measureStart.value = null;
  measureEnd.value = null;
}

/* =========================================================
   SELECCIÓN
   ========================================================= */

function selectEntity(
  type,
  id,
) {
  localSelectedType.value =
    type;

  localSelectedId.value =
    id;

  editedSpaceId.value =
    null;

  editedVertices.value =
    null;

  emit("select-entity", {
    type,
    id,
  });

  // Compatibilidad con la vista actual:
  // select sigue representando selección de ESPACIO.
  if (
    type === "space" ||
    type === null
  ) {
    emit(
      "select",
      id,
    );
  }
}

/* =========================================================
   MOVER ESPACIO
   ========================================================= */

function onSpaceDragStart(
  space,
  event,
) {
  if (
    props.readonly ||
    props.mode !== "manual" ||
    !SELECT_TOOLS.has(
      props.activeTool,
    )
  ) {
    return;
  }

  // Permite tomar y desplazar una figura directamente sin requerir
  // una selección previa. Al iniciar el drag, la figura pasa a ser
  // la selección activa y su inspector se sincroniza en la vista padre.
  if (
    localSelectedType.value !== "space" ||
    localSelectedId.value !== space.id
  ) {
    selectEntity("space", space.id);
  }

  draggingSpace.value = {
    id: space.id,
    geometry:
      normalizeGeometry(
        space.geometry,
      ),
  };

  event.target.position({
    x: 0,
    y: 0,
  });
}

function onSpaceDragEnd(
  space,
  event,
) {
  if (
    !draggingSpace.value ||
    draggingSpace.value.id !==
    space.id
  ) {
    return;
  }

  const node =
    event.target;

  const dx =
    Number(
      node.x(),
    );

  const dy =
    Number(
      node.y(),
    );

  node.position({
    x: 0,
    y: 0,
  });

  const original =
    draggingSpace.value
      .geometry;

  draggingSpace.value = null;

  if (
    !original ||
    (
      Math.abs(dx) <= EPS &&
      Math.abs(dy) <= EPS
    )
  ) {
    return;
  }

  const translated =
    translateGeometry(
      original,
      dx,
      dy,
    );

  const validation =
    validateExistingSpaceGeometry(
      space.id,
      translated,
    );

  if (!validation.isValid) {
    showValidation(
      validation,
    );
    return;
  }

  emit("move-space", {
    id: space.id,
    dx,
    dy,
    geometry:
      translated,
    geometria:
      canonicalGeometryToLegacy(
        translated,
      ),
    areaM2:
      translated.areaM2,
    perimetroM:
      translated.perimeterM,
  });
}

/* =========================================================
   EDITAR NODOS
   ========================================================= */

function ensureEditedVertices() {
  const selected =
    selectedRenderedSpace.value;

  if (!selected) return null;

  if (
    editedSpaceId.value !==
    selected.id ||
    !Array.isArray(
      editedVertices.value,
    )
  ) {
    editedSpaceId.value =
      selected.id;

    editedVertices.value =
      selected.points.map(
        (point) => ({
          ...point,
        }),
      );
  }

  return editedVertices.value;
}

function onNodeDrag(
  index,
  event,
) {
  if (!canEditNodes.value) {
    return;
  }

  const vertices =
    ensureEditedVertices();

  if (
    !vertices?.[index]
  ) {
    return;
  }

  const point =
    currentPoint({
      point: {
        x:
          event.target.x(),
        y:
          event.target.y(),
      },
    });

  if (!point) return;

  const selected =
    selectedRenderedSpace.value;

  const geometry =
    normalizeGeometry(
      selected?.geometry,
    );

  if (
    geometry?.type ===
    "rectangle"
  ) {
    const oppositeIndex =
      (index + 2) % 4;

    const opposite =
      vertices[
      oppositeIndex
      ];

    const rectangle =
      rectFromXYWH({
        x:
          Math.min(
            point.x,
            opposite.x,
          ),
        y:
          Math.min(
            point.y,
            opposite.y,
          ),
        widthM:
          Math.abs(
            point.x -
            opposite.x,
          ),
        lengthM:
          Math.abs(
            point.y -
            opposite.y,
          ),
      });

    if (
      rectangle
        .vertices
        .length !== 4
    ) {
      return;
    }

    editedVertices.value =
      rectangle.vertices.map(
        (item) => ({
          ...item,
        }),
      );

    return;
  }

  vertices[index] = {
    ...point,
  };

  editedVertices.value =
    vertices.map(
      (item) => ({
        ...item,
      }),
    );
}

function onNodeDragEnd(
  index,
  event,
) {
  onNodeDrag(
    index,
    event,
  );

  const selected =
    selectedRenderedSpace.value;

  if (
    !selected ||
    !editedVertices.value
  ) {
    return;
  }

  if (props.mode === "plan") {
    emitRasterNodeUpdate(
      selected,
    );
    return;
  }

  const originalGeometry =
    normalizeGeometry(
      selected.geometry,
    );

  const geometry =
    originalGeometry?.type ===
      "rectangle"
      ? rectFromBoundingVertices(
        editedVertices.value,
      )
      : geometryFromVertices(
        editedVertices.value,
        {
          type: "polygon",
        },
      );

  if (!geometry) return;

  const validation =
    validateExistingSpaceGeometry(
      selected.id,
      geometry,
    );

  if (!validation.isValid) {
    editedSpaceId.value =
      null;

    editedVertices.value =
      null;

    showValidation(
      validation,
    );

    return;
  }

  emit(
    "update-space-geometry",
    {
      id:
        selected.id,

      levelId:
        resolvedLevelIdForSpace(
          selected.raw,
        ),

      nivel:
        resolvedLevelKeyForSpace(
          selected.raw,
        ),

      domain: "metric",

      vertices:
        geometry.vertices,

      xM:
        geometry.type === "rectangle"
          ? geometry.x
          : undefined,

      yM:
        geometry.type === "rectangle"
          ? geometry.y
          : undefined,

      anchoM:
        geometry.type === "rectangle"
          ? geometry.widthM
          : undefined,

      largoM:
        geometry.type === "rectangle"
          ? geometry.lengthM
          : undefined,

      areaM2:
        geometry.areaM2,

      perimetroM:
        geometry.perimeterM,

      confirmed: false,

      geometry,

      geometria:
        canonicalGeometryToLegacy(
          geometry,
        ),
    },
  );
}

function emitRasterNodeUpdate(
  selected,
) {
  const vertices =
    editedVertices.value.map(
      (point) => ({
        ...point,
      }),
    );

  emit(
    "update-space-geometry",
    {
      id:
        selected.id,

      nivel:
        resolvedLevelKeyForSpace(
          selected.raw,
        ),

      domain: "raster",

      vertices,

      confirmed: false,

      geometria: {
        tipo:
          selected.raw
            ?.geometria
            ?.tipo ||
          "poligono",

        raster: {
          vertices,
        },
      },
    },
  );
}

function rectFromBoundingVertices(
  vertices,
) {
  const bbox =
    boundingBox(
      vertices,
    );

  if (
    bbox.width <= EPS ||
    bbox.height <= EPS
  ) {
    return null;
  }

  return rectFromXYWH({
    x: bbox.minX,
    y: bbox.minY,
    widthM: bbox.width,
    lengthM: bbox.height,
  });
}

/* =========================================================
   VALIDACIÓN DE ESPACIOS
   ========================================================= */

function validateNewSpaceGeometry(
  geometry,
) {
  return validateSpaceCandidate({
    space: {
      id: "__draft__",
      levelId:
        resolvedActiveLevelId.value,
      geometry,
    },

    spaces:
      validationSpaces.value,

    terrain:
      terrainGeometry.value
        ? {
          geometry:
            terrainGeometry.value,
        }
        : null,

    ignoreSpaceId: null,
  });
}

function validateExistingSpaceGeometry(
  spaceId,
  geometry,
) {
  const original =
    validationSpaces.value.find(
      (space) =>
        space.id === spaceId,
    );

  return validateSpaceCandidate({
    space: {
      ...original,
      id: spaceId,
      geometry,
    },

    spaces:
      validationSpaces.value,

    terrain:
      terrainGeometry.value
        ? {
          geometry:
            terrainGeometry.value,
        }
        : null,

    ignoreSpaceId:
      spaceId,
  });
}

const validationSpaces = computed(() =>
  normalizedSpaces.value.map(
    (space) => ({
      id: space.id,

      levelId:
        resolvedLevelIdForSpace(
          space.raw,
        ),

      geometry:
        space.geometry,
    }),
  ),
);

/* =========================================================
   CANCEL / KEYBOARD
   ========================================================= */

function cancelDrawing() {
  rectangleStart.value = null;
  rectangleEnd.value = null;

  polygonDraft.value = [];

  wallStart.value = null;
  wallEnd.value = null;

  measureStart.value = null;
  measureEnd.value = null;

  currentSnap.value = null;
}

function onKeyDown(event) {
  if (
    event.key === "Escape"
  ) {
    cancelDrawing();
    return;
  }

  if (
    event.key === "Enter" &&
    POLYGON_TOOLS.has(
      props.activeTool,
    )
  ) {
    finishPolygon();
  }
}

/* =========================================================
   VISUAL HELPERS
   ========================================================= */

function nodeConfig(point) {
  return {
    x: point.x,
    y: point.y,

    radius:
      5 /
      Math.max(
        stageScale.value,
        0.001,
      ),

    fill: "#ffffff",
    stroke: "#2563eb",

    strokeWidth:
      2 /
      Math.max(
        stageScale.value,
        0.001,
      ),

    draggable: true,
  };
}

function draftNode(
  point,
  isFirst = false,
) {
  return {
    x: point.x,
    y: point.y,

    radius:
      (
        isFirst
          ? 5
          : 4
      ) /
      Math.max(
        stageScale.value,
        0.001,
      ),

    fill:
      isFirst
        ? "#dc2626"
        : "#2563eb",

    stroke: "#ffffff",

    strokeWidth:
      1.5 /
      Math.max(
        stageScale.value,
        0.001,
      ),
  };
}

function renderDoor(door) {
  const wall =
    wallMap.value.get(
      door.wallId,
    );

  if (!wall) return null;

  const center =
    pointAtWallPosition(
      wall,
      door.position,
    );

  const wallLength =
    segmentLength(
      wall.start,
      wall.end,
    );

  if (wallLength <= EPS) {
    return null;
  }

  const width =
    positiveNumberOrFallback(
      door.widthM,
      10 /
      Math.max(
        stageScale.value,
        0.001,
      ),
    );

  const halfT =
    Math.min(
      0.49,
      width /
      (
        2 *
        wallLength
      ),
    );

  const centerT =
    clamp(
      numberOrNull(
        door.position,
      ) ?? 0.5,
      0,
      1,
    );

  const start =
    pointAtWallPosition(
      wall,
      clamp(
        centerT - halfT,
        0,
        1,
      ),
    );

  const end =
    pointAtWallPosition(
      wall,
      clamp(
        centerT + halfT,
        0,
        1,
      ),
    );

  const normal =
    segmentNormal(
      wall.start,
      wall.end,
    );

  const selected =
    door.id ===
    localSelectedId.value &&
    localSelectedType.value ===
    "door";

  const stroke =
    selected
      ? "#2563eb"
      : door.kind === "GARAGE_DOOR" ? "#d97706" : "#16a34a";

  return {
    id: door.id,

    opening: {
      points: [
        start.x,
        start.y,
        end.x,
        end.y,
      ],
      stroke,
      strokeWidth:
        4 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      hitStrokeWidth:
        14 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      lineCap: "round",
    },

    leaf: door.kind === "GARAGE_DOOR" || door.operation === "SLIDING" ? null : {
      points: [
        start.x,
        start.y,
        start.x +
        normal.x *
        width,
        start.y +
        normal.y *
        width,
      ],
      stroke,
      strokeWidth:
        1.5 /
        Math.max(
          stageScale.value,
          0.001,
        ),
    },

    center,
  };
}

function renderWindow(
  windowItem,
) {
  const wall =
    wallMap.value.get(
      windowItem.wallId,
    );

  if (!wall) return null;

  const wallLength =
    segmentLength(
      wall.start,
      wall.end,
    );

  if (wallLength <= EPS) {
    return null;
  }

  const width =
    positiveNumberOrFallback(
      windowItem.widthM,
      10 /
      Math.max(
        stageScale.value,
        0.001,
      ),
    );

  const halfT =
    Math.min(
      0.49,
      width /
      (
        2 *
        wallLength
      ),
    );

  const centerT =
    clamp(
      numberOrNull(
        windowItem.position,
      ) ?? 0.5,
      0,
      1,
    );

  const start =
    pointAtWallPosition(
      wall,
      clamp(
        centerT - halfT,
        0,
        1,
      ),
    );

  const end =
    pointAtWallPosition(
      wall,
      clamp(
        centerT + halfT,
        0,
        1,
      ),
    );

  const selected =
    windowItem.id ===
    localSelectedId.value &&
    localSelectedType.value ===
    "window";

  return {
    id: windowItem.id,

    shape: {
      points: [
        start.x,
        start.y,
        end.x,
        end.y,
      ],
      stroke:
        selected
          ? "#2563eb"
          : "#0284c7",
      strokeWidth:
        5 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      hitStrokeWidth:
        14 /
        Math.max(
          stageScale.value,
          0.001,
        ),
      lineCap: "round",
    },
  };
}

function pointAtWallPosition(
  wall,
  position,
) {
  const t =
    clamp(
      numberOrNull(
        position,
      ) ?? 0.5,
      0,
      1,
    );

  return {
    x:
      Number(
        wall.start.x,
      ) +
      (
        Number(
          wall.end.x,
        ) -
        Number(
          wall.start.x,
        )
      ) *
      t,

    y:
      Number(
        wall.start.y,
      ) +
      (
        Number(
          wall.end.y,
        ) -
        Number(
          wall.start.y,
        )
      ) *
      t,
  };
}

function formatCoord(value) {
  if (!Number.isFinite(value)) {
    return "—";
  }

  return props.mode === "manual"
    ? `${value.toFixed(2)} m`
    : `${value.toFixed(0)} px`;
}

/* =========================================================
   NORMALIZACIÓN LEGACY/CANÓNICA
   ========================================================= */

function normalizeSpaceRecord(
  space,
) {
  if (
    !space ||
    typeof space !== "object"
  ) {
    return null;
  }

  const points =
    props.mode === "manual"
      ? metricVertices(space)
      : rasterVertices(space);

  if (points.length < 3) {
    return null;
  }

  let geometry = null;

  if (props.mode === "manual") {
    const canonical =
      normalizeGeometry(
        space.geometry ||
        space.geometria,
      );

    if (
      canonical?.vertices?.length >= 3
    ) {
      geometry =
        canonical;
    } else {
      geometry =
        geometryFromVertices(
          points,
          {
            type:
              isLegacyRectangle(
                space,
              )
                ? "rectangle"
                : "polygon",

            ...(isLegacyRectangle(
              space,
            )
              ? rectangleParamsFromLegacy(
                space,
                points,
              )
              : {}),
          },
        );
    }
  }

  return {
    id:
      String(
        space.id ?? "",
      ),

    raw: space,
    points,

    geometry,
  };
}

function metricVertices(space) {
  const canonical =
    normalizeGeometry(
      space?.geometry,
    );

  if (
    canonical
      ?.vertices
      ?.length >= 3
  ) {
    return canonical.vertices;
  }

  const candidates = [
    space?.geometria
      ?.metrica
      ?.vertices,

    space?.geometria
      ?.metric
      ?.vertices,

    space?.geometria
      ?.vertices,

    space?.geometria
      ?.verticesM,

    space?.verticesM,
  ];

  for (
    const candidate of candidates
  ) {
    const vertices =
      normalizeVertices(
        candidate,
      );

    if (
      vertices.length >= 3
    ) {
      return vertices;
    }
  }

  const x =
    numberOrNull(
      space?.xM ??
      space?.x ??
      space?.posicion?.xM,
    ) ?? 0;

  const y =
    numberOrNull(
      space?.yM ??
      space?.y ??
      space?.posicion?.yM,
    ) ?? 0;

  const width =
    numberOrNull(
      space?.anchoM ??
      space?.widthM,
    );

  const length =
    numberOrNull(
      space?.largoM ??
      space?.lengthM,
    );

  if (
    width > 0 &&
    length > 0
  ) {
    return rectFromXYWH({
      x,
      y,
      widthM: width,
      lengthM: length,
    }).vertices;
  }

  return [];
}

function rasterVertices(space) {
  const candidates = [
    space?.geometria
      ?.raster
      ?.vertices,

    space?.geometria
      ?.raster_px
      ?.vertices,

    space?.geometria
      ?.verticesRaster,

    space?.verticesRaster,
  ];

  for (
    const candidate of candidates
  ) {
    const vertices =
      normalizeVertices(
        candidate,
      );

    if (
      vertices.length >= 3
    ) {
      return vertices;
    }
  }

  return [];
}

function normalizeVertices(values) {
  if (!Array.isArray(values)) {
    return [];
  }

  return values
    .map((value) => {
      const x =
        numberOrNull(
          value?.x ??
          value?.xM ??
          value?.xPx,
        );

      const y =
        numberOrNull(
          value?.y ??
          value?.yM ??
          value?.yPx,
        );

      return (
        x === null ||
        y === null
      )
        ? null
        : {
          x,
          y,
        };
    })
    .filter(Boolean);
}

function isLegacyRectangle(
  space,
) {
  const type =
    String(
      space?.geometry?.type ||
      space?.geometria?.tipo ||
      "",
    )
      .trim()
      .toLowerCase();

  return (
    type === "rectangle" ||
    type === "rectangulo" ||
    (
      numberOrNull(
        space?.anchoM,
      ) > 0 &&
      numberOrNull(
        space?.largoM,
      ) > 0
    )
  );
}

function rectangleParamsFromLegacy(
  space,
  points,
) {
  const bbox =
    boundingBox(
      points,
    );

  return {
    x:
      numberOrNull(
        space?.xM ??
        space?.x,
      ) ??
      bbox.minX,

    y:
      numberOrNull(
        space?.yM ??
        space?.y,
      ) ??
      bbox.minY,

    widthM:
      numberOrNull(
        space?.anchoM ??
        space?.widthM,
      ) ??
      bbox.width,

    lengthM:
      numberOrNull(
        space?.largoM ??
        space?.lengthM,
      ) ??
      bbox.height,
  };
}

function canonicalGeometryToLegacy(
  geometry,
) {
  const normalized =
    normalizeGeometry(
      geometry,
    );

  if (!normalized) {
    return null;
  }

  return {
    tipo:
      normalized.type ===
        "rectangle"
        ? "rectangulo"
        : "poligono",

    metrica: {
      vertices:
        normalized.vertices,

      areaM2:
        normalized.areaM2,

      perimetroM:
        normalized.perimeterM,
    },
  };
}

function spaceMatchesActiveLevel(
  space,
) {
  if (space?.levelId) {
    return (
      space.levelId ===
      resolvedActiveLevelId.value
    );
  }

  const key =
    normalizeLevelKey(
      space?.nivel ||
      space?.level ||
      "planta_baja",
    );

  return (
    key ===
    resolvedActiveLevelKey.value
  );
}

function wallMatchesActiveLevel(
  wall,
) {
  if (wall?.levelId) {
    return (
      wall.levelId ===
      resolvedActiveLevelId.value
    );
  }

  const key =
    normalizeLevelKey(
      wall?.nivel ||
      wall?.level ||
      "planta_baja",
    );

  return (
    key ===
    resolvedActiveLevelKey.value
  );
}

function openingMatchesActiveLevel(
  opening,
) {
  if (opening?.levelId) {
    return (
      opening.levelId ===
      resolvedActiveLevelId.value
    );
  }

  const wall =
    modelWalls.value.find(
      (item) =>
        item.id ===
        opening?.wallId,
    );

  if (wall) {
    return wallMatchesActiveLevel(
      wall,
    );
  }

  const key =
    normalizeLevelKey(
      opening?.nivel ||
      "planta_baja",
    );

  return (
    key ===
    resolvedActiveLevelKey.value
  );
}

function dimensionMatchesActiveLevel(dimension) {
  const rawLevel = dimension?.nivel || dimension?.level;
  if (!rawLevel) return false;

  return (
    normalizeLevelKey(rawLevel) ===
    resolvedActiveLevelKey.value
  );
}

function resolvedLevelIdForSpace(
  space,
) {
  if (space?.levelId) {
    return space.levelId;
  }

  const key =
    resolvedLevelKeyForSpace(
      space,
    );

  return (
    modelLevels.value.find(
      (level) =>
        normalizeLevelKey(
          level.key ||
          level.name,
        ) === key,
    )?.id ||
    key
  );
}

function resolvedLevelKeyForSpace(
  space,
) {
  if (space?.levelId) {
    const level =
      modelLevels.value.find(
        (item) =>
          item.id ===
          space.levelId,
      );

    if (level) {
      return normalizeLevelKey(
        level.key ||
        level.name,
      );
    }
  }

  return normalizeLevelKey(
    space?.nivel ||
    space?.level ||
    resolvedActiveLevelKey.value,
  );
}

/* =========================================================
   MENSAJES / VALIDACIÓN
   ========================================================= */

function showValidation(
  validation,
) {
  const firstError =
    validation?.conflicts?.find(
      (item) =>
        item.severity ===
        "error",
    );

  const message =
    firstError?.message ||
    "La operación no es válida.";

  showMessage(
    message,
    "error",
  );

  emit(
    "validation-error",
    validation,
  );
}

function showMessage(
  text,
  type = "info",
) {
  editorMessage.value = {
    text,
    type,
  };

  if (messageTimer) {
    clearTimeout(
      messageTimer,
    );
  }

  messageTimer =
    setTimeout(() => {
      editorMessage.value =
        null;
    }, 3200);
}

/* =========================================================
   BASE IMAGE / RESIZE
   ========================================================= */

function loadBaseImage() {
  baseImage.value = null;

  const source =
    baseImageSource.value;

  if (
    !source ||
    typeof window ===
    "undefined"
  ) {
    return;
  }

  const image =
    new window.Image();

  image.onload = () => {
    baseImage.value =
      image;

    nextTick(() => {
      fitViewport();
    });
  };

  image.src =
    source;
}

let resizeFrame = null;

function resizeViewport() {
  const element =
    containerRef.value;

  if (!element) return;

  // clientWidth/clientHeight leen el espacio ya asignado por el padre.
  // El Stage no debe imponer un nuevo tamaño al contenedor porque eso
  // puede generar un ciclo ResizeObserver → Stage → contenedor.
  const nextWidth =
    Math.floor(
      element.clientWidth || 0,
    );

  const nextHeight =
    Math.floor(
      element.clientHeight || 0,
    );

  if (
    nextWidth <= 0 ||
    nextHeight <= 0
  ) {
    return;
  }

  if (
    Math.abs(
      viewportWidth.value -
      nextWidth,
    ) <= 1 &&
    Math.abs(
      viewportHeight.value -
      nextHeight,
    ) <= 1
  ) {
    return;
  }

  viewportWidth.value =
    nextWidth;

  viewportHeight.value =
    nextHeight;
}

function scheduleResizeViewport() {
  if (resizeFrame) {
    cancelAnimationFrame(
      resizeFrame,
    );
  }

  resizeFrame =
    requestAnimationFrame(() => {
      resizeFrame = null;
      resizeViewport();
    });
}

/* =========================================================
   WATCHERS
   ========================================================= */

watch(
  () => props.selectedId,
  (value) => {
    localSelectedId.value =
      value;

    if (
      value &&
      props.selectedType
    ) {
      localSelectedType.value =
        props.selectedType;
    } else if (!value) {
      localSelectedType.value =
        null;
    }

    editedSpaceId.value =
      null;

    editedVertices.value =
      null;
  },
);

watch(
  () => props.selectedType,
  (value) => {
    if (
      localSelectedId.value
    ) {
      localSelectedType.value =
        value || "space";
    }
  },
);

watch(
  () => props.activeTool,
  (tool) => {
    cancelDrawing();

    if (
      FIT_TOOLS.has(tool)
    ) {
      nextTick(() => {
        fitViewport();
      });
    }
  },
);

watch(
  [
    resolvedActiveLevelId,
    resolvedActiveLevelKey,
  ],
  () => {
    selectEntity(
      null,
      null,
    );

    cancelDrawing();
  },
);

watch(
  baseImageSource,
  loadBaseImage,
  {
    immediate: true,
  },
);

watch(
  () => [
    viewportWidth.value,
    viewportHeight.value,
  ],
  () => {
    // No hacemos fit automático en cada resize si el usuario ya está navegando.
    // Solo garantizamos que el stage mantenga dimensiones válidas.
  },
);

watch(
  () => props.gridSizeM,
  () => {
    currentSnap.value =
      null;
  },
);

/* =========================================================
   LIFECYCLE
   ========================================================= */

onMounted(() => {
  resizeViewport();

  resizeObserver =
    new ResizeObserver(
      scheduleResizeViewport,
    );

  if (
    containerRef.value
  ) {
    resizeObserver.observe(
      containerRef.value,
    );
  }

  window.addEventListener(
    "keydown",
    onKeyDown,
  );

  requestAnimationFrame(() => {
    if (contentBounds.value) {
      fitViewport();
    } else if (
      props.mode === "manual"
    ) {
      resetManualViewport();
    }
  });
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();

  window.removeEventListener(
    "keydown",
    onKeyDown,
  );

  if (resizeFrame) {
    cancelAnimationFrame(
      resizeFrame,
    );
    resizeFrame = null;
  }

  if (messageTimer) {
    clearTimeout(
      messageTimer,
    );
  }
});

/* =========================================================
   UTILS
   ========================================================= */

function layerVisible(name) {
  if (
    name === "grid" &&
    !props.showGrid
  ) {
    return false;
  }

  const aliases = {
    planoBase: [
      "planoBase",
      "basePlan",
    ],
    terreno: [
      "terreno",
      "terrain",
    ],
    grid: [
      "grid",
    ],
    espacios: [
      "espacios",
      "spaces",
    ],
    muros: [
      "muros",
      "walls",
    ],
    puertas: [
      "puertas",
      "doors",
    ],
    ventanas: [
      "ventanas",
      "windows",
    ],
    cotas: [
      "cotas",
      "dimensions",
    ],
    anotaciones: [
      "anotaciones",
      "annotations",
    ],
  };

  const candidates =
    aliases[name] || [name];

  for (
    const key of candidates
  ) {
    if (
      props.layers?.[key] ===
      false
    ) {
      return false;
    }
  }

  return true;
}

function flatten(vertices) {
  return vertices.flatMap(
    (point) => [
      Number(point.x),
      Number(point.y),
    ],
  );
}

function numberOrNull(value) {
  const parsed =
    Number(value);

  return Number.isFinite(
    parsed,
  )
    ? parsed
    : null;
}

function positiveNumberOrFallback(
  value,
  fallback,
) {
  const parsed =
    Number(value);

  return (
    Number.isFinite(parsed) &&
    parsed > 0
  )
    ? parsed
    : fallback;
}

function normalizeVisualScale(value) {
  return clamp(
    positiveNumberOrFallback(
      value,
      50,
    ),
    5,
    250,
  );
}

function clamp(
  value,
  min,
  max,
) {
  return Math.max(
    min,
    Math.min(
      max,
      Number(value),
    ),
  );
}

function isMultipleOf(
  value,
  step,
) {
  if (
    !Number.isFinite(value) ||
    !Number.isFinite(step) ||
    step <= 0
  ) {
    return false;
  }

  const ratio =
    value / step;

  return (
    Math.abs(
      ratio -
      Math.round(ratio),
    ) < 1e-8
  );
}

defineExpose({
  fitViewport,
  resetManualViewport,
  cancelDrawing,
  finishPolygon,
});
</script>

<style scoped>
.quantia-plan-editor {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  max-width: 100%;
  max-height: 100%;
  overflow: hidden;
  contain: layout paint size;
  border: 1px solid #d7dee8;
  border-radius: 16px;
  background:
    linear-gradient(180deg,
      #fbfcfe 0%,
      #f4f7fb 100%);
  user-select: none;
}

.quantia-plan-editor.is-plan-mode {
  background: #eef2f7;
}

.quantia-plan-editor.is-readonly {
  cursor: default;
}

.quantia-plan-editor :deep(canvas) {
  display: block;
}

.empty-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 8px;
  padding: 32px;
  text-align: center;
  color: #64748b;
  background:
    linear-gradient(180deg,
      #f8fafc 0%,
      #f1f5f9 100%);
}

.empty-state strong {
  color: #0f172a;
  font-size: 15px;
}

.empty-state span {
  max-width: 440px;
  font-size: 13px;
  line-height: 1.5;
}

.status-bar {
  position: absolute;
  right: 12px;
  bottom: 12px;
  z-index: 10;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 7px 10px;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  font-size: 12px;
  line-height: 1;
  pointer-events: none;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(8px);
}

.editor-message {
  position: absolute;
  left: 50%;
  top: 14px;
  z-index: 20;
  max-width: min(520px, calc(100% - 32px));
  transform: translateX(-50%);
  padding: 9px 13px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.96);
  color: #334155;
  font-size: 13px;
  line-height: 1.35;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
  pointer-events: none;
  backdrop-filter: blur(8px);
}

.editor-message.is-error {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(254, 242, 242, 0.97);
  color: #b91c1c;
}

.editor-message.is-success {
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(240, 253, 244, 0.97);
  color: #15803d;
}

@media (max-width: 720px) {
  .quantia-plan-editor {
    min-height: 0;
    border-radius: 12px;
  }

  .status-bar {
    left: 10px;
    right: auto;
    bottom: 10px;
    max-width: calc(100% - 20px);
    flex-wrap: wrap;
  }
}
</style>
