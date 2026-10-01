<template>
  <section class="qw-card workflow-bridge">
    <h3>Modelo de 04 y entrega para 05</h3>
    <p>{{ store.estructuraEspacial?.sourceMode === 'plan' ? 'Origen: archivo de 03' : 'Origen: dibujo manual con datos de 01 y 02' }}</p>
    <p>Intervención: {{ context.tipoIntervencion || 'Pendiente en 01' }} · Sistema: {{ context.sistemaEstructural || 'Pendiente en 02' }} · Cimentación: {{ context.tipoCimentacion || 'Pendiente en 02' }}</p>
    <p>La geometría se edita en metros. Los candidatos y la evidencia de 03 se conservan al guardar.</p>
    <label class="qw-btn">Importar archivo único de 03 <input type="file" accept=".json,application/json" @change="importFile" /></label>
    <button v-if="planReview" class="qw-btn" :disabled="!metricReady" @click="openEditor">Abrir editor métrico común</button>
    <p v-if="planReview && !metricReady">Falta resolver la geometría métrica de 03 antes de abrir el editor común.</p>
    <button class="qw-btn" :disabled="busy" @click="exportModel">{{ busy ? 'Preparando…' : 'Validar y descargar consumo de 05' }}</button>
    <button v-if="store.estructuraEspacial?.intake03" class="qw-btn" @click="download(store.estructuraEspacial.intake03, 'QUANTIA_03_04.json')">Descargar origen de 03</button>
    <p role="status">{{ message }}</p>
    <details v-if="issues.length" open><summary>Pendientes del modelo ({{ issues.length }})</summary><ul><li v-for="(i,index) in issues" :key="index">{{ i.entityIds.join(', ') }}: {{ i.message }} · Resolver en {{ i.resolveIn }}</li></ul></details>
  </section>
</template>
<script setup>
import {computed,ref} from 'vue';
import {useRouter} from 'vue-router';
import {useViviendaStore} from '@/modules/vivienda/store/viviendaStore';
import {exportarConsumo04Backend} from '@/modules/vivienda/services/motorApiService';
import {estructuraEspacialFromEditorState} from '@/modules/vivienda/editor/adapters/viviendaStoreAdapter';
import {receiveSpatialAnalysis, workflowConstructionContext, canOpenMetricEditor} from '@/modules/vivienda/editor/adapters/spatialWorkflowContract';
const props=defineProps({state:Object,spatialModel:Object,planReview:Boolean});
const emit=defineEmits(['imported','open-editor']);
const store=useViviendaStore(), router=useRouter(), busy=ref(false),message=ref(''),issues=ref([]);
const context=computed(()=>workflowConstructionContext(store));
const metricReady=computed(()=>canOpenMetricEditor(props.spatialModel || store.estructuraEspacial));
function download(value,name){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})); const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function importFile(event){
  const file=event.target.files?.[0];if(!file)return;
  try {
    const value=JSON.parse(await file.text());
    if(value.schemaVersion!=='QUANTIA_03_04_V1')throw new Error('Se requiere un archivo QUANTIA_03_04_V1 generado por 03.');
    const spatial=receiveSpatialAnalysis(value);
    if(!canOpenMetricEditor(spatial))throw new Error('El archivo requiere resolver coordenadas métricas en 03 antes de editarlo.');
    if((store.estructuraEspacial?.espacios?.length || store.estructuraEspacial?.muros?.length) && !window.confirm('Importar sustituirá el modelo de 04 en la sesión. Guarda el proyecto actual si necesitas conservarlo. ¿Continuar?'))return;
    // 01/02 in the current project remain authoritative; original context stays in intake03.
    store.setEstructuraEspacial(spatial);emit('imported');message.value='Archivo de 03 importado; evidencia original conservada.';
  }catch(e){message.value=e.message;}finally{event.target.value='';}
}
function openEditor(){emit('open-editor');router.push('/vivienda/workflow/diseno-vivienda/manual?origin=plan');}
async function exportModel(){
  busy.value=true;message.value='';
  try {
    const spatial=props.state ? estructuraEspacialFromEditorState(props.state,store.estructuraEspacial) : props.spatialModel || store.estructuraEspacial;
    const result=await exportarConsumo04Backend({estructuraEspacial:spatial,datosGeneralesObra:store.datosGeneralesObra,controles:context.value});
    issues.value=result.issues;download(result,'QUANTIA_04_05.json');message.value=`Archivo generado. ${result.derivationTrace.length} derivaciones disponibles; ${result.issues.length} pendientes.`;
  }catch(e){message.value=e.message;}finally{busy.value=false;}
}
</script>
<style scoped>.workflow-bridge{margin:1rem 0;padding:1rem}.workflow-bridge button,.workflow-bridge label{margin:.25rem}.workflow-bridge input{max-width:230px}.workflow-bridge ul{max-height:240px;overflow:auto}</style>
