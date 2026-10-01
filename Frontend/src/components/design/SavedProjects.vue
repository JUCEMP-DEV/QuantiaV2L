<template>
<section id="mis-proyectos" class="projects">
<h2>Mis proyectos</h2>
<p>Consulta los proyectos guardados en tu cuenta. Los cambios del editor deben confirmarse en su etapa antes de guardar.</p>
<ProjectSaveButton />
<button :disabled="busy" @click="load">{{ busy ? 'Consultando...' : 'Consultar mis proyectos' }}</button>
<p role="status">{{ error }}</p>
<p v-if="loaded && !rows.length">No hay proyectos guardados en esta cuenta. Los resultados locales de pruebas no se guardan automáticamente aquí.</p>
<article v-for="row in rows" :key="row.id">
<strong>{{ row.resumen_json?.nombre || row.payload_json?.state?.registro?.proyecto?.nombre || 'Proyecto de vivienda' }}</strong>
<span> | {{ row.status }} | {{ row.updated_at || row.created_at }}</span>
<button @click="open(row)">Abrir proyecto</button><button @click="download(row)">Descargar JSON</button>
</article>
<p v-if="pending">Abrir este proyecto reemplazará el estado actual de la sesión. Guarda primero los cambios que quieras conservar.
<button @click="confirmOpen">Abrir y reemplazar sesión</button><button @click="pending = null">Cancelar</button></p>
</section>
</template>
<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { useViviendaStore } from '@/modules/vivienda/store/viviendaStore';
import { projectsRequest, restoreProject } from '@/modules/vivienda/services/projectsApiService';
import ProjectSaveButton from './ProjectSaveButton.vue';
const auth = useAuthStore(), store = useViviendaStore(), router = useRouter();
const rows = ref([]), busy = ref(false), loaded = ref(false), error = ref(''), pending = ref(null);
async function load() {
  busy.value = true; error.value = ''; loaded.value = false; rows.value = [];
  try { rows.value = (await projectsRequest(auth.accessToken, '?limit=200')).quotes; loaded.value = true; }
  catch (e) { error.value = e.message; } finally { busy.value = false; }
}
function open(row) { pending.value = row; }
function confirmOpen() {
  try { restoreProject(store, pending.value); pending.value = null; router.push('/vivienda/workflow/proyecto-alcance'); }
  catch (e) { error.value = e.message; pending.value = null; }
}
function download(row) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(row, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `proyecto-${row.id}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
</script>
<style scoped>.projects { margin:24px 0;padding:24px;background:white;border:1px solid #dbe3ee;border-radius:16px; }button{margin:8px;padding:8px 14px;cursor:pointer}article{padding:12px 0;border-bottom:1px solid #ddd}span{font-size:13px}</style>
