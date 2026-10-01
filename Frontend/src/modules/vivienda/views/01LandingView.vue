  <template>
    <main class="access-page">
      <div class="blueprint blueprint-left" aria-hidden="true"></div>
      <div class="blueprint blueprint-right" aria-hidden="true"></div>

      <section class="access-shell">
        <header class="access-header">
          <LogoQuantia class="brand-logo" />
          <p class="eyebrow">Quantia · Vivienda</p>
          <h1>Accede a tu espacio de trabajo</h1>
          <p class="intro">
            Inicia sesión para continuar un proyecto o crea una cuenta para comenzar uno nuevo.
          </p>
        </header>

        <div class="access-options">
          <article class="access-option login-option" id="iniciar-sesion">
            <div class="option-icon" aria-hidden="true">→</div>
            <span class="option-label">Ya tengo una cuenta</span>
            <h2>Iniciar sesión</h2>
            <p>Recupera tus proyectos, configuraciones y avances guardados.</p>
            <button class="primary-action" type="button" @click="goLogin">Continuar al acceso</button>
          </article>

          <article class="access-option register-option" id="crear-cuenta">
            <div class="option-icon" aria-hidden="true">＋</div>
            <span class="option-label">Primera vez en Quantia</span>
            <h2>Crear cuenta</h2>
            <p>Registra tus datos y selecciona el rol con el que utilizarás la plataforma.</p>
            <button class="secondary-action" type="button" @click="goRegister">Registrarme</button>
          </article>
        </div>

        <footer class="access-status">
          <span>Estado de sesión</span>
          <strong>{{ sessionLabel }}</strong>
          <button v-if="authStore.user" type="button" @click="continueSession">{{ nextLabel }}</button>
        </footer>
      </section>
    </main>
  </template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import LogoQuantia from '@/components/common/LogoQuantia.vue'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()
const sessionLabel = computed(() => authStore.user ? 'Sesión activa' : 'Sin sesión')
const nextLabel = computed(() => 'Ir al panel')

function goLogin() { router.push('/vivienda/login') }
function goRegister() { router.push('/vivienda/registro') }
function continueSession() { router.push('/vivienda/dashboard') }
</script>

<style scoped>
.access-page {
  --navy: #071b5c;
  --blue: #0569f5;
  --violet: #7b21f4;
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  padding: 32px;
  color: var(--navy);
  background: radial-gradient(circle at 50% 0, rgba(57, 107, 255, .15), transparent 36%), linear-gradient(135deg, #f8faff, #edf3ff 52%, #f8faff)
}

.access-page::before,
.access-page::after {
  content: '';
  position: absolute;
  width: 390px;
  height: 390px;
  border: 2px solid rgba(37, 99, 235, .17);
  border-radius: 50%
}

.access-page::before {
  top: -240px;
  right: -100px;
  box-shadow: 22px 12px 0 -18px #00aee9
}

.access-page::after {
  bottom: -270px;
  left: -145px;
  box-shadow: 22px -12px 0 -18px #7246ef
}

.blueprint {
  position: absolute;
  width: 30vw;
  height: 60%;
  bottom: 0;
  opacity: .2;
  background-image: linear-gradient(rgba(44, 100, 239, .32) 1px, transparent 1px), linear-gradient(90deg, rgba(44, 100, 239, .32) 1px, transparent 1px), linear-gradient(28deg, transparent 49.5%, rgba(44, 100, 239, .38) 50%, transparent 50.5%);
  background-size: 27px 27px, 27px 27px, 90px 90px;
  mask-image: linear-gradient(to top, #000 35%, transparent 100%)
}

.blueprint-left {
  left: 0
}

.blueprint-right {
  right: 0;
  transform: scaleX(-1)
}

.access-shell {
  width: min(100%, 1040px);
  position: relative;
  z-index: 1;
  padding: 34px 42px 26px;
  background: rgba(255, 255, 255, .93);
  border: 1px solid white;
  border-radius: 28px;
  box-shadow: 0 20px 65px rgba(34, 61, 128, .16);
  backdrop-filter: blur(8px)
}

.access-header {
  text-align: center
}

.brand-logo {
  display: block;
  width: min(100%, 390px);
  height: 130px;
  margin: 0 auto 2px
}

.eyebrow {
  margin: 0 0 8px;
  color: #1664df;
  font-size: .78rem;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase
}

.access-header h1 {
  margin: 0;
  font-size: 2.25rem;
  letter-spacing: -.035em
}

.intro {
  max-width: 630px;
  margin: 10px auto 26px;
  color: #58668a;
  line-height: 1.55
}

.access-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px
}

.access-option {
  position: relative;
  min-height: 300px;
  padding: 28px;
  border: 1px solid #dbe2f1;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 9px 25px rgba(40, 69, 140, .07);
  display: flex;
  flex-direction: column
}

.access-option::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 5px;
  border-radius: 20px 20px 0 0
}

.login-option::before {
  background: #0569f5
}

.register-option::before {
  background: linear-gradient(90deg, #4f55ee, #7b21f4)
}

.option-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: #eef5ff;
  color: #075ff2;
  font-size: 1.4rem;
  font-weight: 800
}

.register-option .option-icon {
  background: #f4efff;
  color: #7628e9
}

.option-label {
  margin: 20px 0 6px;
  color: #65739a;
  font-size: .79rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em
}

.access-option h2 {
  margin: 0;
  font-size: 1.65rem
}

.access-option p {
  margin: 10px 0 24px;
  color: #5b688a;
  line-height: 1.55
}

.access-option button {
  width: 100%;
  min-height: 47px;
  margin-top: auto;
  border-radius: 9px;
  font-size: .96rem;
  font-weight: 700;
  cursor: pointer
}

.primary-action {
  border: 0;
  background: linear-gradient(90deg, #0569f5, #365eea);
  color: #fff
}

.secondary-action {
  border: 1px solid #6d39ec;
  background: #fff;
  color: #612edc
}

.access-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 22px;
  color: #627092;
  font-size: .86rem
}

.access-status strong {
  color: #17316f
}

.access-status button {
  border: 0;
  background: transparent;
  color: #075ff2;
  font-weight: 700;
  cursor: pointer
}

@media(max-width:760px) {
  .access-page {
    padding: 14px;
    align-items: start
  }

  .access-shell {
    margin: 12px 0;
    padding: 25px 20px;
    border-radius: 21px
  }

  .brand-logo {
    height: 100px
  }

  .access-header h1 {
    font-size: 1.8rem
  }

  .access-options {
    grid-template-columns: 1fr
  }

  .access-option {
    min-height: 250px
  }

  .blueprint {
    display: none
  }

  .access-status {
    flex-wrap: wrap
  }
}
</style>
