<template>
  <QuantiaWorkflowLayout :step="3" title="3.1 Carga de documentos"
    subtitle="Sube los planos y documentos de tu proyecto para que la IA los analice.">
    <!-- =====================================================
         NOTA INFORMATIVA
         ===================================================== -->
    <section class="info-note">
      <div class="info-icon">
        <QuantiaIcon name="info" :size="18" />
      </div>

      <div>
        <strong>Puedes cargar varios archivos</strong>

        <p>
          Quantia utilizará los documentos cargados para identificar
          planos e información relevante antes de pasar a la revisión
          con inteligencia artificial.
        </p>
      </div>
    </section>

    <!-- =====================================================
         ZONA DE CARGA
         ===================================================== -->
    <section class="upload-zone" :class="{
      dragging: dragActive,
      uploading,
    }" @dragenter.prevent="dragActive = true" @dragover.prevent="dragActive = true"
      @dragleave.prevent="handleDragLeave" @drop.prevent="dropFiles">
      <div class="upload-icon">
        <QuantiaIcon name="upload" :size="34" :stroke-width="1.7" />
      </div>

      <div class="upload-copy">
        <span class="section-tag">
          CARGA DE DOCUMENTOS
        </span>

        <h2>
          Arrastra y suelta tus archivos aquí
        </h2>

        <p>
          También puedes seleccionarlos directamente
          desde tu equipo.
        </p>
      </div>

      <input ref="input" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" hidden @change="pickFiles" />

      <button type="button" class="select-files-btn" :disabled="uploading" @click="input?.click()">
        <QuantiaIcon name="folder" :size="18" />

        <span>
          {{
            uploading
              ? "Subiendo archivos..."
              : "Seleccionar archivos"
          }}
        </span>
      </button>

      <div class="upload-rules">
        <span>PDF</span>
        <span>PNG</span>
        <span>JPG</span>
        <span>JPEG</span>

        <small>
          Máximo 100 MB por archivo
        </small>
      </div>
    </section>

    <!-- =====================================================
         ERROR
         ===================================================== -->
    <section v-if="error" class="error-message">
      <div class="error-icon">
        <QuantiaIcon name="warning" :size="18" />
      </div>

      <p>{{ error }}</p>
    </section>

    <!-- =====================================================
         DOCUMENTOS
         ===================================================== -->
    <section class="files-section">
      <header class="files-header">
        <div>
          <span class="section-tag">
            DOCUMENTOS DEL PROYECTO
          </span>

          <h2>Archivos cargados</h2>

          <p>
            Revisa los documentos disponibles antes
            de iniciar el análisis.
          </p>
        </div>

        <div class="documents-counter">
          <strong>
            {{ documents.length }}
          </strong>

          <span>
            {{
              documents.length === 1
                ? "archivo"
                : "archivos"
            }}
          </span>
        </div>
      </header>

      <!-- LISTA -->
      <div v-if="documents.length" class="files-list">
        <article v-for="doc in documents" :key="doc.document_id" class="file-row" :class="{
          failed: doc.status === 'failed',
        }">
          <div class="file-type-icon">
            <QuantiaIcon :name="fileIcon(doc.file_name)" :size="24" />

            <span>
              {{ extension(doc.file_name) }}
            </span>
          </div>

          <div class="file-copy">
            <strong>
              {{ doc.file_name }}
            </strong>

            <div class="file-meta">
              <span>
                {{
                  formatBytes(
                    doc.metadata?.file_size ||
                    doc.size_bytes
                  )
                }}
              </span>

              <span class="meta-divider"></span>

              <span>
                {{ statusLabel(doc.status) }}
              </span>
            </div>
          </div>

          <span class="status-badge" :class="statusClass(doc.status)">
            <QuantiaIcon :name="doc.status === 'failed'
                ? 'warning'
                : 'file-check'
              " :size="14" />

            {{ statusLabel(doc.status) }}
          </span>
        </article>
      </div>

      <!-- VACÍO -->
      <div v-else class="empty-state">
        <div class="empty-icon">
          <QuantiaIcon name="plan" :size="30" />
        </div>

        <div>
          <strong>
            Todavía no hay documentos
          </strong>

          <p>
            Agrega al menos un archivo para continuar
            con el análisis del proyecto.
          </p>
        </div>
      </div>
    </section>

    <!-- =====================================================
         PIE
         ===================================================== -->
    <template #footer>
      <button type="button" class="workflow-btn secondary" @click="goBack">
        <QuantiaIcon name="arrow-left" :size="17" />

        <span>
          Anterior
          <small>
            Cómo se construirá
          </small>
        </span>
      </button>

      <div class="footer-actions">
        <button type="button" class="workflow-btn secondary" :disabled="uploading" @click="loadDocuments">
          <QuantiaIcon name="reset" :size="17" />

          Actualizar lista
        </button>

        <button type="button" class="workflow-btn primary" :disabled="uploading ||
          !documents.length
          " @click="goAnalysis">
          <span>
            Analizar con IA
            <small>
              Planos y revisión
            </small>
          </span>

          <QuantiaIcon name="arrow-right" :size="17" />
        </button>
      </div>
    </template>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import {
  onMounted,
  ref,
} from "vue";

import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/authStore";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";

import QuantiaIcon from "@/components/common/QuantiaIcon.vue";

import {
  listarDocumentos,
  subirDocumento,
} from "@/modules/vivienda/services/documentosApiService";

import "@/assets/styles/quantia-workflow.css";

const router = useRouter();

const auth = useAuthStore();

const input = ref(null);

const documents = ref([]);

const uploading = ref(false);

const dragActive = ref(false);

const error = ref("");

const MAX_FILE_SIZE =
  100 * 1024 * 1024;

const allowedExtensions = [
  "pdf",
  "png",
  "jpg",
  "jpeg",
];

/* =========================================================
   VALIDACIÓN
   ========================================================= */

function validateFiles(files) {
  const validFiles = [];

  error.value = "";

  for (const file of files) {
    const ext = String(
      file.name || ""
    )
      .split(".")
      .pop()
      ?.toLowerCase();

    if (
      !allowedExtensions.includes(ext)
    ) {
      error.value =
        `Formato no permitido: ${file.name}`;

      continue;
    }

    if (
      file.size > MAX_FILE_SIZE
    ) {
      error.value =
        `${file.name} supera el límite de 100 MB.`;

      continue;
    }

    validFiles.push(file);
  }

  return validFiles;
}

/* =========================================================
   CARGA
   ========================================================= */

async function upload(files) {
  const validFiles =
    validateFiles(files);

  if (!validFiles.length) {
    return;
  }

  uploading.value = true;

  const uploadErrors = [];

  for (const file of validFiles) {
    try {
      await subirDocumento({
        file,
        accessToken:
          auth.accessToken || "",
      });
    } catch (e) {
      uploadErrors.push(
        e?.message ||
        `No fue posible subir ${file.name}.`
      );
    }
  }

  uploading.value = false;

  await loadDocuments();

  if (uploadErrors.length) {
    error.value =
      uploadErrors.join(" ");
  }
}

async function pickFiles(event) {
  await upload(
    [...event.target.files]
  );

  event.target.value = "";
}

async function dropFiles(event) {
  dragActive.value = false;

  await upload(
    [...event.dataTransfer.files]
  );
}

function handleDragLeave(event) {
  const current =
    event.currentTarget;

  const related =
    event.relatedTarget;

  if (
    current &&
    related &&
    current.contains(related)
  ) {
    return;
  }

  dragActive.value = false;
}

/* =========================================================
   DOCUMENTOS
   ========================================================= */

async function loadDocuments() {
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
   PRESENTACIÓN
   ========================================================= */

function extension(name) {
  return (
    String(name || "")
      .split(".")
      .pop()
      ?.toUpperCase() ||
    "DOC"
  );
}

function fileIcon(name) {
  const ext = extension(name)
    .toLowerCase();

  if (
    ["png", "jpg", "jpeg"].includes(
      ext
    )
  ) {
    return "image";
  }

  if (ext === "pdf") {
    return "file";
  }

  return "plan";
}

function formatBytes(value) {
  const size =
    Number(value || 0);

  if (size > 1048576) {
    return `${(
      size / 1048576
    ).toFixed(1)} MB`;
  }

  if (size > 1024) {
    return `${(
      size / 1024
    ).toFixed(0)} KB`;
  }

  if (size) {
    return `${size} B`;
  }

  return "Archivo";
}

function statusLabel(value) {
  const labels = {
    uploaded: "Subido",
    failed: "Error",
  };

  return (
    labels[value] ||
    "Subido"
  );
}

function statusClass(value) {
  if (value === "failed") {
    return "error";
  }

  return "success";
}

/* =========================================================
   NAVEGACIÓN
   ========================================================= */

function goBack() {
  router.push(
    "/vivienda/workflow/como-se-construira"
  );
}

function goAnalysis() {
  router.push(
    "/vivienda/workflow/planos-revision/analisis"
  );
}

onMounted(loadDocuments);
</script>

<style scoped>
* {
  box-sizing: border-box;
}

/* =========================================================
   NOTA
   ========================================================= */

.info-note {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #c9d5e6;
  border-radius: 10px;
  background: #f3f6fb;
}

.info-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border: 1px solid #d2deef;
  border-radius: 10px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.info-note strong {
  display: block;
  margin-bottom: 3px;
  color: #162d70;
  font-size: 0.79rem;
}

.info-note p {
  margin: 0;
  color: #637393;
  font-size: 0.73rem;
  line-height: 1.45;
}

/* =========================================================
   ETIQUETA
   ========================================================= */

.section-tag {
  display: block;
  margin-bottom: 6px;
  color: #0877ef;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.055em;
}

/* =========================================================
   ZONA DE CARGA
   ========================================================= */

.upload-zone {
  min-height: 270px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 14px;
  padding: 30px;
  border: 1.5px dashed #aebed5;
  border-radius: 12px;
  background:
    radial-gradient(circle at 50% 20%,
      rgba(7, 95, 242, 0.055),
      transparent 35%),
    #ffffff;
  text-align: center;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.upload-zone.dragging {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f3f7ff,
      #f8f5ff);
  box-shadow:
    0 0 0 3px rgba(7, 95, 242, 0.08);
}

.upload-zone.uploading {
  opacity: 0.8;
}

.upload-icon {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border: 1px solid #d2deef;
  border-radius: 16px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.upload-copy {
  max-width: 620px;
}

.upload-copy h2 {
  margin: 0;
  color: #0a2368;
  font-size: 1.15rem;
}

.upload-copy p {
  margin: 7px 0 0;
  color: #637393;
  font-size: 0.79rem;
  line-height: 1.45;
}

/* =========================================================
   BOTÓN CARGAR
   ========================================================= */

.select-files-btn {
  min-height: 47px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 22px;
  border: 0;
  border-radius: 9px;
  background:
    linear-gradient(90deg,
      #075ff2,
      #8421f1);
  color: #ffffff;
  font-size: 0.84rem;
  font-weight: 750;
  cursor: pointer;
  box-shadow:
    0 7px 17px rgba(51, 69, 211, 0.2);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.select-files-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow:
    0 10px 22px rgba(51, 69, 211, 0.25);
}

.select-files-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* =========================================================
   REGLAS
   ========================================================= */

.upload-rules {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 7px;
}

.upload-rules>span {
  min-height: 25px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border: 1px solid #d2deed;
  border-radius: 6px;
  background: #f3f6fb;
  color: #52678d;
  font-size: 0.62rem;
  font-weight: 800;
}

.upload-rules small {
  margin-left: 5px;
  color: #7b87a7;
  font-size: 0.67rem;
}

/* =========================================================
   ERROR
   ========================================================= */

.error-message {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e8b9b9;
  border-radius: 9px;
  background: #fff5f5;
}

.error-icon {
  flex-shrink: 0;
  color: #c82727;
}

.error-message p {
  margin: 0;
  color: #b02b2b;
  font-size: 0.74rem;
  line-height: 1.45;
}

/* =========================================================
   DOCUMENTOS
   ========================================================= */

.files-section {
  margin-top: 18px;
  padding: 22px;
  border: 1px solid #bcc9dc;
  border-radius: 11px;
  background: #ffffff;
  box-shadow:
    0 3px 10px rgba(32, 55, 105, 0.03);
}

.files-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding-bottom: 17px;
  border-bottom: 1px solid #d4ddea;
}

.files-header h2 {
  margin: 0;
  color: #162d70;
  font-size: 1rem;
}

.files-header p {
  margin: 5px 0 0;
  color: #7180a2;
  font-size: 0.74rem;
}

.documents-counter {
  min-width: 83px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 11px;
  border: 1px solid #c9d5e8;
  border-radius: 9px;
  background: #f1f5fb;
}

.documents-counter strong {
  color: #075ff2;
  font-size: 0.92rem;
}

.documents-counter span {
  color: #697b9d;
  font-size: 0.66rem;
  font-weight: 700;
}

/* =========================================================
   LISTA
   ========================================================= */

.files-list {
  display: grid;
  gap: 9px;
}

.file-row {
  display: grid;
  grid-template-columns:
    58px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 13px 15px;
  border: 1px solid #c5d0e1;
  border-radius: 9px;
  background: #ffffff;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.file-row:hover {
  border-color: #9db4dd;
  box-shadow:
    0 5px 14px rgba(44, 69, 126, 0.05);
}

.file-row.failed {
  border-color: #e1bebe;
}

.file-type-icon {
  position: relative;
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border: 1px solid #d2deef;
  border-radius: 11px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.file-type-icon>span {
  position: absolute;
  right: -5px;
  bottom: -5px;
  min-width: 28px;
  height: 19px;
  display: grid;
  place-items: center;
  padding: 0 5px;
  border: 1px solid #d1dbea;
  border-radius: 5px;
  background: #ffffff;
  color: #52678d;
  font-size: 0.54rem;
  font-weight: 800;
}

.file-copy {
  min-width: 0;
}

.file-copy>strong {
  display: block;
  overflow: hidden;
  color: #162d70;
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 6px;
  color: #7180a2;
  font-size: 0.67rem;
}

.meta-divider {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #a6b3c8;
}

/* =========================================================
   ESTADOS
   ========================================================= */

.status-badge {
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border-radius: 7px;
  font-size: 0.65rem;
  font-weight: 750;
}

.status-badge.success {
  border: 1px solid #c9dfd2;
  background: #f2faf5;
  color: #278453;
}

.status-badge.error {
  border: 1px solid #e6c5c5;
  background: #fff4f4;
  color: #c82727;
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
  font-size: 0.78rem;
}

.empty-state p {
  margin: 4px 0 0;
  color: #7180a2;
  font-size: 0.7rem;
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
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.workflow-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.workflow-btn.secondary {
  border: 1px solid #aebed5;
  background: #ffffff;
  color: #52678d;
}

.workflow-btn.secondary:hover:not(:disabled) {
  border-color: #075ff2;
  color: #075ff2;
}

.workflow-btn.primary {
  min-width: 210px;
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
  transform: none;
  box-shadow: none;
}

/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 760px) {
  .upload-zone {
    min-height: 240px;
    padding: 24px 18px;
  }

  .files-section {
    padding: 18px;
  }

  .files-header {
    flex-direction: column;
  }

  .file-row {
    grid-template-columns:
      52px minmax(0, 1fr);
  }

  .status-badge {
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

@media (max-width: 480px) {
  .info-note {
    padding: 12px;
  }

  .upload-rules small {
    width: 100%;
    margin: 3px 0 0;
  }

  .file-row {
    grid-template-columns: 1fr;
  }

  .file-type-icon {
    width: 48px;
    height: 48px;
  }

  .status-badge {
    grid-column: auto;
  }
}
</style>