<template>
  <QuantiaWorkflowLayout :step="4" title="4. Diseño de la vivienda - Plano Base"
    subtitle="Revisa la reconstrucción generada a partir del plano, corrige la información necesaria y confirma el modelo antes de calcular cantidades.">
    <section class="qw-card reception-panel">
      <h3>Información recibida de 03</h3>
      <p>{{ receivedSummary }} · {{ store.estructuraEspacial?.schemaVersion || 'Sin contrato recibido' }}</p>
      <p v-if="store.estructuraEspacial?.revision">Revisión: {{ store.estructuraEspacial.revision }}</p>
      <p>Revisa la evidencia recibida y abre el editor métrico común para completar las propiedades. Ambas rutas de 04 entregan el mismo contrato a 05.</p>
      <details>
        <summary>Evidencia y elementos pendientes</summary>
        <p>Los candidatos no se convierten automáticamente en puertas, ventanas o muros confirmados.</p>
        <div v-for="bucket in evidenceGroups" :key="bucket.label">
          <h4>{{ bucket.label }} ({{ bucket.items.length }})</h4>
          <details v-for="(item, index) in bucket.items" :key="index">
            <summary>{{ item.id || item.family_hint || item.source_wall?.id || `Elemento ${index + 1}` }}</summary>
            <pre>{{ JSON.stringify(item, null, 2) }}</pre>
          </details>
        </div>
      </details>

    </section>
    <Workflow04Bridge plan-review :spatial-model="{...spatialContract, espacios: sanitizedSpaces()}" @open-editor="persistSpatialContract()" @imported="router.go(0)" />
    <section class="design-summary">
      <div class="qw-card summary-card">
        <small>Área construida</small>
        <strong>{{ formatMetricWithUnit(totalAreaM2, "m²") }}</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área interior</small>
        <strong>{{ formatMetricWithUnit(areaInteriorM2, "m²") }}</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área exterior</small>
        <strong>{{ formatMetricWithUnit(areaExteriorM2, "m²") }}</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área libre</small>
        <strong>{{ formatMetricWithUnit(areaLibreM2, "m²") }}</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Estado</small>
        <span class="qw-pill" :class="validationMessages.length ? 'warning' : 'green'">
          {{ validationMessages.length ? "Por revisar" : "Espacios revisados" }}
        </span>
      </div>
    </section>

    <section class="manual-layout">
      <aside class="spaces-panel qw-card">
        <div class="panel-heading">
          <div>
            <h3>Espacios del proyecto</h3>
            <small>{{ visibleSpaces.length }} visibles</small>
          </div>
          <span class="qw-pill">{{ spatial.espacios.length }}</span>
        </div>

        <label class="field">
          <span>Nivel visible</span>
          <select v-model="activeLevel" class="qw-input">
            <option v-for="option in levelOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <input v-model="search" class="qw-input" placeholder="Buscar espacio" />

        <div class="spaces-list">
          <button v-for="space in filteredSpaces" :key="space.id" type="button" class="space-item"
            :class="{ active: selectedId === space.id }" @click="selectSpace(space.id)">
            <div>
              <strong>{{ spaceLabel(space) }}</strong>
              <small>{{ usageLabel(space.tipo) }} · {{ levelLabel(space.nivel) }}</small>
            </div>

            <div class="space-item-meta">
              <span>{{ formatMetricWithUnit(space.areaM2, "m²") }}</span>
              <span class="status-dot" :class="{ confirmed: space.confirmed }">
                {{ space.confirmed ? "Confirmado" : "Pendiente" }}
              </span>
            </div>
          </button>
        </div>

      </aside>

      <article class="editor-column qw-card">
        <div class="editor-toolbar">
          <button type="button" :class="{ active: activeTool === 'select' }" @click="setTool('select')">
            ↖ Seleccionar
          </button>

          <button type="button" :class="{ active: activeTool === 'pan' }" @click="setTool('pan')">
            ✋ Mano
          </button>

          <span class="toolbar-separator"></span>

          <button type="button" @click="fitEditor">
            ⛶ Ajustar
          </button>

          <span class="toolbar-separator"></span>

          <button type="button" :class="{ active: editorLayers.planoBase }"
            @click="editorLayers.planoBase = !editorLayers.planoBase">
            ▣ Plano base
          </button>

          <button type="button" :class="{ active: editorLayers.espacios }"
            @click="editorLayers.espacios = !editorLayers.espacios">
            ▢ Espacios
          </button>

          <button type="button" :class="{ active: editorLayers.muros }"
            @click="editorLayers.muros = !editorLayers.muros">
            ║ Muros
          </button>

          <button type="button" :class="{ active: editorLayers.cotas }"
            @click="editorLayers.cotas = !editorLayers.cotas">
            ↔ Cotas
          </button>
        </div>
        <div class="level-tabs">
          <button v-for="option in levelOptions" :key="option.value" type="button"
            :class="{ active: activeLevel === option.value }" @click="activeLevel = option.value">
            {{ option.short }}
          </button>

        </div>

        <div class="editor-wrapper">
          <QuantiaPlanEditor ref="editorRef" mode="plan" :spatial-model="spatialContract"
            :base-layer-url="baseLayerObjectUrl" :active-level="activeLevel"
            :active-tool="activeTool" :selected-id="selectedId" :layers="editorLayers" @select="handleEditorSelect" />
        </div>

        <div class="editor-help">
          <span v-if="baseLayerLoadError">
            {{ baseLayerLoadError }}
          </span>

          <span v-if="activeTool === 'select'">
            Selecciona un espacio detectado para revisar la información obtenida del plano.
          </span>

          <span v-else-if="activeTool === 'pan'">
            Arrastra el plano para desplazarte por la reconstrucción.
          </span>

          <span v-else>
            Revisa el plano original y las capas reconstruidas por Quantia.
          </span>
        </div>
      </article>

      <aside class="properties-panel qw-card">
        <template v-if="selected">
          <div class="panel-heading">
            <div>
              <h3>Propiedades del espacio</h3>
              <small>{{ selected.id }}</small>
            </div>

            <span class="qw-pill" :class="selected.confirmed ? 'green' : 'warning'">
              {{ selected.confirmed ? "Confirmado" : "Pendiente" }}
            </span>
          </div>

          <label class="field">
            <span>Nombre</span>
            <input v-model.trim="selected.nombre" class="qw-input" placeholder="Ej. Recámara de visitas"
              @input="markSelectedDirty" />
          </label>

          <label class="field">
            <span>Uso</span>
            <select v-model="selected.tipo" class="qw-input" @change="markSelectedDirty">
              <option value="">Seleccionar uso...</option>

              <optgroup v-for="group in usageGroups" :key="group.label" :label="group.label">
                <option v-for="option in group.options" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </optgroup>
            </select>
          </label>

          <label class="field">
            <span>Nivel</span>
            <select v-model="selected.nivel" class="qw-input" @change="handleSelectedLevelChange">
              <option v-for="option in levelOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <div class="section-title">Geometría</div>

          <div class="two-columns">
            <label class="field">
              <span>X (m)</span>
              <input v-model.number="selected.xM" class="qw-input" type="number" min="0" step="0.01"
                @change="applyRectangleInputs" />
            </label>

            <label class="field">
              <span>Y (m)</span>
              <input v-model.number="selected.yM" class="qw-input" type="number" min="0" step="0.01"
                @change="applyRectangleInputs" />
            </label>
          </div>

          <div class="two-columns">
            <label class="field">
              <span>Ancho (m)</span>
              <input v-model.number="selected.anchoM" class="qw-input" type="number" min="0" step="0.01"
                :disabled="selected.geometria?.tipo === 'poligono'" @change="applyRectangleInputs" />
            </label>

            <label class="field">
              <span>Largo (m)</span>
              <input v-model.number="selected.largoM" class="qw-input" type="number" min="0" step="0.01"
                :disabled="selected.geometria?.tipo === 'poligono'" @change="applyRectangleInputs" />
            </label>
          </div>

          <div class="metric-readout">
            <div>
              <small>Área</small>
              <strong>{{ formatMetricWithUnit(selected.areaM2, "m²") }}</strong>
              <span>Automático</span>
            </div>

            <div>
              <small>Perímetro</small>
              <strong>{{ formatMetricWithUnit(selected.perimetroM, "m") }}</strong>
              <span>Automático</span>
            </div>
          </div>

          <div v-if="selected.dimensiones?.length" class="property-readout dimension-readout">
            <span>Dimensiones grounded</span>
            <strong v-for="dimension in selected.dimensiones" :key="dimension.id">
              {{ String(dimension.eje || "").toUpperCase() }}:
              {{ formatMetricWithUnit(dimension.valorM, "m") }}
              · {{ dimension.ejeInicio }}→{{ dimension.ejeFin }}
              · {{ dimension.estado }}
            </strong>
          </div>

          <label class="check-field">
            <input v-model="selected.dobleAltura" type="checkbox" @change="markSelectedDirty" />
            <span>Doble altura</span>
          </label>

          <div class="section-title">Estado</div>

          <div class="property-readout">
            <span>Altura del nivel</span>
            <strong>{{ formatMetric(heightForLevel(selected.nivel)) }} m</strong>
          </div>

          <div class="property-readout">
            <span>Origen</span>
            <strong>
              {{ originLabel(selected.origen) }}
            </strong>
          </div>

          <div class="property-readout">
            <span>Estado 03.2</span>
            <strong>{{ selected.estado || "PENDIENTE" }}</strong>
          </div>

          <div class="property-readout">
            <span>Confianza IA</span>
            <strong>
              {{
                selected.confianzaIA === null ||
                  selected.confianzaIA === undefined
                  ? "Sin dato"
                  : selected.confianzaIA
              }}
            </strong>
          </div>
          <div class="property-actions">
            <button type="button" class="confirm-button" @click="confirmSelected">
              ✓ Confirmar espacio
            </button>

            <button type="button" class="delete-button" @click="deleteSelected">
              × Eliminar
            </button>
          </div>
        </template>

        <div v-else class="empty-properties">
          <strong>Sin selección</strong>
          <span>
            Dibuja un espacio o selecciona uno existente para editar sus propiedades.
          </span>
        </div>
      </aside>
    </section>

    <div v-if="flowError" class="flow-error">
      {{ flowError }}
    </div>

    <template #footer>
      <button type="button" class="qw-btn" @click="goBack">
        ← Anterior
      </button>

      <span>Unidad: metros (m)</span>

      <button type="button" class="qw-btn primary" :disabled="!spatial.espacios.length" @click="continueFlow">
        Continuar →
      </button>
    </template>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import Workflow04Bridge from "@/components/design/Workflow04Bridge.vue";
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";

import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/authStore";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";

import QuantiaPlanEditor from "@/components/design/QuantiaPlanEditor.vue";

import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import { obtenerPlanoBaseDocumento } from "@/modules/vivienda/services/documentosApiService";

import "@/assets/styles/quantia-workflow.css";

const router = useRouter();
const auth = useAuthStore();
const store = useViviendaStore();
const receivedSummary = computed(() => {
  const data = store.estructuraEspacial || {};
  return `${data.niveles?.length || 0} niveles · ${data.muros?.length || 0} muros · ${data.espacios?.length || 0} espacios`;
});
const evidenceGroups = computed(() => {
  const data = store.estructuraEspacial || {};
  return [
    { label: "Elementos arquitectónicos", items: data.buckets?.ARCHITECTURAL_ELEMENT || [] },
    { label: "Gráficos excluidos conservados", items: data.buckets?.EXCLUDED_GRAPHIC || [] },
    { label: "Sin resolver", items: data.buckets?.UNRESOLVED || [] },
    { label: "Candidatos de Call 2", items: data.call2Candidates || [] },
    { label: "Regiones inciertas de Call 2", items: data.call2Unresolved || [] },
  ];
});
const editorRef = ref(null);

const search = ref("");
const activeTool = ref("select");
const activeLevel = ref("planta_baja");
const selectedId = ref(null);
const flowError = ref("");
const baseLayerObjectUrl = ref("");
const baseLayerLoadError = ref("");

function releaseBaseLayerObjectUrl() {
  if (baseLayerObjectUrl.value) {
    URL.revokeObjectURL(baseLayerObjectUrl.value);
    baseLayerObjectUrl.value = "";
  }
}

async function loadCanonicalBaseLayer() {
  const metadata = store.estructuraEspacial?.metadata || {};
  if (metadata.requiresLocalRasterUrl) {
    baseLayerLoadError.value = "03 debe entregar una URL del recorte local del nivel para superponer el plano. Los muros pueden revisarse sin imagen base.";
    return;
  }
  const documentId = String(metadata.sourceDocumentId || "").trim();

  if (!documentId || store.estructuraEspacial?.planoBase?.referencia) {
    return;
  }

  const fileName = String(metadata.sourceFileName || "").toLowerCase();
  const pdfRenderScale = toNullableNumber(metadata.sourcePdfRenderScale);

  if (fileName.endsWith(".pdf") && pdfRenderScale === null) {
    baseLayerLoadError.value =
      "No se conservó la escala raster del análisis; vuelve a ejecutar 03.2.";
    return;
  }

  try {
    baseLayerLoadError.value = "";
    const blob = await obtenerPlanoBaseDocumento({
      documentId,
      accessToken: auth.accessToken || "",
      pageNumber: Number(metadata.sourcePageNumber || 1),
      pdfRenderScale,
    });
    releaseBaseLayerObjectUrl();
    baseLayerObjectUrl.value = URL.createObjectURL(blob);
  } catch (error) {
    baseLayerLoadError.value =
      error?.message || "No fue posible cargar el plano base.";
  }
}

onMounted(loadCanonicalBaseLayer);
onBeforeUnmount(releaseBaseLayerObjectUrl);

const showGrid = ref(true);
const snapToGrid = ref(true);
const gridSizeM = ref(0.5);

const editorLayers = reactive({
  planoBase: true,
  espacios: true,
  muros: true,
  puertas: true,
  ventanas: true,
  cotas: true,
});

const usageGroups = [
  {
    label: "Habitables",
    options: [
      { value: "recamara_principal", label: "Recámara principal" },
      { value: "recamara_2", label: "Recámara 2" },
      { value: "recamara_3", label: "Recámara 3" },
      { value: "recamara_4", label: "Recámara 4" },
      { value: "sala", label: "Sala" },
      { value: "estancia", label: "Estancia" },
      { value: "estudio", label: "Estudio" },
    ],
  },
  {
    label: "Servicios",
    options: [
      { value: "bano_1", label: "Baño 1" },
      { value: "bano_2", label: "Baño 2" },
      { value: "medio_bano", label: "Medio baño" },
      { value: "cocina", label: "Cocina" },
      { value: "comedor", label: "Comedor" },
      { value: "cuarto_servicio", label: "Cuarto de servicio" },
      { value: "almacen", label: "Almacén" },
    ],
  },
  {
    label: "Circulación",
    options: [
      { value: "pasillo_interior", label: "Pasillo interior" },
      { value: "escalera_1", label: "Escalera 1" },
      { value: "escalera_2", label: "Escalera 2" },
      { value: "escalera_3", label: "Escalera 3" },
    ],
  },
  {
    label: "Exteriores",
    options: [
      { value: "terraza", label: "Terraza" },
      { value: "patio_servicio", label: "Patio de servicio" },
      { value: "patio_exterior", label: "Patio exterior" },
      { value: "cochera", label: "Cochera" },
      { value: "jardin", label: "Jardín" },
      { value: "barda_perimetral", label: "Barda perimetral" },
    ],
  },
];

const usageMap = new Map(
  usageGroups.flatMap((group) =>
    group.options.map((option) => [
      option.value,
      option.label,
    ])
  )
);

function normalizeToken(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\s-]+/g, "_");
}

function normalizeLevel(value) {
  const normalized = normalizeToken(value);

  const aliases = {
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

    azotea: "planta_azotea",
    planta_azotea: "planta_azotea",
  };

  return aliases[normalized] || normalized;
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toNullableNumber(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function roundMetric(value) {
  const parsed = toNullableNumber(value);

  return parsed === null
    ? null
    : Number(parsed.toFixed(2));
}

function normalizeOrigins(value) {
  if (Array.isArray(value)) {
    return value.filter(
      (item) =>
        item &&
        typeof item === "object",
    );
  }

  if (
    value &&
    typeof value === "object"
  ) {
    return [value];
  }

  return [];
}

function originLabel(value) {
  const origins =
    normalizeOrigins(value);

  if (!origins.length) {
    return "Análisis asistido";
  }

  const labels = origins
    .map((origin) => {
      const documento =
        String(
          origin?.documento || "",
        ).trim();

      const fuente =
        String(
          origin?.fuente || "",
        ).trim();

      if (documento && fuente) {
        return `${documento} · ${fuente}`;
      }

      return documento || fuente;
    })
    .filter(Boolean);

  return (
    labels.join(" | ") ||
    "Análisis asistido"
  );
}

function polygonArea(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 3) {
    return 0;
  }

  let sum = 0;

  for (let index = 0; index < vertices.length; index += 1) {
    const current = vertices[index];
    const next = vertices[(index + 1) % vertices.length];

    sum += (
      toNumber(current?.x) * toNumber(next?.y) -
      toNumber(next?.x) * toNumber(current?.y)
    );
  }

  return roundMetric(Math.abs(sum) / 2);
}

function polygonPerimeter(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 2) {
    return 0;
  }

  let total = 0;

  for (let index = 0; index < vertices.length; index += 1) {
    const current = vertices[index];
    const next = vertices[(index + 1) % vertices.length];

    total += Math.hypot(
      toNumber(next?.x) - toNumber(current?.x),
      toNumber(next?.y) - toNumber(current?.y),
    );
  }

  return roundMetric(total);
}

function boundingBox(vertices) {
  if (!Array.isArray(vertices) || !vertices.length) {
    return {
      x: 0,
      y: 0,
      width: 0,
      height: 0,
    };
  }

  const xs = vertices.map((point) => toNumber(point?.x));
  const ys = vertices.map((point) => toNumber(point?.y));

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    x: roundMetric(minX),
    y: roundMetric(minY),
    width: roundMetric(maxX - minX),
    height: roundMetric(maxY - minY),
  };
}

function normalizeMetricVertices(space) {
  const geometry = space?.geometria || {};

  const values =
    geometry?.metrica?.vertices ||
    geometry?.vertices ||
    [];

  if (!Array.isArray(values)) {
    return [];
  }

  return values
    .map((point) => {
      const x = Number(point?.x ?? point?.xM);
      const y = Number(point?.y ?? point?.yM);

      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        return null;
      }

      return { x, y };
    })
    .filter(Boolean);
}

function normalizeSpace(item, index) {
  const vertices =
    normalizeMetricVertices(item);

  const hasMetricVertices =
    vertices.length >= 2;

  const box = hasMetricVertices
    ? boundingBox(vertices)
    : null;

  const explicitWidth =
    toNullableNumber(item?.anchoM);

  const explicitHeight =
    toNullableNumber(item?.largoM);

  const width =
    explicitWidth ??
    (box ? box.width : null);

  const height =
    explicitHeight ??
    (box ? box.height : null);

  const metricArea =
    vertices.length >= 3
      ? polygonArea(vertices)
      : null;

  const metricPerimeter =
    vertices.length >= 2
      ? polygonPerimeter(vertices)
      : null;

  const explicitArea =
    toNullableNumber(
      item?.areaM2 ??
      item?.geometria?.metrica?.areaM2 ??
      item?.geometria?.areaM2,
    );

  const explicitPerimeter =
    toNullableNumber(
      item?.perimetroM ??
      item?.geometria?.metrica?.perimetroM ??
      item?.geometria?.perimetroM,
    );

  const resolvedArea =
    explicitArea ??
    metricArea ??
    (
      width !== null &&
        height !== null &&
        width > 0 &&
        height > 0
        ? roundMetric(
          width * height,
        )
        : null
    );

  const resolvedPerimeter =
    explicitPerimeter ??
    metricPerimeter ??
    (
      width !== null &&
        height !== null &&
        width > 0 &&
        height > 0
        ? roundMetric(
          2 * (width + height),
        )
        : null
    );

  const geometry = {
    ...(item?.geometria || {}),
  };

  if (vertices.length >= 3) {
    geometry.metrica = {
      ...(item?.geometria?.metrica || {}),
      vertices,
      areaM2: resolvedArea,
      perimetroM:
        resolvedPerimeter,
    };
  }

  return {
    ...item,

    id: String(
      item?.id ||
      item?.document_id ||
      `space-${index + 1}`,
    ),

    nombre: String(
      item?.nombre || "",
    ),

    tipo: normalizeToken(
      item?.tipo,
    ),

    nivel: normalizeLevel(
      item?.nivel || "",
    ),

    xM:
      toNullableNumber(
        item?.xM,
      ) ??
      (box ? box.x : null),

    yM:
      toNullableNumber(
        item?.yM,
      ) ??
      (box ? box.y : null),

    anchoM:
      roundMetric(width),

    largoM:
      roundMetric(height),

    areaM2:
      roundMetric(
        resolvedArea,
      ),

    perimetroM:
      roundMetric(
        resolvedPerimeter,
      ),

    dobleAltura:
      Boolean(item?.dobleAltura),

    confirmed:
      Boolean(item?.confirmed),

    estado:
      item?.estado ?? null,

    confianzaIA:
      item?.confianzaIA ?? null,

    origen:
      normalizeOrigins(
        item?.origen,
      ),

    geometria: geometry,
  };
}

const general = reactive({
  anchoTerrenoM: toNumber(
    store.datosGeneralesObra?.anchoTerrenoM,
    0,
  ),
  largoTerrenoM: toNumber(
    store.datosGeneralesObra?.largoTerrenoM,
    0,
  ),
  niveles: Math.max(
    0,
    Math.min(
      3,
      toNumber(store.datosGeneralesObra?.niveles, 0),
    ),
  ),
  alturaNivel1M: toNumber(
    store.datosGeneralesObra?.alturaNivel1M,
    0,
  ),
  alturaNivel2M: toNumber(
    store.datosGeneralesObra?.alturaNivel2M,
    0,
  ),
  alturaNivel3M: toNumber(
    store.datosGeneralesObra?.alturaNivel3M,
    0,
  ),
});

const spatial = reactive({
  espacios: (store.estructuraEspacial?.espacios || [])
    .map(normalizeSpace),
});

const terrain = computed(() => ({
  anchoM: general.anchoTerrenoM,
  largoM: general.largoTerrenoM,
}));

const levelOptions = computed(() => {
  const options = [];
  const seen = new Set();

  const labels = {
    planta_baja: "Planta Baja",
    segunda_planta: "Planta Alta",
    tercera_planta: "Tercera Planta",
    planta_azotea: "Azotea",
  };

  const shorts = {
    planta_baja: "PB",
    segunda_planta: "PA",
    tercera_planta: "P3",
    planta_azotea: "AZ",
  };

  const pushLevel = (
    rawValue,
    preferredLabel = "",
  ) => {
    const value = normalizeLevel(rawValue);

    if (!value || seen.has(value)) {
      return;
    }

    seen.add(value);

    options.push({
      value,
      label:
        preferredLabel ||
        labels[value] ||
        String(value).replaceAll("_", " "),
      short:
        shorts[value] ||
        String(value).slice(0, 3).toUpperCase(),
    });
  };

  const contractLevels =
    Array.isArray(store.estructuraEspacial?.niveles)
      ? store.estructuraEspacial.niveles
      : [];

  for (const level of contractLevels) {
    pushLevel(
      level?.key ||
      level?.nombre ||
      level?.name ||
      level?.id,
      level?.etiqueta ||
      level?.label ||
      level?.nombre ||
      level?.name ||
      "",
    );
  }

  for (const space of spatial.espacios) {
    pushLevel(space?.nivel);
  }

  if (!options.length && general.niveles > 0) {
    pushLevel("planta_baja");

    if (general.niveles >= 2) {
      pushLevel("segunda_planta");
    }

    if (general.niveles >= 3) {
      pushLevel("tercera_planta");
    }
  }

  return options;
});

watch(
  levelOptions,
  (options) => {
    if (!options.some((item) => item.value === activeLevel.value)) {
      activeLevel.value = options[0]?.value || "planta_baja";
    }
  },
  { immediate: true },
);

const selected = computed(() =>
  spatial.espacios.find(
    (space) => space.id === selectedId.value,
  ) || null
);

const visibleSpaces = computed(() =>
  spatial.espacios.filter((space) => {
    const level = normalizeLevel(space.nivel);

    return (
      !level ||
      level === activeLevel.value
    );
  })
);

const filteredSpaces = computed(() => {
  const query = search.value.trim().toLowerCase();

  return visibleSpaces.value.filter((space) => {
    if (!query) {
      return true;
    }

    const haystack = [
      spaceLabel(space),
      usageLabel(space.tipo),
      levelLabel(space.nivel),
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

const spatialContract = computed(() => {
  const sourceLevels =
    Array.isArray(store.estructuraEspacial?.niveles)
      ? store.estructuraEspacial.niveles
      : [];

  const niveles = sourceLevels.length
    ? sourceLevels.map((level) => {
      const key = normalizeLevel(
        level?.key ||
        level?.nombre ||
        level?.name ||
        level?.id,
      );

      return {
        ...level,
        key,
        name:
          level?.name ||
          level?.nombre ||
          level?.etiqueta ||
          key,
      };
    })
    : levelOptions.value.map((item) => ({
      id: item.value,
      key: item.value,
      name: item.label,
      nombre: item.value,
      etiqueta: item.label,
    }));

  return {
    ...store.estructuraEspacial,
    niveles,
    espacios: spatial.espacios,
  };
});

function sumKnownAreas(spaces) {
  if (!spaces.length) {
    return 0;
  }

  const values =
    spaces.map(
      (space) =>
        toNullableNumber(
          space?.areaM2,
        ),
    );

  if (
    values.some(
      (value) =>
        value === null,
    )
  ) {
    return null;
  }

  return roundMetric(
    values.reduce(
      (sum, value) =>
        sum + value,
      0,
    ),
  );
}

const areaTerrenoM2 =
  computed(() => {
    if (
      general.anchoTerrenoM <= 0 ||
      general.largoTerrenoM <= 0
    ) {
      return null;
    }

    return roundMetric(
      general.anchoTerrenoM *
      general.largoTerrenoM,
    );
  });

const exteriorTypes = new Set([
  "terraza",
  "patio_servicio",
  "patio_exterior",
  "cochera",
  "jardin",
  "barda_perimetral",
]);

const areaExteriorM2 =
  computed(() =>
    sumKnownAreas(
      spatial.espacios.filter(
        (space) =>
          exteriorTypes.has(
            space.tipo,
          ),
      ),
    ),
  );

const areaInteriorM2 =
  computed(() =>
    sumKnownAreas(
      spatial.espacios.filter(
        (space) =>
          !exteriorTypes.has(
            space.tipo,
          ),
      ),
    ),
  );

const footprintAreaM2 =
  computed(() => {
    const byLevel =
      new Map();

    for (
      const space of
      spatial.espacios
    ) {
      if (
        space.nivel ===
        "planta_azotea"
      ) {
        continue;
      }

      const area =
        toNullableNumber(
          space.areaM2,
        );

      if (area === null) {
        return null;
      }

      byLevel.set(
        space.nivel,
        (
          byLevel.get(
            space.nivel,
          ) || 0
        ) + area,
      );
    }

    return byLevel.size
      ? roundMetric(
        Math.max(
          ...byLevel.values(),
        ),
      )
      : 0;
  });

const areaLibreM2 =
  computed(() => {
    if (
      areaTerrenoM2.value ===
      null ||
      footprintAreaM2.value ===
      null
    ) {
      return null;
    }

    return roundMetric(
      Math.max(
        areaTerrenoM2.value -
        footprintAreaM2.value,
        0,
      ),
    );
  });

const totalAreaM2 = computed(() =>
  sumKnownAreas(spatial.espacios)
);

const validationMessages = computed(() => {
  const messages = [];
  if (store.estructuraEspacial?.readiness?.workflowContinuation === false) {
    messages.push("La información recibida de 03 está pendiente de parametrización. Puedes revisar y guardar la plantilla para 05.");
  }

  if (
    general.anchoTerrenoM <= 0 ||
    general.largoTerrenoM <= 0
  ) {
    messages.push("Faltan las dimensiones del terreno.");
  }

  if (!spatial.espacios.length) {
    messages.push("No existen espacios registrados.");
  }

  for (const space of spatial.espacios) {
    if (!space.tipo) {
      messages.push(
        `Selecciona el uso de ${spaceLabel(space)}.`,
      );
      break;
    }

    const metricArea =
      toNullableNumber(
        space.areaM2,
      );

    if (metricArea !== null && metricArea <= 0) {
      messages.push(
        `${spaceLabel(space)} tiene un área métrica inválida.`,
      );
      break;
    }

    if (!space.confirmed) {
      messages.push("Existen espacios pendientes de confirmar.");
      break;
    }
  }

  if (
    areaTerrenoM2.value !== null &&
    footprintAreaM2.value !== null &&
    areaTerrenoM2.value > 0 &&
    footprintAreaM2.value >
    areaTerrenoM2.value
  ) {
    messages.push(
      "La huella construida supera el área del terreno.",
    );
  }

  return [...new Set(messages)];
});

function usageLabel(value) {
  return usageMap.get(normalizeToken(value)) || "Sin uso";
}

function levelLabel(value) {
  return (
    levelOptions.value.find(
      (option) => option.value === normalizeLevel(value),
    )?.label ||
    String(value || "Sin nivel")
  );
}

function spaceLabel(space) {
  return (
    String(space?.nombre || "").trim() ||
    usageLabel(space?.tipo) ||
    "Espacio"
  );
}

function formatMetric(value) {
  const parsed =
    toNullableNumber(value);

  return parsed === null
    ? "Sin determinar"
    : parsed.toFixed(2);
}

function formatMetricWithUnit(
  value,
  unit,
) {
  const parsed =
    toNullableNumber(value);

  return parsed === null
    ? "Sin determinar"
    : `${parsed.toFixed(2)} ${unit}`;
}

function heightForLevel(level) {
  const normalized = normalizeLevel(level);

  if (normalized === "planta_baja") {
    return general.alturaNivel1M;
  }

  if (normalized === "segunda_planta") {
    return general.alturaNivel2M;
  }

  if (normalized === "tercera_planta") {
    return general.alturaNivel3M;
  }

  return 0;
}

function selectSpace(id) {
  selectedId.value = id || null;

  const space = selected.value;

  if (space) {
    activeLevel.value = normalizeLevel(space.nivel);
  }

  activeTool.value = "select";
}

function handleEditorSelect(id) {
  selectedId.value = id || null;
}

function setTool(tool) {
  activeTool.value = tool;
  flowError.value = "";
}

function fitEditor() {
  editorRef.value?.fitViewport?.();
}

function prepareNewSpace() {
  selectedId.value = null;
  activeTool.value = "rectangle";
  flowError.value = "";
}

function handleCreateSpace(payload) {
  const nextNumber = spatial.espacios.length + 1;

  const space = normalizeSpace(
    {
      ...payload,
      id: `manual-${Date.now()}`,
      nombre: `Espacio ${nextNumber}`,
      tipo: "",
      nivel: normalizeLevel(
        payload?.nivel || activeLevel.value,
      ),
      estado: "PENDIENTE",
      confirmed: false,
      origen: {
        fuente: "usuario",
      },
    },
    spatial.espacios.length,
  );

  spatial.espacios.push(space);
  selectedId.value = space.id;
  activeTool.value = "select";
  flowError.value = "";
}

function handleUpdateGeometry(payload) {
  const space = spatial.espacios.find(
    (item) => item.id === payload?.id,
  );

  if (!space) {
    return;
  }

  const vertices =
    payload?.geometria?.metrica?.vertices ||
    payload?.vertices ||
    [];

  const normalizedVertices = Array.isArray(vertices)
    ? vertices.map((point) => ({
      x: roundMetric(point?.x),
      y: roundMetric(point?.y),
    }))
    : [];

  const box = boundingBox(normalizedVertices);
  const area = polygonArea(normalizedVertices);
  const perimeter = polygonPerimeter(normalizedVertices);

  space.xM = box.x;
  space.yM = box.y;
  space.anchoM = box.width;
  space.largoM = box.height;
  space.areaM2 = area;
  space.perimetroM = perimeter;

  space.geometria = {
    ...(space.geometria || {}),
    ...(payload?.geometria || {}),
    tipo:
      payload?.geometria?.tipo ||
      space.geometria?.tipo ||
      "poligono",
    metrica: {
      ...(space.geometria?.metrica || {}),
      ...(payload?.geometria?.metrica || {}),
      vertices: normalizedVertices,
      areaM2: area,
      perimetroM: perimeter,
    },
  };

  space.confirmed = false;
  space.estado = "PENDIENTE";
  flowError.value = "";
}

function applyRectangleInputs() {
  const space = selected.value;

  if (!space) {
    return;
  }

  if (space.geometria?.tipo === "poligono") {
    return;
  }

  const x = Math.max(0, toNumber(space.xM));
  const y = Math.max(0, toNumber(space.yM));
  const width = Math.max(0, toNumber(space.anchoM));
  const height = Math.max(0, toNumber(space.largoM));

  const vertices = (
    width > 0 && height > 0
      ? [
        { x, y },
        { x: x + width, y },
        { x: x + width, y: y + height },
        { x, y: y + height },
      ]
      : []
  );

  const area = polygonArea(vertices);
  const perimeter = polygonPerimeter(vertices);

  space.xM = roundMetric(x);
  space.yM = roundMetric(y);
  space.anchoM = roundMetric(width);
  space.largoM = roundMetric(height);
  space.areaM2 = area;
  space.perimetroM = perimeter;

  space.geometria = {
    ...(space.geometria || {}),
    tipo: "rectangulo",
    metrica: {
      ...(space.geometria?.metrica || {}),
      vertices,
      areaM2: area,
      perimetroM: perimeter,
    },
  };

  markSelectedDirty();
}

function markSelectedDirty() {
  if (!selected.value) {
    return;
  }

  selected.value.confirmed = false;
  flowError.value = "";
}

function handleSelectedLevelChange() {
  if (!selected.value) {
    return;
  }

  selected.value.nivel = normalizeLevel(selected.value.nivel);
  activeLevel.value = selected.value.nivel;
  markSelectedDirty();
}

function confirmSelected() {
  const space = selected.value;

  if (!space) {
    return;
  }

  if (!space.tipo) {
    flowError.value = "Selecciona el uso del espacio antes de confirmarlo.";
    return;
  }

  const metricArea = toNullableNumber(space.areaM2);

  if (metricArea !== null && metricArea <= 0) {
    flowError.value = "El espacio debe tener una geometría válida.";
    return;
  }

  space.confirmed = true;
  flowError.value = "";
  persistSpatialContract();
}

function deleteSelected() {
  if (!selected.value) {
    return;
  }

  const id = selected.value.id;

  spatial.espacios = spatial.espacios.filter(
    (space) => space.id !== id,
  );

  selectedId.value = null;
  flowError.value = "";
}

function sanitizedSpaces() {
  return spatial.espacios.map((space) => {
    const vertices =
      normalizeMetricVertices(space);

    const area =
      vertices.length >= 3
        ? polygonArea(vertices)
        : roundMetric(space.areaM2);

    const perimeter =
      vertices.length >= 2
        ? polygonPerimeter(vertices)
        : roundMetric(space.perimetroM);

    const geometry = {
      ...(space.geometria || {}),
    };

    if (vertices.length >= 3) {
      geometry.metrica = {
        ...(space.geometria?.metrica || {}),
        vertices,
        areaM2: area,
        perimetroM: perimeter,
      };
    }

    return {
      ...space,
      nivel: normalizeLevel(space.nivel),
      tipo: normalizeToken(space.tipo),
      areaM2: area,
      perimetroM: perimeter,
      confirmed: Boolean(space.confirmed),
      confianzaIA: space.confianzaIA ?? null,
      origen:
        normalizeOrigins(
          space.origen,
        ), geometria: geometry,
    };
  });
}

function persistSpatialContract(payload = null) {
  const spatialPayload =
    payload || {
      ...store.estructuraEspacial,

      niveles:
        spatialContract.value.niveles,

      espacios:
        sanitizedSpaces(),

      engineInputs:
        store.estructuraEspacial?.engineInputs || {},

      engineInputsByConcept:
        store.estructuraEspacial?.engineInputsByConcept || {},
    };

  store.setEstructuraEspacial(spatialPayload);
}

function continueFlow() {
  flowError.value = "";

  if (validationMessages.value.length) {
    flowError.value =
      validationMessages.value[0];

    return;
  }

  // ------------------------------------------------------------
  // Capturar el contrato COMPLETO antes de actualizar datos
  // generales, porque setDatosGeneralesObra() puede resetear
  // estructuraEspacial si detecta cambios estructurales.
  // ------------------------------------------------------------

  const spatialPayload = {
    ...store.estructuraEspacial,

    niveles:
      Array.isArray(
        spatialContract.value?.niveles,
      )
        ? spatialContract.value.niveles
        : [],

    espacios:
      sanitizedSpaces(),

    engineInputs:
      store.estructuraEspacial?.engineInputs || {},

    engineInputsByConcept:
      store.estructuraEspacial?.engineInputsByConcept || {},
  };

  const heights = [
    general.alturaNivel1M,
    general.alturaNivel2M,
    general.alturaNivel3M,
  ]
    .slice(0, general.niveles)
    .filter((value) => value > 0);

  const averageHeight =
    heights.length
      ? roundMetric(
        heights.reduce(
          (sum, value) =>
            sum + value,
          0,
        ) / heights.length,
      )
      : 0;

  store.setDatosGeneralesObra({
    ...store.datosGeneralesObra,

    anchoTerrenoM:
      general.anchoTerrenoM,

    largoTerrenoM:
      general.largoTerrenoM,

    areaTerrenoM2:
      areaTerrenoM2.value,

    areaConstruccionM2:
      totalAreaM2.value,

    niveles:
      general.niveles,

    alturaPromedioM:
      averageHeight,

    alturaNivel1M:
      general.alturaNivel1M,

    alturaNivel2M:
      general.alturaNivel2M,

    alturaNivel3M:
      general.alturaNivel3M,

    engineInputs: {
      ...(store.datosGeneralesObra
        ?.engineInputs || {}),

      modo_diseno:
        "subir_plano",

      alturas_nivel:
        heights,
    },

    engineInputsByConcept:
      store.datosGeneralesObra
        ?.engineInputsByConcept || {},
  });

  // Si el store reseteó estructuraEspacial,
  // restauramos ahora el contrato capturado completo.
  persistSpatialContract(
    spatialPayload,
  );

  store.setValidacionEspacial({
    ...store.validacionEspacial,

    revisado: true,

    alertas:
      store.validacionEspacial
        ?.alertas || [],
  });

  router.push(
    "/vivienda/workflow/calculo-cantidades",
  );
}

function goBack() {
  router.push("/vivienda/workflow/planos-revision/analisis");
}
</script>

<style scoped>
.reception-panel { padding: 18px; margin-bottom: 16px; overflow-wrap: anywhere; }
.reception-panel details { margin-top: 12px; }
.reception-panel summary { cursor: pointer; font-weight: 600; }
.reception-panel pre { max-height: 260px; overflow: auto; white-space: pre-wrap; font-size: 12px; }
.reception-panel button { margin: 8px 8px 0 0; }
.design-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.summary-card {
  min-height: 82px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.summary-card small {
  color: #64748b;
}

.summary-card strong {
  color: #0f172a;
  font-size: 1.35rem;
}

.manual-layout {
  display: grid;
  grid-template-columns:
    minmax(220px, 0.78fr) minmax(560px, 2.35fr) minmax(270px, 0.95fr);
  gap: 14px;
  align-items: stretch;
}

.spaces-panel,
.properties-panel,
.editor-column {
  min-width: 0;
}

.spaces-panel,
.properties-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.panel-heading h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.panel-heading small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
}

.field {
  display: grid;
  gap: 6px;
}

.field>span {
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
}

.spaces-list {
  display: grid;
  gap: 8px;
  max-height: 540px;
  overflow: auto;
}

.space-item {
  width: 100%;
  display: grid;
  gap: 8px;
  padding: 11px 12px;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.space-item:hover {
  border-color: #93c5fd;
}

.space-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.space-item strong,
.space-item small {
  display: block;
}

.space-item small {
  margin-top: 3px;
  color: #64748b;
}

.space-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  color: #334155;
  font-size: 0.78rem;
}

.status-dot {
  color: #92400e;
}

.status-dot.confirmed {
  color: #166534;
}


.editor-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 670px;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  padding-bottom: 2px;
}

.editor-toolbar button,
.level-tabs button {
  border: 1px solid #dbe3ee;
  border-radius: 9px;
  padding: 8px 10px;
  background: #fff;
  color: #334155;
  font-weight: 600;
  cursor: pointer;
}

.editor-toolbar button.active,
.level-tabs button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.toolbar-separator {
  width: 1px;
  height: 26px;
  margin: 0 2px;
  background: #e2e8f0;
}

.level-tabs {
  display: flex;
  align-items: center;
  gap: 7px;
}

.editor-wrapper {
  flex: 1;
  min-height: 560px;
  overflow: hidden;
  border: 1px solid #dbe3ee;
  border-radius: 12px;
  background: #f8fafc;
}

.editor-help {
  color: #64748b;
  font-size: 0.82rem;
}

.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.section-title {
  margin-top: 3px;
  padding-top: 9px;
  border-top: 1px solid #edf2f7;
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-readout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.metric-readout>div {
  display: grid;
  gap: 3px;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
}

.metric-readout small,
.metric-readout span {
  color: #64748b;
}

.metric-readout strong {
  color: #0f172a;
}

.metric-readout span {
  font-size: 0.72rem;
}

.check-field {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #334155;
}

.property-readout {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5f9;
  color: #64748b;
  font-size: 0.82rem;
}

.property-readout strong {
  max-width: 58%;
  color: #0f172a;
  text-align: right;
  overflow-wrap: anywhere;
}

.property-actions {
  display: grid;
  gap: 8px;
  margin-top: auto;
}

.confirm-button,
.delete-button {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  font-weight: 700;
  cursor: pointer;
}

.confirm-button {
  background: #166534;
  color: #fff;
}

.delete-button {
  background: #fee2e2;
  color: #991b1b;
}

.empty-properties {
  flex: 1;
  display: grid;
  place-content: center;
  gap: 7px;
  min-height: 260px;
  text-align: center;
  color: #64748b;
}

.empty-properties strong {
  color: #0f172a;
}

.flow-error {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fef2f2;
  color: #991b1b;
}

@media (max-width: 1280px) {
  .manual-layout {
    grid-template-columns: 220px minmax(500px, 1fr);
  }

  .properties-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .design-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .manual-layout {
    grid-template-columns: 1fr;
  }

  .properties-panel {
    grid-column: auto;
  }

  .editor-column {
    min-height: 620px;
  }
}

.editor-toolbar button {
  flex: 1 1 auto;
}

.level-tabs {
  flex-wrap: wrap;
}
</style>
