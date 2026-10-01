<template>
  <main class="register-page">
    <div class="blueprint blueprint-left" aria-hidden="true"></div>
    <div class="blueprint blueprint-right" aria-hidden="true"></div>

    <section class="register-card" aria-labelledby="register-title">
      <header class="register-header">
        <LogoQuantia class="brand-logo" />
        <h1 id="register-title">Crea tu cuenta</h1>
        <p>Únete a Quantia Vivienda y gestiona tus proyectos de forma inteligente.</p>
      </header>

      <form class="register-form" novalidate @submit.prevent="handleRegister">
        <div class="name-grid">
          <div class="form-group">
            <label for="nombre">Nombre(s)</label>
            <div :class="['control', { invalid: errors.nombre }]">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" />
              </svg>
              <input id="nombre" v-model.trim="form.nombre" type="text" autocomplete="given-name"
                placeholder="Ingresa tu nombre" :aria-invalid="Boolean(errors.nombre)" />
            </div>
            <small v-if="errors.nombre" class="error-text">{{ errors.nombre }}</small>
          </div>

          <div class="form-group">
            <label for="apellidos">Apellido(s)</label>
            <div :class="['control', { invalid: errors.apellidos }]">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" />
              </svg>
              <input id="apellidos" v-model.trim="form.apellidos" type="text" autocomplete="family-name"
                placeholder="Ingresa tus apellidos" :aria-invalid="Boolean(errors.apellidos)" />
            </div>
            <small v-if="errors.apellidos" class="error-text">{{ errors.apellidos }}</small>
          </div>
        </div>

        <div class="form-group">
          <label for="email">Correo electrónico</label>
          <div :class="['control', { invalid: errors.email }]">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 5h18v14H3zM3 7l9 7 9-7" />
            </svg>
            <input id="email" v-model.trim="form.email" type="email" autocomplete="email"
              placeholder="ejemplo@correo.com" :aria-invalid="Boolean(errors.email)" />
          </div>
          <small v-if="errors.email" class="error-text">{{ errors.email }}</small>
        </div>

        <div class="form-group">
          <label for="password">Contraseña</label>
          <div :class="['control', { invalid: errors.password }]">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="5" y="10" width="14" height="11" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password" placeholder="Crea una contraseña segura"
              :aria-invalid="Boolean(errors.password)" />
            <button type="button" class="visibility-btn"
              :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              @click="showPassword = !showPassword">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
                <circle cx="12" cy="12" r="2.5" />
              </svg>
            </button>
          </div>
          <small v-if="errors.password" class="error-text">{{ errors.password }}</small>
        </div>

        <div class="form-group">
          <label for="confirmPassword">Confirmar contraseña</label>
          <div :class="['control', { invalid: errors.confirmPassword }]">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="5" y="10" width="14" height="11" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <input id="confirmPassword" v-model="form.confirmPassword" :type="showConfirmPassword ? 'text' : 'password'"
              autocomplete="new-password" placeholder="Repite tu contraseña"
              :aria-invalid="Boolean(errors.confirmPassword)" />
            <button type="button" class="visibility-btn"
              :aria-label="showConfirmPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              @click="showConfirmPassword = !showConfirmPassword">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
                <circle cx="12" cy="12" r="2.5" />
              </svg>
            </button>
          </div>
          <small v-if="errors.confirmPassword" class="error-text">{{ errors.confirmPassword }}</small>
        </div>

        <div class="form-group">
          <label for="tipoUsuario">Rol</label>
          <div :class="['control', { invalid: errors.tipoUsuario }]">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3 4.5 6v5c0 4.8 3 8.2 7.5 10 4.5-1.8 7.5-5.2 7.5-10V6L12 3Z" />
              <path d="m9.5 12 1.7 1.7 3.6-4" />
            </svg>
            <select id="tipoUsuario" v-model="form.tipoUsuario" :aria-invalid="Boolean(errors.tipoUsuario)">
              <option disabled value="">Selecciona tu rol</option>
              <option value="general">Usuario general</option>
              <option value="tecnico">Técnico / Profesional</option>
            </select>
          </div>
          <small v-if="errors.tipoUsuario" class="error-text">{{ errors.tipoUsuario }}</small>
        </div>

        <div v-if="serverMessage.text" :class="['server-message', serverMessage.type]" role="status">{{
          serverMessage.text }}</div>

        <button class="submit-btn" type="submit" :disabled="loading">{{ loading ? 'Creando cuenta...' : 'Crear cuenta'
        }}</button>
        <div class="divider"><span>o continúa con</span></div>
        <button class="google-btn" type="button" :disabled="loading" @click="handleGoogleRegister">
          <span class="google-mark" aria-hidden="true">G</span>
          Continuar con Google
        </button>
        <p class="login-link">¿Ya tienes una cuenta? <RouterLink to="/vivienda/login">Inicia sesión</RouterLink>
        </p>
      </form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import { API_BASE_URL } from '@/config/apiBaseUrl'
import LogoQuantia from '@/components/common/LogoQuantia.vue'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)

const form = reactive({ nombre: '', apellidos: '', email: '', tipoUsuario: '', password: '', confirmPassword: '' })
const errors = reactive({ nombre: '', apellidos: '', email: '', tipoUsuario: '', password: '', confirmPassword: '' })
const serverMessage = reactive({ type: '', text: '' })

function resetErrors() {
  Object.keys(errors).forEach((key) => { errors[key] = '' })
  serverMessage.type = ''
  serverMessage.text = ''
}

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function validateForm() {
  resetErrors()
  let isValid = true
  if (!form.nombre) { errors.nombre = 'El nombre es obligatorio.'; isValid = false }
  if (!form.apellidos) { errors.apellidos = 'Los apellidos son obligatorios.'; isValid = false }
  if (!form.email) { errors.email = 'El correo es obligatorio.'; isValid = false }
  else if (!validateEmail(form.email)) { errors.email = 'Ingresa un correo válido.'; isValid = false }
  if (!form.password) { errors.password = 'La contraseña es obligatoria.'; isValid = false }
  else if (form.password.length < 8) { errors.password = 'La contraseña debe tener al menos 8 caracteres.'; isValid = false }
  if (!form.confirmPassword) { errors.confirmPassword = 'Confirma tu contraseña.'; isValid = false }
  else if (form.password !== form.confirmPassword) { errors.confirmPassword = 'Las contraseñas no coinciden.'; isValid = false }
  if (!form.tipoUsuario) { errors.tipoUsuario = 'Selecciona tu rol.'; isValid = false }
  return isValid
}

async function hashPassword(password) {
  const encoded = new TextEncoder().encode(password)
  const digest = await crypto.subtle.digest('SHA-256', encoded)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}


async function handleGoogleRegister() {
  resetErrors()
  if (typeof authStore.signInWithGoogle !== 'function') {
    serverMessage.type = 'error'
    serverMessage.text = 'El registro con Google estará disponible al conectar el proveedor de autenticación.'
    return
  }
  loading.value = true
  try { await authStore.signInWithGoogle() }
  catch (error) {
    serverMessage.type = 'error'
    serverMessage.text = error?.message || 'No se pudo continuar con Google.'
  } finally { loading.value = false }
}

async function handleRegister() {
  if (!validateForm()) return
  loading.value = true
  resetErrors()
  try {
    const payload = {
      nombre: `${form.nombre} ${form.apellidos}`.trim(),
      nombres: form.nombre,
      apellidos: form.apellidos,
      email: form.email,
      telefono: '', profesion: '', alias: '', direccion: '',
      tipo_usuario: form.tipoUsuario === 'tecnico' ? 'tecnico' : 'general',
      password: form.password
    }
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    })
    const data = await response.json()
    if (!response.ok) {
      serverMessage.type = 'error'
      serverMessage.text = data.detail || 'No se pudo completar el registro.'
      return
    }

  } finally { loading.value = false }
}
</script>

<style scoped>
.register-page {
  --navy: #071b5c;
  --blue: #0569f5;
  --violet: #7b21f4;
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  padding: 24px;
  color: var(--navy);
  background: radial-gradient(circle at 50% 2%, rgba(63, 111, 255, .13), transparent 38%), linear-gradient(135deg, #f8faff 0%, #edf3ff 52%, #f8faff 100%);
}

.register-page::before,
.register-page::after {
  content: '';
  position: absolute;
  width: 360px;
  height: 360px;
  border: 2px solid rgba(37, 99, 235, .17);
  border-radius: 50%;
}

.register-page::before {
  top: -205px;
  right: -105px;
  box-shadow: 22px 12px 0 -18px #00aee9;
}

.register-page::after {
  bottom: -250px;
  left: -140px;
  box-shadow: 22px -12px 0 -18px #7246ef;
}

.blueprint {
  position: absolute;
  width: 27vw;
  height: 58%;
  bottom: 0;
  opacity: .22;
  background-image: linear-gradient(rgba(44, 100, 239, .32) 1px, transparent 1px), linear-gradient(90deg, rgba(44, 100, 239, .32) 1px, transparent 1px), linear-gradient(28deg, transparent 49.5%, rgba(44, 100, 239, .38) 50%, transparent 50.5%);
  background-size: 26px 26px, 26px 26px, 86px 86px;
  mask-image: linear-gradient(to top, #000 35%, transparent 100%);
}

.blueprint-left {
  left: 0;
}

.blueprint-right {
  right: 0;
  transform: scaleX(-1);
}

.register-card {
  width: min(100%, 600px);
  position: relative;
  z-index: 1;
  padding: 38px 62px 34px;
  background: rgba(255, 255, 255, .94);
  border: 1px solid rgba(255, 255, 255, .9);
  border-radius: 24px;
  box-shadow: 0 18px 55px rgba(34, 61, 128, .16);
  backdrop-filter: blur(8px);
}

.register-header {
  text-align: center;
}

.brand-logo {
  width: min(100%, 370px);
  height: 115px;
  margin: 0 auto 6px;
  display: block;
}

.register-header h1 {
  margin: 0;
  font-size: 1.82rem;
  line-height: 1.2;
  letter-spacing: -.03em;
}

.register-header p {
  max-width: 390px;
  margin: 8px auto 22px;
  color: #53628a;
  font-size: .93rem;
  line-height: 1.45;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.name-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.form-group label {
  margin: 0 0 6px;
  font-size: .88rem;
  font-weight: 600;
  color: #263a70;
}

.control {
  min-height: 46px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 13px;
  background: #fff;
  border: 1px solid #cbd3e5;
  border-radius: 8px;
  transition: border-color .18s ease, box-shadow .18s ease;
}

.control:focus-within {
  border-color: #3678f6;
  box-shadow: 0 0 0 3px rgba(54, 120, 246, .12);
}

.control.invalid {
  border-color: #dc2626;
}

.control>svg {
  width: 19px;
  height: 19px;
  flex: 0 0 auto;
  fill: none;
  stroke: #415b9c;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.control input,
.control select {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #172657;
  font: inherit;
  font-size: .9rem;
}

.control input::placeholder {
  color: #8994b3;
}

.control select {
  cursor: pointer;
}

.visibility-btn {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #314d92;
  cursor: pointer;
}

.visibility-btn svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
}

.error-text {
  margin-top: 5px;
  color: #c81e1e;
  font-size: .78rem;
}

.server-message {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: .84rem;
  font-weight: 600;
}

.server-message.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.server-message.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.submit-btn {
  min-height: 48px;
  margin-top: 1px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: linear-gradient(90deg, var(--blue), var(--violet));
  box-shadow: 0 8px 18px rgba(62, 75, 226, .2);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform .18s ease, box-shadow .18s ease;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(62, 75, 226, .28);
}

.submit-btn:disabled,
.google-btn:disabled {
  opacity: .65;
  cursor: not-allowed;
}

.divider {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #566486;
  font-size: .85rem;
}

.divider::before,
.divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: #cfd6e5;
}

.divider span {
  white-space: nowrap;
}

.google-btn {
  min-height: 43px;
  width: min(100%, 300px);
  align-self: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: 1px solid #cdd4e3;
  border-radius: 8px;
  background: #fff;
  color: #263a70;
  font-size: .91rem;
  font-weight: 500;
  cursor: pointer;
}

.google-mark {
  font-size: 1.25rem;
  font-weight: 800;
  color: #4285f4;
}

.login-link {
  margin: 4px 0 0;
  text-align: center;
  color: #4f5f83;
  font-size: .9rem;
}

.login-link a {
  color: #075ff2;
  font-weight: 700;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}

@media (max-width: 660px) {
  .register-page {
    padding: 14px;
    align-items: start;
  }

  .register-card {
    margin: 12px 0;
    padding: 28px 22px 26px;
    border-radius: 20px;
  }

  .brand-logo {
    height: 94px;
  }

  .name-grid {
    grid-template-columns: 1fr;
    gap: 13px;
  }

  .blueprint {
    display: none;
  }
}

@media (max-height: 850px) and (min-width: 661px) {
  .register-page {
    align-items: start;
  }

  .register-card {
    margin: 18px 0;
    padding-top: 24px;
    padding-bottom: 24px;
  }

  .brand-logo {
    height: 92px;
  }

  .register-header p {
    margin-bottom: 14px;
  }

  .register-form {
    gap: 9px;
  }
}
</style>
