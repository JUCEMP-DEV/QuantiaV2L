import test from 'node:test';
import assert from 'node:assert/strict';
import { receiveSpatialAnalysis, buildQuantityHandoff } from '../src/modules/vivienda/editor/adapters/spatialWorkflowContract.js';

test('03 review maps levels, preserves evidence and does not use a full page for a local crop', () => {
  const input = { schemaVersion: 'SPATIAL_INTERFACE04_REVIEW_V1',
    niveles: [{ id: 'LV1', key: 'planta_alta' }],
    muros: [{ id: 'W1', levelId: 'LV1', start: { x: 1, y: 2 } }],
    planoBase: { referencia: 'original.png' },
    source: { documentId: 'DOC', pageNumber: 2 },
    buckets: { EXCLUDED_GRAPHIC: [{ id: 'E1' }] },
  };
  const result = receiveSpatialAnalysis(input);
  assert.equal(result.muros[0].nivel, 'planta_alta');
  assert.equal(result.metadata.sourcePageNumber, 2);
  assert.equal(result.planoBase.referencia, null);
  assert.equal(result.metadata.requiresLocalRasterUrl, true);
  assert.deepEqual(result.buckets, input.buckets);
  assert.equal(input.muros[0].nivel, undefined);
  assert.equal(receiveSpatialAnalysis(result).metadata.sourceRasterAsset, 'original.png');
});

test('legacy 03 contract survives unchanged and independently', () => {
  const input = { espacios: [{ id: 'S1', areaM2: null }], metadata: { sourcePageNumber: 3 } };
  const result = receiveSpatialAnalysis(input);
  assert.deepEqual(result, input);
  result.espacios[0].areaM2 = 10;
  assert.equal(input.espacios[0].areaM2, null);
});

test('05 draft distinguishes unknown openings from confirmed absence', () => {
  const source = { revision: 'r1', puertas: [], ventanas: [], quantityHandoff: { old: true },
    call2Candidates: [{ family_hint: 'DOOR' }] };
  const draft = buildQuantityHandoff(source);
  assert.equal(draft.data.puertas, null);
  assert.equal(draft.data.ventanas, null);
  assert.equal(draft.readyForCalculation, false);
  assert.equal(draft.sourceRevision, 'r1');
  assert.equal(draft.reviewSource.quantityHandoff, undefined);
  assert.deepEqual(draft.reviewSource.call2Candidates, source.call2Candidates);
  const confirmed = buildQuantityHandoff({ ...source, completeness: { openings: 'CONFIRMED' } });
  assert.deepEqual(confirmed.data.puertas, []);
  assert.equal(confirmed.status, 'DRAFT');
});

test('05 template reflects current edits and keeps missing metrics', () => {
  const source = { espacios: [{ id: 'S1', confirmed: true, areaM2: null }],
    muros: [{ id: 'W1', confirmed: false, heightM: null, thicknessM: .15 }],
    engineInputsByConcept: { A: { measure: null } } };
  const draft = buildQuantityHandoff(source);
  assert.ok(draft.missing.some((text) => text.includes('área')));
  assert.ok(draft.missing.some((text) => text.includes('altura')));
  assert.equal(draft.data.muros[0].heightM, null);
  assert.deepEqual(draft.data.engineInputsByConcept, source.engineInputsByConcept);
});
