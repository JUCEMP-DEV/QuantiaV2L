<template>
  <QuantiaWorkflowLayout
    :step="3"
    title="3.2 Análisis con IA"
    subtitle="Analiza el plano y prepara una propuesta espacial para revisarla en Diseño y validación."
  >
    <!-- =====================================================
         ESTADO GENERAL
         ===================================================== -->
    <section class="analysis-card">
      <!-- ÉXITO DE RECONSTRUCCIÓN -->
      <div class="score-column">
        <div
          class="score-ring"
          :class="scoreTone"
          :style="{ '--score': `${successPercent ?? 0}%` }"
        >
          <div class="score-inner">
            <strong>{{ successDisplay }}</strong>
            <span>éxito</span>
          </div>
        </div>

        <small class="score-caption">
          Reconstrucción
        </small>
      </div>

      <!-- ESTADO + BARRAS -->
      <div class="analysis-copy">
        <div class="analysis-heading-row">
          <div>
            <span class="section-tag">
              ANÁLISIS ESPACIAL
            </span>

            <h2>{{ analysisTitle }}</h2>
          </div>

          <span
            class="run-badge"
            :class="runStatusTone"
          >
            {{ runStatusLabel }}
          </span>
        </div>

        <p>
          {{ analysisDescription }}
        </p>

        <!-- AVANCE DE EJECUCIÓN -->
        <div class="execution-block">
          <div class="execution-head">
            <div>
              <strong>Avance del análisis</strong>
              <small>{{ executionDetail }}</small>
            </div>

            <span v-if="executionProgress !== null">
              {{ executionProgress }}%
            </span>

            <span v-else-if="processing">
              En ejecución
            </span>

            <span v-else>
              Pendiente
            </span>
          </div>

          <div
            class="execution-track"
            :class="{ indeterminate: processing && executionProgress === null }"
          >
            <div
              class="execution-fill"
              :style="executionProgress !== null
                ? { width: `${executionProgress}%` }
                : {}"
            ></div>
          </div>
        </div>

        <!-- CALIDAD POR COMPONENTE -->
        <div class="quality-grid">
          <article
            v-for="item in qualityComponents"
            :key="item.key"
            class="quality-item"
            :class="item.tone"
          >
            <div class="quality-icon">
              <QuantiaIcon
                :name="item.icon"
                :size="17"
              />
            </div>

            <div class="quality-content">
              <div class="quality-head">
                <strong>{{ item.label }}</strong>

                <span>
                  {{ item.percent !== null
                    ? `${item.percent}%`
                    : item.statusLabel }}
                </span>
              </div>

              <div
                class="quality-track"
                :class="{
                  indeterminate:
                    processing &&
                    item.percent === null
                }"
              >
                <div
                  class="quality-fill"
                  :style="item.percent !== null
                    ? { width: `${item.percent}%` }
                    : {}"
                ></div>
              </div>

              <small>
                {{ item.detail }}
              </small>
            </div>
          </article>
        </div>
      </div>

      <!-- PANEL INFORMATIVO -->
      <aside class="ai-panel">
        <div class="ai-icon">
          <QuantiaIcon
            name="ai"
            :size="28"
          />
        </div>

        <span class="section-tag">
          QUANTIA SPATIAL
        </span>

        <h3>Interpretación del plano</h3>

        <p>
          Spatial analiza la geometría y genera una propuesta
          para la siguiente etapa. Los resultados incompletos
          o inciertos podrán corregirse en Diseño y validación.
        </p>

        <div class="ai-note">
          <QuantiaIcon
            name="info"
            :size="16"
          />

          <span>
            El porcentaje de éxito solo representa métricas
            reportadas por Spatial. No se calcula visualmente
            ni se completa con valores estimados.
          </span>
        </div>

        <div
          v-if="spatialStatusLabel"
          class="spatial-status"
          :class="spatialStatusTone"
        >
          <small>Estado espacial</small>
          <strong>{{ spatialStatusLabel }}</strong>
        </div>
      </aside>
    </section>

    <!-- =====================================================
         ERROR
         ===================================================== -->
    <section
      v-if="error"
      class="error-message"
    >
      <QuantiaIcon
        name="warning"
        :size="18"
      />

      <p>{{ error }}</p>
    </section>

    <!-- =====================================================
         ARCHIVOS
         ===================================================== -->
    <section class="documents-section">
      <header class="documents-header">
        <div>
          <span class="section-tag">
            DOCUMENTOS DEL PROYECTO
          </span>

          <h2>Selecciona el plano a analizar</h2>

          <p>
            Spatial trabaja directamente con el archivo seleccionado.
            Analizar otro plano sustituirá la propuesta espacial actual.
          </p>
        </div>

        <div class="documents-summary">
          <div>
            <strong>{{ analyzedCount }}</strong>
            <span>analizado</span>
          </div>

          <div class="summary-divider"></div>

          <div>
            <strong>{{ documents.length }}</strong>
            <span>disponibles</span>
          </div>
        </div>
      </header>

      <!-- LISTA -->
      <div
        v-if="documents.length"
        class="documents-list"
      >
        <article
          v-for="doc in documents"
          :key="doc.document_id"
          class="document-row"
          :class="documentRowClass(doc)"
        >
          <div class="document-icon">
            <QuantiaIcon
              :name="documentIcon(doc)"
              :size="23"
            />
          </div>

          <div class="document-info">
            <strong>
              {{ doc.file_name }}
            </strong>

            <div class="document-meta">
              <span
                class="document-status"
                :class="documentSpatialTone(doc)"
              >
                <span class="status-dot"></span>

                {{ documentSpatialLabel(doc) }}
              </span>

              <span
                v-if="documentDetail(doc)"
                class="meta-divider"
              ></span>

              <span
                v-if="documentDetail(doc)"
                class="detail"
              >
                {{ documentDetail(doc) }}
              </span>
            </div>
          </div>

          <button
            type="button"
            class="process-btn"
            :disabled="processing"
            @click="analyze(doc)"
          >
            <QuantiaIcon
              :name="isProcessing(doc)
                ? 'scan-line'
                : analysisButtonIcon(doc)"
              :size="17"
            />

            {{ analysisButtonLabel(doc) }}
          </button>
        </article>
      </div>

      <!-- VACÍO -->
      <div
        v-else
        class="empty-state"
      >
        <div class="empty-icon">
          <QuantiaIcon
            name="plan"
            :size="29"
          />
        </div>

        <div>
          <strong>
            No hay documentos disponibles
          </strong>

          <p>
            Regresa a Carga de documentos y agrega al menos
            un plano para iniciar el análisis espacial.
          </p>
        </div>
      </div>
    </section>

    <!-- =====================================================
         RESULTADO / TRANSICIÓN
         ===================================================== -->
    <section
      v-if="spatialFinished"
      class="next-stage-note"
      :class="nextStageTone"
    >
      <div class="next-stage-icon">
        <QuantiaIcon
          :name="nextStageIcon"
          :size="22"
        />
      </div>

      <div>
        <strong>
          {{ nextStageTitle }}
        </strong>

        <p>
          {{ nextStageDescription }}
        </p>

        <div
          v-if="runWarnings.length"
          class="result-summary"
        >
          <span>
            {{ runWarnings.length }}
            advertencia{{ runWarnings.length === 1 ? "" : "s" }}
          </span>
        </div>
      </div>
    </section>

    <!-- =====================================================
         FOOTER
         ===================================================== -->
    <template #footer>
      <button
        type="button"
        class="workflow-btn secondary"
        @click="goBack"
      >
        <QuantiaIcon
          name="arrow-left"
          :size="17"
        />

        <span>
          Anterior
          <small>Carga de documentos</small>
        </span>
      </button>

      <div class="footer-actions">
        <button
          type="button"
          class="workflow-btn secondary"
          :disabled="processing"
          @click="load"
        >
          <QuantiaIcon
            name="reset"
            :size="17"
          />

          Actualizar documentos
        </button>

        <button
          type="button"
          class="workflow-btn primary"
          :disabled="!canContinue"
          @click="goDesign"
        >
          <span>
            Continuar
            <small>Diseño y validación</small>
          </span>

          <QuantiaIcon
            name="arrow-right"
            :size="17"
          />
        </button>
      </div>
    </template>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref,
} from "vue";

import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/authStore";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import QuantiaIcon from "@/components/common/QuantiaIcon.vue";

import {
  analizarPlanoDocumento,
  listarDocumentos,
} from "@/modules/vivienda/services/documentosApiService";

import {
  buildPhase03Delivery,
} from "@/modules/vivienda/editor/adapters/spatialWorkflowContract";

import "@/assets/styles/quantia-workflow.css";


const router = useRouter();

const auth = useAuthStore();
const store = useViviendaStore();


/* =========================================================
   ESTADO LOCAL
   ========================================================= */

const documents = ref([]);
const processingDocumentId = ref("");
const error = ref("");

const spatialRun = ref(
  createInitialSpatialRun()
);


/* =========================================================
   CONSTANTES DE ESTADO
   ========================================================= */

const TERMINAL_RUN_STATUSES =
  new Set([
    "COMPLETED",
    "PARTIAL",
    "FAILED",
  ]);

const SUPPORTED_RUN_STATUSES =
  new Set([
    "IDLE",
    "RUNNING",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
  ]);

const SUPPORTED_SPATIAL_STATUSES =
  new Set([
    "VALID",
    "REVIEW",
    "INVALID",
    "UNRESOLVED",
  ]);

const QUALITY_COMPONENT_CATALOG = [
  {
    key: "scale",
    label: "Escala y métrica",
    icon: "scan-line",
  },
  {
    key: "perimeter",
    label: "Perímetro",
    icon: "plan",
  },
  {
    key: "walls",
    label: "Muros",
    icon: "floor-plan",
  },
  {
    key: "spaces",
    label: "Espacios",
    icon: "file-search",
  },
  {
    key: "openings",
    label: "Puertas y ventanas",
    icon: "file-check",
  },
  {
    key: "correlation",
    label: "Correlación global",
    icon: "ai",
  },
];


/* =========================================================
   ESTADO DERIVADO
   ========================================================= */

const processing = computed(
  () =>
    Boolean(
      processingDocumentId.value
    )
);

const spatialFinished = computed(
  () =>
    TERMINAL_RUN_STATUSES.has(
      spatialRun.value.status
    )
);

const analyzedDocumentExists = computed(
  () =>
    documents.value.some(
      (document) =>
        String(
          document?.document_id || ""
        ) ===
        String(
          spatialRun.value.documentId || ""
        )
    )
);

const analyzedCount = computed(
  () =>
    spatialFinished.value &&
    analyzedDocumentExists.value
      ? 1
      : 0
);

const canContinue = computed(
  () =>
    !processing.value &&
    spatialFinished.value &&
    analyzedDocumentExists.value
);


/* =========================================================
   PORCENTAJE DE ÉXITO
   ========================================================= */

const successPercent = computed(
  () =>
    normalizePercent(
      spatialRun.value.quality
        ?.successPercent
    )
);

const successDisplay = computed(() => {
  if (
    processing.value &&
    successPercent.value === null
  ) {
    return "…";
  }

  if (successPercent.value === null) {
    return "--";
  }

  return `${successPercent.value}%`;
});

const scoreTone = computed(() => {
  const value =
    successPercent.value;

  if (value === null) {
    if (
      spatialRun.value.status ===
      "FAILED"
    ) {
      return "error";
    }

    return "neutral";
  }

  if (value >= 90) {
    return "success";
  }

  if (value >= 70) {
    return "review";
  }

  return "error";
});


/* =========================================================
   AVANCE DE EJECUCIÓN
   ========================================================= */

const executionProgress = computed(() => {
  const explicit =
    normalizePercent(
      spatialRun.value
        .progressPercent
    );

  if (explicit !== null) {
    return explicit;
  }

  if (spatialFinished.value) {
    return 100;
  }

  return null;
});

const executionDetail = computed(() => {
  if (processing.value) {
    return (
      spatialRun.value.phaseLabel ||
      "Spatial está analizando el plano."
    );
  }

  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "La ejecución terminó correctamente.";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "La ejecución terminó con información pendiente de revisión.";
  }

  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "La ejecución terminó sin reconstrucción utilizable completa.";
  }

  return "Selecciona un plano para iniciar.";
});


/* =========================================================
   CALIDAD POR COMPONENTE
   ========================================================= */

const qualityComponents = computed(() => {
  const components =
    spatialRun.value.quality
      ?.components || {};

  return QUALITY_COMPONENT_CATALOG.map(
    (definition) => {
      const source =
        components[
          definition.key
        ] || {};

      const percent =
        normalizePercent(
          source.percent
        );

      const status =
        normalizeQualityStatus(
          source.status
        );

      return {
        ...definition,

        percent,

        status,

        tone:
          qualityTone(
            percent,
            status
          ),

        statusLabel:
          qualityStatusLabel(
            percent,
            status
          ),

        detail:
          qualityDetail(
            source,
            percent,
            status
          ),
      };
    }
  );
});


/* =========================================================
   TEXTOS GENERALES
   ========================================================= */

const analysisTitle = computed(() => {
  if (processing.value) {
    return "Reconstruyendo el plano…";
  }

  if (!documents.value.length) {
    return "No hay planos para analizar";
  }

  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "Reconstrucción espacial completada";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "Reconstrucción parcial disponible";
  }

  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "El análisis terminó con incidencias";
  }

  return "Plano listo para análisis";
});

const analysisDescription = computed(() => {
  if (processing.value) {
    return "Quantia Spatial está interpretando la geometría, relaciones y evidencia del plano seleccionado.";
  }

  if (!documents.value.length) {
    return "Carga un plano del proyecto antes de iniciar el análisis espacial.";
  }

  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "Spatial generó una propuesta para revisar y confirmar en Diseño y validación.";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "Spatial recuperó información útil, pero existen elementos que deberán completarse o corregirse en Diseño y validación.";
  }

  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "Spatial no logró generar una reconstrucción suficiente. Puedes continuar a Diseño y validación para completar el modelo manualmente.";
  }

  return "Selecciona el plano que deseas reconstruir. No es necesario procesarlo previamente mediante RAG u OCR documental.";
});


/* =========================================================
   BADGES DE EJECUCIÓN
   ========================================================= */

const runStatusLabel = computed(() => {
  const labels = {
    IDLE: "Pendiente",
    RUNNING: "Analizando",
    COMPLETED: "Completado",
    PARTIAL: "Parcial",
    FAILED: "Con incidencias",
  };

  return (
    labels[
      spatialRun.value.status
    ] ||
    "Pendiente"
  );
});

const runStatusTone = computed(() => {
  const status =
    spatialRun.value.status;

  if (status === "COMPLETED") {
    return "success";
  }

  if (status === "PARTIAL") {
    return "review";
  }

  if (status === "FAILED") {
    return "error";
  }

  if (status === "RUNNING") {
    return "active";
  }

  return "neutral";
});


/* =========================================================
   ESTADO ESPACIAL
   ========================================================= */

const spatialStatusLabel = computed(() => {
  const labels = {
    VALID: "VALID",
    REVIEW: "REVIEW",
    INVALID: "INVALID",
    UNRESOLVED: "UNRESOLVED",
  };

  return (
    labels[
      spatialRun.value
        .spatialStatus
    ] || ""
  );
});

const spatialStatusTone = computed(() => {
  const status =
    spatialRun.value
      .spatialStatus;

  if (status === "VALID") {
    return "success";
  }

  if (status === "REVIEW") {
    return "review";
  }

  if (
    status === "INVALID" ||
    status === "UNRESOLVED"
  ) {
    return "error";
  }

  return "neutral";
});


/* =========================================================
   RESULTADO / TRANSICIÓN
   ========================================================= */

const runWarnings = computed(
  () =>
    Array.isArray(
      spatialRun.value.warnings
    )
      ? spatialRun.value.warnings
      : []
);

const nextStageTone = computed(() => {
  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "success";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "review";
  }

  return "error";
});

const nextStageIcon = computed(() => {
  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "warning";
  }

  return "floor-plan";
});

const nextStageTitle = computed(() => {
  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "Propuesta espacial preparada";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "Propuesta parcial preparada";
  }

  return "Continuación manual disponible";
});

const nextStageDescription = computed(() => {
  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "Continúa a Diseño y validación para revisar y confirmar la reconstrucción antes de cuantificar.";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "Se conservará toda la información recuperada. Continúa a Diseño y validación para completar los elementos pendientes.";
  }

  return "El análisis automático no bloquea el proyecto. Continúa a Diseño y validación para construir o completar manualmente el modelo.";
});


/* =========================================================
   DOCUMENTOS
   ========================================================= */

function isProcessing(document) {
  return (
    String(
      processingDocumentId.value
    ) ===
    String(
      document?.document_id || ""
    )
  );
}

function isAnalyzedDocument(document) {
  return (
    String(
      spatialRun.value.documentId ||
      ""
    ) ===
    String(
      document?.document_id ||
      ""
    )
  );
}

function documentRowClass(document) {
  if (!isAnalyzedDocument(document)) {
    return {};
  }

  return {
    active:
      spatialRun.value.status ===
      "RUNNING",

    success:
      spatialRun.value.status ===
      "COMPLETED",

    partial:
      spatialRun.value.status ===
      "PARTIAL",

    failed:
      spatialRun.value.status ===
      "FAILED",
  };
}

function documentSpatialLabel(document) {
  if (!isAnalyzedDocument(document)) {
    return "Disponible";
  }

  const labels = {
    IDLE: "Disponible",
    RUNNING: "Analizando",
    COMPLETED: "Reconstruido",
    PARTIAL: "Resultado parcial",
    FAILED: "Revisión manual",
  };

  return (
    labels[
      spatialRun.value.status
    ] ||
    "Disponible"
  );
}

function documentSpatialTone(document) {
  if (!isAnalyzedDocument(document)) {
    return "pending";
  }

  if (
    spatialRun.value.status ===
    "COMPLETED"
  ) {
    return "success";
  }

  if (
    spatialRun.value.status ===
    "PARTIAL"
  ) {
    return "review";
  }

  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "error";
  }

  if (
    spatialRun.value.status ===
    "RUNNING"
  ) {
    return "processing";
  }

  return "pending";
}

function analysisButtonLabel(document) {
  if (isProcessing(document)) {
    return "Analizando...";
  }

  if (!isAnalyzedDocument(document)) {
    return "Analizar plano";
  }

  if (
    spatialRun.value.status ===
    "FAILED"
  ) {
    return "Reintentar";
  }

  if (
    spatialRun.value.status ===
      "COMPLETED" ||
    spatialRun.value.status ===
      "PARTIAL"
  ) {
    return "Reanalizar";
  }

  return "Analizar plano";
}

function analysisButtonIcon(document) {
  if (
    isAnalyzedDocument(document) &&
    spatialFinished.value
  ) {
    return "reset";
  }

  return "ai";
}

function documentIcon(document) {
  const fileName =
    String(
      document?.file_name ||
      ""
    )
      .trim()
      .toLowerCase();

  if (
    fileName.endsWith(".png") ||
    fileName.endsWith(".jpg") ||
    fileName.endsWith(".jpeg")
  ) {
    return "image";
  }

  return "file";
}

function documentDetail(document) {
  const pages =
    Number(
      document?.page_count ||
      document?.metadata
        ?.page_count ||
      0
    );

  if (pages > 0) {
    return `${pages} página${pages === 1 ? "" : "s"}`;
  }

  const size =
    Number(
      document?.file_size ||
      document?.size ||
      0
    );

  if (size > 0) {
    return formatFileSize(size);
  }

  return "";
}


/* =========================================================
   CONSULTA DE DOCUMENTOS
   ========================================================= */

async function load() {
  try {
    error.value = "";

    const response =
      await listarDocumentos({
        accessToken:
          auth.accessToken ||
          "",
      });

    documents.value =
      Array.isArray(
        response?.documents
      )
        ? response.documents
        : [];
  } catch (e) {
    error.value =
      e?.message ||
      "No fue posible consultar los documentos.";
  }
}


/* =========================================================
   EJECUCIÓN SPATIAL
   ========================================================= */

async function analyze(document) {
  if (
    !document?.document_id ||
    processing.value
  ) {
    return;
  }

  const documentId =
    String(
      document.document_id
    );

  processingDocumentId.value =
    documentId;

  error.value = "";

  spatialRun.value = {
    ...createInitialSpatialRun(),

    documentId,

    status: "RUNNING",

    spatialStatus:
      "UNRESOLVED",

    phaseLabel:
      "Iniciando Quantia Spatial…",
  };

  try {
    const contract =
      await runSpatialAnalysis(
        document
      );

    const execution =
      extractExecution(
        contract
      );

    const quality =
      extractQuality(
        contract
      );

    spatialRun.value = {
      documentId,

      status:
        execution.status,

      spatialStatus:
        execution.spatialStatus,

      progressPercent:
        execution.progressPercent,

      phaseLabel:
        execution.phaseLabel,

      warnings:
        execution.warnings,

      errors:
        execution.errors,

      quality,
    };

    persistSpatialContract(
      document,
      contract,
      spatialRun.value
    );
  } catch (e) {
    const message =
      e?.message ||
      "No fue posible ejecutar Quantia Spatial.";

    spatialRun.value = {
      ...createInitialSpatialRun(),

      documentId,

      status: "FAILED",

      spatialStatus:
        "UNRESOLVED",

      progressPercent: 100,

      errors: [message],
    };

    error.value = message;

    persistFailedSpatialRun(
      document,
      message
    );
  } finally {
    processingDocumentId.value =
      "";
  }
}


/* =========================================================
   LLAMADA A SPATIAL
   ========================================================= */

async function runSpatialAnalysis(
  document
) {
  /*
   * 03.2 ya NO decide:
   * - pdf_render_scale
   * - OCR strategy interna
   * - escala arquitectónica
   * - fases del motor
   *
   * Esas decisiones pertenecen a QuantiaSpatialV1.
   *
   * El siguiente cambio de integración debe llevar
   * QUANTIA_02_03_SPATIAL_CONTEXT_V1 desde el servicio
   * documental/backend. No se inventa aquí un contrato local.
   */
  const contract =
    await analizarPlanoDocumento({
      documentId:
        document.document_id,

      accessToken:
        auth.accessToken ||
        "",
    });

  if (
    !contract ||
    typeof contract !==
      "object" ||
    Array.isArray(contract)
  ) {
    throw new Error(
      "Spatial no devolvió un resultado válido."
    );
  }

  return contract;
}


/* =========================================================
   PERSISTENCIA TEMPORAL 03 → 04
   ========================================================= */

function persistSpatialContract(
  document,
  contract,
  runState
) {
  /*
   * Mientras QUANTIA_03_04_V2 se implementa en el adaptador,
   * conservamos el boundary vigente QUANTIA_03_04_V1 para que
   * este Vue compile y no duplique la normalización de 04.
   *
   * Este bloque deberá sustituirse únicamente cuando
   * spatialWorkflowContract.js publique el receptor V2.
   */
  const spatialPayload = {
    ...contract,

    sourceMode: "plan",

    execution: {
      status:
        runState.status,

      spatialStatus:
        runState.spatialStatus,

      progressPercent:
        runState.progressPercent,

      warnings:
        runState.warnings,

      errors:
        runState.errors,
    },

    quality:
      runState.quality,

    metadata: {
      ...(contract.metadata ||
        {}),

      sourceMode: "plan",

      sourceDocumentId:
        String(
          document.document_id
        ),

      sourceFileName:
        String(
          document.file_name ||
          ""
        ),
    },
  };

  store.setEstructuraEspacial(
    buildPhase03Delivery(
      spatialPayload,
      store
    )
  );

  console.info(
    "[TRACE][03.2][SPATIAL_RESULT]",
    {
      documentId:
        String(
          document.document_id
        ),

      status:
        runState.status,

      spatialStatus:
        runState.spatialStatus,

      successPercent:
        runState.quality
          ?.successPercent ??
        null,
    }
  );
}

function persistFailedSpatialRun(
  document,
  message
) {
  /*
   * Evita conservar geometría antigua cuando una nueva
   * ejecución termina FAILED. 04 recibirá un modelo vacío
   * y podrá continuar por el editor común.
   */
  store.setEstructuraEspacial({
    sourceMode: "plan",

    metadata: {
      sourceMode: "plan",

      sourceDocumentId:
        String(
          document.document_id
        ),

      sourceFileName:
        String(
          document.file_name ||
          ""
        ),
    },

    terreno: null,

    niveles: [],
    espacios: [],
    muros: [],
    puertas: [],
    ventanas: [],
    escaleras: [],
    anotaciones: [],

    execution: {
      status: "FAILED",

      spatialStatus:
        "UNRESOLVED",

      progressPercent: 100,

      warnings: [],

      errors: [message],
    },

    quality: {
      successPercent: null,
      components: {},
    },

    readiness: {
      workflowContinuation: true,
      quantification: false,
      missing: [
        "La reconstrucción automática debe completarse en 04.",
      ],
    },
  });
}


/* =========================================================
   NORMALIZACIÓN DEL RESULTADO
   ========================================================= */

function extractExecution(
  contract
) {
  const source =
    contract?.execution &&
    typeof contract.execution ===
      "object"
      ? contract.execution
      : {};

  const explicitStatus =
    normalizeRunStatus(
      source.status
    );

  let status =
    explicitStatus ||
    "COMPLETED";

  /*
   * Compatibilidad temporal con el exporter experimental
   * de SpatialV1: si declara explícitamente que el flujo
   * no puede continuar automáticamente, el resultado se
   * considera PARTIAL, no FAILED.
   */
  if (
    !explicitStatus &&
    contract?.readiness
      ?.workflowContinuation ===
      false
  ) {
    status = "PARTIAL";
  }

  return {
    status,

    spatialStatus:
      normalizeSpatialStatus(
        source.spatialStatus ||
        contract?.spatialStatus ||
        contract?.estado
      ),

    progressPercent:
      normalizePercent(
        source.progressPercent
      ) ??
      (
        TERMINAL_RUN_STATUSES.has(
          status
        )
          ? 100
          : null
      ),

    phaseLabel:
      String(
        source.phaseLabel ||
        source.phase ||
        ""
      ).trim(),

    warnings:
      normalizeStringList(
        source.warnings ||
        contract?.warnings
      ),

    errors:
      normalizeStringList(
        source.errors
      ),
  };
}

function extractQuality(
  contract
) {
  const source =
    contract?.quality &&
    typeof contract.quality ===
      "object"
      ? contract.quality
      : {};

  const components =
    source.components &&
    typeof source.components ===
      "object" &&
    !Array.isArray(
      source.components
    )
      ? source.components
      : {};

  return {
    successPercent:
      normalizePercent(
        source.successPercent
      ),

    components:
      JSON.parse(
        JSON.stringify(
          components
        )
      ),
  };
}


/* =========================================================
   HIDRATACIÓN DESDE STORE
   ========================================================= */

function hydrateSpatialRunFromStore() {
  const spatial =
    store.estructuraEspacial ||
    {};

  const documentId =
    String(
      spatial.metadata
        ?.sourceDocumentId ||
      ""
    );

  if (!documentId) {
    spatialRun.value =
      createInitialSpatialRun();

    return;
  }

  const execution =
    spatial.execution &&
    typeof spatial.execution ===
      "object"
      ? spatial.execution
      : {};

  const storedStatus =
    normalizeRunStatus(
      execution.status
    );

  const hasSpatialData =
    [
      spatial.niveles,
      spatial.muros,
      spatial.espacios,
    ].some(
      (value) =>
        Array.isArray(value) &&
        value.length > 0
    );

  spatialRun.value = {
    documentId,

    status:
      storedStatus ||
      (
        hasSpatialData
          ? "COMPLETED"
          : "IDLE"
      ),

    spatialStatus:
      normalizeSpatialStatus(
        execution.spatialStatus ||
        spatial.estado
      ),

    progressPercent:
      normalizePercent(
        execution.progressPercent
      ),

    phaseLabel:
      String(
        execution.phaseLabel ||
        ""
      ).trim(),

    warnings:
      normalizeStringList(
        execution.warnings
      ),

    errors:
      normalizeStringList(
        execution.errors
      ),

    quality: {
      successPercent:
        normalizePercent(
          spatial.quality
            ?.successPercent
        ),

      components:
        spatial.quality
          ?.components &&
        typeof spatial.quality
          .components ===
          "object"
          ? JSON.parse(
            JSON.stringify(
              spatial.quality
                .components
            )
          )
          : {},
    },
  };
}


/* =========================================================
   NAVEGACIÓN
   ========================================================= */

function goBack() {
  router.push(
    "/vivienda/workflow/planos-revision/carga"
  );
}

function goDesign() {
  error.value = "";

  if (!canContinue.value) {
    error.value =
      "Espera a que termine el análisis espacial del plano seleccionado.";

    return;
  }

  /*
   * FAILED siempre entra al editor común.
   * PARTIAL también entra al editor común cuando no existe
   * geometría métrica suficiente para la revisión desde plano.
   */
  if (
    spatialRun.value.status ===
      "FAILED" ||
    !hasUsableSpatialGeometry(
      store.estructuraEspacial
    )
  ) {
    router.push({
      path:
        "/vivienda/workflow/diseno-vivienda/manual",

      query: {
        origin: "plan",

        spatialStatus:
          spatialRun.value.status,
      },
    });

    return;
  }

  router.push(
    "/vivienda/workflow/diseno-vivienda/plano"
  );
}


/* =========================================================
   HELPERS
   ========================================================= */

function createInitialSpatialRun() {
  return {
    documentId: "",
    status: "IDLE",
    spatialStatus: "UNRESOLVED",
    progressPercent: null,
    phaseLabel: "",
    warnings: [],
    errors: [],

    quality: {
      successPercent: null,
      components: {},
    },
  };
}

function normalizeRunStatus(
  value
) {
  const normalized =
    String(
      value || ""
    )
      .trim()
      .toUpperCase();

  return SUPPORTED_RUN_STATUSES.has(
    normalized
  )
    ? normalized
    : "";
}

function normalizeSpatialStatus(
  value
) {
  const normalized =
    String(
      value || ""
    )
      .trim()
      .toUpperCase();

  return SUPPORTED_SPATIAL_STATUSES.has(
    normalized
  )
    ? normalized
    : "UNRESOLVED";
}

function normalizePercent(
  value
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const parsed =
    Number(value);

  if (!Number.isFinite(parsed)) {
    return null;
  }

  return Math.round(
    Math.min(
      100,
      Math.max(
        0,
        parsed
      )
    )
  );
}

function normalizeQualityStatus(
  value
) {
  const normalized =
    String(
      value || ""
    )
      .trim()
      .toUpperCase();

  if (
    [
      "VALID",
      "REVIEW",
      "INVALID",
      "UNRESOLVED",
      "PENDING",
    ].includes(
      normalized
    )
  ) {
    return normalized;
  }

  return "";
}

function qualityTone(
  percent,
  status
) {
  if (
    status === "INVALID" ||
    status === "UNRESOLVED"
  ) {
    return "error";
  }

  if (status === "REVIEW") {
    return "review";
  }

  if (status === "VALID") {
    return "success";
  }

  if (percent === null) {
    return processing.value
      ? "active"
      : "neutral";
  }

  if (percent >= 90) {
    return "success";
  }

  if (percent >= 70) {
    return "review";
  }

  return "error";
}

function qualityStatusLabel(
  percent,
  status
) {
  if (percent !== null) {
    return "";
  }

  if (processing.value) {
    return "Analizando";
  }

  const labels = {
    VALID: "Validado",
    REVIEW: "Revisión",
    INVALID: "Inválido",
    UNRESOLVED: "Sin resolver",
    PENDING: "Pendiente",
  };

  return (
    labels[status] ||
    (
      spatialFinished.value
        ? "Sin métrica"
        : "Pendiente"
    )
  );
}

function qualityDetail(
  source,
  percent,
  status
) {
  const explicit =
    String(
      source?.detail ||
      source?.message ||
      ""
    ).trim();

  if (explicit) {
    return explicit;
  }

  if (processing.value) {
    return "Spatial está evaluando este componente.";
  }

  if (
    status === "VALID" ||
    (
      percent !== null &&
      percent >= 90
    )
  ) {
    return "Componente validado por Spatial.";
  }

  if (
    status === "REVIEW" ||
    (
      percent !== null &&
      percent >= 70
    )
  ) {
    return "Requiere revisión en Diseño y validación.";
  }

  if (
    status === "INVALID" ||
    status === "UNRESOLVED" ||
    (
      percent !== null &&
      percent < 70
    )
  ) {
    return "Spatial detectó información insuficiente o inconsistente.";
  }

  if (spatialFinished.value) {
    return "El motor aún no reporta una métrica para este componente.";
  }

  return "Pendiente de ejecutar.";
}

function normalizeStringList(
  value
) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map(
      (item) =>
        String(
          item || ""
        ).trim()
    )
    .filter(Boolean);
}

function hasUsableSpatialGeometry(
  spatial
) {
  const walls =
    Array.isArray(
      spatial?.muros
    )
      ? spatial.muros
      : [];

  const spaces =
    Array.isArray(
      spatial?.espacios
    )
      ? spatial.espacios
      : [];

  const hasMetricWall =
    walls.some(
      (wall) =>
        isMetricPoint(
          wall?.start
        ) &&
        isMetricPoint(
          wall?.end
        )
    );

  const hasMetricSpace =
    spaces.some(
      (space) => {
        const geometry =
          space?.geometry ||
          space?.geometria ||
          {};

        const vertices =
          geometry?.metrica
            ?.vertices ||
          geometry?.vertices ||
          [];

        return (
          Array.isArray(
            vertices
          ) &&
          vertices.length >= 3 &&
          vertices.every(
            isMetricPoint
          )
        );
      }
    );

  return (
    hasMetricWall ||
    hasMetricSpace
  );
}

function isMetricPoint(
  point
) {
  return (
    point &&
    Number.isFinite(
      Number(
        point.x
      )
    ) &&
    Number.isFinite(
      Number(
        point.y
      )
    )
  );
}

function formatFileSize(
  bytes
) {
  const value =
    Number(bytes);

  if (
    !Number.isFinite(value) ||
    value <= 0
  ) {
    return "";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  if (
    value <
    1024 * 1024
  ) {
    return `${(
      value / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    value /
    (
      1024 * 1024
    )
  ).toFixed(1)} MB`;
}


/* =========================================================
   MONTAJE
   ========================================================= */

onMounted(
  async () => {
    hydrateSpatialRunFromStore();

    await load();
  }
);
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.section-tag {
  display: block;
  margin-bottom: 6px;
  color: #0877ef;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.055em;
}


/* =========================================================
   ANÁLISIS
   ========================================================= */

.analysis-card {
  display: grid;
  grid-template-columns:
    150px minmax(0, 1fr) 280px;
  gap: 30px;
  align-items: center;
  padding: 26px;
  border: 1px solid #bcc9dc;
  border-radius: 11px;
  background: #ffffff;
  box-shadow:
    0 3px 10px rgba(32, 55, 105, 0.03);
}


/* =========================================================
   ÉXITO DE RECONSTRUCCIÓN
   ========================================================= */

.score-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-ring {
  --ring-color: #a6b2c4;

  position: relative;
  width: 124px;
  height: 124px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    conic-gradient(
      var(--ring-color)
      var(--score),
      #e7ecf4 0
    );
}

.score-ring::before {
  content: "";
  position: absolute;
  inset: 10px;
  border-radius: 50%;
  background: #ffffff;
}

.score-ring.success {
  --ring-color: #25a566;
}

.score-ring.review {
  --ring-color: #d89b23;
}

.score-ring.error {
  --ring-color: #d64a4a;
}

.score-ring.neutral {
  --ring-color: #9baac0;
}

.score-inner {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
}

.score-inner strong {
  color: #0a2368;
  font-size: 1.42rem;
  line-height: 1;
}

.score-inner span {
  margin-top: 5px;
  color: #7180a2;
  font-size: 0.61rem;
  font-weight: 700;
}

.score-caption {
  margin-top: 9px;
  color: #7180a2;
  font-size: 0.62rem;
  font-weight: 700;
}


/* =========================================================
   CABECERA DE ANÁLISIS
   ========================================================= */

.analysis-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.analysis-copy h2 {
  margin: 0;
  color: #0a2368;
  font-size: 1.08rem;
}

.analysis-copy > p {
  margin: 7px 0 16px;
  max-width: 650px;
  color: #637393;
  font-size: 0.75rem;
  line-height: 1.5;
}

.run-badge {
  min-width: 84px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 9px;
  border: 1px solid #d3dce9;
  border-radius: 999px;
  background: #f6f8fb;
  color: #6f7f9c;
  font-size: 0.61rem;
  font-weight: 800;
}

.run-badge.success {
  border-color: #c9dfd2;
  background: #f2faf5;
  color: #278453;
}

.run-badge.review {
  border-color: #ead8a7;
  background: #fffaf0;
  color: #a36d08;
}

.run-badge.error {
  border-color: #e7c0c0;
  background: #fff5f5;
  color: #c82727;
}

.run-badge.active {
  border-color: #c5d6f6;
  background: #f3f7ff;
  color: #075ff2;
}


/* =========================================================
   AVANCE DE EJECUCIÓN
   ========================================================= */

.execution-block {
  margin-bottom: 13px;
  padding: 11px 12px;
  border: 1px solid #d4deeb;
  border-radius: 9px;
  background: #f8fafd;
}

.execution-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.execution-head strong {
  display: block;
  color: #405477;
  font-size: 0.69rem;
}

.execution-head small {
  display: block;
  margin-top: 2px;
  color: #8995aa;
  font-size: 0.59rem;
}

.execution-head > span {
  color: #075ff2;
  font-size: 0.64rem;
  font-weight: 800;
}

.execution-track,
.quality-track {
  position: relative;
  overflow: hidden;
  height: 6px;
  margin-top: 8px;
  border-radius: 999px;
  background: #e6ebf2;
}

.execution-fill,
.quality-fill {
  height: 100%;
  border-radius: inherit;
  background:
    linear-gradient(
      90deg,
      #075ff2,
      #8421f1
    );
  transition: width 0.3s ease;
}

.execution-track.indeterminate
.execution-fill,
.quality-track.indeterminate
.quality-fill {
  position: absolute;
  width: 38%;
  animation:
    progress-slide
    1.25s ease-in-out
    infinite;
}

@keyframes progress-slide {
  0% {
    left: -38%;
  }

  100% {
    left: 100%;
  }
}


/* =========================================================
   CALIDAD
   ========================================================= */

.quality-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 7px;
}

.quality-item {
  display: grid;
  grid-template-columns:
    32px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-height: 61px;
  padding: 8px 9px;
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  background: #fbfcfe;
}

.quality-icon {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f0f3f8;
  color: #8793a9;
}

.quality-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.quality-head strong {
  color: #526584;
  font-size: 0.65rem;
}

.quality-head span {
  color: #6c7b96;
  font-size: 0.6rem;
  font-weight: 800;
}

.quality-content small {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #8a95aa;
  font-size: 0.56rem;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quality-item.success {
  border-color: #d3e6da;
  background: #f8fcf9;
}

.quality-item.success
.quality-icon {
  background: #edf8f1;
  color: #278453;
}

.quality-item.success
.quality-fill {
  background: #32a768;
}

.quality-item.review {
  border-color: #eadcb9;
  background: #fffaf2;
}

.quality-item.review
.quality-icon {
  background: #fff4d9;
  color: #ad770d;
}

.quality-item.review
.quality-fill {
  background: #d89b23;
}

.quality-item.error {
  border-color: #ebcccc;
  background: #fff7f7;
}

.quality-item.error
.quality-icon {
  background: #fff0f0;
  color: #c83b3b;
}

.quality-item.error
.quality-fill {
  background: #d64a4a;
}

.quality-item.active {
  border-color: #c5d6f6;
  background: #f6f9ff;
}

.quality-item.active
.quality-icon {
  background: #edf4ff;
  color: #075ff2;
}


/* =========================================================
   IA
   ========================================================= */

.ai-panel {
  min-height: 310px;
  padding-left: 25px;
  border-left: 1px solid #d6deea;
}

.ai-icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  margin-bottom: 14px;
  border: 1px solid #d2deef;
  border-radius: 12px;
  background:
    linear-gradient(
      135deg,
      #edf4ff,
      #f3efff
    );
  color: #075ff2;
}

.ai-panel h3 {
  margin: 0;
  color: #162d70;
  font-size: 0.9rem;
}

.ai-panel > p {
  margin: 7px 0 14px;
  color: #697897;
  font-size: 0.7rem;
  line-height: 1.5;
}

.ai-note {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 9px 10px;
  border: 1px solid #d5dfed;
  border-radius: 8px;
  background: #f5f8fc;
  color: #637393;
  font-size: 0.63rem;
  line-height: 1.4;
}

.spatial-status {
  display: grid;
  gap: 2px;
  margin-top: 11px;
  padding: 9px 10px;
  border: 1px solid #d5dfed;
  border-radius: 8px;
  background: #f7f9fc;
}

.spatial-status small {
  color: #7e8ca4;
  font-size: 0.57rem;
}

.spatial-status strong {
  color: #536786;
  font-size: 0.68rem;
}

.spatial-status.success {
  border-color: #c9dfd2;
  background: #f2faf5;
}

.spatial-status.success strong {
  color: #278453;
}

.spatial-status.review {
  border-color: #ead8a7;
  background: #fffaf0;
}

.spatial-status.review strong {
  color: #a36d08;
}

.spatial-status.error {
  border-color: #e7c0c0;
  background: #fff5f5;
}

.spatial-status.error strong {
  color: #c82727;
}


/* =========================================================
   ERROR
   ========================================================= */

.error-message {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e8b9b9;
  border-radius: 9px;
  background: #fff5f5;
  color: #c82727;
}

.error-message p {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
}


/* =========================================================
   DOCUMENTOS
   ========================================================= */

.documents-section {
  margin-top: 18px;
  padding: 22px;
  border: 1px solid #bcc9dc;
  border-radius: 11px;
  background: #ffffff;
  box-shadow:
    0 3px 10px rgba(32, 55, 105, 0.03);
}

.documents-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 17px;
  padding-bottom: 16px;
  border-bottom: 1px solid #d4ddea;
}

.documents-header h2 {
  margin: 0;
  color: #162d70;
  font-size: 1rem;
}

.documents-header p {
  margin: 5px 0 0;
  max-width: 720px;
  color: #7180a2;
  font-size: 0.72rem;
}

.documents-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border: 1px solid #c9d5e8;
  border-radius: 9px;
  background: #f1f5fb;
}

.documents-summary > div {
  display: grid;
  place-items: center;
}

.documents-summary strong {
  color: #075ff2;
  font-size: 0.9rem;
}

.documents-summary span {
  color: #7180a2;
  font-size: 0.59rem;
  font-weight: 700;
}

.summary-divider {
  width: 1px;
  height: 28px;
  background: #d1dbe9;
}


/* =========================================================
   LISTA
   ========================================================= */

.documents-list {
  display: grid;
  gap: 8px;
}

.document-row {
  display: grid;
  grid-template-columns:
    48px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 70px;
  padding: 10px 13px;
  border: 1px solid #c5d0e1;
  border-radius: 9px;
  background: #ffffff;
}

.document-row.active {
  border-color: #9fbbec;
  background: #f7faff;
}

.document-row.success {
  border-color: #cae1d2;
}

.document-row.partial {
  border-color: #e6d5aa;
}

.document-row.failed {
  border-color: #e1bebe;
}

.document-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: 1px solid #d2deef;
  border-radius: 10px;
  background:
    linear-gradient(
      135deg,
      #edf4ff,
      #f3efff
    );
  color: #075ff2;
}

.document-info {
  min-width: 0;
}

.document-info > strong {
  display: block;
  overflow: hidden;
  color: #162d70;
  font-size: 0.76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 6px;
  color: #7180a2;
  font-size: 0.63rem;
}

.document-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #a6b2c4;
}

.document-status.success
.status-dot {
  background: #2d9a60;
}

.document-status.review
.status-dot {
  background: #d89b23;
}

.document-status.processing
.status-dot {
  background: #075ff2;
}

.document-status.error
.status-dot {
  background: #cf3434;
}

.meta-divider {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #a7b4c8;
}


/* =========================================================
   BOTÓN DE ANÁLISIS
   ========================================================= */

.process-btn {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  border: 1px solid #9eb4d6;
  border-radius: 8px;
  background: #ffffff;
  color: #075ff2;
  font-size: 0.68rem;
  font-weight: 750;
  cursor: pointer;
}

.process-btn:hover:not(:disabled) {
  border-color: #075ff2;
  background: #f5f9ff;
}

.process-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}


/* =========================================================
   VACÍO
   ========================================================= */

.empty-state {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 20px;
  border: 1px dashed #c4cfdf;
  border-radius: 9px;
  background: #f8fafd;
}

.empty-icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 11px;
  background:
    linear-gradient(
      135deg,
      #edf4ff,
      #f3efff
    );
  color: #075ff2;
}

.empty-state strong {
  display: block;
  color: #162d70;
  font-size: 0.76rem;
}

.empty-state p {
  margin: 4px 0 0;
  color: #7180a2;
  font-size: 0.68rem;
}


/* =========================================================
   SIGUIENTE ETAPA
   ========================================================= */

.next-stage-note {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px solid #cad9f0;
  border-radius: 10px;
  background: #f4f7fc;
}

.next-stage-note.success {
  border-color: #c9dfd2;
  background: #f3faf6;
}

.next-stage-note.review {
  border-color: #ead8a7;
  background: #fffaf1;
}

.next-stage-note.error {
  border-color: #e7c0c0;
  background: #fff7f7;
}

.next-stage-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 10px;
  background:
    linear-gradient(
      135deg,
      #edf4ff,
      #f3efff
    );
  color: #075ff2;
}

.next-stage-note strong {
  display: block;
  color: #162d70;
  font-size: 0.75rem;
}

.next-stage-note p {
  margin: 4px 0 0;
  max-width: 780px;
  color: #687899;
  font-size: 0.68rem;
  line-height: 1.45;
}

.result-summary {
  margin-top: 7px;
}

.result-summary span {
  display: inline-flex;
  padding: 4px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: #7b6a3e;
  font-size: 0.58rem;
  font-weight: 750;
}


/* =========================================================
   FOOTER
   ========================================================= */

.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workflow-btn {
  min-height: 47px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 22px;
  border-radius: 9px;
  font-size: 0.82rem;
  font-weight: 750;
  cursor: pointer;
}

.workflow-btn.secondary {
  border: 1px solid #aebed5;
  background: #ffffff;
  color: #52678d;
}

.workflow-btn.primary {
  min-width: 215px;
  border: 0;
  background:
    linear-gradient(
      90deg,
      #075ff2,
      #8421f1
    );
  color: #ffffff;
  box-shadow:
    0 7px 17px rgba(51, 69, 211, 0.2);
}

.workflow-btn > span {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.workflow-btn small {
  margin-top: 2px;
  color: inherit;
  font-size: 0.59rem;
  font-weight: 600;
  opacity: 0.78;
}

.workflow-btn:disabled {
  cursor: not-allowed;
  opacity: 0.48;
  box-shadow: none;
}


/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 1120px) {
  .analysis-card {
    grid-template-columns:
      135px minmax(0, 1fr);
  }

  .ai-panel {
    grid-column: 1 / -1;
    min-height: auto;
    padding: 18px 0 0;
    border-top: 1px solid #d6deea;
    border-left: 0;
  }
}

@media (max-width: 760px) {
  .analysis-card {
    grid-template-columns: 1fr;
  }

  .score-column {
    align-items: flex-start;
  }

  .analysis-heading-row {
    flex-direction: column;
  }

  .quality-grid {
    grid-template-columns: 1fr;
  }

  .documents-header {
    flex-direction: column;
  }

  .document-row {
    grid-template-columns:
      44px minmax(0, 1fr);
  }

  .process-btn {
    grid-column: 2;
    width: max-content;
  }

  .footer-actions {
    width: 100%;
    flex-direction: column;
  }

  .workflow-btn {
    width: 100%;
  }

  .workflow-btn.primary {
    min-width: 0;
  }
}
</style>
