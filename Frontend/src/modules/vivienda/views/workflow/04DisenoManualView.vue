<template>
  <QuantiaWorkflowLayout :step="4" :title="editorState.metadata?.sourceMode === 'plan' ? '4. Editor de vivienda desde plano' : '4. Editor de vivienda manual'"
    subtitle="Edita la geometría y confirma las propiedades constructivas. Se conservan los datos de 01 y 02 y la evidencia recibida de 03.">
    <!-- =========================================================
         RESUMEN
         ========================================================= -->
    <section class="design-summary">
      <div class="qw-card summary-card">
        <small>Área construida</small>
        <strong>{{ formatMetric(totalAreaM2) }} m²</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área interior</small>
        <strong>{{ formatMetric(areaInteriorM2) }} m²</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área exterior</small>
        <strong>{{ formatMetric(areaExteriorM2) }} m²</strong>
      </div>

      <div class="qw-card summary-card">
        <small>Área libre</small>
        <strong>
          {{ areaLibreM2 === null ? "—" : `${formatMetric(areaLibreM2)} m²` }}
        </strong>
      </div>

      <div class="qw-card summary-card">
        <small>Estado</small>
        <span class="qw-pill" :class="validationMessages.length ? 'warning' : 'green'">
          {{ validationMessages.length ? "Por revisar" : "Espacios revisados" }}
        </span>
      </div>
    </section>

    <!-- =========================================================
         LAYOUT PRINCIPAL
         ========================================================= -->
    <section class="manual-layout">
      <!-- =======================================================
           PANEL IZQUIERDO
           ======================================================= -->
      <aside class="spaces-panel qw-card">
        <div class="panel-heading">
          <div>
            <h3>Modelo de vivienda</h3>
            <small>
              {{ editorState.spaces.length }} espacios ·
              {{ structuralLevels.length }} niveles
              <template v-if="hasRoofLevel"> · azotea</template>
            </small>
          </div>

          <span class="qw-pill">
            {{ confirmedSpacesCount }}/{{ editorState.spaces.length }}
          </span>
        </div>

        <div class="side-tabs">
          <button type="button" :class="{ active: sideTab === 'spaces' }" @click="sideTab = 'spaces'">
            Espacios
          </button>

          <button type="button" :class="{ active: sideTab === 'uses' }" @click="sideTab = 'uses'">
            Usos
          </button>

          <button type="button" :class="{ active: sideTab === 'levels' }" @click="sideTab = 'levels'">
            Niveles
          </button>
        </div>

        <!-- ESPACIOS -->
        <template v-if="sideTab === 'spaces'">
          <label class="field">
            <span>Nivel visible</span>

            <select v-model="activeLevelId" class="qw-input" :disabled="!levelOptions.length"
              @change="handleActiveLevelChange">
              <option v-if="!levelOptions.length" value="">
                Sin niveles definidos
              </option>

              <option v-for="option in levelOptions" :key="option.id" :value="option.id">
                {{ option.label }}
              </option>
            </select>
          </label>

          <input v-model="search" class="qw-input" placeholder="Buscar espacio" />

          <div v-if="filteredSpaces.length" class="spaces-list">
            <button v-for="space in filteredSpaces" :key="space.id" type="button" class="space-item" :class="{
              active:
                selectedEntityType === 'space' &&
                selectedEntityId === space.id,
            }" @click="selectSpace(space.id)">
              <div>
                <strong>{{ spaceLabel(space) }}</strong>
                <small>
                  {{ usageLabel(space.usageCode || space.tipo) }}
                  ·
                  {{ levelLabel(space.levelId || space.nivel) }}
                </small>
              </div>

              <div class="space-item-meta">
                <span>{{ formatMetric(space.areaM2) }} m²</span>

                <span class="status-dot" :class="{ confirmed: space.confirmed }">
                  {{ space.confirmed ? "Confirmado" : "Pendiente" }}
                </span>
              </div>
            </button>
          </div>

          <div v-else class="panel-empty">
            <span v-if="!activeLevelId">
              Primero agrega o selecciona un nivel.
            </span>

            <span v-else>
              No hay espacios en este nivel.
            </span>
          </div>

          <button type="button" class="add-space" :disabled="!activeLevelId" @click="prepareNewSpace">
            ＋ Agregar espacio
          </button>
        </template>

        <!-- USOS -->
        <template v-else-if="sideTab === 'uses'">
          <div class="usage-help">
            <strong>Catálogo de usos</strong>
            <span>
              Selecciona un espacio y asigna su uso sin escribir categorías libres.
            </span>
          </div>

          <div v-for="group in usageGroups" :key="group.label" class="usage-group">
            <small>{{ group.label }}</small>

            <button v-for="option in group.options" :key="option.value" type="button" class="usage-option"
              :disabled="selectedEntityType !== 'space'" :class="{
                active:
                  selectedSpace &&
                  selectedSpace.usageCode === option.value,
              }" @click="applyUsage(option, group.category)">
              {{ option.label }}
            </button>
          </div>
        </template>

        <!-- NIVELES -->
        <template v-else>
          <div class="level-count-card">
            <label class="field">
              <span>Cantidad de niveles</span>

              <div class="level-count-row">
                <input v-model="levelCountDraft" class="qw-input" type="number" min="1" step="1" placeholder="Ej. 2"
                  @keyup.enter="applyLevelCount" />

                <button type="button" class="apply-button compact-action" @click="applyLevelCount">
                  Aplicar
                </button>
              </div>

              <small>
                La azotea se controla por separado y no cuenta como nivel habitable.
              </small>
            </label>
          </div>

          <div v-if="levelOptions.length" class="levels-list">
            <div v-for="level in levelOptions" :key="level.id" class="level-config-row" :class="{
              active:
                activeLevelId === level.id ||
                (
                  selectedEntityType === 'level' &&
                  selectedEntityId === level.id
                ),
            }">
              <button type="button" class="level-select-button" @click="selectLevel(level.id)">
                <div>
                  <strong>{{ level.label }}</strong>
                  <small>{{ level.key }}</small>
                </div>

                <span>{{ level.short }}</span>
              </button>

              <label class="inline-height">
                <span>Altura (m)</span>

                <input v-model="level.raw.heightM" class="qw-input compact-height" type="number" min="0" step="0.01"
                  placeholder="Pendiente" @change="commitInlineLevelHeight(level.raw)" />
              </label>
            </div>
          </div>

          <div v-else class="panel-empty">
            <span>
              Define la cantidad de niveles para comenzar.
            </span>
          </div>

          <div class="level-actions">
            <button type="button" class="add-space" @click="increaseLevelCount">
              ＋ Agregar nivel
            </button>

            <button v-if="!hasRoofLevel" type="button" class="secondary-action" @click="addRoofLevel">
              ＋ Azotea
            </button>

            <button v-else type="button" class="secondary-action" @click="selectRoofLevel">
              Editar azotea
            </button>
          </div>
        </template>
      </aside>

      <!-- =======================================================
           EDITOR CENTRAL
           ======================================================= -->
      <article class="editor-column qw-card">
        <div class="editor-toolbar">
          <button type="button" :class="{ active: activeTool === 'select' }" @click="setTool('select')">
            ↖ Seleccionar
          </button>

          <button type="button" :class="{ active: activeTool === 'pan' }" @click="setTool('pan')">
            ✋ Mano
          </button>

          <span class="toolbar-separator"></span>

          <button type="button" :class="{ active: activeTool === 'rectangle' }" @click="setTool('rectangle')">
            ▭ Rectángulo
          </button>

          <button type="button" :class="{ active: activeTool === 'polygon' }" @click="setTool('polygon')">
            ⬡ Polígono
          </button>

          <button type="button" :class="{ active: activeTool === 'wall' }" @click="setTool('wall')">
            ╱ Muro
          </button>

          <button type="button" :class="{ active: activeTool === 'door' }" @click="setTool('door')">
            ⌞ Puerta
          </button>

          <button type="button" :class="{ active: activeTool === 'window' }" @click="setTool('window')">
            ╫ Ventana
          </button>

          <button type="button" :class="{ active: activeTool === 'garage' }" @click="setTool('garage')">Portón</button>
          <button type="button" :class="{ active: activeTool === 'stair' }" @click="setTool('stair')">Escalera</button>
          <button type="button" :class="{ active: activeTool === 'measure' }" @click="setTool('measure')">
            ↔ Medir
          </button>

          <span class="toolbar-separator"></span>

          <button type="button" title="Deshacer" :disabled="!historyState.canUndo" @click="undo">
            ↶
          </button>

          <button type="button" title="Rehacer" :disabled="!historyState.canRedo" @click="redo">
            ↷
          </button>

          <button type="button" @click="fitEditor">
            ⛶ Ajustar
          </button>

          <button type="button" :class="{ active: showGrid }" @click="showGrid = !showGrid">
            # Grid
          </button>

          <button type="button" :class="{ active: snapEnabled }" @click="snapEnabled = !snapEnabled">
            ⊕ Snap
          </button>

          <details class="layers-menu">
            <summary>Capas</summary>

            <div class="layers-popover">
              <label v-for="layer in layerControls" :key="layer.key">
                <input v-model="editorLayers[layer.key]" type="checkbox" />
                <span>{{ layer.label }}</span>
              </label>
            </div>
          </details>
        </div>

        <div class="level-tabs">
          <button v-for="option in levelOptions" :key="option.id" type="button"
            :class="{ active: activeLevelId === option.id }" @click="setActiveLevel(option.id)">
            {{ option.short }}
          </button>

          <span v-if="!levelOptions.length" class="no-level-chip">
            Sin nivel
          </span>

          <label class="grid-size">
            Grid
            <select v-model.number="gridSizeM" class="qw-input compact">
              <option :value="0.25">0.25 m</option>
              <option :value="0.5">0.50 m</option>
              <option :value="1">1.00 m</option>
            </select>
          </label>
        </div>

        <div class="editor-wrapper">
          <QuantiaPlanEditor ref="editorRef" mode="manual" :spatial-model="editorState"
            :active-level-id="activeLevelId || null" :active-level="activeLevelKey" :terrain="terrainCompat"
            :active-tool="activeTool" :selected-id="selectedEntityId" :selected-type="selectedEntityType"
            :grid-size-m="gridSizeM" :show-grid="showGrid" :snap-to-grid="snapEnabled" :snap-enabled="snapEnabled"
            :layers="editorLayers" @select-entity="handleEditorSelectEntity" @create-space="handleCreateSpace"
            @update-space-geometry="handleUpdateGeometry" @move-space="handleMoveSpace" @create-wall="handleCreateWall"
            @create-door="handleCreateDoor" @create-window="handleCreateWindow" @measure="handleMeasurement"
            @validation-error="handleEditorValidation" />
        </div>

        <div class="editor-help">
          <span v-if="activeTool === 'garage'">Haz clic sobre un muro para colocar el portón. Define sus dimensiones y apertura en el inspector.</span>
          <span v-else-if="activeTool === 'stair'">Arrastra la huella de la escalera; después define niveles, tramos y descansos.</span>
          <span v-else-if="activeTool === 'rectangle'">
            Arrastra para crear un espacio rectangular. X, Y, ancho y largo se calculan automáticamente.
          </span>

          <span v-else-if="activeTool === 'polygon'">
            Haz clic para agregar nodos. Cierra sobre el primer nodo o presiona Enter.
          </span>

          <span v-else-if="activeTool === 'wall'">
            Arrastra entre dos puntos para crear un muro.
          </span>

          <span v-else-if="activeTool === 'door'">
            Haz clic sobre un muro. La puerta queda ligada al muro y después defines sus medidas.
          </span>

          <span v-else-if="activeTool === 'window'">
            Haz clic sobre un muro. La ventana queda ligada al muro y después defines sus medidas.
          </span>

          <span v-else-if="activeTool === 'measure'">
            Marca dos puntos para medir una distancia.
          </span>

          <span v-else-if="activeTool === 'select'">
            Selecciona un elemento para editar sus propiedades. Los solapes entre espacios se bloquean.
          </span>

          <span v-else>
            Arrastra el lienzo para desplazarte.
          </span>
        </div>

        <div v-if="lastMeasurement" class="measurement-chip">
          Última medida:
          <strong>{{ formatMetric(lastMeasurement.distance) }} m</strong>
          <button type="button" @click="lastMeasurement = null">
            ×
          </button>
        </div>
      </article>

      <!-- =======================================================
           INSPECTOR DERECHO
           ======================================================= -->
      <aside class="properties-panel qw-card">
        <!-- ESPACIO -->
        <template v-if="selectedEntityType === 'space' && selectedSpace">
          <div class="panel-heading">
            <div>
              <h3>Propiedades del espacio</h3>
              <small>{{ selectedSpace.id }}</small>
            </div>

            <span class="qw-pill" :class="selectedSpace.confirmed ? 'green' : 'warning'">
              {{ selectedSpace.confirmed ? "Confirmado" : "Pendiente" }}
            </span>
          </div>

          <label class="field">
            <span>Nombre</span>
            <input v-model.trim="spaceDraft.name" class="qw-input" placeholder="Ej. Recámara de visitas" />
          </label>

          <label class="field">
            <span>Uso</span>

            <select v-model="spaceDraft.usageCode" class="qw-input" @change="syncUsageDraft">
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

            <select v-model="spaceDraft.levelId" class="qw-input">
              <option v-for="option in levelOptions" :key="option.id" :value="option.id">
                {{ option.label }}
              </option>
            </select>
          </label>

          <div class="section-title-row">
            <div class="section-title no-border">Geometría</div>

            <button type="button" class="geometry-edit-button" :class="{ active: geometryEditMode }"
              @click="geometryEditMode = !geometryEditMode">
              {{ geometryEditMode ? "Cerrar edición" : "Editar geometría" }}
            </button>
          </div>

          <div class="geometry-guidance">
            Arrastra la figura directamente en el lienzo para cambiar su posición.
            X e Y se actualizan automáticamente. Usa “Editar geometría” para un
            ajuste numérico preciso.
          </div>

          <div class="two-columns">
            <label class="field">
              <span>X (m)</span>
              <input v-model.number="spaceDraft.x" class="qw-input" type="number" step="0.01"
                :disabled="!geometryEditMode" />
            </label>

            <label class="field">
              <span>Y (m)</span>
              <input v-model.number="spaceDraft.y" class="qw-input" type="number" step="0.01"
                :disabled="!geometryEditMode" />
            </label>
          </div>

          <div class="two-columns">
            <label class="field">
              <span>Ancho (m)</span>
              <input v-model.number="spaceDraft.widthM" class="qw-input" type="number" min="0" step="0.01" :disabled="!geometryEditMode ||
                selectedSpaceGeometry?.type !== 'rectangle'
                " />
            </label>

            <label class="field">
              <span>Largo (m)</span>
              <input v-model.number="spaceDraft.lengthM" class="qw-input" type="number" min="0" step="0.01" :disabled="!geometryEditMode ||
                selectedSpaceGeometry?.type !== 'rectangle'
                " />
            </label>
          </div>

          <div class="metric-readout">
            <div>
              <small>Área</small>
              <strong>{{ formatMetric(selectedSpace.areaM2) }} m²</strong>
              <span>Automático</span>
            </div>

            <div>
              <small>Perímetro</small>
              <strong>{{ formatMetric(selectedSpace.perimeterM) }} m</strong>
              <span>Automático</span>
            </div>
          </div>

          <label class="check-field">
            <input v-model="spaceDraft.doubleHeight" type="checkbox" />
            <span>Doble altura</span>
          </label>

          <label class="field">
            <span>Altura excepcional (m)</span>
            <input v-model="spaceDraft.heightM" class="qw-input" type="number" min="0" step="0.01"
              placeholder="Hereda del nivel" />
            <small>
              Déjalo vacío para usar la altura general del nivel.
            </small>
          </label>

          <div class="property-readout">
            <span>Altura del nivel</span>
            <strong>
              {{
                selectedSpaceLevel?.heightM
                  ? `${formatMetric(selectedSpaceLevel.heightM)} m`
                  : "Pendiente"
              }}
            </strong>
          </div>

          <div class="property-actions">
            <button type="button" class="apply-button" @click="applySpaceProperties">
              Aplicar cambios
            </button>

            <button type="button" class="confirm-button" @click="confirmSelectedSpace">
              ✓ Confirmar espacio
            </button>

            <button type="button" class="delete-button" @click="deleteSelectedEntity">
              × Eliminar
            </button>
          </div>
        </template>

        <template v-else-if="['wall','door','window','stair'].includes(selectedEntityType)">
          <div class="panel-heading"><h3>Elemento seleccionado</h3><small>{{ selectedEntityId }}</small></div>
          <button v-if="selectedEntityType !== 'stair'" type="button" class="delete-button" @click="deleteSelectedEntity">Eliminar elemento</button>
        </template>

        <!-- NIVEL -->
        <template v-else-if="selectedEntityType === 'level' && selectedLevel">
          <div class="panel-heading">
            <div>
              <h3>Propiedades del nivel</h3>
              <small>{{ selectedLevel.key }}</small>
            </div>

            <span class="qw-pill" :class="hasValidLevelHeight(selectedLevel) ? 'green' : 'warning'">
              {{ hasValidLevelHeight(selectedLevel) ? "Listo" : "Falta altura" }}
            </span>
          </div>

          <label class="field">
            <span>Nombre visible</span>
            <input v-model.trim="levelDraft.name" class="qw-input" />
          </label>

          <label class="field">
            <span>Altura del nivel (m)</span>
            <input v-model="levelDraft.heightM" class="qw-input" type="number" min="0" step="0.01"
              placeholder="Obligatoria para calcular" />
          </label>

          <label class="field">
            <span>Elevación (m)</span>
            <input v-model="levelDraft.elevationM" class="qw-input" type="number" step="0.01" placeholder="Pendiente" />
          </label>

          <div class="property-readout">
            <span>Espacios en este nivel</span>
            <strong>{{ spacesForLevel(selectedLevel.id).length }}</strong>
          </div>

          <div class="property-actions">
            <button type="button" class="apply-button" @click="applyLevelProperties">
              Aplicar cambios
            </button>

            <button type="button" class="delete-button" @click="deleteSelectedEntity">
              × Eliminar nivel
            </button>
          </div>
        </template>

        <!-- PROYECTO -->
        <template v-else>
          <div class="panel-heading">
            <div>
              <h3>Proyecto</h3>
              <small>Configuración del editor</small>
            </div>
          </div>

          <div class="project-note">
            <strong>El terreno es opcional.</strong>
            <span>
              Puedes comenzar a dibujar sin terreno. Si lo defines, Quantia lo usa como límite geométrico.
            </span>
          </div>

          <div class="section-title">Terreno rectangular</div>

          <div class="two-columns">
            <label class="field">
              <span>Ancho (m)</span>
              <input v-model="terrainDraft.widthM" class="qw-input" type="number" min="0" step="0.01"
                placeholder="Opcional" />
            </label>

            <label class="field">
              <span>Largo (m)</span>
              <input v-model="terrainDraft.lengthM" class="qw-input" type="number" min="0" step="0.01"
                placeholder="Opcional" />
            </label>
          </div>

          <button type="button" class="apply-button" @click="applyTerrain">
            Aplicar terreno
          </button>

          <button v-if="editorState.terrain" type="button" class="secondary-action full" @click="removeTerrain">
            Quitar terreno
          </button>

          <div class="section-title">Niveles</div>

          <div class="property-readout">
            <span>Definidos</span>
            <strong>{{ structuralLevels.length }}</strong>
          </div>

          <div class="property-readout">
            <span>Con altura pendiente</span>
            <strong>{{ missingHeightLevels.length }}</strong>
          </div>

          <div class="project-note compact">
            <span>
              La altura puede quedar pendiente mientras dibujas, pero es obligatoria antes de pasar a Cálculo de
              cantidades.
            </span>
          </div>
        </template>
        <ConstructionInspector :state="editorState" :selected-id="selectedEntityId" :selected-type="selectedEntityType"
          @select="handleEditorSelectEntity" @update-entity="updateConstructionEntity" @remove-stair="removeConstructionStair"
          @completeness="value => { editorState.completeness = {...editorState.completeness, ...value}; commitState('Revisar completitud'); }" />
      </aside>
    </section>

    <Workflow04Bridge :state="editorState" @imported="reloadImportedModel" />
    <!-- =========================================================
         VALIDACIÓN DE FLUJO
         ========================================================= -->
    <div v-if="flowError" class="flow-error">
      {{ flowError }}
    </div>

    <div v-else-if="validationMessages.length" class="flow-warning">
      <strong>Pendiente para continuar:</strong>
      <span>{{ validationMessages[0] }}</span>
    </div>

    <template #footer>
      <button type="button" class="qw-btn" @click="goBack">
        ← Anterior
      </button>

      <span>Unidad: metros (m)</span>

      <button type="button" class="qw-btn primary" :disabled="!editorState.spaces.length" @click="continueFlow">
        Continuar →
      </button>
    </template>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import {
  computed,
  reactive,
  ref,
  watch,
} from "vue";

import { useRouter } from "vue-router";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import ConstructionInspector from "@/components/design/ConstructionInspector.vue";
import Workflow04Bridge from "@/components/design/Workflow04Bridge.vue";
import QuantiaPlanEditor from "@/components/design/QuantiaPlanEditor.vue";

import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";

import {
  applyEditorStateToViviendaStore,
  editorStateFromViviendaStore,
} from "@/modules/vivienda/editor/adapters/viviendaStoreAdapter";

import {
  getMissingRequiredLevelHeights,
  levelKeyFromNumber,
  levelNameFromNumber,
} from "@/modules/vivienda/editor/adapters/projectConfigAdapter";

import {
  createDoor,
  createStair,
  createEntityId,
  createLevel,
  createSourceInfo,
  createSpace,
  createTerrain,
  createWall,
  createWindow,
  nowIso,
} from "@/modules/vivienda/editor/core/editorSchema";

import {
  boundingBox,
  geometryFromVertices,
  normalizeGeometry,
  polygonArea,
  rectFromXYWH,
  segmentAngle,
  segmentLength,
  translateGeometry,
} from "@/modules/vivienda/editor/core/geometry";

import {
  canRemoveLevel,
  addLevel,
  normalizeLevelKey,
  normalizeLevels,
  removeLevelCascade,
  updateLevel,
} from "@/modules/vivienda/editor/core/levels";

import {
  validateOpening,
  validateReadyForCalculation,
  validateSpaceCandidate,
} from "@/modules/vivienda/editor/core/constraints";

import {
  reconcileWallGraph,
  removeSpaceAndReconcile,
  translateExclusiveWallsForSpace,
  updateSpaceWallRelations,
} from "@/modules/vivienda/editor/core/wallGraph";

import {
  cascadeRemoveOpeningsForWalls,
  remapOpeningsAfterWallReconcile,
  wallPointAtPosition,
} from "@/modules/vivienda/editor/core/openings";

import {
  createEditorHistory,
} from "@/modules/vivienda/editor/core/history";

import "@/assets/styles/quantia-workflow.css";

const router = useRouter();
const store = useViviendaStore();

const editorRef = ref(null);

const editorState = ref(
  editorStateFromViviendaStore(store),
);

const requestedProjectLevelCount =
  positiveIntegerOrZero(
    store.datosGeneralesObra?.niveles,
  );

seedMissingStructuralLevels(
  editorState.value,
  requestedProjectLevelCount,
);

const history = createEditorHistory();
history.reset(editorState.value, "Estado inicial");

const historyState = ref(history.getSummary());

const search = ref("");
const sideTab = ref("spaces");

const activeTool = ref("select");
const selectedEntityType = ref(null);
const selectedEntityId = ref(null);

const geometryEditMode = ref(false);

const levelCountDraft = ref(
  requestedProjectLevelCount ||
  countStructuralLevels(
    editorState.value.levels,
  ) ||
  "",
);

const activeLevelId = ref(
  editorState.value.activeLevelId ||
  editorState.value.levels[0]?.id ||
  "",
);

const flowError = ref("");
const lastMeasurement = ref(null);

const showGrid = ref(
  editorState.value.editorSettings?.showGrid !== false,
);

const snapEnabled = ref(
  editorState.value.editorSettings?.snapEnabled !== false,
);

const gridSizeM = ref(
  positiveNumberOrFallback(
    editorState.value.editorSettings?.gridSizeM,
    0.5,
  ),
);

const editorLayers = reactive({
  planoBase: false,
  terreno: true,
  grid: true,
  espacios: true,
  muros: true,
  puertas: true,
  ventanas: true,
  cotas: true,
  anotaciones: false,
});

const layerControls = [
  { key: "terreno", label: "Terreno" },
  { key: "grid", label: "Grid" },
  { key: "espacios", label: "Espacios" },
  { key: "muros", label: "Muros" },
  { key: "puertas", label: "Puertas" },
  { key: "ventanas", label: "Ventanas" },
  { key: "cotas", label: "Cotas" },
];

const usageGroups = [
  {
    label: "Habitables",
    category: "habitable",
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
    category: "servicio",
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
    category: "circulacion",
    options: [
      { value: "pasillo_interior", label: "Pasillo interior" },
      { value: "escalera_1", label: "Escalera 1" },
      { value: "escalera_2", label: "Escalera 2" },
      { value: "escalera_3", label: "Escalera 3" },
    ],
  },
  {
    label: "Exteriores",
    category: "exterior",
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

const usageInfoMap = new Map(
  usageGroups.flatMap((group) =>
    group.options.map((option) => [
      option.value,
      {
        ...option,
        category: group.category,
      },
    ]),
  ),
);

const spaceDraft = reactive({
  name: "",
  usageCode: "",
  usageLabel: "",
  category: "",
  levelId: "",
  x: 0,
  y: 0,
  widthM: 0,
  lengthM: 0,
  doubleHeight: false,
  heightM: "",
});

const wallDraft = reactive({
  type: "uncertain",
  thicknessM: "",
  heightM: "",
});

const doorDraft = reactive({
  position: 0.5,
  widthM: "",
  heightM: "",
  swingDirection: "unknown",
});

const windowDraft = reactive({
  position: 0.5,
  widthM: "",
  heightM: "",
  sillHeightM: "",
});

const levelDraft = reactive({
  name: "",
  heightM: "",
  elevationM: "",
});

const terrainDraft = reactive({
  widthM: "",
  lengthM: "",
});

/* =========================================================
   COMPUTED — NIVELES
   ========================================================= */

const orderedLevels = computed(() =>
  [...editorState.value.levels]
    .sort((a, b) => Number(a.order) - Number(b.order)),
);

const levelOptions = computed(() =>
  orderedLevels.value.map((level, index) => ({
    id: level.id,
    key: normalizeLevelKey(level.key || level.name),
    label: level.name || levelLabelFromKey(level.key),
    short: shortLevelLabel(level, index),
    raw: level,
  })),
);

const activeLevel = computed(() =>
  editorState.value.levels.find(
    (level) => level.id === activeLevelId.value,
  ) || null,
);

const activeLevelKey = computed(() =>
  normalizeLevelKey(
    activeLevel.value?.key ||
    "planta_baja",
  ),
);

const hasRoofLevel = computed(() =>
  editorState.value.levels.some(
    (level) =>
      normalizeLevelKey(level.key) === "planta_azotea",
  ),
);

const structuralLevels = computed(() =>
  orderedLevels.value.filter(
    (level) =>
      normalizeLevelKey(level.key) !== "planta_azotea",
  ),
);

const missingHeightLevels = computed(() =>
  getMissingRequiredLevelHeights(
    editorState.value.levels,
    editorState.value.spaces,
  ),
);

/* =========================================================
   COMPUTED — SELECCIÓN
   ========================================================= */

const selectedSpace = computed(() =>
  selectedEntityType.value === "space"
    ? editorState.value.spaces.find(
      (item) => item.id === selectedEntityId.value,
    ) || null
    : null,
);

const selectedWall = computed(() =>
  selectedEntityType.value === "wall"
    ? editorState.value.walls.find(
      (item) => item.id === selectedEntityId.value,
    ) || null
    : null,
);

const selectedDoor = computed(() =>
  selectedEntityType.value === "door"
    ? editorState.value.doors.find(
      (item) => item.id === selectedEntityId.value,
    ) || null
    : null,
);

const selectedWindow = computed(() =>
  selectedEntityType.value === "window"
    ? editorState.value.windows.find(
      (item) => item.id === selectedEntityId.value,
    ) || null
    : null,
);

const selectedLevel = computed(() =>
  selectedEntityType.value === "level"
    ? editorState.value.levels.find(
      (item) => item.id === selectedEntityId.value,
    ) || null
    : null,
);

const selectedSpaceGeometry = computed(() =>
  selectedSpace.value
    ? normalizeGeometry(selectedSpace.value.geometry)
    : null,
);

const selectedSpaceLevel = computed(() =>
  selectedSpace.value
    ? editorState.value.levels.find(
      (level) => level.id === selectedSpace.value.levelId,
    ) || null
    : null,
);

/* =========================================================
   COMPUTED — ESPACIOS / RESUMEN
   ========================================================= */

const visibleSpaces = computed(() =>
  editorState.value.spaces.filter(
    (space) => space.levelId === activeLevelId.value,
  ),
);

const filteredSpaces = computed(() => {
  const query = search.value.trim().toLowerCase();

  return visibleSpaces.value.filter((space) => {
    if (!query) return true;

    const haystack = [
      spaceLabel(space),
      usageLabel(space.usageCode || space.tipo),
      levelLabel(space.levelId || space.nivel),
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  });
});

const confirmedSpacesCount = computed(() =>
  editorState.value.spaces.filter(
    (space) => space.confirmed,
  ).length,
);

const totalAreaM2 = computed(() =>
  roundMetric(
    editorState.value.spaces.reduce(
      (sum, space) => sum + numberOrZero(space.areaM2),
      0,
    ),
  ),
);

const areaExteriorM2 = computed(() =>
  roundMetric(
    editorState.value.spaces
      .filter((space) => isExteriorSpace(space))
      .reduce(
        (sum, space) => sum + numberOrZero(space.areaM2),
        0,
      ),
  ),
);

const areaInteriorM2 = computed(() =>
  roundMetric(
    editorState.value.spaces
      .filter((space) => !isExteriorSpace(space))
      .reduce(
        (sum, space) => sum + numberOrZero(space.areaM2),
        0,
      ),
  ),
);

const terrainAreaM2 = computed(() => {
  const geometry = normalizeGeometry(
    editorState.value.terrain?.geometry,
  );

  return geometry
    ? roundMetric(geometry.areaM2)
    : null;
});

const footprintAreaM2 = computed(() => {
  const byLevel = new Map();

  for (const space of editorState.value.spaces) {
    const level = editorState.value.levels.find(
      (item) => item.id === space.levelId,
    );

    if (
      normalizeLevelKey(level?.key) === "planta_azotea"
    ) {
      continue;
    }

    byLevel.set(
      space.levelId,
      (byLevel.get(space.levelId) || 0) +
      numberOrZero(space.areaM2),
    );
  }

  return byLevel.size
    ? Math.max(...byLevel.values())
    : 0;
});

const areaLibreM2 = computed(() => {
  if (terrainAreaM2.value === null) {
    return null;
  }

  return roundMetric(
    Math.max(
      terrainAreaM2.value - footprintAreaM2.value,
      0,
    ),
  );
});

const calculationValidation = computed(() =>
  validateReadyForCalculation(editorState.value),
);

const validationMessages = computed(() => {
  const messages = [];

  if (!editorState.value.levels.length) {
    messages.push("Define al menos un nivel.");
  }

  if (!editorState.value.spaces.length) {
    messages.push("No existen espacios registrados.");
  }

  for (const space of editorState.value.spaces) {
    if (!space.usageCode) {
      messages.push(
        `Selecciona el uso de ${spaceLabel(space)}.`,
      );
      break;
    }

    if (numberOrZero(space.areaM2) <= 0) {
      messages.push(
        `${spaceLabel(space)} no tiene geometría válida.`,
      );
      break;
    }

    if (!space.confirmed) {
      messages.push("Existen espacios pendientes de confirmar.");
      break;
    }
  }

  for (const conflict of calculationValidation.value.conflicts || []) {
    if (conflict.severity === "error") {
      messages.push(conflict.message);
    }
  }

  return [...new Set(messages)];
});

const terrainCompat = computed(() => {
  const geometry = normalizeGeometry(
    editorState.value.terrain?.geometry,
  );

  return {
    anchoM:
      geometry?.type === "rectangle"
        ? geometry.widthM
        : null,
    largoM:
      geometry?.type === "rectangle"
        ? geometry.lengthM
        : null,
  };
});

/* =========================================================
   HISTORIAL / COMMIT
   ========================================================= */

function commitState(
  label,
  options = {},
) {
  editorState.value.metadata = {
    ...(editorState.value.metadata || {}),
    sourceMode: editorState.value.metadata?.sourceMode || "manual",
    updatedAt: nowIso(),
  };

  editorState.value.editorSettings = {
    ...(editorState.value.editorSettings || {}),
    showGrid: showGrid.value,
    gridSizeM: gridSizeM.value,
    snapEnabled: snapEnabled.value,
  };

  editorState.value.activeLevelId =
    activeLevelId.value || null;

  refreshRelationshipIds();

  if (label !== 'Revisar completitud') {
    editorState.value.completeness = {...editorState.value.completeness, openings:'PARTIAL', stairs:'PARTIAL'};
  }
  applyEditorStateToViviendaStore(
    store,
    editorState.value,
    {
      useStoreAction: false,
    },
  );

  history.push(editorState.value, {
    label,
    coalesceKey: options.coalesceKey || null,
    force: options.force === true,
  });

  historyState.value = history.getSummary();
  flowError.value = "";
}

function undo() {
  const previous = history.undo();
  if (!previous) return;

  editorState.value = previous;
  restoreUiFromState();
  syncWorkingStateWithoutHistory();
}

function redo() {
  const next = history.redo();
  if (!next) return;

  editorState.value = next;
  restoreUiFromState();
  syncWorkingStateWithoutHistory();
}

function syncWorkingStateWithoutHistory() {
  applyEditorStateToViviendaStore(
    store,
    editorState.value,
    {
      useStoreAction: false,
    },
  );

  historyState.value = history.getSummary();
}

function restoreUiFromState() {
  const availableIds = new Set(
    editorState.value.levels.map((level) => level.id),
  );

  if (!availableIds.has(activeLevelId.value)) {
    activeLevelId.value =
      editorState.value.activeLevelId ||
      editorState.value.levels[0]?.id ||
      "";
  }

  selectedEntityType.value = null;
  selectedEntityId.value = null;

  syncTerrainDraft();
}

/* =========================================================
   SELECCIÓN
   ========================================================= */

function selectSpace(id) {
  const space = editorState.value.spaces.find(
    (item) => item.id === id,
  );

  if (!space) return;

  selectedEntityType.value = "space";
  selectedEntityId.value = id;

  activeLevelId.value = space.levelId;
  editorState.value.activeLevelId = space.levelId;

  activeTool.value = "select";
  sideTab.value = "spaces";
  geometryEditMode.value = false;

  populateSpaceDraft(space);
}

function selectLevel(id) {
  const level = editorState.value.levels.find(
    (item) => item.id === id,
  );

  if (!level) return;

  selectedEntityType.value = "level";
  selectedEntityId.value = id;
  activeLevelId.value = id;
  editorState.value.activeLevelId = id;
  activeTool.value = "select";

  populateLevelDraft(level);
}

function handleEditorSelectEntity(payload) {
  selectedEntityType.value = payload?.type || null;
  selectedEntityId.value = payload?.id || null;
  geometryEditMode.value = false;

  const entity = selectedEntity.value;

  if (entity?.levelId || entity?.levelFromId) {
    activeLevelId.value = entity.levelId || entity.levelFromId;
  }

  populateDraftForSelection();
}

const selectedEntity = computed(() => {
  switch (selectedEntityType.value) {
    case "space":
      return selectedSpace.value;
    case "wall":
      return selectedWall.value;
    case "door":
      return selectedDoor.value;
    case "window":
      return selectedWindow.value;
    case "stair":
      return editorState.value.stairs.find(s=>s.id===selectedEntityId.value);
    case "level":
      return selectedLevel.value;
    default:
      return null;
  }
});

function clearSelection() {
  selectedEntityType.value = null;
  selectedEntityId.value = null;
}

watch(
  [selectedEntityType, selectedEntityId],
  populateDraftForSelection,
);

/* =========================================================
   HERRAMIENTAS
   ========================================================= */

function setTool(tool) {
  const requiresLevel = [
    "rectangle",
    "polygon",
    "wall",
    "door",
    "window",
    "garage",
    "stair",
    "measure",
  ].includes(tool);

  if (requiresLevel && !activeLevelId.value) {
    flowError.value =
      "Define o selecciona un nivel antes de usar esta herramienta.";
    sideTab.value = "levels";
    return;
  }

  activeTool.value = tool;
  flowError.value = "";
}

function fitEditor() {
  editorRef.value?.fitViewport?.();
}

function prepareNewSpace() {
  clearSelection();
  setTool("rectangle");
}

function handleActiveLevelChange() {
  setActiveLevel(activeLevelId.value);
}

function setActiveLevel(levelId) {
  if (
    !editorState.value.levels.some(
      (level) => level.id === levelId,
    )
  ) {
    return;
  }

  activeLevelId.value = levelId;
  editorState.value.activeLevelId = levelId;
  clearSelection();
  activeTool.value = "select";

  syncWorkingStateWithoutHistory();
}

/* =========================================================
   CREAR / MODIFICAR ESPACIO
   ========================================================= */

function handleCreateSpace(payload) {
  if (activeTool.value === 'stair') {
    const stair = createStair({geometry: payload.geometry, levelFromId:activeLevelId.value, type:'STRAIGHT', source:manualSource()});
    editorState.value.stairs.push(stair);
    selectedEntityType.value='stair'; selectedEntityId.value=stair.id; activeTool.value='select';
    commitState('Crear escalera'); return;
  }
  if (!activeLevelId.value) {
    flowError.value = "Selecciona un nivel antes de crear espacios.";
    return;
  }

  const geometry = normalizeGeometry(
    payload?.geometry ||
    payload?.geometria,
  );

  if (!geometry) {
    flowError.value = "La geometría creada no es válida.";
    return;
  }

  const space = createSpace({
    id: createEntityId("space"),
    name: `Espacio ${editorState.value.spaces.length + 1}`,
    usageCode: "",
    usageLabel: "",
    category: "",
    levelId: activeLevelId.value,
    geometry,
    areaM2: geometry.areaM2,
    perimeterM: geometry.perimeterM,
    doubleHeight: false,
    heightM: null,
    confirmed: false,
    source: manualSource(),
  });

  const validation = validateSpaceCandidate({
    space,
    spaces: editorState.value.spaces,
    terrain: editorState.value.terrain,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  editorState.value.spaces.push(space);

  reconcileWallsAndOpenings({
    oldWalls: [...editorState.value.walls],
    reasonSpaceId: space.id,
  });

  selectSpace(space.id);
  activeTool.value = "select";

  commitState("Crear espacio");
}

function handleUpdateGeometry(payload) {
  const index = editorState.value.spaces.findIndex(
    (space) => space.id === payload?.id,
  );

  if (index < 0) return;

  const current = editorState.value.spaces[index];

  const geometry = normalizeGeometry(
    payload?.geometry ||
    payload?.geometria ||
    {
      type:
        payload?.geometria?.tipo === "rectangulo"
          ? "rectangle"
          : "polygon",
      vertices:
        payload?.vertices ||
        payload?.geometria?.metrica?.vertices ||
        [],
    },
  );

  if (!geometry) {
    flowError.value = "La geometría actualizada no es válida.";
    return;
  }

  const candidate = {
    ...current,
    geometry,
    areaM2: geometry.areaM2,
    perimeterM: geometry.perimeterM,
    confirmed: false,
  };

  const validation = validateSpaceCandidate({
    space: candidate,
    spaces: editorState.value.spaces,
    terrain: editorState.value.terrain,
    ignoreSpaceId: current.id,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  const oldWalls = editorState.value.walls.map((wall) => ({
    ...wall,
    start: { ...wall.start },
    end: { ...wall.end },
  }));

  editorState.value.spaces[index] = candidate;

  reconcileWallsAndOpenings({
    oldWalls,
    reasonSpaceId: current.id,
  });

  if (
    selectedEntityType.value === "space" &&
    selectedEntityId.value === current.id
  ) {
    populateSpaceDraft(candidate);
  }

  commitState("Editar geometría");
}

function handleMoveSpace(payload) {
  const index = editorState.value.spaces.findIndex(
    (space) => space.id === payload?.id,
  );

  if (index < 0) return;

  const current = editorState.value.spaces[index];

  const geometry = normalizeGeometry(payload.geometry);

  if (!geometry) return;

  const candidate = {
    ...current,
    geometry,
    areaM2: geometry.areaM2,
    perimeterM: geometry.perimeterM,
    confirmed: false,
  };

  const validation = validateSpaceCandidate({
    space: candidate,
    spaces: editorState.value.spaces,
    terrain: editorState.value.terrain,
    ignoreSpaceId: current.id,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  const oldWalls = editorState.value.walls.map((wall) => ({
    ...wall,
    start: { ...wall.start },
    end: { ...wall.end },
  }));

  editorState.value.spaces[index] = candidate;

  editorState.value.walls = translateExclusiveWallsForSpace(
    editorState.value.walls,
    current.id,
    payload.dx,
    payload.dy,
  );

  reconcileWallsAndOpenings({
    oldWalls,
    reasonSpaceId: current.id,
  });

  if (
    selectedEntityType.value === "space" &&
    selectedEntityId.value === current.id
  ) {
    // El drag es la acción principal de posicionamiento:
    // el inspector recibe automáticamente las nuevas X / Y.
    populateSpaceDraft(candidate);
  }

  commitState("Mover espacio", {
    coalesceKey: `move-space:${current.id}`,
  });
}

/* =========================================================
   MUROS
   ========================================================= */

function handleCreateWall(payload) {
  const wall = createWall({
    ...payload,
    id: createEntityId("wall"),
    levelId: activeLevelId.value,
    lengthM: segmentLength(payload.start, payload.end),
    thicknessM: null,
    heightM: null,
    type: "uncertain",
    confirmed: false,
    source: manualSource(),
  });

  editorState.value.walls.push(wall);

  selectedEntityType.value = "wall";
  selectedEntityId.value = wall.id;
  activeTool.value = "select";

  populateWallDraft(wall);
  refreshRelationshipIds();

  commitState("Crear muro");
}

function applyWallProperties() {
  const wall = selectedWall.value;
  if (!wall) return;

  const thicknessM = nullablePositiveNumber(wallDraft.thicknessM);
  const heightM = nullablePositiveNumber(wallDraft.heightM);

  if (
    wallDraft.thicknessM !== "" &&
    thicknessM === null
  ) {
    flowError.value = "El espesor debe ser mayor que cero o quedar vacío.";
    return;
  }

  if (
    wallDraft.heightM !== "" &&
    heightM === null
  ) {
    flowError.value = "La altura específica debe ser mayor que cero o quedar vacía.";
    return;
  }

  Object.assign(wall, {
    type: wallDraft.type || "uncertain",
    thicknessM,
    heightM,
    confirmed: false,
  });

  commitState("Editar muro");
}

/* =========================================================
   PUERTAS / VENTANAS
   ========================================================= */

function handleCreateDoor(payload) {
  const door = createDoor({
    kind: activeTool.value === "garage" ? "GARAGE_DOOR" : "DOOR",
    usage: activeTool.value === "garage" ? "VEHICLE_ACCESS" : "UNKNOWN",
    ...payload,
    id: createEntityId("door"),
    widthM: null,
    heightM: null,
    confirmed: false,
    source: manualSource(),
  });

  const validation = validateOpening({
    opening: door,
    walls: editorState.value.walls,
    doors: [...editorState.value.doors, door],
    windows: editorState.value.windows,
    levels: editorState.value.levels,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  editorState.value.doors.push(door);
  refreshRelationshipIds();

  selectedEntityType.value = "door";
  selectedEntityId.value = door.id;
  activeTool.value = "select";
  populateDoorDraft(door);

  commitState("Crear puerta");
}

function handleCreateWindow(payload) {
  const windowItem = createWindow({
    ...payload,
    id: createEntityId("window"),
    widthM: null,
    heightM: null,
    sillHeightM: null,
    confirmed: false,
    source: manualSource(),
  });

  const validation = validateOpening({
    opening: windowItem,
    walls: editorState.value.walls,
    doors: editorState.value.doors,
    windows: [...editorState.value.windows, windowItem],
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  editorState.value.windows.push(windowItem);
  refreshRelationshipIds();

  selectedEntityType.value = "window";
  selectedEntityId.value = windowItem.id;
  activeTool.value = "select";
  populateWindowDraft(windowItem);

  commitState("Crear ventana");
}

function applyDoorProperties() {
  const door = selectedDoor.value;
  if (!door) return;

  const candidate = {
    ...door,
    position: Number(doorDraft.position),
    widthM: nullablePositiveNumber(doorDraft.widthM),
    heightM: nullablePositiveNumber(doorDraft.heightM),
    swingDirection: doorDraft.swingDirection || "unknown",
    confirmed: false,
  };

  if (
    doorDraft.widthM !== "" &&
    candidate.widthM === null
  ) {
    flowError.value = "El ancho de la puerta debe ser mayor que cero.";
    return;
  }

  if (
    doorDraft.heightM !== "" &&
    candidate.heightM === null
  ) {
    flowError.value = "El alto de la puerta debe ser mayor que cero.";
    return;
  }

  const validation = validateOpening({
    opening: candidate,
    walls: editorState.value.walls,
    doors: editorState.value.doors.map(
      (item) => item.id === candidate.id ? candidate : item,
    ),
    windows: editorState.value.windows,
    levels: editorState.value.levels,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  Object.assign(door, candidate);
  commitState("Editar puerta");
}

function applyWindowProperties() {
  const windowItem = selectedWindow.value;
  if (!windowItem) return;

  const candidate = {
    ...windowItem,
    position: Number(windowDraft.position),
    widthM: nullablePositiveNumber(windowDraft.widthM),
    heightM: nullablePositiveNumber(windowDraft.heightM),
    sillHeightM: nullableNonNegativeNumber(windowDraft.sillHeightM),
    confirmed: false,
  };

  if (
    windowDraft.widthM !== "" &&
    candidate.widthM === null
  ) {
    flowError.value = "El ancho de la ventana debe ser mayor que cero.";
    return;
  }

  if (
    windowDraft.heightM !== "" &&
    candidate.heightM === null
  ) {
    flowError.value = "El alto de la ventana debe ser mayor que cero.";
    return;
  }

  if (
    windowDraft.sillHeightM !== "" &&
    candidate.sillHeightM === null
  ) {
    flowError.value = "El antepecho no puede ser negativo.";
    return;
  }

  const validation = validateOpening({
    opening: candidate,
    walls: editorState.value.walls,
    doors: editorState.value.doors,
    windows: editorState.value.windows.map(
      (item) => item.id === candidate.id ? candidate : item,
    ),
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  Object.assign(windowItem, candidate);
  commitState("Editar ventana");
}

/* =========================================================
   PROPIEDADES DE ESPACIO
   ========================================================= */

function applySpaceProperties() {
  const space = selectedSpace.value;
  if (!space) return;

  const currentGeometry = normalizeGeometry(space.geometry);
  if (!currentGeometry) return;

  const nextLevelId = spaceDraft.levelId;

  if (
    !editorState.value.levels.some(
      (level) => level.id === nextLevelId,
    )
  ) {
    flowError.value = "Selecciona un nivel válido.";
    return;
  }

  let geometry;

  if (currentGeometry.type === "rectangle") {
    const widthM = Number(spaceDraft.widthM);
    const lengthM = Number(spaceDraft.lengthM);
    const x = Number(spaceDraft.x);
    const y = Number(spaceDraft.y);

    if (
      !Number.isFinite(x) ||
      !Number.isFinite(y) ||
      !Number.isFinite(widthM) ||
      !Number.isFinite(lengthM) ||
      widthM <= 0 ||
      lengthM <= 0
    ) {
      flowError.value =
        "X, Y, ancho y largo deben formar un rectángulo válido.";
      return;
    }

    geometry = rectFromXYWH({
      x,
      y,
      widthM,
      lengthM,
    });
  } else {
    const bbox = boundingBox(currentGeometry.vertices);
    const nextX = Number(spaceDraft.x);
    const nextY = Number(spaceDraft.y);

    if (
      !Number.isFinite(nextX) ||
      !Number.isFinite(nextY)
    ) {
      flowError.value = "X y Y deben ser valores válidos.";
      return;
    }

    geometry = translateGeometry(
      currentGeometry,
      nextX - bbox.minX,
      nextY - bbox.minY,
    );
  }

  const usage = usageInfoMap.get(spaceDraft.usageCode);

  const candidate = {
    ...space,
    name: spaceDraft.name,
    usageCode: spaceDraft.usageCode,
    usageLabel: usage?.label || "",
    category: usage?.category || "",
    levelId: nextLevelId,
    geometry,
    areaM2: geometry.areaM2,
    perimeterM: geometry.perimeterM,
    doubleHeight: Boolean(spaceDraft.doubleHeight),
    heightM: nullablePositiveNumber(spaceDraft.heightM),
    confirmed: false,
  };

  if (
    spaceDraft.heightM !== "" &&
    candidate.heightM === null
  ) {
    flowError.value =
      "La altura excepcional debe ser mayor que cero o quedar vacía.";
    return;
  }

  const validation = validateSpaceCandidate({
    space: candidate,
    spaces: editorState.value.spaces,
    terrain: editorState.value.terrain,
    ignoreSpaceId: space.id,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  const oldWalls = editorState.value.walls.map((wall) => ({
    ...wall,
    start: { ...wall.start },
    end: { ...wall.end },
  }));

  const index = editorState.value.spaces.findIndex(
    (item) => item.id === space.id,
  );

  editorState.value.spaces[index] = candidate;

  activeLevelId.value = nextLevelId;
  editorState.value.activeLevelId = nextLevelId;

  reconcileWallsAndOpenings({
    oldWalls,
    reasonSpaceId: space.id,
  });

  commitState("Editar espacio");
  populateSpaceDraft(candidate);
}

function confirmSelectedSpace() {
  const space = selectedSpace.value;
  if (!space) return;

  if (!space.usageCode) {
    flowError.value =
      "Selecciona el uso del espacio antes de confirmarlo.";
    return;
  }

  const validation = validateSpaceCandidate({
    space,
    spaces: editorState.value.spaces,
    terrain: editorState.value.terrain,
    ignoreSpaceId: space.id,
  });

  if (!validation.isValid) {
    handleEditorValidation(validation);
    return;
  }

  space.confirmed = true;
  space.source = manualSource();

  commitState("Confirmar espacio", {
    force: true,
  });
}

function applyUsage(option, category) {
  const space = selectedSpace.value;
  if (!space) return;

  space.usageCode = option.value;
  space.usageLabel = option.label;
  space.category = category;
  space.confirmed = false;

  populateSpaceDraft(space);
  commitState("Asignar uso");
}

/* =========================================================
   NIVELES
   ========================================================= */

function addRegularLevel() {
  increaseLevelCount();
}

function increaseLevelCount() {
  const current =
    countStructuralLevels(
      editorState.value.levels,
    );

  levelCountDraft.value =
    current + 1;

  applyLevelCount();
}

function applyLevelCount() {
  const desired =
    positiveIntegerOrZero(
      levelCountDraft.value,
    );

  if (!desired) {
    flowError.value =
      "La cantidad de niveles debe ser un número entero mayor que cero.";
    return;
  }

  const currentStructural =
    getStructuralLevels(
      editorState.value.levels,
    );

  if (desired < currentStructural.length) {
    const levelsToRemove =
      currentStructural.slice(
        desired,
      );

    const requiresConfirmation =
      levelsToRemove.some((level) =>
        canRemoveLevel({
          levelId: level.id,
          levels: editorState.value.levels,
          spaces: editorState.value.spaces,
          walls: editorState.value.walls,
          doors: editorState.value.doors,
          windows: editorState.value.windows,
          stairs: editorState.value.stairs,
        }).requiresConfirmation,
      );

    if (
      requiresConfirmation &&
      !window.confirm(
        "Reducir la cantidad de niveles eliminará los elementos contenidos en los niveles retirados. ¿Continuar?",
      )
    ) {
      levelCountDraft.value =
        currentStructural.length;
      return;
    }

    for (
      const level of [...levelsToRemove].reverse()
    ) {
      const next =
        removeLevelCascade({
          levelId: level.id,
          levels: editorState.value.levels,
          spaces: editorState.value.spaces,
          walls: editorState.value.walls,
          doors: editorState.value.doors,
          windows: editorState.value.windows,
          stairs: editorState.value.stairs,
          annotations: editorState.value.annotations,
        });

      Object.assign(
        editorState.value,
        next,
      );
    }
  }

  const structural =
    getStructuralLevels(
      editorState.value.levels,
    );

  const roof =
    editorState.value.levels.find(
      (level) =>
        normalizeLevelKey(
          level.key,
        ) === "planta_azotea",
    ) || null;

  const nextStructural = [];

  for (
    let index = 0;
    index < desired;
    index += 1
  ) {
    const number =
      index + 1;

    const current =
      structural[index] || null;

    const canonicalKey =
      levelKeyFromNumber(number);

    const canonicalName =
      levelNameFromNumber(number);

    if (current) {
      nextStructural.push({
        ...current,
        key: canonicalKey,
        name:
          String(
            current.name || "",
          ).trim() ||
          canonicalName,
        order: index,
      });
    } else {
      nextStructural.push(
        createLevel({
          key: canonicalKey,
          name: canonicalName,
          order: index,
          elevationM:
            number === 1
              ? 0
              : null,
          heightM: null,
          visible: true,
          locked: false,
          confirmed: false,
          source: manualSource(),
        }),
      );
    }
  }

  const nextLevels = [
    ...nextStructural,
  ];

  if (roof) {
    nextLevels.push({
      ...roof,
      key: "planta_azotea",
      name:
        String(
          roof.name || "",
        ).trim() ||
        "Azotea",
      order: desired,
    });
  }

  editorState.value.levels =
    normalizeLevels(
      nextLevels,
    );

  const levelIds =
    new Set(
      editorState.value.levels.map(
        (level) => level.id,
      ),
    );

  if (
    !levelIds.has(
      activeLevelId.value,
    )
  ) {
    activeLevelId.value =
      editorState.value.levels[0]?.id ||
      "";

    editorState.value.activeLevelId =
      activeLevelId.value || null;

    clearSelection();
  }

  levelCountDraft.value =
    desired;

  flowError.value = "";

  commitState(
    "Configurar niveles",
    {
      force: true,
    },
  );
}

function commitInlineLevelHeight(level) {
  if (!level) return;

  const raw =
    level.heightM;

  const heightM =
    nullablePositiveNumber(
      raw,
    );

  if (
    raw !== "" &&
    raw != null &&
    heightM === null
  ) {
    flowError.value =
      "La altura del nivel debe ser mayor que cero o quedar pendiente.";

    level.heightM = null;
    return;
  }

  editorState.value.levels =
    updateLevel(
      editorState.value.levels,
      level.id,
      {
        heightM,
        confirmed:
          heightM !== null,
        source:
          manualSource(),
      },
    );

  if (
    selectedEntityType.value === "level" &&
    selectedEntityId.value === level.id
  ) {
    populateLevelDraft(
      editorState.value.levels.find(
        (item) => item.id === level.id,
      ),
    );
  }

  commitState(
    "Editar altura de nivel",
    {
      coalesceKey:
        `level-height:${level.id}`,
    },
  );
}

function selectRoofLevel() {
  const roof =
    editorState.value.levels.find(
      (level) =>
        normalizeLevelKey(
          level.key,
        ) === "planta_azotea",
    );

  if (roof) {
    selectLevel(roof.id);
  }
}

function addRoofLevel() {
  if (hasRoofLevel.value) return;

  editorState.value.levels = addLevel(
    editorState.value.levels,
    {
      key: "planta_azotea",
      name: "Azotea",
      heightM: null,
      elevationM: null,
      visible: true,
      locked: false,
      confirmed: false,
      source: manualSource(),
    },
  );

  const created = editorState.value.levels.find(
    (level) => normalizeLevelKey(level.key) === "planta_azotea",
  );

  if (created) {
    activeLevelId.value = created.id;
    editorState.value.activeLevelId = created.id;
    selectLevel(created.id);
  }

  commitState("Agregar azotea");
}

function applyLevelProperties() {
  const level = selectedLevel.value;
  if (!level) return;

  const heightM = nullablePositiveNumber(levelDraft.heightM);
  const elevationM = nullableNumber(levelDraft.elevationM);

  if (
    levelDraft.heightM !== "" &&
    heightM === null
  ) {
    flowError.value =
      "La altura del nivel debe ser mayor que cero o quedar pendiente.";
    return;
  }

  if (
    levelDraft.elevationM !== "" &&
    elevationM === null
  ) {
    flowError.value = "La elevación debe ser un número válido.";
    return;
  }

  editorState.value.levels = updateLevel(
    editorState.value.levels,
    level.id,
    {
      name:
        levelDraft.name.trim() ||
        level.name ||
        level.key,
      heightM,
      elevationM,
      confirmed: heightM !== null,
      source: manualSource(),
    },
  );

  editorState.value.doors = editorState.value.doors.map(o => o.levelId === level.id ? {...o, confirmed:false} : o);
  editorState.value.windows = editorState.value.windows.map(o => o.levelId === level.id ? {...o, confirmed:false} : o);
  editorState.value.stairs = editorState.value.stairs.map(o => o.levelFromId === level.id || o.levelToId === level.id ? {...o, confirmed:false} : o);
  commitState("Editar nivel");
  populateLevelDraft(
    editorState.value.levels.find((item) => item.id === level.id),
  );
}

/* =========================================================
   TERRENO
   ========================================================= */

function applyTerrain() {
  const widthM = nullablePositiveNumber(terrainDraft.widthM);
  const lengthM = nullablePositiveNumber(terrainDraft.lengthM);

  if (
    terrainDraft.widthM === "" &&
    terrainDraft.lengthM === ""
  ) {
    editorState.value.terrain = null;
    commitState("Quitar terreno");
    return;
  }

  if (widthM === null || lengthM === null) {
    flowError.value =
      "Para definir un terreno rectangular captura ancho y largo mayores que cero.";
    return;
  }

  const geometry = rectFromXYWH({
    x: 0,
    y: 0,
    widthM,
    lengthM,
  });

  for (const space of editorState.value.spaces) {
    const validation = validateSpaceCandidate({
      space,
      spaces: editorState.value.spaces,
      terrain: { geometry },
      ignoreSpaceId: space.id,
    });

    const outside = validation.conflicts?.find(
      (item) => item.code === "SPACE_OUTSIDE_TERRAIN",
    );

    if (outside) {
      flowError.value =
        "El nuevo terreno dejaría uno o más espacios fuera de sus límites.";
      return;
    }
  }

  editorState.value.terrain = createTerrain({
    shape: "rectangle",
    geometry,
    widthM,
    lengthM,
    confirmed: true,
    source: manualSource(),
  });

  commitState("Definir terreno");
}

function removeTerrain() {
  editorState.value.terrain = null;
  terrainDraft.widthM = "";
  terrainDraft.lengthM = "";

  commitState("Quitar terreno");
}

/* =========================================================
   ELIMINACIÓN
   ========================================================= */

function deleteSelectedEntity() {
  switch (selectedEntityType.value) {
    case "space":
      deleteSelectedSpace();
      break;
    case "wall":
      deleteSelectedWall();
      break;
    case "door":
      deleteSelectedDoor();
      break;
    case "window":
      deleteSelectedWindow();
      break;
    case "level":
      deleteSelectedLevel();
      break;
  }
}

function deleteSelectedSpace() {
  const space = selectedSpace.value;
  if (!space) return;

  const result = removeSpaceAndReconcile({
    spaces: editorState.value.spaces,
    walls: editorState.value.walls,
    spaceId: space.id,
    levelId: space.levelId,
  });

  const openingCascade = cascadeRemoveOpeningsForWalls({
    wallIds: result.removedWallIds,
    doors: editorState.value.doors,
    windows: editorState.value.windows,
    levels: editorState.value.levels,
  });

  editorState.value.spaces = result.spaces;
  editorState.value.walls = result.walls;
  editorState.value.doors = openingCascade.doors;
  editorState.value.windows = openingCascade.windows;

  clearSelection();
  commitState("Eliminar espacio");
}

function deleteSelectedWall() {
  const wall = selectedWall.value;
  if (!wall) return;

  const doorIds = editorState.value.doors
    .filter((door) => door.wallId === wall.id)
    .map((door) => door.id);

  const windowIds = editorState.value.windows
    .filter((windowItem) => windowItem.wallId === wall.id)
    .map((windowItem) => windowItem.id);

  const hasOpenings = doorIds.length || windowIds.length;

  if (
    hasOpenings &&
    !window.confirm(
      "Este muro contiene puertas o ventanas. Si lo eliminas, también se eliminarán esos vanos. ¿Continuar?",
    )
  ) {
    return;
  }

  editorState.value.walls = editorState.value.walls.filter(
    (item) => item.id !== wall.id,
  );

  const cascade = cascadeRemoveOpeningsForWalls({
    wallIds: [wall.id],
    doors: editorState.value.doors,
    windows: editorState.value.windows,
    levels: editorState.value.levels,
  });

  editorState.value.doors = cascade.doors;
  editorState.value.windows = cascade.windows;

  clearSelection();
  refreshRelationshipIds();

  commitState("Eliminar muro");
}

function deleteSelectedDoor() {
  const door = selectedDoor.value;
  if (!door) return;

  editorState.value.doors = editorState.value.doors.filter(
    (item) => item.id !== door.id,
  );

  clearSelection();
  refreshRelationshipIds();
  commitState("Eliminar puerta");
}

function deleteSelectedWindow() {
  const windowItem = selectedWindow.value;
  if (!windowItem) return;

  editorState.value.windows = editorState.value.windows.filter(
    (item) => item.id !== windowItem.id,
  );

  clearSelection();
  refreshRelationshipIds();
  commitState("Eliminar ventana");
}

function deleteSelectedLevel() {
  const level = selectedLevel.value;
  if (!level) return;

  const check = canRemoveLevel({
    levelId: level.id,
    levels: editorState.value.levels,
    spaces: editorState.value.spaces,
    walls: editorState.value.walls,
    doors: editorState.value.doors,
    windows: editorState.value.windows,
    stairs: editorState.value.stairs,
  });

  if (!check.allowed) {
    flowError.value = check.reason || "No se puede eliminar el nivel.";
    return;
  }

  if (
    check.requiresConfirmation &&
    !window.confirm(
      "Este nivel contiene elementos. Al eliminarlo se eliminarán también sus espacios, muros, puertas, ventanas y conexiones asociadas. ¿Continuar?",
    )
  ) {
    return;
  }

  const next = removeLevelCascade({
    levelId: level.id,
    levels: editorState.value.levels,
    spaces: editorState.value.spaces,
    walls: editorState.value.walls,
    doors: editorState.value.doors,
    windows: editorState.value.windows,
    stairs: editorState.value.stairs,
    annotations: editorState.value.annotations,
  });

  Object.assign(editorState.value, next);

  activeLevelId.value =
    editorState.value.levels[0]?.id || "";

  editorState.value.activeLevelId =
    activeLevelId.value || null;

  levelCountDraft.value =
    countStructuralLevels(
      editorState.value.levels,
    ) || "";

  clearSelection();
  commitState("Eliminar nivel");
}

/* =========================================================
   RECONCILIACIÓN WALL GRAPH + VANOS
   ========================================================= */

function reconcileWallsAndOpenings({
  oldWalls,
  reasonSpaceId = null,
}) {
  const existingWalls = editorState.value.walls;

  const reconciled = reconcileWallGraph({
    spaces: editorState.value.spaces,
    existingWalls,
  });

  // Conservar muros manuales huérfanos que no coinciden todavía con
  // un borde de espacio. Si después coinciden, reconcileWallGraph los reutiliza.
  const reconciledIds = new Set(
    reconciled.walls.map((wall) => wall.id),
  );

  const orphanManualWalls = existingWalls.filter((wall) => {
    if (reconciledIds.has(wall.id)) return false;

    return (
      !wall.spaceAId &&
      !wall.spaceBId &&
      wall.source?.type === "manual"
    );
  });

  const newWalls = [
    ...reconciled.walls,
    ...orphanManualWalls,
  ];

  const doorRemap = remapOpeningsAfterWallReconcile({
    openings: editorState.value.doors,
    oldWalls,
    newWalls,
    toleranceM: 1e-6,
  });

  const windowRemap = remapOpeningsAfterWallReconcile({
    openings: editorState.value.windows,
    oldWalls,
    newWalls,
    toleranceM: 1e-6,
  });

  editorState.value.walls = newWalls;
  editorState.value.doors = remapUnresolvedOpenings(
    doorRemap.openings,
    doorRemap.unresolvedIds,
    oldWalls,
    newWalls,
    reasonSpaceId,
  );

  editorState.value.windows = remapUnresolvedOpenings(
    windowRemap.openings,
    windowRemap.unresolvedIds,
    oldWalls,
    newWalls,
    reasonSpaceId,
  );

  refreshRelationshipIds();
}

function remapUnresolvedOpenings(
  openings,
  unresolvedIds,
  oldWalls,
  newWalls,
  reasonSpaceId,
) {
  if (!unresolvedIds?.length) return openings;

  const unresolved = new Set(unresolvedIds);
  const oldWallMap = new Map(
    oldWalls.map((wall) => [wall.id, wall]),
  );

  return openings.map((opening) => {
    if (!unresolved.has(opening.id)) return opening;

    const oldWall = oldWallMap.get(opening.wallId);
    if (!oldWall) return {...opening, confirmed:false};

    const center = wallPointAtPosition(
      oldWall,
      opening.position,
    );

    const oldOwners = new Set(
      [oldWall.spaceAId, oldWall.spaceBId].filter(Boolean),
    );

    const candidates = newWalls
      .filter((wall) => wall.levelId === oldWall.levelId)
      .filter((wall) => {
        const owners = [wall.spaceAId, wall.spaceBId].filter(Boolean);

        return (
          owners.some((owner) => oldOwners.has(owner)) ||
          (
            reasonSpaceId &&
            owners.includes(reasonSpaceId)
          )
        );
      })
      .filter((wall) =>
        wallsAreParallel(oldWall, wall),
      )
      .map((wall) => {
        const projected = projectToWall(center, wall);

        return {
          wall,
          projected,
          distance: projected.distance,
        };
      })
      .sort((a, b) => a.distance - b.distance);

    const best = candidates[0];

    if (!best || best.distance > 0.01 || (candidates[1] && Math.abs(candidates[1].distance-best.distance)<0.001)) {
      return {...opening, confirmed:false};
    }

    return {
      ...opening,
      wallId: best.wall.id,
      levelId: best.wall.levelId,
      position: best.projected.t,
      confirmed: false,
    };
  });
}

function wallsAreParallel(a, b) {
  const angleA = segmentAngle(a.start, a.end);
  const angleB = segmentAngle(b.start, b.end);

  const difference = Math.abs(
    Math.sin(angleA - angleB),
  );

  return difference < 1e-5;
}

function projectToWall(point, wall) {
  const ax = Number(wall.start.x);
  const ay = Number(wall.start.y);
  const bx = Number(wall.end.x);
  const by = Number(wall.end.y);

  const dx = bx - ax;
  const dy = by - ay;
  const length2 = dx * dx + dy * dy;

  if (length2 <= 0) {
    return {
      x: ax,
      y: ay,
      t: 0,
      distance: Math.hypot(point.x - ax, point.y - ay),
    };
  }

  const rawT =
    ((point.x - ax) * dx + (point.y - ay) * dy) / length2;

  const t = Math.max(0, Math.min(1, rawT));

  const x = ax + dx * t;
  const y = ay + dy * t;

  return {
    x,
    y,
    t,
    distance: Math.hypot(point.x - x, point.y - y),
  };
}

function refreshRelationshipIds() {
  const wallMap = new Map(
    editorState.value.walls.map((wall) => [
      wall.id,
      {
        ...wall,
        doorIds: [],
        windowIds: [],
      },
    ]),
  );

  for (const door of editorState.value.doors) {
    const wall = wallMap.get(door.wallId);
    if (wall) {
      wall.doorIds.push(door.id);
    }
  }

  for (const windowItem of editorState.value.windows) {
    const wall = wallMap.get(windowItem.wallId);
    if (wall) {
      wall.windowIds.push(windowItem.id);
    }
  }

  editorState.value.walls = [...wallMap.values()];

  editorState.value.spaces = updateSpaceWallRelations(
    editorState.value.spaces,
    editorState.value.walls,
  ).map((space) => {
    const relatedWalls = editorState.value.walls.filter(
      (wall) =>
        wall.spaceAId === space.id ||
        wall.spaceBId === space.id,
    );

    const doorIds = relatedWalls.flatMap(
      (wall) => wall.doorIds || [],
    );

    const windowIds = relatedWalls.flatMap(
      (wall) => wall.windowIds || [],
    );

    return {
      ...space,
      doorIds: [...new Set(doorIds)],
      windowIds: [...new Set(windowIds)],
    };
  });
}

/* =========================================================
   MEDIDA / VALIDACIÓN
   ========================================================= */

function handleMeasurement(payload) {
  lastMeasurement.value = payload;
}

function handleEditorValidation(validation) {
  const first = validation?.conflicts?.find(
    (item) => item.severity === "error",
  );

  flowError.value =
    first?.message ||
    "La operación no es válida.";
}

/* =========================================================
   DRAFTS
   ========================================================= */

function populateDraftForSelection() {
  switch (selectedEntityType.value) {
    case "space":
      populateSpaceDraft(selectedSpace.value);
      break;
    case "wall":
      populateWallDraft(selectedWall.value);
      break;
    case "door":
      populateDoorDraft(selectedDoor.value);
      break;
    case "window":
      populateWindowDraft(selectedWindow.value);
      break;
    case "level":
      populateLevelDraft(selectedLevel.value);
      break;
    default:
      syncTerrainDraft();
  }
}

function populateSpaceDraft(space) {
  if (!space) return;

  const geometry = normalizeGeometry(space.geometry);
  if (!geometry) return;

  const bbox = boundingBox(geometry.vertices);

  Object.assign(spaceDraft, {
    name: space.name || "",
    usageCode: space.usageCode || "",
    usageLabel: space.usageLabel || "",
    category: space.category || "",
    levelId: space.levelId || "",
    x:
      geometry.type === "rectangle"
        ? geometry.x
        : bbox.minX,
    y:
      geometry.type === "rectangle"
        ? geometry.y
        : bbox.minY,
    widthM:
      geometry.type === "rectangle"
        ? geometry.widthM
        : bbox.width,
    lengthM:
      geometry.type === "rectangle"
        ? geometry.lengthM
        : bbox.height,
    doubleHeight: Boolean(space.doubleHeight),
    heightM:
      space.heightM == null
        ? ""
        : space.heightM,
  });
}

function populateWallDraft(wall) {
  if (!wall) return;

  Object.assign(wallDraft, {
    type: wall.type || "uncertain",
    thicknessM:
      wall.thicknessM == null
        ? ""
        : wall.thicknessM,
    heightM:
      wall.heightM == null
        ? ""
        : wall.heightM,
  });
}

function populateDoorDraft(door) {
  if (!door) return;

  Object.assign(doorDraft, {
    position: door.position ?? 0.5,
    widthM:
      door.widthM == null
        ? ""
        : door.widthM,
    heightM:
      door.heightM == null
        ? ""
        : door.heightM,
    swingDirection:
      door.swingDirection || "unknown",
  });
}

function populateWindowDraft(windowItem) {
  if (!windowItem) return;

  Object.assign(windowDraft, {
    position: windowItem.position ?? 0.5,
    widthM:
      windowItem.widthM == null
        ? ""
        : windowItem.widthM,
    heightM:
      windowItem.heightM == null
        ? ""
        : windowItem.heightM,
    sillHeightM:
      windowItem.sillHeightM == null
        ? ""
        : windowItem.sillHeightM,
  });
}

function populateLevelDraft(level) {
  if (!level) return;

  Object.assign(levelDraft, {
    name: level.name || "",
    heightM:
      level.heightM == null
        ? ""
        : level.heightM,
    elevationM:
      level.elevationM == null
        ? ""
        : level.elevationM,
  });
}

function syncTerrainDraft() {
  const geometry = normalizeGeometry(
    editorState.value.terrain?.geometry,
  );

  if (geometry?.type === "rectangle") {
    terrainDraft.widthM = geometry.widthM;
    terrainDraft.lengthM = geometry.lengthM;
  } else {
    terrainDraft.widthM = "";
    terrainDraft.lengthM = "";
  }
}

function syncUsageDraft() {
  const usage = usageInfoMap.get(spaceDraft.usageCode);

  spaceDraft.usageLabel = usage?.label || "";
  spaceDraft.category = usage?.category || "";
}

/* =========================================================
   CONTINUAR / PERSISTIR
   ========================================================= */

function reloadImportedModel() {
  editorState.value=editorStateFromViviendaStore(store);
  activeLevelId.value=editorState.value.activeLevelId; clearSelection(); history.reset(editorState.value, 'Importar 03');
  historyState.value=history.getSummary();
}
function updateConstructionEntity({type, entity}) {
  const key={wall:'walls',door:'doors',window:'windows',stair:'stairs',space:'spaces'}[type];
  if(!key)return;
  editorState.value[key]=editorState.value[key].map(item=>item.id===entity.id?entity:item);
  commitState('Editar propiedades constructivas'); populateDraftForSelection();
}
function removeConstructionStair(id) {
  editorState.value.stairs=editorState.value.stairs.filter(s=>s.id!==id); clearSelection(); commitState('Eliminar escalera');
}
function continueFlow() {
  flowError.value = "";

  if (validationMessages.value.length) {
    flowError.value = validationMessages.value[0];
    return;
  }

  const levelHeights = orderedLevels.value
    .map((level) => ({
      levelId: level.id,
      key: level.key,
      heightM: Number(level.heightM),
    }))
    .filter(
      (item) => Number.isFinite(item.heightM) && item.heightM > 0,
    );

  const structural = structuralLevels.value;

  const explicitHeights = structural
    .map((level) => Number(level.heightM))
    .filter((value) => Number.isFinite(value) && value > 0);

  const averageHeight = explicitHeights.length
    ? roundMetric(
      explicitHeights.reduce(
        (sum, value) => sum + value,
        0,
      ) / explicitHeights.length,
    )
    : 0;

  const firstThree = structural.slice(0, 3);

  const capturedSpatial = JSON.parse(JSON.stringify(store.estructuraEspacial || {}));
  const capturedConceptInputs = structuredClone(JSON.parse(JSON.stringify(store.estructuraEspacial?.engineInputsByConcept || {})));
  const capturedEngineInputs = structuredClone(JSON.parse(JSON.stringify(store.estructuraEspacial?.engineInputs || {})));
  store.setDatosGeneralesObra({
    ...store.datosGeneralesObra,

    // El área declarada del predio pertenece a 02.
    // La geometría editada permanece en estructuraEspacial.terreno.
    areaConstruccionM2:
      totalAreaM2.value,

    niveles:
      structural.length,

    alturaNivel1M:
      firstThree[0]?.heightM ?? "",

    alturaNivel2M:
      firstThree[1]?.heightM ?? "",

    alturaNivel3M:
      firstThree[2]?.heightM ?? "",

    alturaPromedioM:
      averageHeight,

    engineInputs: {
      ...(store.datosGeneralesObra?.engineInputs || {}),
      modo_diseno: editorState.value.metadata?.sourceMode === "plan" ? "subir_plano" : "dibujar",
      alturas_nivel: levelHeights,
    },

    engineInputsByConcept:
      store.datosGeneralesObra?.engineInputsByConcept || {},
  });

  // setDatosGeneralesObra puede invalidar estructura espacial.
  // Por eso persistimos el EditorState DESPUÉS.
  applyEditorStateToViviendaStore(
    store,
    editorState.value,
    {
      useStoreAction: true,
      currentSpatial: capturedSpatial,
    },
  );

  store.setEstructuraEspacial({ ...store.estructuraEspacial, engineInputs: capturedEngineInputs, engineInputsByConcept: capturedConceptInputs });

  store.setValidacionEspacial({
    ...store.validacionEspacial,
    revisado: true,
    coherenciaArea: true,
    coherenciaVolumetria: true,
    confianza: "Usuario",
    alertas: [],
  });

  router.push("/vivienda/workflow/calculo-cantidades");
}

function goBack() {
  syncWorkingStateWithoutHistory();
  router.push("/vivienda/workflow/como-se-construira");
}

function seedMissingStructuralLevels(
  state,
  requestedCount,
) {
  const desired =
    positiveIntegerOrZero(
      requestedCount,
    );

  if (!desired) return;

  const structural =
    getStructuralLevels(
      state.levels || [],
    );

  if (
    structural.length >= desired
  ) {
    return;
  }

  const roof =
    (state.levels || []).find(
      (level) =>
        normalizeLevelKey(
          level.key,
        ) === "planta_azotea",
    ) || null;

  const nextStructural = [];

  for (
    let index = 0;
    index < desired;
    index += 1
  ) {
    const number =
      index + 1;

    const current =
      structural[index] || null;

    if (current) {
      nextStructural.push({
        ...current,
        key:
          levelKeyFromNumber(
            number,
          ),
        order: index,
      });
      continue;
    }

    nextStructural.push(
      createLevel({
        key:
          levelKeyFromNumber(
            number,
          ),
        name:
          levelNameFromNumber(
            number,
          ),
        order: index,
        elevationM:
          number === 1
            ? 0
            : null,
        heightM: null,
        visible: true,
        locked: false,
        confirmed: false,
        source:
          manualSource(),
      }),
    );
  }

  const next = [
    ...nextStructural,
  ];

  if (roof) {
    next.push({
      ...roof,
      order: desired,
    });
  }

  state.levels =
    normalizeLevels(next);

  if (
    !state.activeLevelId ||
    !state.levels.some(
      (level) =>
        level.id ===
        state.activeLevelId,
    )
  ) {
    state.activeLevelId =
      state.levels[0]?.id ||
      null;
  }
}

function getStructuralLevels(
  levels = [],
) {
  return [...levels]
    .filter(
      (level) =>
        normalizeLevelKey(
          level.key,
        ) !==
        "planta_azotea",
    )
    .sort(
      (a, b) =>
        Number(a.order) -
        Number(b.order),
    );
}

function countStructuralLevels(
  levels = [],
) {
  return getStructuralLevels(
    levels,
  ).length;
}

function positiveIntegerOrZero(value) {
  if (
    value === "" ||
    value == null
  ) {
    return 0;
  }

  const parsed =
    Number(value);

  if (
    !Number.isFinite(parsed) ||
    parsed <= 0 ||
    !Number.isInteger(parsed)
  ) {
    return 0;
  }

  return parsed;
}

/* =========================================================
   HELPERS — PROYECTO / NIVELES / ETIQUETAS
   ========================================================= */

function nextRegularLevelNumber() {
  const keys = new Set(
    editorState.value.levels.map(
      (level) => normalizeLevelKey(level.key),
    ),
  );

  if (!keys.has("planta_baja")) return 1;
  if (!keys.has("segunda_planta")) return 2;
  if (!keys.has("tercera_planta")) return 3;

  let number = 4;

  while (keys.has(`nivel_${number}`)) {
    number += 1;
  }

  return number;
}

function uniqueLevelKey(candidate) {
  const used = new Set(
    editorState.value.levels.map(
      (level) => normalizeLevelKey(level.key),
    ),
  );

  if (!used.has(candidate)) return candidate;

  let suffix = 2;
  let value = `${candidate}_${suffix}`;

  while (used.has(value)) {
    suffix += 1;
    value = `${candidate}_${suffix}`;
  }

  return value;
}

function shortLevelLabel(level, index) {
  const key = normalizeLevelKey(level.key);

  if (key === "planta_baja") return "PB";
  if (key === "segunda_planta") return "PA";
  if (key === "tercera_planta") return "P3";
  if (key === "planta_azotea") return "AZ";

  return `N${index + 1}`;
}

function levelLabelFromKey(value) {
  const key = normalizeLevelKey(value);

  const labels = {
    planta_baja: "Planta Baja",
    segunda_planta: "Planta Alta",
    tercera_planta: "Tercera Planta",
    planta_azotea: "Azotea",
  };

  return labels[key] || String(value || "Nivel");
}

function levelLabel(value) {
  const byId = editorState.value.levels.find(
    (level) => level.id === value,
  );

  if (byId) {
    return byId.name || levelLabelFromKey(byId.key);
  }

  return levelLabelFromKey(value);
}

function spacesForLevel(levelId) {
  return editorState.value.spaces.filter(
    (space) => space.levelId === levelId,
  );
}

function hasValidLevelHeight(level) {
  const value = Number(level?.heightM);

  return Number.isFinite(value) && value > 0;
}

function usageLabel(value) {
  return (
    usageInfoMap.get(String(value || ""))?.label ||
    "Sin uso"
  );
}

function spaceLabel(space) {
  return (
    String(space?.name || space?.nombre || "").trim() ||
    usageLabel(space?.usageCode || space?.tipo) ||
    "Espacio"
  );
}

function isExteriorSpace(space) {
  if (space.category === "exterior") return true;

  const code = space.usageCode || space.tipo;

  return usageInfoMap.get(code)?.category === "exterior";
}

function entitySpaceName(spaceId) {
  if (!spaceId) return "Exterior / sin relación";

  const space = editorState.value.spaces.find(
    (item) => item.id === spaceId,
  );

  return space ? spaceLabel(space) : "No identificado";
}

function effectiveWallHeightLabel(wall) {
  const own = Number(wall?.heightM);

  if (Number.isFinite(own) && own > 0) {
    return `${formatMetric(own)} m`;
  }

  const level = editorState.value.levels.find(
    (item) => item.id === wall?.levelId,
  );

  const inherited = Number(level?.heightM);

  return Number.isFinite(inherited) && inherited > 0
    ? `${formatMetric(inherited)} m · nivel`
    : "Pendiente";
}

function manualSource() {
  return createSourceInfo({
    type: "manual",
    state: "MANUAL",
    note: "usuario",
  });
}

/* =========================================================
   HELPERS — NÚMEROS
   ========================================================= */

function numberOrZero(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function nullableNumber(value) {
  if (value === "" || value == null) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function nullablePositiveNumber(value) {
  if (value === "" || value == null) return null;

  const parsed = Number(value);

  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : null;
}

function nullableNonNegativeNumber(value) {
  if (value === "" || value == null) return null;

  const parsed = Number(value);

  return Number.isFinite(parsed) && parsed >= 0
    ? parsed
    : null;
}

function positiveNumberOrFallback(value, fallback) {
  const parsed = Number(value);

  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : fallback;
}

function roundMetric(value) {
  return Number(numberOrZero(value).toFixed(2));
}

function formatMetric(value) {
  return numberOrZero(value).toFixed(2);
}

/* =========================================================
   WATCHERS INICIALES
   ========================================================= */

watch(
  () => editorState.value.levels.map(
    (level) => level.id,
  ),
  () => {
    const ids = new Set(
      editorState.value.levels.map((level) => level.id),
    );

    if (!ids.has(activeLevelId.value)) {
      activeLevelId.value =
        editorState.value.levels[0]?.id || "";

      editorState.value.activeLevelId =
        activeLevelId.value || null;
    }
  },
  {
    deep: true,
  },
);

watch(
  [showGrid, snapEnabled, gridSizeM],
  () => {
    editorState.value.editorSettings = {
      ...(editorState.value.editorSettings || {}),
      showGrid: showGrid.value,
      snapEnabled: snapEnabled.value,
      gridSizeM: gridSizeM.value,
    };

    syncWorkingStateWithoutHistory();
  },
);

syncTerrainDraft();
</script>

<style scoped>
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
    minmax(230px, 0.82fr) minmax(600px, 2.55fr) minmax(285px, 1fr);
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

.properties-panel {
  max-height: 790px;
  overflow-y: auto;
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

.side-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 3px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.side-tabs button {
  border: 0;
  border-radius: 8px;
  padding: 8px 5px;
  background: transparent;
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}

.side-tabs button.active {
  background: #ffffff;
  color: #1d4ed8;
  box-shadow: 0 1px 5px rgba(15, 23, 42, 0.08);
}

.field {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 0.82rem;
}

.field>span {
  font-weight: 600;
}

.field>small {
  color: #94a3b8;
  font-size: 0.73rem;
  line-height: 1.35;
}

.spaces-list,
.levels-list {
  display: grid;
  gap: 7px;
  max-height: 430px;
  overflow-y: auto;
}

.space-item,
.level-item {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 9px 10px;
  background: #fff;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.space-item:hover,
.level-item:hover {
  border-color: #93c5fd;
}

.space-item.active,
.level-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.space-item strong,
.level-item strong {
  display: block;
  color: #0f172a;
  font-size: 0.82rem;
}

.space-item small,
.level-item small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 0.72rem;
}

.space-item-meta,
.level-state {
  display: grid;
  align-content: start;
  justify-items: end;
  gap: 4px;
  color: #64748b;
  font-size: 0.72rem;
}

.level-state span:last-child.missing {
  color: #b45309;
}

.status-dot {
  color: #b45309;
}

.status-dot.confirmed {
  color: #15803d;
}

.add-space,
.secondary-action,
.apply-button {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  font-weight: 700;
  cursor: pointer;
}

.add-space {
  border: 1px dashed #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}

.add-space:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-action {
  border: 1px solid #dbe3ed;
  background: #fff;
  color: #475569;
}

.secondary-action.full {
  width: 100%;
}

.apply-button {
  background: #2563eb;
  color: #fff;
}

.level-actions {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 7px;
}

.level-count-card {
  padding: 10px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
}

.level-count-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 7px;
}

.compact-action {
  align-self: stretch;
  padding-inline: 12px;
}

.level-config-row {
  display: grid;
  gap: 8px;
  padding: 9px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}

.level-config-row.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.level-select-button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border: 0;
  padding: 0;
  background: transparent;
  color: #334155;
  text-align: left;
  cursor: pointer;
}

.level-select-button strong {
  display: block;
  color: #0f172a;
  font-size: 0.82rem;
}

.level-select-button small {
  display: block;
  margin-top: 3px;
  color: #94a3b8;
  font-size: 0.72rem;
}

.level-select-button>span {
  color: #2563eb;
  font-size: 0.74rem;
  font-weight: 800;
}

.inline-height {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 0.74rem;
}

.qw-input.compact-height {
  min-height: 32px;
  padding: 5px 7px;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

.section-title.no-border {
  margin: 0;
  padding: 0;
  border-top: 0;
}

.geometry-edit-button {
  border: 1px solid #dbe3ed;
  border-radius: 8px;
  padding: 6px 8px;
  background: #fff;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.geometry-edit-button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.geometry-guidance {
  padding: 9px 10px;
  border-radius: 9px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.74rem;
  line-height: 1.4;
}

.panel-empty {
  display: grid;
  min-height: 100px;
  place-content: center;
  padding: 14px;
  border: 1px dashed #dbe3ed;
  border-radius: 10px;
  color: #94a3b8;
  text-align: center;
  font-size: 0.78rem;
}

.usage-help,
.project-note {
  display: grid;
  gap: 5px;
  padding: 10px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #eff6ff;
  color: #475569;
  font-size: 0.77rem;
  line-height: 1.4;
}

.usage-help strong,
.project-note strong {
  color: #1e3a8a;
}

.project-note.compact {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.usage-group {
  display: grid;
  gap: 5px;
}

.usage-group>small {
  color: #64748b;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.usage-option {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 9px;
  background: #fff;
  color: #475569;
  text-align: left;
  cursor: pointer;
}

.usage-option.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.usage-option:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.editor-column {
  height: clamp(640px, 74vh, 780px);
  min-height: 0;
  max-height: 780px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 10px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.editor-toolbar>button,
.layers-menu>summary {
  border: 1px solid #dbe3ed;
  border-radius: 9px;
  padding: 7px 9px;
  background: #fff;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}

.editor-toolbar>button:hover,
.layers-menu>summary:hover {
  border-color: #93c5fd;
}

.editor-toolbar>button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.editor-toolbar>button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.toolbar-separator {
  width: 1px;
  height: 24px;
  background: #e2e8f0;
  margin: 0 2px;
}

.layers-menu {
  position: relative;
}

.layers-menu>summary {
  list-style: none;
}

.layers-menu>summary::-webkit-details-marker {
  display: none;
}

.layers-popover {
  position: absolute;
  z-index: 50;
  right: 0;
  top: calc(100% + 6px);
  min-width: 150px;
  display: grid;
  gap: 7px;
  padding: 10px;
  border: 1px solid #dbe3ed;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
}

.layers-popover label {
  display: flex;
  gap: 7px;
  align-items: center;
  color: #475569;
  font-size: 0.76rem;
}

.level-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 8px;
}

.level-tabs>button {
  border: 1px solid #dbe3ed;
  border-radius: 9px;
  min-width: 42px;
  padding: 7px 10px;
  background: #fff;
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
  cursor: pointer;
}

.level-tabs>button.active {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.no-level-chip {
  color: #b45309;
  font-size: 0.78rem;
}

.grid-size {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
  color: #64748b;
  font-size: 0.75rem;
}

.qw-input.compact {
  width: 92px;
  min-height: 32px;
  padding: 5px 7px;
}

.editor-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
  border-radius: 14px;
}

.editor-wrapper :deep(.quantia-plan-editor) {
  width: 100%;
  height: 100%;
  min-height: 0;
  max-height: 100%;
}

.editor-help {
  min-height: 34px;
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 9px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.77rem;
  line-height: 1.35;
}

.measurement-chip {
  position: absolute;
  right: 24px;
  bottom: 68px;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 0.76rem;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.07);
}

.editor-column {
  position: relative;
}

.measurement-chip button {
  border: 0;
  background: transparent;
  color: #9a3412;
  cursor: pointer;
}

.section-title {
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
  color: #334155;
  font-size: 0.77rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.two-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.metric-readout {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.metric-readout>div {
  display: grid;
  gap: 3px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.metric-readout small,
.metric-readout span {
  color: #94a3b8;
  font-size: 0.7rem;
}

.metric-readout strong {
  color: #0f172a;
  font-size: 0.92rem;
}

.check-field {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 0.82rem;
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
  word-break: break-word;
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

.flow-error,
.flow-warning {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 0.82rem;
}

.flow-error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
}

.flow-warning {
  display: flex;
  gap: 7px;
  align-items: baseline;
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
}

@media (max-width: 1360px) {
  .manual-layout {
    grid-template-columns: 220px minmax(520px, 1fr);
  }

  .properties-panel {
    grid-column: 1 / -1;
    max-height: none;
  }
}

@media (max-width: 980px) {
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
    height: 680px;
    min-height: 0;
    max-height: 680px;
  }
}

@media (max-width: 620px) {
  .design-summary {
    grid-template-columns: 1fr;
  }

  .two-columns,
  .metric-readout {
    grid-template-columns: 1fr;
  }

  .editor-toolbar {
    align-items: stretch;
  }

  .editor-toolbar>button {
    flex: 1 1 auto;
  }

  .level-tabs {
    flex-wrap: wrap;
  }

  .grid-size {
    width: 100%;
    margin-left: 0;
  }
}
</style>
