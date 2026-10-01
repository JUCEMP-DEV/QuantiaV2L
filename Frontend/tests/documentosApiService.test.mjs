import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import {
  DocumentApiError,
  listarDocumentos,
  obtenerPlanoBaseDocumento,
  preguntarDocumento,
  subirDocumento,
} from "../src/modules/vivienda/services/documentosApiService.js";


const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("rechaza peticiones sin token", async () => {
  await assert.rejects(
    listarDocumentos(),
    (error) => error instanceof DocumentApiError && error.code === "document_auth_required"
  );
});

test("lista documentos con Bearer y URL local", async () => {
  let capturedUrl = "";
  let capturedOptions = null;
  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return new Response(JSON.stringify({ documents: [] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const result = await listarDocumentos({ accessToken: "token-prueba" });

  assert.deepEqual(result, { documents: [] });
  assert.equal(capturedUrl, "http://127.0.0.1:8000/api/documentos");
  assert.equal(capturedOptions.headers.Authorization, "Bearer token-prueba");
});

test("sube multipart sin fijar Content-Type manualmente", async () => {
  let capturedOptions = null;
  globalThis.fetch = async (_url, options) => {
    capturedOptions = options;
    return new Response(JSON.stringify({ document_id: "doc-1", status: "ocr_completed" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  const file = new Blob(["contenido"], { type: "text/plain" });

  await subirDocumento({
    file,
    accessToken: "token-prueba",
    quoteId: "11111111-1111-1111-1111-111111111111",
    moduleKey: "preliminares",
  });

  assert.equal(capturedOptions.method, "POST");
  assert.ok(capturedOptions.body instanceof FormData);
  assert.equal(capturedOptions.headers["Content-Type"], undefined);
  assert.equal(capturedOptions.body.get("module_key"), "preliminares");
});

test("descarga el raster canónico con autenticación y escala", async () => {
  let capturedUrl = "";
  let capturedOptions = null;
  const expected = new Blob(["png"], { type: "image/png" });
  globalThis.fetch = async (url, options) => {
    capturedUrl = url;
    capturedOptions = options;
    return new Response(expected, {
      status: 200,
      headers: { "Content-Type": "image/png" },
    });
  };

  const result = await obtenerPlanoBaseDocumento({
    documentId: "doc 1",
    accessToken: "token-prueba",
    pageNumber: 2,
    pdfRenderScale: 0.7935,
  });

  assert.ok(result instanceof Blob);
  assert.equal(result.type, "image/png");
  assert.match(capturedUrl, /doc%201\/plano-base\?/);
  assert.match(capturedUrl, /page_number=2/);
  assert.match(capturedUrl, /pdf_render_scale=0.7935/);
  assert.equal(capturedOptions.headers.Authorization, "Bearer token-prueba");
});

test("clasifica indisponibilidad de Ollama", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Ollama no responde y el modelo no esta disponible" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    preguntarDocumento({
      documentId: "doc-1",
      query: "Que contiene?",
      accessToken: "token-prueba",
    }),
    (error) =>
      error instanceof DocumentApiError &&
      error.code === "document_llm_unavailable" &&
      error.status === 503
  );
});

test("clasifica OCR sin texto utilizable", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "El OCR no produjo chunks ni texto utilizable" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    subirDocumento({ file: new Blob(["imagen"]), accessToken: "token-prueba" }),
    (error) => error instanceof DocumentApiError && error.code === "document_ocr_empty"
  );
});

test("clasifica embeddings no disponibles", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "El servicio de embeddings no esta disponible" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    preguntarDocumento({
      documentId: "doc-1",
      query: "consulta",
      accessToken: "token-prueba",
    }),
    (error) => error instanceof DocumentApiError && error.code === "document_embeddings_unavailable"
  );
});

test("clasifica documento inexistente", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Documento no encontrado" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    preguntarDocumento({
      documentId: "doc-inexistente",
      query: "consulta",
      accessToken: "token-prueba",
    }),
    (error) => error instanceof DocumentApiError && error.code === "document_not_found"
  );
});

test("distingue timeout de cancelacion externa", async () => {
  globalThis.fetch = (_url, options) =>
    new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    });

  await assert.rejects(
    listarDocumentos({ accessToken: "token-prueba", timeoutMs: 5 }),
    (error) => error instanceof DocumentApiError && error.code === "document_list_timeout"
  );
});

test("envia pregunta y top_k como JSON", async () => {
  let capturedOptions = null;
  globalThis.fetch = async (_url, options) => {
    capturedOptions = options;
    return new Response(JSON.stringify({ answer: "respuesta" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  await preguntarDocumento({
    documentId: "doc 1",
    query: "  pregunta  ",
    topK: 4,
    accessToken: "token-prueba",
  });

  assert.equal(capturedOptions.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(capturedOptions.body), { query: "pregunta", top_k: 4 });
});
