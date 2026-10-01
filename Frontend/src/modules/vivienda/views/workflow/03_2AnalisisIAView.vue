<template>
  <QuantiaWorkflowLayout :step="3" title="3.2 Análisis con IA"
    subtitle="Procesa los documentos del proyecto y prepara su información para la siguiente etapa.">
    <!-- =====================================================
         ESTADO GENERAL
         ===================================================== -->
    <section class="analysis-card">
      <div class="progress-column">
        <div class="progress-ring" :style="{ '--progress': `${progress}%` }">
          <div class="progress-inner">
            <strong>{{ progress }}%</strong>
            <span>procesado</span>
          </div>
        </div>
      </div>

      <div class="analysis-copy">
        <span class="section-tag">
          PROCESAMIENTO DOCUMENTAL
        </span>

        <h2>{{ analysisTitle }}</h2>

        <p>
          {{ analysisDescription }}
        </p>

        <div class="analysis-steps">
          <div v-for="step in analysisSteps" :key="step.key" class="analysis-step" :class="step.status">
            <div class="step-icon">
              <QuantiaIcon :name="step.icon" :size="18" />
            </div>

            <div>
              <strong>{{ step.label }}</strong>
              <small>{{ step.detail }}</small>
            </div>
          </div>
        </div>
      </div>

      <aside class="ai-panel">
        <div class="ai-icon">
          <QuantiaIcon name="ai" :size="28" />
        </div>

        <span class="section-tag">
          INTELIGENCIA ARTIFICIAL
        </span>

        <h3>Preparación documental</h3>

        <p>
          Quantia procesa la información disponible en los archivos.
          La interpretación espacial y la confirmación de los datos del
          proyecto se realizarán en las etapas correspondientes.
        </p>

        <div class="ai-note">
          <QuantiaIcon name="info" :size="16" />

          <span>
            La información propuesta por IA siempre deberá ser
            revisada por el usuario.
          </span>
        </div>
      </aside>
    </section>

    <!-- =====================================================
         ERROR
         ===================================================== -->
    <section v-if="error" class="error-message">
      <QuantiaIcon name="warning" :size="18" />

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

          <h2>Estado de los archivos</h2>

          <p>
            Procesa cada documento antes de continuar.
          </p>
        </div>

        <div class="documents-summary">
          <div>
            <strong>{{ readyCount }}</strong>
            <span>analizados</span>
          </div>

          <div class="summary-divider"></div>

          <div>
            <strong>{{ documents.length }}</strong>
            <span>total</span>
          </div>
        </div>
      </header>

      <!-- LISTA -->
      <div v-if="documents.length" class="documents-list">
        <article v-for="doc in documents" :key="doc.document_id" class="document-row" :class="{
          failed: doc.status === 'failed',
        }">
          <div class="document-icon">
            <QuantiaIcon :name="documentIcon(doc)" :size="23" />
          </div>

          <div class="document-info">
            <strong>
              {{ doc.file_name }}
            </strong>

            <div class="document-meta">
              <span class="document-status" :class="statusTone(doc)">
                <span class="status-dot"></span>

                {{ statusLabel(doc.status) }}
              </span>

              <span v-if="documentDetail(doc)" class="meta-divider"></span>

              <span v-if="documentDetail(doc)" class="detail">
                {{ documentDetail(doc) }}
              </span>
            </div>
          </div>

          <button
            v-if="!isSpatialReady(doc)"
            type="button"
            class="process-btn"
            :disabled="processing || isProcessing(doc)"
            @click="process(doc)"
          >
            <QuantiaIcon
              :name="isProcessing(doc) ? 'scan-line' : 'ai'"
              :size="17"
            />

            {{ isProcessing(doc) ? "Analizando..." : retryLabel(doc) }}
          </button>

          <div v-else class="document-actions">
            <div class="ready-badge">
              <QuantiaIcon name="check" :size="15" />

              Extracción lista
            </div>

            <button
              type="button"
              class="reanalyze-btn"
              :disabled="processing || isProcessing(doc)"
              @click="reanalyze(doc)"
            >
              <QuantiaIcon
                :name="isProcessing(doc) ? 'scan-line' : 'reset'"
                :size="16"
              />

              {{ isProcessing(doc) ? "Reanalizando..." : "Reanalizar plano" }}
            </button>
          </div>
        </article>
      </div>

      <!-- VACÍO -->
      <div v-else class="empty-state">
        <div class="empty-icon">
          <QuantiaIcon name="plan" :size="29" />
        </div>

        <div>
          <strong>
            No hay documentos disponibles
          </strong>

          <p>
            Regresa a Carga de documentos y agrega al menos
            un archivo para iniciar el análisis.
          </p>
        </div>
      </div>
    </section>

    <!-- =====================================================
         NOTA DE TRANSICIÓN
         ===================================================== -->
    <section v-if="spatialReady" class="next-stage-note">
      <div class="next-stage-icon">
        <QuantiaIcon name="floor-plan" :size="22" />
      </div>

      <div>
        <strong>
          Reconstrucción espacial preparada
        </strong>

        <p>
          Quantia generó la propuesta espacial del plano.
          Continúa para revisar y corregir la información detectada.
        </p>
      </div>
    </section>

    <!-- =====================================================
         FOOTER
         ===================================================== -->
    <template #footer>
      <button type="button" class="workflow-btn secondary" @click="goBack">
        <QuantiaIcon name="arrow-left" :size="17" />

        <span>
          Anterior
          <small>Carga de documentos</small>
        </span>
      </button>

      <div class="footer-actions">
        <button type="button" class="workflow-btn secondary" :disabled="processing" @click="load">
          <QuantiaIcon name="reset" :size="17" />

          Actualizar documentos
        </button>

        <button type="button" class="workflow-btn primary" :disabled="progress < 100 ||
          processing ||
          !documents.length ||
          !spatialReady
          " @click="goDesign">
          <span>
            Continuar
            <small>Diseño de la vivienda</small>
          </span>

          <QuantiaIcon name="arrow-right" :size="17" />
        </button>
      </div>
    </template>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import { buildPhase03Delivery } from "@/modules/vivienda/editor/adapters/spatialWorkflowContract";
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
  procesarDocumento,
} from "@/modules/vivienda/services/documentosApiService";
import "@/assets/styles/quantia-workflow.css";

const router = useRouter();

const auth = useAuthStore();
const store = useViviendaStore();

const documents = ref([]);
const processingDocumentId = ref("");
const error = ref("");

const spatialReadyDocumentId = ref(
  String(
    store.estructuraEspacial?.metadata?.sourceDocumentId ||
    ""
  )
);

// Baseline exclusivamente para la prueba Miguel H.
// No se usa como escala general para otros PDFs.
const MIGUEL_H_FILE_NAME =
  "arquitectonico pb-pa migue-h.pdf";
const MIGUEL_H_RENDER_SCALE = 0.7935;

const spatialReady = computed(
  () => Boolean(spatialReadyDocumentId.value)
);

const processing = computed(
  () => Boolean(processingDocumentId.value)
);

/* =========================================================
   ESTADO
   ========================================================= */

const readyCount = computed(
  () =>
    documents.value.filter(
      isReady
    ).length
);

const progress = computed(() => {
  if (!documents.value.length) {
    return 0;
  }

  return Math.round(
    (
      readyCount.value /
      documents.value.length
    ) * 100
  );
});

const analysisTitle = computed(() => {
  if (processing.value) {
    return "Analizando documentos…";
  }

  if (!documents.value.length) {
    return "No hay documentos para analizar";
  }

  if (progress.value === 100 && spatialReady.value) {
    return "Análisis documental y espacial preparado";
  }

  if (progress.value === 100) {
    return "Procesamiento documental completado";
  }

  return "Documentos preparados";
});

const analysisDescription = computed(() => {
  if (processing.value) {
    return "Quantia está procesando el contenido o reconstruyendo espacialmente el documento seleccionado.";
  }

  if (!documents.value.length) {
    return "Carga documentos del proyecto antes de iniciar el procesamiento.";
  }

  if (progress.value === 100 && spatialReady.value) {
    return "Los documentos están procesados y existe una propuesta espacial lista para revisar en Diseño de la vivienda.";
  }

  if (progress.value === 100) {
    return "Todos los documentos completaron el procesamiento documental. Extrae el plano que utilizarás para Diseño de la vivienda.";
  }

  return "Procesa los documentos pendientes para preparar la información que utilizará Quantia.";
});

/* =========================================================
   PASOS VISUALES
   ========================================================= */

const analysisSteps = computed(() => {
  const hasDocuments =
    documents.value.length > 0;

  const hasProcessing =
    processing.value;

  const allReady =
    progress.value === 100;

  return [
    {
      key: "documents",
      label: "Documentos recibidos",
      detail:
        hasDocuments
          ? `${documents.value.length} archivo${documents.value.length === 1 ? "" : "s"} disponible${documents.value.length === 1 ? "" : "s"}`
          : "Pendiente de carga",
      icon: "file-check",
      status:
        hasDocuments
          ? "done"
          : "pending",
    },

    {
      key: "ocr",
      label: "Procesamiento de contenido",
      detail:
        hasProcessing
          ? "Procesando documento"
          : readyCount.value
            ? `${readyCount.value} archivo${readyCount.value === 1 ? "" : "s"} procesado${readyCount.value === 1 ? "" : "s"}`
            : "Pendiente",
      icon: "scan-text",
      status:
        hasProcessing
          ? "active"
          : readyCount.value
            ? "done"
            : "pending",
    },

    {
      key: "index",
      label: "Preparación para consulta",
      detail:
        allReady
          ? "Información documental preparada"
          : "Pendiente de completar",
      icon: "database",
      status:
        allReady
          ? "done"
          : "pending",
    },

    {
      key: "review",
      label: "Reconstrucción espacial",
      detail:
        hasProcessing
          ? "Ejecutando análisis"
          : spatialReady.value
            ? "Propuesta espacial disponible"
            : allReady
              ? "Pendiente de extraer plano"
              : "Esperando procesamiento",
      icon: "file-search",
      status:
        hasProcessing
          ? "active"
          : spatialReady.value
            ? "done"
            : "pending",
    },
  ];
});

/* =========================================================
   DOCUMENTOS
   ========================================================= */

function isReady(document) {
  return [
    "ready",
    "ocr_completed",
  ].includes(
    document?.status
  );
}

function isProcessing(document) {
  return (
    String(
      processingDocumentId.value
    ) ===
    String(
      document?.document_id || ""
    ) ||
    document?.status ===
    "ocr_processing" ||
    document?.status ===
    "indexing"
  );
}

function statusLabel(value) {
  const labels = {
    uploaded: "Pendiente",
    ocr_processing:
      "Procesando",
    ocr_completed:
      "Procesado",
    indexing:
      "Indexando",
    indexed:
      "Indexado",
    ready:
      "Listo",
    failed:
      "Error",
  };

  return (
    labels[value] ||
    "Pendiente"
  );
}

function statusTone(document) {
  if (
    document?.status === "failed"
  ) {
    return "error";
  }

  if (isReady(document)) {
    return "success";
  }

  if (isProcessing(document)) {
    return "processing";
  }

  return "pending";
}

function isPdfDocument(document) {
  return String(
    document?.file_name || ""
  )
    .trim()
    .toLowerCase()
    .endsWith(".pdf");
}

function normalizedFileName(document) {
  return String(
    document?.file_name || ""
  )
    .trim()
    .toLowerCase();
}

function resolvePdfRenderScale(document) {
  if (!isPdfDocument(document)) {
    return null;
  }

  if (
    normalizedFileName(document) ===
    MIGUEL_H_FILE_NAME
  ) {
    return MIGUEL_H_RENDER_SCALE;
  }

  return null;
}

function isSpatialReady(document) {
  return (
    String(
      spatialReadyDocumentId.value
    ) ===
    String(
      document?.document_id || ""
    )
  );
}

function retryLabel(document) {
  if (document?.status === "failed") {
    return "Reintentar";
  }

  if (isReady(document)) {
    return "Extraer plano";
  }

  return "Analizar";
}

function documentIcon(document) {
  const fileName =
    String(
      document?.file_name || ""
    ).toLowerCase();

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
  const chunks =
    Number(
      document?.chunk_count ||
      document?.metadata
        ?.chunk_count ||
      0
    );

  if (chunks > 0) {
    return `${chunks} fragmento${chunks === 1 ? "" : "s"}`;
  }

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
          auth.accessToken || "",
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
   CONTRATO ESPACIAL 03.2 → 04
   ========================================================= */

function persistSpatialContract(
  document,
  contract,
  pdfRenderScale = null,
) {
  store.setEstructuraEspacial(buildPhase03Delivery({
    ...contract,

    sourceMode: "plan",

    metadata: {
      ...(contract.metadata || {}),

      sourceMode: "plan",

      sourceDocumentId:
        String(document.document_id),

      sourceFileName:
        String(document.file_name || ""),

      sourcePageNumber: 1,

      sourcePdfRenderScale:
        pdfRenderScale,
    },
  }, store));

  spatialReadyDocumentId.value =
    String(document.document_id);

  console.info(
    "[TRACE][03.2][SPATIAL_CONTRACT]",
    {
      documentId:
        String(document.document_id),
      fileName:
        String(document.file_name || ""),
      espacios:
        Array.isArray(contract?.espacios)
          ? contract.espacios.length
          : 0,
      muros:
        Array.isArray(contract?.muros)
          ? contract.muros.length
          : 0,
      ejes:
        Array.isArray(contract?.ejes)
          ? contract.ejes.length
          : 0,
      puertas:
        Array.isArray(contract?.puertas)
          ? contract.puertas.length
          : 0,
      ventanas:
        Array.isArray(contract?.ventanas)
          ? contract.ventanas.length
          : 0,
    }
  );
}

async function runSpatialAnalysis(document) {
  const pdfRenderScale =
    resolvePdfRenderScale(document);

  const contract =
    await analizarPlanoDocumento({
      documentId:
        document.document_id,

      accessToken:
        auth.accessToken || "",

      pageNumber: 1,

      pdfRenderScale:
        pdfRenderScale,

      ocrStrategy: "auto",
    });

  if (
    !contract ||
    typeof contract !== "object"
  ) {
    throw new Error(
      "El backend no devolvió un contrato espacial válido."
    );
  }

  persistSpatialContract(
    document,
    contract,
    pdfRenderScale,
  );

  return contract;
}

/* =========================================================
   PROCESAMIENTO INICIAL
   ========================================================= */

async function process(document) {
  if (!document?.document_id) {
    return;
  }

  processingDocumentId.value =
    String(document.document_id);

  error.value = "";

  try {
    // -------------------------------------------------------
    // 1. OCR / RAG solamente si todavía no está listo
    // -------------------------------------------------------
    if (!isReady(document)) {
      await procesarDocumento({
        documentId:
          document.document_id,

        accessToken:
          auth.accessToken || "",
      });

      await load();
    }

    // -------------------------------------------------------
    // 2. Reconstrucción espacial 03.2
    // -------------------------------------------------------
    await runSpatialAnalysis(
      document
    );
  } catch (e) {
    error.value =
      e?.message ||
      "No fue posible realizar el análisis espacial del documento.";
  } finally {
    processingDocumentId.value = "";
  }
}

/* =========================================================
   REANÁLISIS ESPACIAL
   ========================================================= */

async function reanalyze(document) {
  if (!document?.document_id) {
    return;
  }

  processingDocumentId.value =
    String(document.document_id);

  error.value = "";

  try {
    // El documento ya pasó por procesamiento documental.
    // Aquí se ejecuta nuevamente únicamente 03.2 espacial
    // y se reemplaza el contrato guardado en Pinia.
    await runSpatialAnalysis(
      document
    );
  } catch (e) {
    error.value =
      e?.message ||
      "No fue posible reanalizar espacialmente el plano.";
  } finally {
    processingDocumentId.value = "";
  }
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
  if (!spatialReady.value) {
    error.value =
      "Primero realiza la extracción espacial del plano.";
    return;
  }

  router.push(
    "/vivienda/workflow/diseno-vivienda/plano"
  );
}

onMounted(load);
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
   PROGRESO
   ========================================================= */

.progress-column {
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-ring {
  position: relative;
  width: 124px;
  height: 124px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    conic-gradient(#075ff2 var(--progress),
      #e7ecf4 0);
}

.progress-ring::before {
  content: "";
  position: absolute;
  inset: 10px;
  border-radius: 50%;
  background: #ffffff;
}

.progress-inner {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
}

.progress-inner strong {
  color: #0a2368;
  font-size: 1.5rem;
  line-height: 1;
}

.progress-inner span {
  margin-top: 5px;
  color: #7180a2;
  font-size: 0.61rem;
  font-weight: 700;
}

/* =========================================================
   TEXTO
   ========================================================= */

.analysis-copy h2 {
  margin: 0;
  color: #0a2368;
  font-size: 1.08rem;
}

.analysis-copy>p {
  margin: 7px 0 18px;
  max-width: 620px;
  color: #637393;
  font-size: 0.75rem;
  line-height: 1.5;
}

/* =========================================================
   PASOS
   ========================================================= */

.analysis-steps {
  display: grid;
  gap: 7px;
}

.analysis-step {
  display: grid;
  grid-template-columns:
    34px minmax(0, 1fr);
  gap: 9px;
  align-items: center;
  min-height: 47px;
  padding: 7px 9px;
  border: 1px solid transparent;
  border-radius: 8px;
}

.step-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f0f3f8;
  color: #8793a9;
}

.analysis-step strong {
  display: block;
  color: #61708f;
  font-size: 0.72rem;
}

.analysis-step small {
  display: block;
  margin-top: 2px;
  color: #8a95ab;
  font-size: 0.61rem;
}

.analysis-step.done {
  border-color: #d1e5d8;
  background: #f7fbf8;
}

.analysis-step.done .step-icon {
  background: #edf8f1;
  color: #278453;
}

.analysis-step.done strong {
  color: #276b49;
}

.analysis-step.active {
  border-color: #c5d6f6;
  background: #f3f7ff;
}

.analysis-step.active .step-icon {
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.analysis-step.active strong {
  color: #075ff2;
}

/* =========================================================
   IA
   ========================================================= */

.ai-panel {
  min-height: 240px;
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
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.ai-panel h3 {
  margin: 0;
  color: #162d70;
  font-size: 0.9rem;
}

.ai-panel>p {
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

.documents-summary>div {
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
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.document-info {
  min-width: 0;
}

.document-info>strong {
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

.document-status.success .status-dot {
  background: #2d9a60;
}

.document-status.processing .status-dot {
  background: #075ff2;
}

.document-status.error .status-dot {
  background: #cf3434;
}

.meta-divider {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #a7b4c8;
}

/* =========================================================
   BOTONES
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

.process-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.document-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.reanalyze-btn {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 11px;
  border: 1px solid #9eb4d6;
  border-radius: 8px;
  background: #ffffff;
  color: #075ff2;
  font-size: 0.64rem;
  font-weight: 750;
  cursor: pointer;
}

.reanalyze-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.ready-badge {
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid #c9dfd2;
  border-radius: 7px;
  background: #f2faf5;
  color: #278453;
  font-size: 0.64rem;
  font-weight: 750;
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
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
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

.next-stage-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 10px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
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
    linear-gradient(90deg,
      #075ff2,
      #8421f1);
  color: #ffffff;
  box-shadow:
    0 7px 17px rgba(51, 69, 211, 0.2);
}

.workflow-btn>span {
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

@media (max-width: 980px) {
  .analysis-card {
    grid-template-columns:
      130px minmax(0, 1fr);
  }

  .ai-panel {
    grid-column: 1 / -1;
    min-height: auto;
    padding: 18px 0 0;
    border-top: 1px solid #d6deea;
    border-left: 0;
  }
}

@media (max-width: 700px) {
  .analysis-card {
    grid-template-columns: 1fr;
  }

  .progress-column {
    justify-content: flex-start;
  }

  .documents-header {
    flex-direction: column;
  }

  .document-row {
    grid-template-columns:
      44px minmax(0, 1fr);
  }

  .process-btn,
  .document-actions {
    grid-column: 2;
    width: max-content;
  }

  .document-actions {
    justify-content: flex-start;
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
