<template><div><button class="qw-btn" :disabled="busy" @click="save">{{ busy ? 'Guardando...' : 'Guardar proyecto' }}</button><small role="status"> {{ message }}</small></div></template>
<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { useViviendaStore } from '@/modules/vivienda/store/viviendaStore';
import { projectsRequest, projectSnapshot } from '@/modules/vivienda/services/projectsApiService';
const auth = useAuthStore(), store = useViviendaStore(), busy = ref(false), message = ref('');
async function save() {
  busy.value = true; message.value = '';
  try {
    const snapshot = projectSnapshot(store.$state);
    const current = store.projectPersistence;
    if (current.userId && current.userId !== auth.user?.id) throw new Error('El proyecto abierto pertenece a otra sesión.');
    const result = await projectsRequest(auth.accessToken, '', {
      quote_id: current.id, user_email: auth.user?.email, status: 'draft', modulo: 'vivienda',
      payload_json: snapshot,
      resumen_json: { nombre: store.registro?.proyecto?.nombre || 'Proyecto de vivienda' },
    });
    store.projectPersistence = { id: result.quote.id, userId: result.quote.user_id };
    message.value = 'Proyecto guardado en tu cuenta. Guarda de nuevo después de realizar cambios.';
  } catch (error) { message.value = error.message; }
  finally { busy.value = false; }
}
</script>
