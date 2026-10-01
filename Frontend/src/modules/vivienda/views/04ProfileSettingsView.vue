<template>
  <main class="profile-page">
    <section class="profile-card" aria-labelledby="profile-title">
      <LogoQuantia class="brand-logo" />
      <p class="eyebrow">Cuenta Quantia</p>
      <h1 id="profile-title">Perfil de usuario</h1>
      <p class="intro">Actualiza tus datos para mantener completa la información de tus proyectos.</p>

      <form class="profile-form" @submit.prevent="saveProfile">
        <label>
          Nombre
          <input v-model.trim="form.nombre" type="text" required autocomplete="name" />
        </label>
        <label>
          Correo electrónico
          <input :value="authStore.user?.email || ''" type="email" disabled />
        </label>
        <label>
          Teléfono
          <input v-model.trim="form.telefono" type="tel" autocomplete="tel" />
        </label>
        <label>
          Profesión
          <input v-model.trim="form.profesion" type="text" />
        </label>
        <label class="full-width">
          Dirección
          <input v-model.trim="form.direccion" type="text" autocomplete="street-address" />
        </label>

        <p v-if="saved" class="success-message" role="status">Perfil actualizado.</p>
        <p v-if="errorMessage" class="success-message" role="alert">{{ errorMessage }}</p>
        <div class="actions">
          <button class="secondary-button" type="button" @click="router.push('/vivienda/dashboard')">Volver</button>
          <button class="primary-button" type="submit" :disabled="loading">
            {{ loading ? 'Guardando...' : 'Guardar cambios' }}
          </button>
        </div>
      </form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import LogoQuantia from '@/components/common/LogoQuantia.vue'
import { useAuthStore } from '@/stores/authStore'
import { buildApiUrl } from '@/config/apiBaseUrl'

const router = useRouter()
const authStore = useAuthStore()

const saved = ref(false)
const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  nombre: authStore.user?.nombre || '',
  telefono: authStore.user?.telefono || '',
  profesion: authStore.user?.profesion || '',
  direccion: authStore.user?.direccion || '',
})

async function saveProfile() {
  saved.value = false
  errorMessage.value = ''
  loading.value = true

  try {
    if (!authStore.accessToken) throw new Error('Inicia sesi?n nuevamente para guardar tu perfil.')
    const response = await fetch(buildApiUrl('/api/auth/profile/update'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.accessToken}`,
      },
      body: JSON.stringify({
        user_id: authStore.user?.id || '',
        email: authStore.user?.email || '',
        nombre: form.nombre,
        telefono: form.telefono,
        profesion: form.profesion,
        direccion: form.direccion,
        tipo_usuario:
          authStore.accessProfile ||
          authStore.user?.perfil ||
          'oficial',
      }),
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      throw new Error(data?.detail || 'No se pudo actualizar el perfil.')
    }

    authStore.setUser(data.user)
    authStore.setAccessProfile(data.user?.perfil || '')

    saved.value = true
  } catch (error) {
    errorMessage.value =
      error?.message || 'No se pudo actualizar el perfil.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 20px;
  color: #172657;
  background: linear-gradient(135deg, #f7faff, #e9f1ff);
}

.profile-card {
  width: min(100%, 720px);
  padding: 36px;
  background: #fff;
  border: 1px solid #d8e1f2;
  border-radius: 16px;
  box-shadow: 0 18px 45px rgba(34, 61, 128, .14);
}

.brand-logo {
  width: 190px;
  height: 70px;
  margin: 0 auto 20px;
}

.eyebrow {
  margin: 0;
  color: #1266ed;
  font-size: .8rem;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 6px 0;
  font-size: 2rem;
}

.intro {
  margin: 0 0 26px;
  color: #53628a;
}

.profile-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

label {
  display: grid;
  gap: 7px;
  color: #263a70;
  font-size: .9rem;
  font-weight: 600;
}

input {
  min-height: 44px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid #cbd3e5;
  border-radius: 8px;
  color: #172657;
  font: inherit;
}

input:focus {
  outline: 3px solid rgba(54, 120, 246, .14);
  border-color: #3678f6;
}

input:disabled {
  background: #f2f5fa;
  color: #6a7695;
}

.full-width,
.success-message,
.actions {
  grid-column: 1 / -1;
}

.success-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #ecfdf3;
  color: #167044;
  font-size: .9rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 8px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.primary-button {
  border: 0;
  color: #fff;
  background: #1266ed;
}

.secondary-button {
  border: 1px solid #b9c7df;
  color: #263a70;
  background: #fff;
}

@media (max-width: 620px) {
  .profile-card {
    padding: 26px 20px;
  }

  .profile-form {
    grid-template-columns: 1fr;
  }

  .full-width,
  .success-message,
  .actions {
    grid-column: auto;
  }

  .actions {
    justify-content: stretch;
  }

  button {
    flex: 1;
  }
}
</style>