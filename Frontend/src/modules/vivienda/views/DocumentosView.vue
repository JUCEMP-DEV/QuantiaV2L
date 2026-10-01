<template>
  <div class="documents-page">
    <div class="background-orb orb-left"></div>
    <div class="background-orb orb-right"></div>

    <main class="documents-shell">
      <header class="topbar">
        <LogoQuantia />

        <nav class="topnav" aria-label="Navegacion del modulo documental">
          <a href="#" @click.prevent="goDashboard">Inicio</a>
          <a href="#document-list">Documentos</a>
          <a href="#assistant-panel">Asistente</a>
        </nav>

        <div class="user-pill">
          <span>Sesion activa</span>
          <strong>{{ userName }}</strong>
        </div>
      </header>

      <section class="hero-card">
        <div>
          <p class="eyebrow">Quantia · Asistente documental</p>
          <h1>Consulta documentos sin alterar tu cotizacion</h1>
          <p class="hero-copy">
            Sube planos, reportes o imagenes; revisa el resultado del OCR, prepara el contenido
            para busqueda semantica y consulta el documento seleccionado.
          </p>
        </div>

        <div class="health-panel" :class="healthTone">
          <div class="health-heading">
            <span class="status-dot" aria-hidden="true"></span>
            <strong>Estado del modelo</strong>
          </div>
          <p>{{ healthMessage }}</p>
          <small v-if="llmHealth?.model">Modelo: {{ llmHealth.model }}</small>
          <button class="text-button" type="button" :disabled="loadingHealth" @click="loadHealth">
            {{ loadingHealth ? "Comprobando..." : "Volver a comprobar" }}
          </button>
        </div>
      </section>

      <div v-if="notice.message" class="notice" :class="`notice-${notice.type}`" role="status">
        <div>
          <strong>{{ notice.message }}</strong>
          <span v-if="lastError?.suggestion">{{ lastError.suggestion }}</span>
        </div>
        <button
          v-if="lastError?.retryAction"
          class="notice-action"
          type="button"
          @click="retryLastOperation"
        >
          {{ retryLabel }}
        </button>
      </div>

      <section class="workflow-strip" aria-label="Estado del flujo documental">
        <div
          v-for="(phase, index) in workflowPhases"
          :key="phase.key"
          class="workflow-phase"
          :class="phase.status"
        >
          <span class="phase-number">{{ index + 1 }}</span>
          <div>
            <strong>{{ phase.label }}</strong>
            <small>{{ phase.detail }}</small>
          </div>
        </div>
      </section>

      <section class="workspace-grid">
        <article class="panel upload-panel">
          <div class="panel-heading">
            <div>
              <p class="section-label">1 · Incorporar fuente</p>
              <h2>Subir documento</h2>
            </div>
            <span class="panel-badge">OCR</span>
          </div>

          <label class="file-drop" :class="{ selected: selectedFile }">
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.txt,application/pdf,image/*,text/plain"
              @change="handleFileChange"
            />
            <span class="file-icon" aria-hidden="true">DOC</span>
            <strong>{{ selectedFile?.name || "Selecciona un PDF, imagen o TXT" }}</strong>
            <small>
              {{ selectedFile ? formatBytes(selectedFile.size) : "El backend validara tipo, tamano y paginas." }}
            </small>
          </label>

          <button class="primary-button full-width" type="button" :disabled="!selectedFile || uploading" @click="uploadDocument">
            {{ uploading ? "Subiendo y procesando OCR..." : "Subir y procesar OCR" }}
          </button>

          <div class="ocr-preview" :class="{ empty: !selectedUploadResult?.text }">
            <div class="preview-heading">
              <strong>Texto extraido</strong>
              <span v-if="selectedUploadResult?.text">{{ selectedUploadResult.text.length }} caracteres</span>
            </div>
            <p>
              {{
                selectedUploadResult?.text ||
                "El texto OCR del documento que subas aparecera aqui durante esta sesion."
              }}
            </p>
          </div>
        </article>

        <article id="document-list" class="panel list-panel">
          <div class="panel-heading">
            <div>
              <p class="section-label">2 · Biblioteca personal</p>
              <h2>Documentos procesados</h2>
            </div>
            <button class="secondary-button compact" type="button" :disabled="loadingDocuments" @click="loadDocuments">
              {{ loadingDocuments ? "Actualizando..." : "Actualizar" }}
            </button>
          </div>

          <div v-if="loadingDocuments && !documents.length" class="empty-state">
            Cargando documentos...
          </div>
          <div v-else-if="!documents.length" class="empty-state">
            <strong>Aun no hay documentos</strong>
            <span>Sube el primero para comenzar a consultar su contenido.</span>
          </div>

          <div v-else class="document-list">
            <article
              v-for="document in documents"
              :key="document.document_id"
              class="document-card"
              :class="{ active: document.document_id === selectedDocumentId }"
              @click="selectDocument(document.document_id)"
            >
              <div class="document-title-row">
                <div>
                  <strong>{{ document.file_name }}</strong>
                  <span>{{ documentType(document) }}</span>
                </div>
                <span class="index-status" :class="document.indexed ? 'ready' : 'pending'">
                  {{ document.indexed ? "Indexado" : "Sin indexar" }}
                </span>
              </div>

              <dl class="metadata-grid">
                <div>
                  <dt>Paginas</dt>
                  <dd>{{ pageCount(document) }}</dd>
                </div>
                <div>
                  <dt>Chunks</dt>
                  <dd>{{ document.chunk_count || 0 }}</dd>
                </div>
                <div>
                  <dt>Estado</dt>
                  <dd>{{ statusLabel(document.status) }}</dd>
                </div>
                <div>
                  <dt>Fecha</dt>
                  <dd>{{ formatDate(document.created_at) }}</dd>
                </div>
              </dl>

              <button
                class="secondary-button full-width"
                type="button"
                :disabled="document.indexed || indexingId === document.document_id"
                @click.stop="indexDocument(document)"
              >
                {{
                  indexingId === document.document_id
                    ? "Indexando..."
                    : document.indexed
                      ? "Documento listo"
                      : "Indexar para consultas"
                }}
              </button>
            </article>
          </div>
        </article>

        <article id="assistant-panel" class="panel assistant-panel">
          <div class="panel-heading">
            <div>
              <p class="section-label">3 · Consulta contextual</p>
              <h2>Pregunta al documento</h2>
            </div>
            <span class="panel-badge">RAG</span>
          </div>

          <div v-if="selectedDocument" class="selected-document">
            <span>Documento seleccionado</span>
            <strong>{{ selectedDocument.file_name }}</strong>
            <small :class="selectedDocument.indexed ? 'ready-text' : 'pending-text'">
              {{
                selectedDocument.indexed
                  ? "Listo para preguntas"
                  : "Indexa el documento antes de consultar el modelo"
              }}
            </small>
          </div>
          <div v-else class="empty-state compact-empty">
            Selecciona un documento de la biblioteca.
          </div>

          <label class="question-field">
            <span>Pregunta</span>
            <textarea
              v-model="question"
              rows="4"
              maxlength="2000"
              placeholder="Ejemplo: ¿Cuales son las condiciones principales indicadas en el documento?"
            ></textarea>
          </label>

          <label class="top-k-field">
            <span>Fragmentos a recuperar</span>
            <input v-model.number="topK" type="number" min="1" max="20" />
          </label>

          <button
            class="primary-button full-width"
            type="button"
            :disabled="!canAsk"
            @click="askDocument"
          >
            {{ asking ? "Consultando modelo..." : "Obtener respuesta" }}
          </button>

          <div class="answer-box" :class="{ empty: !answer }">
            <span>Respuesta</span>
            <p>{{ answer || "La respuesta aparecera aqui cuando realices una consulta." }}</p>
          </div>

          <div class="matches-block">
            <div class="preview-heading">
              <strong>Fragmentos recuperados</strong>
              <span>{{ selectedMatches.length }}</span>
            </div>
            <div v-if="selectedMatches.length" class="matches-list">
              <article v-for="match in selectedMatches" :key="match.chunk_id" class="match-card">
                <div>
                  <span>{{ match.chunk_id }}</span>
                  <strong>Similitud {{ formatScore(match.score) }}</strong>
                </div>
                <p>{{ match.content }}</p>
              </article>
            </div>
            <p v-else class="matches-empty">Los fragmentos usados por el modelo apareceran aqui.</p>
          </div>
        </article>

        <article class="panel chunks-panel">
          <div class="panel-heading">
            <div>
              <p class="section-label">Evidencia de indexacion</p>
              <h2>Chunks generados</h2>
            </div>
            <span class="panel-badge">{{ selectedIndexedChunks.length }}</span>
          </div>

          <div v-if="selectedIndexedChunks.length" class="chunks-grid">
            <article v-for="chunk in selectedIndexedChunks" :key="chunk.chunk_id" class="chunk-card">
              <div>
                <strong>{{ chunk.chunk_id }}</strong>
                <span v-if="chunk.metadata?.page">Pagina {{ chunk.metadata.page }}</span>
              </div>
              <p>{{ chunk.content }}</p>
            </article>
          </div>
          <div v-else class="empty-state compact-empty">
            Indexa el documento seleccionado para revisar los fragmentos generados durante esta sesion.
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import LogoQuantia from "@/components/common/LogoQuantia.vue";
import { useAuthStore } from "@/stores/authStore";
import {
  listarDocumentos,
  obtenerEstadoLlmDocumental,
  preguntarDocumento,
  procesarDocumento,
  subirDocumento,
} from "@/modules/vivienda/services/documentosApiService";

const router = useRouter();
const authStore = useAuthStore();

const documents = ref([]);
const llmHealth = ref(null);
const selectedDocumentId = ref("");
const selectedFile = ref(null);
const fileInput = ref(null);
const question = ref("");
const topK = ref(4);
const answer = ref("");
const uploadResults = ref({});
const indexResults = ref({});
const askResults = ref({});
const loadingHealth = ref(false);
const loadingDocuments = ref(false);
const uploading = ref(false);
const indexingId = ref("");
const asking = ref(false);
const notice = ref({ type: "info", message: "" });
const lastError = ref(null);

const accessToken = computed(() => authStore.accessToken || "");
const userName = computed(() => authStore.user?.nombre || authStore.user?.email || "Usuario Quantia");
const selectedDocument = computed(() =>
  documents.value.find((document) => document.document_id === selectedDocumentId.value)
);
const selectedUploadResult = computed(() => uploadResults.value[selectedDocumentId.value] || null);
const selectedIndexResult = computed(() => indexResults.value[selectedDocumentId.value] || null);
const selectedAskResult = computed(() => askResults.value[selectedDocumentId.value] || null);
const selectedIndexedChunks = computed(() => selectedIndexResult.value?.chunks || []);
const selectedMatches = computed(() => selectedAskResult.value?.matches || []);

const canAsk = computed(
  () =>
    Boolean(selectedDocument.value?.indexed) &&
    Boolean(question.value.trim()) &&
    Boolean(llmHealth.value?.available) &&
    Boolean(llmHealth.value?.model_available) &&
    !asking.value &&
    !indexingId.value
);

const workflowPhases = computed(() => {
  const hasDocument = Boolean(selectedDocument.value);
  const ocrCompleted = ["ocr_completed", "indexing", "ready"].includes(
    selectedDocument.value?.status
  );
  const hasAnswer = Boolean(selectedAskResult.value?.answer);

  return [
    {
      key: "upload",
      label: "Subiendo",
      status: uploading.value ? "active" : hasDocument ? "complete" : selectedFile.value ? "ready" : "idle",
      detail: uploading.value ? "Enviando el archivo al backend" : hasDocument ? "Archivo recibido" : "Selecciona un archivo",
    },
    {
      key: "ocr",
      label: "Procesando OCR",
      status: uploading.value ? "active" : ocrCompleted ? "complete" : hasDocument ? "ready" : "idle",
      detail: uploading.value ? "Extrayendo contenido" : ocrCompleted ? "Texto extraido" : "Pendiente de carga",
    },
    {
      key: "index",
      label: "Indexando",
      status: indexingId.value ? "active" : selectedDocument.value?.indexed ? "complete" : hasDocument ? "ready" : "idle",
      detail: indexingId.value
        ? "Generando embeddings y chunks"
        : selectedDocument.value?.indexed
          ? `${selectedDocument.value.chunk_count || selectedIndexedChunks.value.length} chunks listos`
          : "Pendiente de indexacion",
    },
    {
      key: "ask",
      label: "Consultando modelo",
      status: asking.value ? "active" : hasAnswer ? "complete" : selectedDocument.value?.indexed ? "ready" : "idle",
      detail: asking.value ? "Recuperando contexto y generando respuesta" : hasAnswer ? "Respuesta disponible" : "Pendiente de pregunta",
    },
  ];
});

const retryLabel = computed(() => {
  const labels = {
    health: "Comprobar modelo",
    list: "Actualizar lista",
    upload: "Reintentar carga",
    index: "Reintentar indexacion",
    ask: "Reintentar consulta",
  };
  return labels[lastError.value?.retryAction] || "Reintentar";
});

const healthTone = computed(() => {
  if (loadingHealth.value) return "checking";
  if (llmHealth.value?.available && llmHealth.value?.model_available) return "available";
  return "unavailable";
});

const healthMessage = computed(() => {
  if (loadingHealth.value) return "Consultando disponibilidad de Ollama...";
  if (!llmHealth.value) return "No fue posible comprobar el modelo.";
  if (!llmHealth.value.available) return "Ollama no esta disponible.";
  if (!llmHealth.value.model_available) return "Ollama responde, pero falta descargar el modelo configurado.";
  return "Ollama y el modelo estan disponibles.";
});

function showNotice(message, type = "info") {
  notice.value = { message: String(message || ""), type };
  if (type !== "error") lastError.value = null;
}

function errorMessage(error) {
  return error?.message || "No se pudo completar la operacion documental.";
}

function errorSuggestion(code) {
  const suggestions = {
    document_auth_required: "Vuelve a iniciar sesion para renovar el token de acceso.",
    document_auth_invalid: "La sesion ya no es valida. Inicia sesion nuevamente.",
    document_too_large: "Selecciona un archivo mas pequeno y vuelve a intentarlo.",
    document_type_unsupported: "Usa un archivo PDF, TXT, PNG, JPG o TIFF compatible.",
    document_validation_error: "Revisa el archivo y los datos enviados antes de reintentar.",
    document_ocr_empty: "Prueba con una imagen mas nitida o un PDF que contenga texto legible.",
    document_embeddings_unavailable: "Espera unos segundos y reintenta la indexacion.",
    document_llm_unavailable: "Comprueba Ollama y descarga el modelo configurado antes de preguntar.",
    document_not_found: "Actualiza la biblioteca y selecciona un documento disponible.",
    document_network_error: "Comprueba la conexion con el backend y vuelve a intentarlo.",
    document_backend_unavailable: "El backend no esta disponible temporalmente; reintenta en unos segundos.",
  };
  if (String(code || "").endsWith("_timeout")) {
    return "La operacion puede tardar con documentos grandes. Reintenta o usa un archivo mas pequeno.";
  }
  return suggestions[code] || "Revisa el estado del servicio y vuelve a intentarlo.";
}

function showFailure(error, retryAction) {
  lastError.value = {
    code: error?.code || "document_api_error",
    retryAction,
    suggestion: errorSuggestion(error?.code),
  };
  notice.value = { message: errorMessage(error), type: "error" };
}

async function loadHealth() {
  loadingHealth.value = true;
  try {
    llmHealth.value = await obtenerEstadoLlmDocumental({ accessToken: accessToken.value });
  } catch (error) {
    llmHealth.value = null;
    showFailure(error, "health");
  } finally {
    loadingHealth.value = false;
  }
}

async function loadDocuments({ preserveNotice = false } = {}) {
  loadingDocuments.value = true;
  try {
    const response = await listarDocumentos({ accessToken: accessToken.value });
    documents.value = Array.isArray(response?.documents) ? response.documents : [];
    if (
      selectedDocumentId.value &&
      !documents.value.some((document) => document.document_id === selectedDocumentId.value)
    ) {
      selectedDocumentId.value = "";
      answer.value = "";
    }
    if (!selectedDocumentId.value && documents.value.length) {
      selectedDocumentId.value = documents.value[0].document_id;
    }
    if (!preserveNotice) showNotice("");
  } catch (error) {
    showFailure(error, "list");
  } finally {
    loadingDocuments.value = false;
  }
}

function handleFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null;
}

async function uploadDocument() {
  if (!selectedFile.value) return;
  uploading.value = true;
  answer.value = "";
  try {
    const uploaded = await subirDocumento({
      file: selectedFile.value,
      accessToken: accessToken.value,
    });
    uploadResults.value = {
      ...uploadResults.value,
      [uploaded.document_id]: uploaded,
    };
    selectedDocumentId.value = uploaded.document_id;
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = "";
    showNotice(`OCR completado para ${uploaded.file_name}.`, "success");
    await loadDocuments({ preserveNotice: true });
  } catch (error) {
    showFailure(error, "upload");
  } finally {
    uploading.value = false;
  }
}

async function indexDocument(document) {
  indexingId.value = document.document_id;
  selectedDocumentId.value = document.document_id;
  try {
    const result = await procesarDocumento({
      documentId: document.document_id,
      accessToken: accessToken.value,
    });
    indexResults.value = {
      ...indexResults.value,
      [document.document_id]: result,
    };
    showNotice(`Documento indexado en ${result.chunk_count} fragmentos.`, "success");
    await loadDocuments({ preserveNotice: true });
  } catch (error) {
    showFailure(error, "index");
  } finally {
    indexingId.value = "";
  }
}

async function askDocument() {
  if (!selectedDocumentId.value || !question.value.trim()) return;
  asking.value = true;
  answer.value = "";
  try {
    const result = await preguntarDocumento({
      documentId: selectedDocumentId.value,
      query: question.value,
      topK: Math.min(20, Math.max(1, Number(topK.value) || 4)),
      accessToken: accessToken.value,
    });
    askResults.value = {
      ...askResults.value,
      [selectedDocumentId.value]: result,
    };
    answer.value = result.answer || "El modelo no devolvio una respuesta.";
    showNotice("Consulta completada.", "success");
    await loadDocuments({ preserveNotice: true });
  } catch (error) {
    showFailure(error, "ask");
  } finally {
    asking.value = false;
  }
}

function selectDocument(documentId) {
  if (selectedDocumentId.value !== documentId) {
    answer.value = askResults.value[documentId]?.answer || "";
    showNotice("");
  }
  selectedDocumentId.value = documentId;
}

async function retryLastOperation() {
  const action = lastError.value?.retryAction;
  if (action === "health") return loadHealth();
  if (action === "list") return loadDocuments();
  if (action === "upload") return uploadDocument();
  if (action === "ask") return askDocument();
  if (action === "index") {
    const document = selectedDocument.value;
    if (document) return indexDocument(document);
  }
}

function pageCount(document) {
  return document.metadata?.page_count ?? document.metadata?.source_page_count ?? "—";
}

function documentType(document) {
  const mime = document.metadata?.mime_type || document.metadata?.content_type;
  if (mime) return mime;
  const extension = String(document.file_name || "").split(".").pop();
  return extension ? extension.toUpperCase() : "Archivo";
}

function statusLabel(status) {
  const labels = {
    uploaded: "Subido",
    ocr_processing: "Procesando OCR",
    ocr_completed: "OCR completado",
    indexing: "Indexando",
    ready: "Listo",
    failed: "Con error",
  };
  return labels[status] || "Sin estado";
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium" }).format(date);
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? score.toFixed(3) : "—";
}

function goDashboard() {
  router.push("/vivienda/dashboard");
}

onMounted(() => {
  loadHealth();
  loadDocuments({ preserveNotice: true });
});
</script>

<style scoped>
.documents-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  padding: 32px;
  color: #f8f7ff;
  background:
    radial-gradient(circle at 12% 18%, rgba(63, 211, 255, 0.2), transparent 22%),
    radial-gradient(circle at 88% 14%, rgba(175, 92, 255, 0.22), transparent 24%),
    linear-gradient(135deg, #131b66 0%, #2b1d83 40%, #5528ad 72%, #743fca 100%);
}

.background-orb {
  position: absolute;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  filter: blur(70px);
  pointer-events: none;
}

.orb-left {
  left: -120px;
  bottom: 10%;
  background: rgba(56, 218, 255, 0.14);
}

.orb-right {
  top: 20%;
  right: -130px;
  background: rgba(213, 108, 255, 0.14);
}

.documents-shell {
  position: relative;
  z-index: 1;
  width: min(1420px, 100%);
  margin: 0 auto;
}

.topbar,
.hero-card,
.panel {
  border: 1px solid rgba(255, 255, 255, 0.13);
  background: rgba(255, 255, 255, 0.09);
  box-shadow: 0 24px 70px rgba(12, 14, 61, 0.24);
  backdrop-filter: blur(18px);
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 16px 22px;
  border-radius: 22px;
}

.topnav {
  display: flex;
  gap: 26px;
}

.topnav a {
  color: rgba(255, 255, 255, 0.86);
  text-decoration: none;
  font-weight: 700;
}

.topnav a:hover {
  color: #8fe8ff;
}

.user-pill {
  min-width: 170px;
  padding: 10px 14px;
  text-align: right;
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.09);
}

.user-pill span,
.user-pill strong {
  display: block;
}

.user-pill span {
  margin-bottom: 3px;
  color: rgba(255, 255, 255, 0.62);
  font-size: 0.76rem;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.65fr);
  gap: 30px;
  align-items: center;
  margin-top: 24px;
  padding: 34px;
  border-radius: 28px;
}

.eyebrow,
.section-label {
  margin: 0 0 8px;
  color: #8fe8ff;
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.hero-card h1 {
  max-width: 800px;
  margin: 0;
  font-size: clamp(2rem, 4vw, 3.45rem);
  line-height: 1.05;
}

.hero-copy {
  max-width: 820px;
  margin: 18px 0 0;
  color: rgba(247, 246, 255, 0.8);
  font-size: 1.03rem;
  line-height: 1.65;
}

.health-panel {
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.11);
  border-radius: 20px;
  background: rgba(10, 18, 69, 0.35);
}

.health-panel.available .status-dot {
  background: #4ade80;
  box-shadow: 0 0 18px rgba(74, 222, 128, 0.75);
}

.health-panel.unavailable .status-dot {
  background: #fb7185;
}

.health-panel.checking .status-dot {
  background: #facc15;
}

.health-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.health-panel p {
  margin: 13px 0 7px;
  line-height: 1.45;
}

.health-panel small {
  display: block;
  color: rgba(255, 255, 255, 0.64);
}

.text-button {
  margin-top: 14px;
  padding: 0;
  border: 0;
  color: #91ebff;
  background: transparent;
  font-weight: 800;
  cursor: pointer;
}

.notice {
  margin: 18px 0 0;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border: 1px solid transparent;
  border-radius: 15px;
}

.notice strong,
.notice span {
  display: block;
}

.notice span {
  margin-top: 5px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.88rem;
}

.notice-action {
  flex: 0 0 auto;
  padding: 9px 13px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 11px;
  color: white;
  background: rgba(255, 255, 255, 0.1);
  font-weight: 800;
  cursor: pointer;
}

.notice-success {
  border-color: rgba(74, 222, 128, 0.35);
  background: rgba(22, 163, 74, 0.2);
}

.notice-error {
  border-color: rgba(251, 113, 133, 0.38);
  background: rgba(190, 24, 93, 0.2);
}

.workflow-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.workflow-phase {
  min-width: 0;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 11px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  background: rgba(10, 17, 67, 0.28);
}

.workflow-phase strong,
.workflow-phase small {
  display: block;
}

.workflow-phase small {
  margin-top: 3px;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.73rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.phase-number {
  flex: 0 0 auto;
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.62);
  background: rgba(255, 255, 255, 0.09);
  font-weight: 900;
}

.workflow-phase.ready {
  border-color: rgba(250, 204, 21, 0.28);
}

.workflow-phase.active {
  border-color: rgba(143, 232, 255, 0.65);
  background: rgba(48, 128, 224, 0.22);
}

.workflow-phase.active .phase-number {
  color: #14206e;
  background: #8fe8ff;
}

.workflow-phase.complete {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(22, 163, 74, 0.13);
}

.workflow-phase.complete .phase-number {
  color: #123f2a;
  background: #86efac;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.75fr) minmax(390px, 1.35fr) minmax(310px, 0.9fr);
  gap: 20px;
  margin-top: 20px;
  align-items: start;
}

.panel {
  padding: 24px;
  border-radius: 24px;
}

.panel-heading,
.document-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.panel h2 {
  margin: 0;
  font-size: 1.45rem;
}

.panel-badge,
.index-status {
  padding: 7px 10px;
  border-radius: 999px;
  color: #a8efff;
  background: rgba(62, 203, 255, 0.12);
  font-size: 0.75rem;
  font-weight: 800;
}

.file-drop {
  min-height: 190px;
  margin: 22px 0 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  text-align: center;
  border: 1px dashed rgba(143, 232, 255, 0.5);
  border-radius: 19px;
  background: rgba(23, 30, 102, 0.35);
  cursor: pointer;
}

.file-drop.selected {
  border-style: solid;
  background: rgba(55, 48, 145, 0.44);
}

.file-drop input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
}

.file-drop small {
  color: rgba(255, 255, 255, 0.62);
  line-height: 1.45;
}

.file-icon {
  display: grid;
  width: 50px;
  height: 58px;
  place-items: center;
  border-radius: 10px;
  color: #15206e;
  background: linear-gradient(145deg, #a6f0ff, #cfb8ff);
  font-size: 0.72rem;
  font-weight: 900;
}

.ocr-preview,
.matches-block {
  margin-top: 17px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  background: rgba(8, 15, 59, 0.32);
}

.preview-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-heading span {
  color: #8fe8ff;
  font-size: 0.75rem;
  font-weight: 800;
}

.ocr-preview p {
  max-height: 190px;
  margin: 11px 0 0;
  overflow: auto;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.86rem;
  line-height: 1.55;
  white-space: pre-wrap;
}

.ocr-preview.empty p {
  color: rgba(255, 255, 255, 0.5);
}

.primary-button,
.secondary-button {
  min-height: 44px;
  padding: 11px 17px;
  border: 0;
  border-radius: 13px;
  color: white;
  font-weight: 800;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(135deg, #27bce9, #6a4df4 58%, #a855f7);
  box-shadow: 0 13px 28px rgba(48, 81, 229, 0.28);
}

.secondary-button {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.1);
}

.primary-button:disabled,
.secondary-button:disabled,
.text-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.full-width {
  width: 100%;
}

.compact {
  min-height: 38px;
  padding: 8px 12px;
}

.document-list {
  max-height: 660px;
  margin-top: 18px;
  padding-right: 4px;
  display: grid;
  gap: 13px;
  overflow: auto;
}

.document-card {
  padding: 17px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 17px;
  background: rgba(18, 25, 88, 0.32);
  cursor: pointer;
}

.document-card.active {
  border-color: rgba(143, 232, 255, 0.64);
  background: rgba(54, 47, 145, 0.48);
}

.document-title-row strong,
.document-title-row span {
  display: block;
}

.document-title-row strong {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-title-row div > span {
  margin-top: 5px;
  color: rgba(255, 255, 255, 0.58);
  font-size: 0.78rem;
}

.index-status.ready {
  color: #86efac;
  background: rgba(22, 163, 74, 0.18);
}

.index-status.pending {
  color: #fde68a;
  background: rgba(202, 138, 4, 0.18);
}

.metadata-grid {
  margin: 16px 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}

.metadata-grid div {
  min-width: 0;
  padding: 9px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.06);
}

.metadata-grid dt {
  color: rgba(255, 255, 255, 0.55);
  font-size: 0.67rem;
}

.metadata-grid dd {
  margin: 4px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.8rem;
  font-weight: 800;
  white-space: nowrap;
}

.empty-state {
  min-height: 180px;
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  text-align: center;
  color: rgba(255, 255, 255, 0.62);
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 16px;
}

.compact-empty {
  min-height: 80px;
}

.selected-document {
  margin: 20px 0;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.07);
}

.selected-document span,
.selected-document strong {
  display: block;
}

.selected-document span {
  margin-bottom: 5px;
  color: rgba(255, 255, 255, 0.57);
  font-size: 0.76rem;
}

.selected-document small {
  display: block;
  margin-top: 8px;
  font-weight: 700;
}

.ready-text {
  color: #86efac;
}

.pending-text {
  color: #fde68a;
}

.question-field {
  display: grid;
  gap: 8px;
  margin: 18px 0 14px;
  font-weight: 800;
}

.question-field textarea {
  width: 100%;
  resize: vertical;
  padding: 13px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 14px;
  outline: none;
  color: white;
  background: rgba(12, 18, 70, 0.42);
  font: inherit;
  line-height: 1.5;
}

.question-field textarea:focus {
  border-color: #8fe8ff;
}

.top-k-field {
  margin: 0 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.86rem;
  font-weight: 700;
}

.top-k-field input {
  width: 72px;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  color: white;
  background: rgba(12, 18, 70, 0.42);
  font: inherit;
}

.answer-box {
  min-height: 160px;
  margin-top: 17px;
  padding: 17px;
  border-radius: 16px;
  background: rgba(8, 15, 59, 0.4);
}

.answer-box > span {
  color: #8fe8ff;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

.answer-box p {
  margin: 11px 0 0;
  white-space: pre-wrap;
  line-height: 1.65;
}

.answer-box.empty p {
  color: rgba(255, 255, 255, 0.52);
}

.matches-list {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.match-card,
.chunk-card {
  padding: 13px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.055);
}

.match-card > div,
.chunk-card > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.match-card span,
.chunk-card span {
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.72rem;
}

.match-card strong {
  color: #8fe8ff;
  font-size: 0.75rem;
}

.match-card p,
.chunk-card p,
.matches-empty {
  margin: 9px 0 0;
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.82rem;
  line-height: 1.5;
}

.matches-empty {
  color: rgba(255, 255, 255, 0.5);
}

.chunks-panel {
  grid-column: 1 / -1;
}

.chunks-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 13px;
}

.chunk-card p {
  max-height: 130px;
  overflow: auto;
  white-space: pre-wrap;
}

@media (max-width: 1120px) {
  .workspace-grid {
    grid-template-columns: 1fr 1fr;
  }

  .assistant-panel {
    grid-column: 1 / -1;
  }

  .workflow-strip,
  .chunks-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .documents-page {
    padding: 16px;
  }

  .topbar,
  .hero-card,
  .workspace-grid {
    display: flex;
    flex-direction: column;
  }

  .workflow-strip,
  .chunks-grid {
    grid-template-columns: 1fr;
  }

  .notice {
    align-items: stretch;
    flex-direction: column;
  }

  .topbar {
    align-items: stretch;
  }

  .topnav {
    justify-content: center;
    gap: 16px;
  }

  .user-pill {
    text-align: center;
  }

  .hero-card,
  .panel {
    padding: 21px;
  }

  .metadata-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
