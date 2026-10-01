import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const editorSource = await readFile(
  new URL("../src/components/design/QuantiaPlanEditor.vue", import.meta.url),
  "utf8",
);
const viewSource = await readFile(
  new URL(
    "../src/modules/vivienda/views/workflow/04DisenoViviendaView.vue",
    import.meta.url,
  ),
  "utf8",
);

test("modo plan consume muros y cotas canónicas raster", () => {
  assert.match(editorSource, /segment\?\.geometria\s*\?\.raster\s*\?\.vertices/s);
  assert.match(editorSource, /const renderedDimensions\s*=\s*computed/);
  assert.match(editorSource, /dimensionMatchesActiveLevel/);
  assert.match(editorSource, /layerVisible\(['"]cotas['"]\)/);
});

test("filtra espacios y muros con la misma clave de nivel", () => {
  assert.match(editorSource, /spaceMatchesActiveLevel\(space\.raw\)/);
  assert.match(editorSource, /wallMatchesActiveLevel\(wall\)/);
  assert.match(editorSource, /resolvedActiveLevelKey\.value/);
});

test("04 conserva null métrico y muestra Sin determinar", () => {
  assert.match(viewSource, /const totalAreaM2\s*=\s*computed\(\(\)\s*=>\s*sumKnownAreas/s);
  assert.match(viewSource, /parsed === null\s*\?\s*["']Sin determinar["']/s);
  assert.doesNotMatch(viewSource, /<strong>\{\{ totalAreaM2 \}\} m²<\/strong>/);
});

test("04 carga el raster canónico autenticado y expone controles", () => {
  assert.match(viewSource, /obtenerPlanoBaseDocumento/);
  assert.match(viewSource, /:base-layer-url="baseLayerObjectUrl"/);
  assert.match(viewSource, />\s*║ Muros\s*</);
  assert.match(viewSource, />\s*↔ Cotas\s*</);
});
