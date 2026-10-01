import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const viewSource = await readFile(
  new URL("../src/modules/vivienda/views/DocumentosView.vue", import.meta.url),
  "utf8"
);
const routerSource = await readFile(
  new URL("../src/modules/vivienda/router/index.js", import.meta.url),
  "utf8"
);
const workflowLayoutSource = await readFile(
  new URL(
    "../src/modules/vivienda/views/QuantiaWorkflowLayout.vue",
    import.meta.url
  ),
  "utf8"
);

test("registra la ruta documental como vista protegida", () => {
  assert.match(
    routerSource,
    /const DocumentosView\s*=\s*\(\)\s*=>\s*import\(["']@\/modules\/vivienda\/views\/DocumentosView\.vue["']\)/s,
  );
  assert.match(routerSource, /path:\s*["']\/vivienda\/documentos["']/);
  assert.match(routerSource, /name:\s*["']vivienda-documentos["']/);
  assert.match(routerSource, /component:\s*DocumentosView/);
  assert.match(routerSource, /requiresAuth:\s*true/);
});

test("incluye las operaciones basicas de la tarea 7.3", () => {
  for (const operation of [
    "obtenerEstadoLlmDocumental",
    "listarDocumentos",
    "subirDocumento",
    "procesarDocumento",
    "preguntarDocumento",
  ]) {
    assert.match(viewSource, new RegExp(`\\b${operation}\\b`));
  }

  assert.match(viewSource, /Subir documento/);
  assert.match(viewSource, /Documentos procesados/);
  assert.match(viewSource, /Indexar para consultas/);
  assert.match(viewSource, /Pregunta al documento/);
});

test("muestra metadata OCR sin depender del estado de cotizacion", () => {
  assert.match(viewSource, /file_name/);
  assert.match(viewSource, /page_count/);
  assert.match(viewSource, /chunk_count/);
  assert.match(viewSource, /document\.indexed/);
  assert.doesNotMatch(viewSource, /useViviendaStore/);
  assert.doesNotMatch(viewSource, /resultadoFinal/);
});

test("mantiene separados el gestor documental y el flujo de planos", () => {
  assert.doesNotMatch(routerSource, /requiresFlow:[^}]*documentos/s);
  assert.match(workflowLayoutSource, /Documentos e IA/);
  assert.match(
    workflowLayoutSource,
    /go\(["']\/vivienda\/workflow\/planos-revision\/carga["']\)/
  );
  assert.match(
    routerSource,
    /path:\s*["']\/vivienda\/workflow\/planos-revision\/analisis["']/
  );
});

test("presenta el flujo completo con evidencia y recuperacion de errores", () => {
  for (const phase of ["Subiendo", "Procesando OCR", "Indexando", "Consultando modelo"]) {
    assert.match(viewSource, new RegExp(phase));
  }

  assert.match(viewSource, /selectedUploadResult\?\.text/);
  assert.match(viewSource, /selectedIndexedChunks/);
  assert.match(viewSource, /selectedMatches/);
  assert.match(viewSource, /Fragmentos recuperados/);
  assert.match(viewSource, /errorSuggestion/);
  assert.match(viewSource, /retryLastOperation/);
});
