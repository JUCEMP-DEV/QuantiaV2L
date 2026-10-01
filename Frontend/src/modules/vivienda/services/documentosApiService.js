import { buildApiUrl } from "../../../config/apiBaseUrl.js";

export const DOCUMENT_REQUEST_TIMEOUTS = Object.freeze({
  health: 10000,
  list: 15000,
  upload: 120000,
  process: 180000,
  spatial: 180000,
  basePlan: 60000,
  ask: 120000,
  remove: 30000,
  query: 120000,
});

export class DocumentApiError extends Error {
  constructor(message, { code, status = 0, detail = null, retryable = false, cause = null } = {}) {
    super(message);
    this.name = "DocumentApiError";
    this.code = code || "document_api_error";
    this.status = Number(status || 0);
    this.detail = detail;
    this.retryable = Boolean(retryable);
    if (cause) this.cause = cause;
  }
}

function requireAccessToken(accessToken) {
  const token = String(accessToken || "").trim();
  if (!token) {
    throw new DocumentApiError("Inicia sesión nuevamente para usar el módulo documental.", {
      code: "document_auth_required",
      status: 401,
    });
  }
  return token;
}

function requireDocumentId(documentId) {
  const normalized = String(documentId || "").trim();
  if (!normalized) {
    throw new DocumentApiError("document_id es obligatorio.", {
      code: "document_id_required",
      status: 422,
    });
  }
  return encodeURIComponent(normalized);
}

function classifyBackendError(status, detail, operation) {
  const normalized = String(detail || "").toLowerCase();
  if (status === 401 || status === 403) return "document_auth_invalid";
  if (status === 404) return "document_not_found";
  if (status === 413) return "document_too_large";
  if (status === 415) return "document_type_unsupported";
  if (normalized.includes("embedding")) return "document_embeddings_unavailable";
  if (
    normalized.includes("ollama") ||
    normalized.includes("modelo") ||
    normalized.includes("llama")
  ) {
    return "document_llm_unavailable";
  }
  if (
    normalized.includes("ocr") ||
    normalized.includes("no produjo chunks") ||
    normalized.includes("texto vacio") ||
    normalized.includes("texto vacío")
  ) {
    return "document_ocr_empty";
  }
  if (status === 422) return "document_validation_error";
  if (status >= 500) return "document_backend_unavailable";
  return `document_${operation}_failed`;
}

function defaultMessage(code) {
  const messages = {
    document_auth_invalid: "La sesión expiró o no tiene acceso al documento.",
    document_not_found: "El documento no existe o pertenece a otro usuario.",
    document_too_large: "El archivo supera el tamaño máximo permitido.",
    document_type_unsupported: "El tipo de archivo no está permitido.",
    document_embeddings_unavailable: "No fue posible generar o consultar los embeddings.",
    document_llm_unavailable: "Ollama o el modelo configurado no están disponibles.",
    document_ocr_empty: "El OCR no produjo texto utilizable para indexar.",
    document_validation_error: "Los datos del documento no son válidos.",
    document_backend_unavailable: "El servicio documental no está disponible temporalmente.",
  };
  return messages[code] || "No se pudo completar la operación documental.";
}

async function parseResponsePayload(response) {
  const raw = await response.text().catch(() => "");
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

async function documentRequest(
  path,
  {
    accessToken,
    operation,
    method = "GET",
    body,
    headers = {},
    timeoutMs,
    signal,
    responseType = "json",
  } = {}
) {
  const token = requireAccessToken(accessToken);
  const controller = new AbortController();
  const effectiveTimeout = Number(timeoutMs || DOCUMENT_REQUEST_TIMEOUTS[operation] || 30000);
  let callerAborted = false;
  const abortFromCaller = () => {
    callerAborted = true;
    controller.abort();
  };
  if (signal?.aborted) abortFromCaller();
  else signal?.addEventListener?.("abort", abortFromCaller, { once: true });
  const timeout = setTimeout(() => controller.abort(), effectiveTimeout);

  try {
    const response = await fetch(buildApiUrl(path), {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...headers,
      },
      body,
      signal: controller.signal,
    });
    const payload =
      response.ok && responseType === "blob"
        ? await response.blob()
        : await parseResponsePayload(response);
    if (!response.ok) {
      const detail = payload?.detail || payload?.message || "";
      const code = classifyBackendError(response.status, detail, operation);
      throw new DocumentApiError(String(detail || defaultMessage(code)), {
        code,
        status: response.status,
        detail: payload,
        retryable: response.status >= 500,
      });
    }
    return payload;
  } catch (error) {
    if (error instanceof DocumentApiError) throw error;
    if (error?.name === "AbortError") {
      const code = callerAborted ? "document_request_cancelled" : `document_${operation}_timeout`;
      throw new DocumentApiError(
        callerAborted
          ? "La operación documental fue cancelada."
          : "El servicio documental tardó más de lo esperado.",
        { code, retryable: !callerAborted, cause: error }
      );
    }
    throw new DocumentApiError("No fue posible conectar con el backend documental.", {
      code: "document_network_error",
      retryable: true,
      cause: error,
    });
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener?.("abort", abortFromCaller);
  }
}

export function obtenerEstadoLlmDocumental({ accessToken, timeoutMs, signal } = {}) {
  return documentRequest("/api/documentos/llm/health", {
    accessToken,
    operation: "health",
    timeoutMs,
    signal,
  });
}

export function listarDocumentos({ accessToken, timeoutMs, signal } = {}) {
  return documentRequest("/api/documentos", {
    accessToken,
    operation: "list",
    timeoutMs,
    signal,
  });
}

export function subirDocumento({
  file,
  accessToken,
  quoteId = null,
  moduleKey = null,
  timeoutMs,
  signal,
} = {}) {
  const isFileLike = typeof Blob !== "undefined" && file instanceof Blob;
  if (!isFileLike) {
    throw new DocumentApiError("Selecciona un archivo para procesar.", {
      code: "document_file_required",
      status: 422,
    });
  }
  const form = new FormData();
  form.append("file", file);
  if (quoteId) form.append("quote_id", String(quoteId));
  if (moduleKey) form.append("module_key", String(moduleKey));
  return documentRequest("/api/documentos/upload", {
    accessToken,
    operation: "upload",
    method: "POST",
    body: form,
    timeoutMs,
    signal,
  });
}

export function procesarDocumento({ documentId, accessToken, timeoutMs, signal } = {}) {
  const encodedId = requireDocumentId(documentId);
  return documentRequest(`/api/documentos/${encodedId}/procesar`, {
    accessToken,
    operation: "process",
    method: "POST",
    timeoutMs,
    signal,
  });
}
export function analizarPlanoDocumento({
  documentId,
  accessToken,
  pageNumber = 1,
  pdfRenderScale = null,
  ocrStrategy = "auto",
  timeoutMs,
  signal,
} = {}) {
  const encodedId = requireDocumentId(documentId);

  const params = new URLSearchParams();

  params.set(
    "page_number",
    String(pageNumber)
  );

  if (
    pdfRenderScale !== null &&
    pdfRenderScale !== undefined
  ) {
    params.set(
      "pdf_render_scale",
      String(pdfRenderScale)
    );
  }

  params.set(
    "ocr_strategy",
    String(ocrStrategy || "auto")
  );

  return documentRequest(
    `/api/documentos/${encodedId}/analizar-plano?${params.toString()}`,
    {
      accessToken,
      operation: "spatial",
      method: "POST",
      timeoutMs,
      signal,
    }
  );
}

export function obtenerPlanoBaseDocumento({
  documentId,
  accessToken,
  pageNumber = 1,
  pdfRenderScale = null,
  timeoutMs,
  signal,
} = {}) {
  const encodedId = requireDocumentId(documentId);
  const params = new URLSearchParams();
  params.set("page_number", String(pageNumber));

  if (pdfRenderScale !== null && pdfRenderScale !== undefined) {
    params.set("pdf_render_scale", String(pdfRenderScale));
  }

  return documentRequest(
    `/api/documentos/${encodedId}/plano-base?${params.toString()}`,
    {
      accessToken,
      operation: "basePlan",
      timeoutMs,
      signal,
      responseType: "blob",
    }
  );
}
export function preguntarDocumento({
  documentId,
  query,
  topK = null,
  accessToken,
  timeoutMs,
  signal,
} = {}) {
  const encodedId = requireDocumentId(documentId);
  const normalizedQuery = String(query || "").trim();
  if (!normalizedQuery) {
    throw new DocumentApiError("Escribe una pregunta para consultar el documento.", {
      code: "document_query_required",
      status: 422,
    });
  }
  const payload = { query: normalizedQuery };
  if (topK !== null && topK !== undefined && topK !== "") payload.top_k = Number(topK);
  return documentRequest(`/api/documentos/${encodedId}/preguntar`, {
    accessToken,
    operation: "ask",
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeoutMs,
    signal,
  });
}

export function eliminarDocumento({ documentId, accessToken, timeoutMs, signal } = {}) {
  const encodedId = requireDocumentId(documentId);
  return documentRequest(`/api/documentos/${encodedId}`, {
    accessToken,
    operation: "remove",
    method: "DELETE",
    timeoutMs,
    signal,
  });
}

export function consultarTextoDocumental({ text, query, accessToken, timeoutMs, signal } = {}) {
  const normalizedText = String(text || "").trim();
  const normalizedQuery = String(query || "").trim();
  if (!normalizedText || !normalizedQuery) {
    throw new DocumentApiError("El texto y la pregunta son obligatorios.", {
      code: "document_query_required",
      status: 422,
    });
  }
  return documentRequest("/api/documentos/query", {
    accessToken,
    operation: "query",
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: normalizedText, query: normalizedQuery }),
    timeoutMs,
    signal,
  });
}
