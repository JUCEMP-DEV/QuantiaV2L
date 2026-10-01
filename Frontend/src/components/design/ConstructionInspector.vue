<template>
  <section class="construction-inspector">
    <h3>Información constructiva para 05</h3>
    <p>Selecciona un elemento. Sus medidas dibujadas se reutilizan en el cálculo.</p>
    <select class="qw-input" :value="selection" @change="choose($event.target.value)">
      <option value="">Seleccionar elemento</option>
      <optgroup v-for="group in groups" :key="group.type" :label="group.label">
        <option v-for="item in state[group.key] || []" :key="item.id" :value="`${group.type}:${item.id}`">{{ item.name || item.kind || group.label }} · {{ item.id }}</option>
      </optgroup>
    </select>
    <template v-if="draft">
      <label v-if="['wall','door','window','stair'].includes(type)">Material / sistema
        <select class="qw-input" v-model="draft.material" v-if="type !== 'stair'">
          <option value="UNKNOWN">Por definir</option><option v-for="m in materials" :key="m[0]" :value="m[0]">{{ m[1] }}</option>
        </select>
        <select v-else class="qw-input" v-model="draft.system"><option value="UNKNOWN">Por definir</option><option value="CONCRETE">Concreto</option><option value="STEEL">Acero</option><option value="WOOD">Madera</option></select>
      </label>
      <template v-if="type === 'wall'">
        <label>Función estructural<select v-model="draft.structuralRole" class="qw-input"><option value="UNKNOWN">Por definir</option><option value="LOAD_BEARING">Portante</option><option value="PARTITION">Divisorio</option></select></label>
        <label>Espesor (m)<input class="qw-input" type="number" step="0.01" v-model.number="draft.thicknessM" /></label>
        <label>Altura propia (m; vacío hereda del nivel)<input class="qw-input" type="number" step="0.01" v-model="draft.heightM" /></label>
      </template>
      <template v-if="type === 'door' || type === 'window'">
        <label>Muro anfitrión<select class="qw-input" v-model="draft.wallId"><option v-for="w in state.walls.filter(w => w.levelId === draft.levelId)" :key="w.id" :value="w.id">{{ w.id }}</option></select></label>
        <label v-if="type === 'door'">Familia<select v-model="draft.kind" class="qw-input"><option value="DOOR">Puerta</option><option value="GARAGE_DOOR">Portón de garaje</option></select></label>
        <label v-if="type === 'door'">Uso<select class="qw-input" v-model="draft.usage"><option value="UNKNOWN">Por definir</option><option value="INTERIOR">Interior</option><option value="MAIN_ENTRANCE">Acceso principal</option><option value="VEHICLE_ACCESS">Acceso vehicular</option></select></label>
        <label>Apertura<select v-model="draft.operation" class="qw-input"><option value="UNKNOWN">Por definir</option><option v-for="op in operations" :key="op[0]" :value="op[0]">{{ op[1] }}</option></select></label>
        <label>Acristalamiento<select class="qw-input" v-model="draft.glazing"><option value="UNKNOWN">Por definir</option><option value="NONE">Sin vidrio</option><option value="GLASS">Con vidrio</option></select></label>
        <label v-if="type === 'door'">Número de hojas<input class="qw-input" type="number" min="1" step="1" v-model.number="draft.leafCount" /></label>
        <label>Posición central (0–1)<input class="qw-input" type="number" step="0.01" min="0" max="1" v-model.number="draft.position" /></label>
        <label>Ancho (m)<input class="qw-input" type="number" step="0.01" v-model.number="draft.widthM" /></label>
        <label>Alto (m)<input class="qw-input" type="number" step="0.01" v-model.number="draft.heightM" /></label>
        <label v-if="type === 'window'">Antepecho (m)<input class="qw-input" type="number" step="0.01" v-model.number="draft.sillHeightM" /></label>
        <p v-if="draft.kind === 'GARAGE_DOOR'">El portón se conserva con su geometría. El catálogo actual no incluye su suministro.</p>
      </template>
      <template v-if="type === 'space'">
        <label>Intervención<select class="qw-input" v-model="draft.intervention"><option value="UNKNOWN">Según alcance de 02</option><option value="NEW">Nuevo</option><option value="RETAIN">Conservar</option><option value="DEMOLISH">Demoler</option><option value="MODIFY">Modificar</option></select></label>
        <label>Acabado de piso<select class="qw-input" v-model="floorFinish"><option value="UNKNOWN">Por definir</option><option value="CERAMIC">Cerámico</option><option value="NONE">Sin acabado</option></select></label>
      </template>
      <template v-if="type === 'stair'">
        <label>Planta de origen<select class="qw-input" v-model="draft.levelFromId"><option v-for="l in state.levels" :key="l.id" :value="l.id">{{ l.name || l.key }}</option></select></label>
        <label>Planta de destino<select class="qw-input" v-model="draft.levelToId"><option value="">Selecciona</option><option v-for="l in state.levels" :key="l.id" :value="l.id">{{ l.name || l.key }}</option></select></label>
        <label>Forma<select class="qw-input" v-model="draft.type"><option value="STRAIGHT">Recta</option><option value="L">L</option><option value="U">U</option><option value="OTHER">Otra por tramos</option></select></label>
        <p>Altura a salvar: {{ stairRise(draft, state.levels) ?? 'Faltan elevaciones de los niveles' }} m</p>
        <fieldset v-for="(flight, i) in draft.flights" :key="flight.id"><legend>Tramo {{ i + 1 }}</legend>
          <label v-for="(point, j) in flight.pathM" :key="j">{{ j ? 'Final' : 'Inicio' }} (m)
            <input class="qw-input" aria-label="X del tramo" type="number" step="0.01" v-model.number="point.x" /><input class="qw-input" aria-label="Y del tramo" type="number" step="0.01" v-model.number="point.y" />
          </label>
          <label>Ancho (m)<input class="qw-input" type="number" step="0.01" v-model.number="flight.widthM" /></label>
          <label>Contrahuellas<input class="qw-input" type="number" min="2" step="1" v-model.number="flight.riserCount" /></label>
          <p>Contrahuella: {{ resolveStair(draft, state.levels).flights[i]?.riserHeightM?.toFixed(3) ?? 'Pendiente' }} m · Huella: {{ resolveStair(draft, state.levels).flights[i]?.treadDepthM?.toFixed(3) ?? 'Pendiente' }} m</p>
          <button class="qw-btn" @click="draft.flights.splice(i,1)">Quitar tramo</button>
        </fieldset>
        <button class="qw-btn" @click="addFlight">Agregar tramo</button>
        <fieldset v-for="(landing, i) in draft.landings" :key="i"><legend>Descanso {{ i + 1 }} (vértices en metros)</legend>
          <label v-for="(p, j) in landing.outer" :key="j">Vértice {{ j + 1 }}<input class="qw-input" type="number" step="0.01" v-model.number="p.x" /><input class="qw-input" type="number" step="0.01" v-model.number="p.y" /></label>
          <button class="qw-btn" @click="draft.landings.splice(i,1)">Quitar descanso</button>
        </fieldset>
        <button class="qw-btn" @click="draft.landings.push({outer: draft.geometry.vertices.map(p=>({...p})), holes:[]})">Agregar descanso desde huella</button>
        <label><input type="checkbox" v-model="draft.hasSlabVoid" /> Vincular un hueco de losa en destino con la huella dibujada</label>
        <label>Barandal por tramo<select class="qw-input" v-model="draft.railingSide"><option value="UNKNOWN">Por definir</option><option value="NONE">Sin barandal en los tramos</option><option value="LEFT">Izquierdo</option><option value="RIGHT">Derecho</option><option value="BOTH">Ambos lados</option></select></label>
        <label v-if="['LEFT','RIGHT','BOTH'].includes(draft.railingSide)">Material del barandal<select class="qw-input" v-model="draft.railingMaterial"><option value="UNKNOWN">Por definir</option><option value="STEEL">Metálico</option><option value="WOOD">Madera</option><option value="GLASS">Vidrio</option></select></label>
        <p>Los tramos y descansos se dibujan sobre la planta. Su definición geométrica no certifica el diseño estructural.</p>
        <button class="qw-btn" @click="$emit('remove-stair', draft.id)">Eliminar escalera</button>
      </template>
      <ul v-if="errors.length" role="alert"><li v-for="error in errors" :key="error">{{ error }}</li></ul>
      <div class="actions"><button class="qw-btn" @click="save(false)">Guardar pendiente</button><button class="qw-btn primary" @click="save(true)">Confirmar propiedades</button></div>
      <p>{{ draft.confirmed ? 'Confirmado' : 'Pendiente' }}</p>
    </template>
    <hr />
    <label><input type="checkbox" :checked="state.completeness?.openings === 'COMPLETE'" @change="$emit('completeness', {openings: $event.target.checked ? 'COMPLETE' : 'PARTIAL'})" /> Ya dibujé todas las puertas, ventanas y portones</label>
    <label><input type="checkbox" :checked="state.completeness?.stairs === 'COMPLETE'" @change="$emit('completeness', {stairs: $event.target.checked ? 'COMPLETE' : 'PARTIAL'})" /> Ya dibujé todas las escaleras (o no existen)</label>
  </section>
</template>
<script setup>
import { ref, computed, watch } from 'vue';
import { createEntityId } from '@/modules/vivienda/editor/core/editorSchema';
import { constructionErrors, stairRise, resolveStair } from '@/modules/vivienda/editor/core/construction';
const props = defineProps({ state: {type:Object,required:true}, selectedId:String, selectedType:String });
const emit = defineEmits(['update-entity','select','completeness','remove-stair']);
const groups = [{type:'wall',key:'walls',label:'Muros'},{type:'door',key:'doors',label:'Puertas / portones'},{type:'window',key:'windows',label:'Ventanas'},{type:'stair',key:'stairs',label:'Escaleras'},{type:'space',key:'spaces',label:'Espacios'}];
const operations = [['HINGED','Abatible'],['SLIDING','Corrediza'],['FOLDING','Plegable'],['SECTIONAL','Seccional'],['ROLLING','Enrollable'],['TILT_UP','Basculante'],['FIXED','Fija']];
const type = computed(()=>props.selectedType);
const selection = computed(()=>props.selectedId ? `${type.value}:${props.selectedId}` : '');
const materials = computed(()=>type.value==='wall' ? [['BRICK','Tabique'],['BLOCK','Block'],['CONCRETE','Concreto'],['DRYWALL','Tablaroca']] : [['WOOD','Madera'],['ALUMINUM','Aluminio'],['STEEL','Acero'],['PVC','PVC'],['GLASS','Vidrio']]);
const draft=ref(null), errors=ref([]), floorFinish=ref('UNKNOWN');
watch(()=>[props.selectedId, props.selectedType, props.state.metadata?.updatedAt],()=>{
  const group=groups.find(g=>g.type===type.value);
  const item=(props.state[group?.key]||[]).find(x=>x.id===props.selectedId);
  draft.value=item ? JSON.parse(JSON.stringify(item)) : null;
  if(draft.value) { draft.value.flights ||= []; draft.value.landings ||= []; draft.value.railingSide ||= 'UNKNOWN'; draft.value.railingMaterial ||= 'UNKNOWN'; }
  floorFinish.value=item?.finishes?.find(f=>f.side==='FLOOR')?.finish || 'UNKNOWN'; errors.value=[];
},{immediate:true});
function choose(value){const i=value.indexOf(':');emit('select',{type:value.slice(0,i),id:value.slice(i+1)});}
function addFlight(){ const points=draft.value.geometry?.vertices || [{x:0,y:0},{x:0,y:0}]; draft.value.flights.push({id:createEntityId('flight'),pathM:points.slice(0,2).map(p=>({...p})),widthM:null,riserCount:null,slabThicknessM:null}); }
function save(confirm){
  let next=JSON.parse(JSON.stringify(draft.value));
  for(const key of ['heightM','widthM','thicknessM','sillHeightM','leafCount']) if(key in next) next[key]=next[key]==='' ? null : next[key];
  if(type.value==='space') next.finishes=[...(next.finishes||[]).filter(f=>f.side!=='FLOOR'),{id:`${next.id}:floor`,side:'FLOOR',material:floorFinish.value,finish:floorFinish.value,coverageHeightM:null,state:confirm?'CONFIRMED':'PROPOSED'}];
  if(type.value==='stair') next=resolveStair(next,props.state.levels);
  errors.value=confirm ? constructionErrors(next,type.value,props.state) : [];
  if(errors.value.length)return;
  // Space geometry/use is confirmed in the existing space inspector.
  next.confirmed=type.value==='space' ? next.confirmed : confirm;
  emit('update-entity',{type:type.value,entity:next});
}
</script>
<style scoped>
.construction-inspector{padding:1rem;border-top:1px solid #cbd5e1;margin-top:1rem}.construction-inspector label{display:block;margin:.65rem 0}.construction-inspector p{font-size:.85rem;color:#475569}.construction-inspector fieldset{margin:1rem 0;border:1px solid #cbd5e1;min-width:0}.actions{display:flex;flex-wrap:wrap;gap:.4rem}.construction-inspector ul{color:#b91c1c}
</style>
