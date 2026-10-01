import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { buildPhase03Delivery, receiveSpatialAnalysis, workflowConstructionContext } from '../src/modules/vivienda/editor/adapters/spatialWorkflowContract.js';
const server = await createServer({server:{middlewareMode:true},appType:'custom'});
after(()=>server.close());
const schema=await server.ssrLoadModule('/src/modules/vivienda/editor/core/editorSchema.js');
const {validateOpening}=await server.ssrLoadModule('/src/modules/vivienda/editor/core/constraints.js');
const {createDoorOnWall}=await server.ssrLoadModule('/src/modules/vivienda/editor/core/openings.js');
const {editorStateFromViviendaStore,estructuraEspacialFromEditorState,applyEditorStateToViviendaStore}=await server.ssrLoadModule('/src/modules/vivienda/editor/adapters/viviendaStoreAdapter.js');
const {resolveStair,constructionErrors}=await server.ssrLoadModule('/src/modules/vivienda/editor/core/construction.js');
const levels=[schema.createLevel({id:'L0',key:'planta_baja',heightM:3,elevationM:0}),schema.createLevel({id:'L1',key:'segunda_planta',heightM:3,elevationM:3})];
const wall=schema.createWall({id:'W',levelId:'L0',start:{x:0,y:0},end:{x:8,y:0},heightM:3,thicknessM:.15});

test('click placement projects onto the wall instead of treating null as zero',()=>{
 const result=createDoorOnWall({wall,point:{x:4,y:0},data:{widthM:1,heightM:2},walls:[wall]});
 assert.equal(result.ok,true);assert.equal(result.entity.position,.5);
});
test('vertical bounds and overlap are evaluated in the wall face',()=>{
 const door=schema.createDoor({id:'D',levelId:'L0',wallId:'W',widthM:1,heightM:2,position:.5});
 const window=schema.createWindow({id:'V',levelId:'L0',wallId:'W',widthM:1,heightM:.5,sillHeightM:2.2,position:.5});
 assert.equal(validateOpening({opening:window,walls:[wall],doors:[door],levels,requireComplete:true}).isValid,true);
 assert.equal(validateOpening({opening:{...window,sillHeightM:1.5},walls:[wall],doors:[door]}).isValid,false);
 assert.equal(validateOpening({opening:{...window,sillHeightM:2.8},walls:[wall]}).isValid,false);
 assert.equal(validateOpening({opening:{...window,levelId:'L1'},walls:[wall]}).isValid,false);
});
test('manual skips 03, seeds actual 01/02 data and preserves new fields through reopening',()=>{
 const store={datosGeneralesObra:{niveles:2,alturaNivel1M:3,alturaNivel2M:2.8,anchoTerrenoM:8,largoTerrenoM:10,sistemaEstructural:'tradicional'},estructuraEspacial:{},clasificacion:{tipoIntervencion:'obra_nueva'},alcance:{alcance:'completo'}};
 const state=editorStateFromViviendaStore(store);
 assert.equal(state.levels.length,2);assert.equal(state.levels[0].heightM,3);assert.equal(state.levels[1].elevationM,null);
 assert.equal(state.spaces.length,0);assert.equal(state.terrain.geometry.areaM2,80);
 state.levels=levels;state.walls=[wall];state.doors=[schema.createDoor({id:'G',wallId:'W',levelId:'L0',kind:'GARAGE_DOOR',material:'STEEL',operation:'ROLLING',usage:'VEHICLE_ACCESS',widthM:3,heightM:2.4,position:.5})];
 state.stairs=[schema.createStair({id:'S',levelFromId:'L0',levelToId:'L1',type:'STRAIGHT',system:'CONCRETE',hasSlabVoid:true,flights:[{id:'F',pathM:[{x:1,y:1},{x:1,y:5}],riserCount:18,widthM:1}],geometry:{type:'polygon',vertices:[{x:0,y:0},{x:2,y:0},{x:2,y:5},{x:0,y:5}]}})];
 state.completeness={openings:'COMPLETE'};
 const spatial=estructuraEspacialFromEditorState(state,{buckets:{EXCLUDED_GRAPHIC:[{id:'E'}]}});
 const reopened=editorStateFromViviendaStore({...store,estructuraEspacial:spatial});
 assert.equal(reopened.doors[0].kind,'GARAGE_DOOR');assert.equal(reopened.doors[0].material,'STEEL');assert.equal(reopened.stairs[0].flights[0].riserCount,18);assert.equal(reopened.stairs[0].hasSlabVoid,true);assert.equal(reopened.completeness.openings,'COMPLETE');
 assert.equal(spatial.buckets.EXCLUDED_GRAPHIC[0].id,'E');
 assert.equal(workflowConstructionContext(store).tipoIntervencion,'obra_nueva');
 const file=buildPhase03Delivery(spatial,store);const received=receiveSpatialAnalysis(file);
 assert.deepEqual(received.muros,spatial.muros);assert.equal(received.intake03.schemaVersion,'QUANTIA_03_04_V1');assert.equal(received.sourceMode,'plan');
 // Updating 01/02 can clear the store: the handoff must preserve the original evidence snapshot.
 const resetStore={...store,estructuraEspacial:{},setEstructuraEspacial(value){this.estructuraEspacial=value;}};
 applyEditorStateToViviendaStore(resetStore,state,{currentSpatial:received});
 assert.equal(resetStore.estructuraEspacial.intake03.schemaVersion,'QUANTIA_03_04_V1');
 assert.equal(resetStore.estructuraEspacial.buckets.EXCLUDED_GRAPHIC[0].id,'E');
});
test('stair rise follows levels and missing elevations never become a typical height',()=>{
 const stair=schema.createStair({id:'S',levelFromId:'L0',levelToId:'L1',type:'STRAIGHT',system:'CONCRETE',geometry:{vertices:[{x:0,y:0},{x:2,y:0},{x:2,y:5},{x:0,y:5}]},flights:[{id:'F',pathM:[{x:1,y:0},{x:1,y:4.25}],riserCount:18,widthM:1}]});
 const resolved=resolveStair(stair,levels);assert.equal(resolved.totalRiseM,3);assert.equal(resolved.flights[0].treadDepthM,.25);assert.equal(constructionErrors(stair,'stair',{levels}).length,0);
 const missing=levels.map(l=>({...l,elevationM:null}));assert.equal(resolveStair(stair,missing).totalRiseM,null);assert.ok(constructionErrors(stair,'stair',{levels:missing}).length);
});
