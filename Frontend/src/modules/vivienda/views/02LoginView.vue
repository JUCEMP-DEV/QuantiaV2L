<template>
  <main class="auth-page">
    <div class="blueprint blueprint-left" aria-hidden="true"></div>
    <div class="blueprint blueprint-right" aria-hidden="true"></div>

    <section class="auth-card" aria-labelledby="login-title">
      <header class="auth-header">
        <LogoQuantia class="brand-logo" />
        <h1 id="login-title">Bienvenido de nuevo</h1>
        <p>Inicia sesión para continuar gestionando tus proyectos y análisis.</p>
      </header>

      <form class="login-form" novalidate @submit.prevent="handleContinue">
        <div class="field-group">
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

        <div class="field-group">
          <label for="password">Contraseña</label>
          <div :class="['control', { invalid: errors.password }]">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="5" y="10" width="14" height="11" rx="2" />
              <path d="M8 10V7a4 4 0 0 1 8 0v3" />
            </svg>
            <input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password" placeholder="Ingresa tu contraseña"
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

        <div class="options-row">
          <label class="remember-box"><input v-model="form.remember" type="checkbox" /><span>Recordarme</span></label>
          <a href="#recuperar" class="helper-link" @click.prevent="showRecoveryMessage">¿Olvidaste tu contraseña?</a>
        </div>

        <div v-if="serverMessage" class="server-message error" role="alert">{{ serverMessage }}</div>

        <button class="submit-btn" type="submit" :disabled="loading">{{ loading ? 'Validando...' : 'Iniciar sesión'
          }}</button>
        <div class="divider"><span>o continúa con</span></div>
        <button class="google-btn" type="button" :disabled="loading" @click="handleGoogleLogin"><span
            class="google-mark" aria-hidden="true">G</span>Continuar con Google</button>

        <p class="register-link">¿No tienes una cuenta? <RouterLink to="/vivienda/registro">Regístrate</RouterLink>
        </p>
      </form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import LogoQuantia from '@/components/common/LogoQuantia.vue'
import { useAuthStore } from '@/stores/authStore'
import { API_BASE_URL } from '@/config/apiBaseUrl'

const router = useRouter()
const authStore = useAuthStore()
const showPassword = ref(false)
const loading = ref(false)
const serverMessage = ref('')
const form = reactive({ email: '', password: '', remember: false })
const errors = reactive({ email: '', password: '' })

function validateForm() {
  errors.email = ''
  errors.password = ''
  serverMessage.value = ''
  let valid = true
  if (!form.email.trim()) { errors.email = 'El correo electrónico es obligatorio.'; valid = false }
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { errors.email = 'Ingresa un correo válido.'; valid = false }
  if (!form.password.trim()) { errors.password = 'La contraseña es obligatoria.'; valid = false }
  else if (form.password.trim().length < 6) { errors.password = 'La contraseña debe tener al menos 6 caracteres.'; valid = false }
  return valid
}

function getProfileFromSource(raw = '') {
  const value = String(raw || '').toLowerCase()
  if (value === 'tecnico' || value === 'tecnico_profesional') return 'tecnico'
  return 'oficial'
}

function normalizeAuthenticatedUser(source, fallbackEmail, fallbackProfile) {
  const profile = getProfileFromSource(source?.perfil || source?.tipo_usuario || fallbackProfile)
  return {
    id: source?.id || '', email: source?.email || fallbackEmail,
    nombre: source?.nombre || source?.name || 'Usuario Quantia',
    telefono: source?.telefono || source?.phone || '', profesion: source?.profesion || '',
    alias: source?.alias || '', direccion: source?.direccion || '', perfil: profile
  }
}

async function authenticateAgainstBackend() {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: form.email.trim(), password: form.password })
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(String(payload?.detail || 'Credenciales inválidas.'))
  const user = payload?.user || payload?.data || payload
  return {
    user: normalizeAuthenticatedUser(user, form.email.trim(), authStore.accessProfile),
    accessToken: payload?.access_token || '', tokenType: payload?.token_type || 'bearer'
  }
}

async function hashPassword(password) {
  const encoded = new TextEncoder().encode(password)
  const digest = await crypto.subtle.digest('SHA-256', encoded)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function authenticateAgainstLocalFallback() {
  const localUsers = JSON.parse(localStorage.getItem('quantia_users') || '[]')
  const passwordHash = await hashPassword(form.password)
  const matchedUser = localUsers.find((item) => String(item.email || '').toLowerCase() === form.email.trim().toLowerCase() && String(item.passwordHash || '') === passwordHash)
  if (!matchedUser) throw new Error('No fue posible autenticar con esas credenciales.')
  return { user: normalizeAuthenticatedUser(matchedUser, form.email.trim(), matchedUser?.perfil), accessToken: '', tokenType: 'local' }
}

function completeSession(session) {
  const authenticatedUser = session.user
  authStore.setAccessProfile(authenticatedUser.perfil)
  authStore.setSession(session)
  router.push('/vivienda/dashboard')
}

async function handleContinue() {
  if (!validateForm()) return
  loading.value = true
  serverMessage.value = ''
  try {
    completeSession(await authenticateAgainstBackend())
  } catch (backendError) {
    try { completeSession(await authenticateAgainstLocalFallback()) }
    catch { serverMessage.value = String(backendError?.message || 'No se pudo iniciar sesión.') }
  } finally { loading.value = false }
}

function showRecoveryMessage() {
  serverMessage.value = 'La recuperación de contraseña se habilitará al conectar el servicio de autenticación.'
}

async function handleGoogleLogin() {
  serverMessage.value = ''
  if (typeof authStore.signInWithGoogle !== 'function') {
    serverMessage.value = 'El acceso con Google estará disponible al conectar el proveedor de autenticación.'
    return
  }
  loading.value = true
  try { await authStore.signInWithGoogle() }
  catch (error) { serverMessage.value = error?.message || 'No se pudo continuar con Google.' }
  finally { loading.value = false }
}
</script>

<style scoped>
.auth-page {
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
  background: radial-gradient(circle at 50% 2%, rgba(63, 111, 255, .13), transparent 38%), linear-gradient(135deg, #f8faff, #edf3ff 52%, #f8faff);
}

.auth-page::before,
.auth-page::after {
  content: '';
  position: absolute;
  width: 360px;
  height: 360px;
  border: 2px solid rgba(37, 99, 235, .17);
  border-radius: 50%;
}

.auth-page::before {
  top: -205px;
  right: -105px;
  box-shadow: 22px 12px 0 -18px #00aee9;
}

.auth-page::after {
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
  left: 0
}

.blueprint-right {
  right: 0;
  transform: scaleX(-1)
}

.auth-card {
  width: min(100%, 600px);
  position: relative;
  z-index: 1;
  padding: 42px 62px 38px;
  background: rgba(255, 255, 255, .95);
  border: 1px solid white;
  border-radius: 24px;
  box-shadow: 0 18px 55px rgba(34, 61, 128, .16);
  backdrop-filter: blur(8px);
}

.auth-header {
  text-align: center
}

.brand-logo {
  width: min(100%, 370px);
  height: 135px;
  margin: 0 auto 8px;
  display: block
}

.auth-header h1 {
  margin: 0;
  font-size: 2rem;
  letter-spacing: -.03em
}

.auth-header p {
  max-width: 390px;
  margin: 9px auto 26px;
  color: #53628a;
  font-size: .96rem;
  line-height: 1.5
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 17px
}

.field-group {
  display: flex;
  flex-direction: column
}

.field-group label {
  margin: 0 0 7px;
  font-size: .9rem;
  font-weight: 600;
  color: #263a70
}

.control {
  min-height: 50px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid #cbd3e5;
  border-radius: 9px
}

.control:focus-within {
  border-color: #3678f6;
  box-shadow: 0 0 0 3px rgba(54, 120, 246, .12)
}

.control.invalid {
  border-color: #dc2626
}

.control>svg {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: none;
  stroke: #415b9c;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round
}

.control input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #172657;
  font: inherit;
  font-size: .94rem
}

.control input::placeholder {
  color: #8994b3
}

.visibility-btn {
  display: grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border: 0;
  background: transparent;
  color: #314d92;
  cursor: pointer
}

.visibility-btn svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7
}

.error-text {
  margin: 5px 0 0;
  color: #c81e1e;
  font-size: .78rem
}

.options-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: .9rem
}

.remember-box {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #4f5f83
}

.remember-box input {
  width: 17px;
  height: 17px;
  accent-color: #1266ed
}

.helper-link {
  color: #075ff2;
  text-decoration: none;
  font-weight: 600
}

.server-message {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: .84rem;
  font-weight: 600
}

.server-message.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca
}

.submit-btn {
  min-height: 50px;
  border: 0;
  border-radius: 9px;
  color: white;
  background: linear-gradient(90deg, var(--blue), var(--violet));
  box-shadow: 0 8px 18px rgba(62, 75, 226, .2);
  font-size: 1.04rem;
  font-weight: 700;
  cursor: pointer
}

.submit-btn:disabled,
.google-btn:disabled {
  opacity: .65;
  cursor: not-allowed
}

.divider {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #566486;
  font-size: .85rem
}

.divider::before,
.divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: #cfd6e5
}

.google-btn {
  min-height: 45px;
  width: min(100%, 325px);
  align-self: center;
  border: 1px solid #cdd4e3;
  border-radius: 8px;
  background: #fff;
  color: #263a70;
  font-size: .94rem;
  cursor: pointer
}

.google-mark {
  font-size: 1.25rem;
  font-weight: 800;
  color: #4285f4;
  margin-right: 12px
}

.register-link {
  margin: 2px 0 0;
  text-align: center;
  color: #4f5f83;
  font-size: .94rem
}

.register-link a {
  color: #075ff2;
  font-weight: 700;
  text-decoration: none
}

.register-link a:hover,
.helper-link:hover {
  text-decoration: underline
}

@media(max-width:660px) {
  .auth-page {
    padding: 14px;
    align-items: start
  }

  .auth-card {
    margin: 12px 0;
    padding: 28px 22px 27px;
    border-radius: 20px
  }

  .brand-logo {
    height: 105px
  }

  .blueprint {
    display: none
  }

  .options-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 9px
  }
}
</style>
