import assert from "node:assert/strict";
import { File } from "node:buffer";
import { readFile } from "node:fs/promises";

import {
  eliminarDocumento,
  listarDocumentos,
  obtenerEstadoLlmDocumental,
  preguntarDocumento,
  procesarDocumento,
  subirDocumento,
} from "../src/modules/vivienda/services/documentosApiService.js";


const accessToken = String(process.env.DOCUMENT_TEST_TOKEN || "").trim();
if (!accessToken) throw new Error("DOCUMENT_TEST_TOKEN es obligatorio para la prueba de integracion.");

const source = await readFile(new URL("../../Backend/tests/fixtures/rag_real/documento_rag_control.txt", import.meta.url));
const file = new File([source], "integracion-rag.txt", {
  type: "text/plain",
});

const health = await obtenerEstadoLlmDocumental({ accessToken, timeoutMs: 10000 });
assert.equal(health.available, true);
assert.equal(health.model_available, true);

let documentId = "";
try {
  const uploaded = await subirDocumento({ file, accessToken, timeoutMs: 120000 });
  assert.equal(uploaded.status, "ocr_completed");
  assert.ok(uploaded.document_id);
  assert.match(uploaded.text, /\$250,000\.00 MXN/);
  documentId = uploaded.document_id;

  const indexed = await procesarDocumento({
    documentId,
    accessToken,
    timeoutMs: 180000,
  });
  assert.equal(indexed.document_id, documentId);
  assert.ok(indexed.chunk_count >= 3);

  const asked = await preguntarDocumento({
    documentId,
    query: "¿Cuál es el presupuesto exclusivo de cimentación?",
    topK: 3,
    accessToken,
    timeoutMs: 120000,
  });
  assert.equal(asked.document_id, documentId);
  assert.match(asked.answer, /250,000\.00 MXN/);
  assert.ok(asked.matches.length > 0);
  assert.ok(asked.matches.some((match) => asked.answer.includes(`[${match.chunk_id}]`)));

  const listed = await listarDocumentos({ accessToken, timeoutMs: 10000 });
  const listedDocument = listed.documents.find((item) => item.document_id === documentId);
  assert.ok(listedDocument);
  assert.equal(listedDocument.status, "ready");
  assert.equal(listedDocument.chunk_count, indexed.chunk_count);

  console.log(
    JSON.stringify({
      document_id: documentId,
      chunk_count: indexed.chunk_count,
      answer: asked.answer,
      matches: asked.matches.length,
    })
  );
} finally {
  if (documentId) {
    const deleted = await eliminarDocumento({
      documentId,
      accessToken,
      timeoutMs: 30000,
    });
    assert.equal(deleted.document_id, documentId);
    const listedAfterDelete = await listarDocumentos({ accessToken, timeoutMs: 10000 });
    assert.ok(!listedAfterDelete.documents.some((item) => item.document_id === documentId));
  }
}

console.log(`Integracion documental local completa: ${documentId}`);
