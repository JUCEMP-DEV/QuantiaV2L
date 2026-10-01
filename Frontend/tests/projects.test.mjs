import test from 'node:test';
import assert from 'node:assert/strict';
import { projectSnapshot, restoreProject, projectsRequest } from '../src/modules/vivienda/services/projectsApiService.js';
test('snapshot preserves state without session identifiers or cached catalogs', () => {
 const state = { registro: { nombre:'Casa' }, estructuraEspacial: { revision:'r1' }, projectPersistence:{id:'old'}, reglasSnapshot:{} };
 const snapshot = projectSnapshot(state);
 assert.equal(snapshot.state.projectPersistence, undefined);
 assert.equal(snapshot.state.estructuraEspacial.revision, 'r1');
 assert.equal(state.projectPersistence.id, 'old');
});
test('legacy records do not overwrite the current session', () => {
 assert.throws(() => restoreProject({ $reset(){throw new Error('must not reset');} }, {payload_json:{}}), /formato anterior/);
});
test('restore only recognized state keys and resets previous data', () => {
 let reset = false, patch;
 const store = { $state:{registro:{},resultado:{},projectPersistence:{}}, $reset(){reset=true;}, $patch(data){patch=data;} };
 restoreProject(store,{id:'q1',user_id:'u1',payload_json:{schemaVersion:'QUANTIA_PROJECT_V1',state:{registro:{nombre:'Casa'},unknown:'ignore'}}});
 assert.equal(reset,true); assert.deepEqual(patch,{registro:{nombre:'Casa'}});
 assert.deepEqual(store.projectPersistence,{id:'q1',userId:'u1'});
});
test('requests require a session before fetching', async () => {
 await assert.rejects(projectsRequest(''), /Inicia/);
});
