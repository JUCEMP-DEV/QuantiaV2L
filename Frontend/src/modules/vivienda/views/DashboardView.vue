<template>
  <div class="dashboard-page">
    <!-- =====================================================
         TOPBAR
         ===================================================== -->
    <header class="topbar">
      <RouterLink to="/vivienda/landing" class="brand-wrap" aria-label="Ir al inicio de Quantia">
        <LogoQuantia />
      </RouterLink>

      <nav class="topnav" aria-label="Navegación principal">
        <a href="#mis-proyectos" class="topnav-link">Mis proyectos</a>
        <RouterLink to="/vivienda/landing" class="topnav-link">
          Inicio
        </RouterLink>

        <RouterLink to="/vivienda/perfil" class="topnav-link">
          Perfil
        </RouterLink>
      </nav>

      <RouterLink to="/vivienda/perfil" class="user-pill" aria-label="Abrir perfil">
        <span>Mi cuenta</span>

        <strong>{{ userName }}</strong>

        <svg viewBox="0 0 24 24" aria-hidden="true" class="user-chevron">
          <path d="m9 18 6-6-6-6" />
        </svg>
      </RouterLink>
    </header>

    <!-- =====================================================
         CONTENIDO
         ===================================================== -->
    <main class="dashboard-shell">
      <!-- ===================================================
           PANEL PRINCIPAL
           =================================================== -->
      <section class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">
            QUANTIA · VIVIENDA
          </span>

          <h1>Panel principal</h1>

          <p>
            Crea un proyecto de vivienda y avanza desde la información
            inicial hasta el cálculo de cantidades y presupuesto.
          </p>
        </div>

        <div class="hero-actions">
          <RouterLink to="/vivienda/workflow/proyecto-alcance" class="btn btn-primary" @click="startNewProject">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>

            Nuevo proyecto
          </RouterLink>
        </div>
      </section>

      <!-- ===================================================
           NUEVO PROYECTO / FLUJO
           =================================================== -->
      <section class="workflow-section">
        <header class="workflow-header">
          <div class="workflow-heading">
            <span class="section-tag">
              NUEVO PROYECTO
            </span>

            <h2>
              De los datos de tu vivienda al presupuesto
            </h2>

            <p>
              Quantia organiza cada proyecto en seis etapas.
              Primero defines la vivienda y cómo se construirá;
              después puedes utilizar un plano existente o continuar
              directamente con el diseño de la vivienda.
            </p>
          </div>

          <div class="steps-badge">
            <strong>6</strong>
            <span>etapas</span>
          </div>
        </header>

        <!-- =================================================
             SEIS ETAPAS
             ================================================= -->
        <div class="steps-grid">
          <article v-for="step in steps" :key="step.number" class="step-card">
            <header class="step-card-header">
              <div class="step-icon">
                <!-- 01 PROYECTO -->
                <svg v-if="step.icon === 'project'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 21V5a2 2 0 0 1 2-2h8l6 6v12Z" />
                  <path d="M14 3v6h6" />
                  <path d="M8 13h8M8 17h5" />
                </svg>

                <!-- 02 CONSTRUCCIÓN -->
                <svg v-else-if="step.icon === 'construction'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-3 3-3-3Z" />
                  <path d="m15 5 4-4" />
                </svg>

                <!-- 03 PLANOS -->
                <svg v-else-if="step.icon === 'plans'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 3h16v18H4Z" />
                  <path d="M8 7h8M8 11h3M14 11h2M8 15h8" />
                  <path d="M11 11v4" />
                </svg>

                <!-- 04 DISEÑO -->
                <svg v-else-if="step.icon === 'design'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m3 11 9-8 9 8" />
                  <path d="M5 10v11h14V10" />
                  <path d="M9 21v-6h6v6" />
                </svg>

                <!-- 05 CÁLCULO -->
                <svg v-else-if="step.icon === 'calculate'" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="4" y="2" width="16" height="20" rx="2" />
                  <path d="M8 6h8M8 11h2M14 11h2M8 15h2M14 15h2M8 19h2M14 19h2" />
                </svg>

                <!-- 06 PRESUPUESTO -->
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2v20" />
                  <path
                    d="M17 6.5c-1.1-1-2.7-1.5-5-1.5-2.8 0-5 1.4-5 3.5S9 12 12 12s5 1.4 5 3.5S14.8 19 12 19c-2.3 0-4-.6-5-1.7" />
                </svg>
              </div>

              <span class="step-number">
                {{ step.number }}
              </span>
            </header>

            <div class="step-copy">
              <h3>
                {{ step.title }}
              </h3>

              <p>
                {{ step.description }}
              </p>
            </div>

            <footer class="step-footer">
              {{ step.label }}
            </footer>
          </article>
        </div>

        <!-- =================================================
             DOS FORMAS DE CONTINUAR
             ================================================= -->
        <section class="design-options">
          <header class="design-options-heading">
            <span class="section-tag">
              DESPUÉS DE CONFIGURAR EL PROYECTO
            </span>

            <h3>
              Dos formas de continuar con el diseño
            </h3>

            <p>
              Después de definir los datos del proyecto y cómo se construirá,
              puedes elegir la opción que corresponda a la información
              disponible de tu vivienda.
            </p>
          </header>

          <div class="design-options-grid">
            <!-- CON PLANO -->
            <article class="design-option-card">
              <div class="option-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 3h16v18H4Z" />
                  <path d="M8 7h8M8 11h3M14 11h2M8 15h8" />
                  <path d="M11 11v4" />
                </svg>
              </div>

              <div class="option-copy">
                <span class="option-label">
                  OPCIÓN 1
                </span>

                <h4>
                  Ya tengo un plano
                </h4>

                <p>
                  Sube tu plano en PDF o imagen. Quantia analizará la
                  información disponible y generará una propuesta con
                  espacios, medidas y elementos para que puedas revisarla.
                </p>

                <div class="option-route">
                  <span>03</span>
                  Planos y revisión

                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>

                  <span>04</span>
                  Diseño de la vivienda
                </div>
              </div>
            </article>

            <!-- SIN PLANO -->
            <article class="design-option-card">
              <div class="option-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m3 11 9-8 9 8" />
                  <path d="M5 10v11h14V10" />
                  <path d="M9 21v-6h6v6" />
                  <path d="M16.5 4.5 19 7" />
                </svg>
              </div>

              <div class="option-copy">
                <span class="option-label">
                  OPCIÓN 2
                </span>

                <h4>
                  Quiero dibujar la vivienda
                </h4>

                <p>
                  Si no tienes un plano disponible, puedes continuar
                  directamente al diseño y capturar los espacios,
                  dimensiones y elementos de la vivienda manualmente.
                </p>

                <div class="option-route">
                  <span>04</span>
                  Diseño de la vivienda
                </div>
              </div>
            </article>
          </div>
        </section>

        <!-- =================================================
             CÓMO FUNCIONA
             ================================================= -->
        <section class="process-guide">
          <header class="process-heading">
            <span class="section-tag">
              CÓMO FUNCIONA EL PROCESO
            </span>

            <h3>
              La información avanza contigo
            </h3>

            <p>
              Cada etapa utiliza la información confirmada en la anterior.
              De esta forma puedes revisar los datos antes de que Quantia
              los utilice para calcular cantidades y presupuesto.
            </p>
          </header>

          <div class="process-grid">
            <article class="process-item">
              <div class="process-number">
                1
              </div>

              <div class="process-copy">
                <strong>
                  Define el proyecto
                </strong>

                <p>
                  Registra los datos de la vivienda, ubicación, alcance
                  y las condiciones generales de construcción.
                </p>

                <span>
                  Etapas 01 y 02
                </span>
              </div>
            </article>

            <article class="process-item">
              <div class="process-number">
                2
              </div>

              <div class="process-copy">
                <strong>
                  Revisa o captura el diseño
                </strong>

                <p>
                  Utiliza un plano para obtener una propuesta inicial
                  o captura directamente la vivienda. En ambos casos
                  puedes revisar y corregir la información.
                </p>

                <span>
                  Etapas 03 y 04
                </span>
              </div>
            </article>

            <article class="process-item">
              <div class="process-number">
                3
              </div>

              <div class="process-copy">
                <strong>
                  Obtén cantidades y presupuesto
                </strong>

                <p>
                  Con la información validada, Quantia calcula las
                  cantidades de obra e integra los precios y resultados.
                </p>

                <span>
                  Etapas 05 y 06
                </span>
              </div>
            </article>
          </div>

          <div class="process-note">
            <div class="note-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 10v6M12 7h.01" />
              </svg>
            </div>

            <div>
              <strong>
                Tú confirmas la información antes del cálculo
              </strong>

              <p>
                Puedes regresar a los pasos anteriores para revisar o
                corregir datos antes de obtener los resultados definitivos.
              </p>
            </div>
          </div>
        </section>
      </section>
      <SavedProjects />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import SavedProjects from "@/components/design/SavedProjects.vue";
import { RouterLink } from "vue-router";

import LogoQuantia from "@/components/common/LogoQuantia.vue";
import { useAuthStore } from "@/stores/authStore";

const authStore = useAuthStore();
const projectStore = useViviendaStore();
function startNewProject(event) {
  if (!window.confirm('Iniciar un proyecto nuevo reemplazará la sesión actual. Guarda los cambios antes de continuar.')) { event.preventDefault(); return; }
  projectStore.$reset();
}

const steps = [
  {
    number: "01",
    icon: "project",
    title: "Proyecto y alcance",
    label: "Información inicial",
    description:
      "Registra los datos de la vivienda, ubicación y define el alcance de la obra.",
  },
  {
    number: "02",
    icon: "construction",
    title: "Cómo se construirá",
    label: "Configuración",
    description:
      "Define el sistema constructivo y elige si continuarás con un plano o dibujando la vivienda.",
  },
  {
    number: "03",
    icon: "plans",
    title: "Planos y revisión",
    label: "Si ya tienes un plano",
    description:
      "Sube el plano para que Quantia analice y organice la información disponible.",
  },
  {
    number: "04",
    icon: "design",
    title: "Diseño de la vivienda",
    label: "Revisa o dibuja",
    description:
      "Revisa la propuesta obtenida del plano o captura manualmente espacios y elementos.",
  },
  {
    number: "05",
    icon: "calculate",
    title: "Cálculo de cantidades",
    label: "Cuantificación",
    description:
      "Quantia utiliza la información validada para calcular las cantidades necesarias de obra.",
  },
  {
    number: "06",
    icon: "budget",
    title: "Presupuesto y resultados",
    label: "Resultado final",
    description:
      "Integra las cantidades y precios para presentar el presupuesto y sus resultados.",
  },
];

const userName = computed(() => {
  return (
    authStore.user?.nombre ||
    authStore.user?.name ||
    authStore.user?.email ||
    "Usuario"
  );
});
</script>

<style scoped>
/* =========================================================
   PÁGINA
   ========================================================= */

.dashboard-page {
  min-height: 100vh;
  background: #f1f4f9;
  color: #0a2368;
  font-family: Inter, Segoe UI, Arial, sans-serif;
}

/* =========================================================
   TOPBAR
   ========================================================= */

.topbar {
  min-height: 118px;
  display: grid;
  grid-template-columns: 310px 1fr 190px;
  align-items: center;
  gap: 26px;
  padding: 8px 38px;
  background: #ffffff;
  border-bottom: 1px solid #cbd5e5;
}

.brand-wrap {
  width: 285px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  text-decoration: none;
}

.brand-wrap :deep(.logo-quantia) {
  width: 100%;
}

.brand-wrap :deep(img) {
  display: block;
  width: 285px;
  max-width: 285px;
  max-height: 100px;
  object-fit: contain;
  object-position: left center;
}

.topnav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
}

.topnav-link {
  min-height: 42px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  border-radius: 8px;
  color: #526286;
  font-size: 0.88rem;
  font-weight: 650;
  text-decoration: none;
  transition:
    color 0.18s ease,
    background 0.18s ease;
}

.topnav-link:hover {
  color: #075ff2;
  background: #f1f5fc;
}

.topnav-link.router-link-active {
  color: #075ff2;
}

.user-pill {
  min-height: 58px;
  display: grid;
  grid-template-columns: 1fr 18px;
  grid-template-rows: auto auto;
  column-gap: 12px;
  align-items: center;
  padding: 8px 13px 8px 16px;
  border: 1px solid #cbd6e6;
  border-radius: 10px;
  background: #ffffff;
  color: #0a2368;
  text-decoration: none;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.user-pill:hover {
  border-color: #91ace1;
  box-shadow: 0 5px 14px rgba(43, 73, 139, 0.08);
}

.user-pill span {
  grid-column: 1;
  grid-row: 1;
  color: #7b87a7;
  font-size: 0.68rem;
}

.user-pill strong {
  grid-column: 1;
  grid-row: 2;
  max-width: 135px;
  overflow: hidden;
  color: #162d70;
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chevron {
  grid-column: 2;
  grid-row: 1 / 3;
  width: 17px;
  height: 17px;
  fill: none;
  stroke: #075ff2;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* =========================================================
   CONTENEDOR
   ========================================================= */

.dashboard-shell {
  width: 100%;
  max-width: 1380px;
  margin: 0 auto;
  padding: 24px 38px 42px;
}

/* =========================================================
   HERO
   ========================================================= */

.hero-card {
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 34px;
  margin-bottom: 22px;
  padding: 26px 30px;
  border: 1px solid #c3cfe1;
  border-radius: 12px;
  background:
    radial-gradient(circle at 91% 20%,
      rgba(132, 33, 241, 0.08),
      transparent 29%),
    radial-gradient(circle at 76% 100%,
      rgba(7, 95, 242, 0.08),
      transparent 31%),
    #ffffff;
  box-shadow: 0 3px 10px rgba(32, 55, 105, 0.035);
}

.hero-copy {
  max-width: 760px;
}

.eyebrow,
.section-tag {
  display: block;
  margin: 0 0 7px;
  color: #0877ef;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.055em;
}

.hero-copy h1 {
  margin: 0;
  color: #0a2368;
  font-size: 1.75rem;
  line-height: 1.15;
}

.hero-copy p {
  max-width: 700px;
  margin: 8px 0 0;
  color: #637393;
  font-size: 0.91rem;
  line-height: 1.55;
}

.hero-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* =========================================================
   BOTÓN
   ========================================================= */

.btn {
  min-height: 47px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 22px;
  border-radius: 9px;
  font-size: 0.88rem;
  font-weight: 750;
  text-decoration: none;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.btn:hover {
  transform: translateY(-1px);
}

.btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.btn-primary {
  border: 0;
  background: linear-gradient(90deg, #075ff2, #8421f1);
  color: #ffffff;
  box-shadow: 0 7px 17px rgba(51, 69, 211, 0.2);
}

.btn-primary:hover {
  box-shadow: 0 10px 22px rgba(51, 69, 211, 0.26);
}

/* =========================================================
   WORKFLOW PRINCIPAL
   ========================================================= */

.workflow-section {
  padding: 30px;
  border: 1px solid #bcc9dc;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 3px 11px rgba(32, 55, 105, 0.035);
}

.workflow-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 30px;
  margin-bottom: 25px;
}

.workflow-heading {
  max-width: 820px;
}

.workflow-heading h2 {
  margin: 0;
  color: #0a2368;
  font-size: 1.55rem;
}

.workflow-heading p {
  margin: 8px 0 0;
  color: #637393;
  font-size: 0.88rem;
  line-height: 1.55;
}

.steps-badge {
  min-width: 88px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 12px;
  border: 1px solid #c9d5e8;
  border-radius: 9px;
  background: #f1f5fb;
}

.steps-badge strong {
  color: #075ff2;
  font-size: 1rem;
}

.steps-badge span {
  color: #526286;
  font-size: 0.75rem;
  font-weight: 700;
}

/* =========================================================
   TARJETAS DEL WORKFLOW
   ========================================================= */

.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 15px;
}

.step-card {
  position: relative;
  min-height: 205px;
  display: flex;
  flex-direction: column;
  padding: 19px;
  overflow: hidden;
  border: 1px solid #c5d0e1;
  border-radius: 11px;
  background: #ffffff;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.step-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  opacity: 0;
  background: linear-gradient(90deg, #075ff2, #8421f1);
  transition: opacity 0.18s ease;
}

.step-card:hover {
  transform: translateY(-3px);
  border-color: #88a6dc;
  box-shadow: 0 10px 24px rgba(40, 66, 135, 0.1);
}

.step-card:hover::before {
  opacity: 1;
}

.step-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 15px;
}

.step-icon {
  width: 47px;
  height: 47px;
  display: grid;
  place-items: center;
  border: 1px solid #d8e1ef;
  border-radius: 11px;
  background: linear-gradient(135deg, #edf4ff, #f3efff);
  color: #075ff2;
}

.step-icon svg {
  width: 23px;
  height: 23px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.step-number {
  color: #94a7c5;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.09em;
}

.step-copy {
  flex: 1;
}

.step-copy h3 {
  margin: 0;
  color: #162d70;
  font-size: 0.96rem;
}

.step-copy p {
  margin: 7px 0 0;
  color: #667797;
  font-size: 0.79rem;
  line-height: 1.5;
}

.step-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #dbe2ed;
  color: #6e82a5;
  font-size: 0.7rem;
  font-weight: 700;
}

/* =========================================================
   OPCIONES DE DISEÑO
   ========================================================= */

.design-options {
  margin-top: 28px;
  padding: 25px;
  border: 1px solid #bfcce0;
  border-radius: 11px;
  background: #f3f6fb;
}

.design-options-heading {
  max-width: 820px;
  margin-bottom: 20px;
}

.design-options-heading h3 {
  margin: 0;
  color: #162d70;
  font-size: 1.18rem;
}

.design-options-heading p {
  margin: 7px 0 0;
  color: #637393;
  font-size: 0.83rem;
  line-height: 1.5;
}

.design-options-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 15px;
}

.design-option-card {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr);
  gap: 15px;
  min-height: 185px;
  padding: 20px;
  border: 1px solid #c3cfe0;
  border-radius: 10px;
  background: #ffffff;
}

.option-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid #d2deef;
  border-radius: 11px;
  background: linear-gradient(135deg, #edf4ff, #f3efff);
  color: #075ff2;
}

.option-icon svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.option-label {
  display: block;
  margin-bottom: 5px;
  color: #0877ef;
  font-size: 0.67rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.option-copy h4 {
  margin: 0;
  color: #162d70;
  font-size: 0.94rem;
}

.option-copy p {
  margin: 7px 0 14px;
  color: #667797;
  font-size: 0.78rem;
  line-height: 1.5;
}

.option-route {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  padding-top: 12px;
  border-top: 1px solid #dbe3ee;
  color: #52678d;
  font-size: 0.7rem;
  font-weight: 700;
}

.option-route span {
  min-width: 25px;
  height: 25px;
  display: inline-grid;
  place-items: center;
  border-radius: 7px;
  background: #edf4ff;
  color: #075ff2;
  font-size: 0.67rem;
  font-weight: 800;
}

.option-route svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: #075ff2;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* =========================================================
   CÓMO FUNCIONA
   ========================================================= */

.process-guide {
  margin-top: 20px;
  padding: 25px;
  border: 1px solid #bfcad9;
  border-radius: 11px;
  background:
    linear-gradient(135deg,
      #f5f7fb,
      #f7f5fb);
}

.process-heading {
  max-width: 800px;
  margin-bottom: 20px;
}

.process-heading h3 {
  margin: 0;
  color: #162d70;
  font-size: 1.18rem;
}

.process-heading p {
  margin: 7px 0 0;
  color: #637393;
  font-size: 0.83rem;
  line-height: 1.5;
}

.process-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.process-item {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
  padding: 18px;
  border: 1px solid #c6d0df;
  border-radius: 10px;
  background: #ffffff;
}

.process-number {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid #d3deed;
  border-radius: 50%;
  background: #edf4ff;
  color: #075ff2;
  font-weight: 800;
}

.process-copy strong {
  color: #162d70;
  font-size: 0.84rem;
}

.process-copy p {
  margin: 6px 0 9px;
  color: #667797;
  font-size: 0.76rem;
  line-height: 1.5;
}

.process-copy span {
  color: #075ff2;
  font-size: 0.69rem;
  font-weight: 750;
}

.process-note {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-top: 16px;
  padding: 15px 17px;
  border: 1px solid #c9d3e2;
  border-radius: 9px;
  background: #ffffff;
}

.note-icon {
  width: 39px;
  height: 39px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border: 1px solid #d2deed;
  border-radius: 50%;
  background: #edf4ff;
  color: #075ff2;
}

.note-icon svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.process-note strong {
  display: block;
  color: #162d70;
  font-size: 0.82rem;
}

.process-note p {
  margin: 3px 0 0;
  color: #667797;
  font-size: 0.75rem;
  line-height: 1.45;
}

/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 1100px) {
  .topbar {
    grid-template-columns: 250px 1fr 160px;
    padding-left: 24px;
    padding-right: 24px;
  }

  .brand-wrap,
  .brand-wrap :deep(img) {
    width: 235px;
    max-width: 235px;
  }

  .dashboard-shell {
    padding-left: 24px;
    padding-right: 24px;
  }

  .steps-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .process-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .topbar {
    grid-template-columns: 1fr auto;
    gap: 12px;
    padding: 12px 18px;
  }

  .brand-wrap {
    width: 220px;
    height: 80px;
  }

  .brand-wrap :deep(img) {
    width: 220px;
    max-width: 220px;
    max-height: 80px;
  }

  .topnav {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .user-pill {
    grid-column: 2;
    grid-row: 1;
  }

  .hero-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .workflow-header {
    flex-direction: column;
    gap: 14px;
  }

  .design-options-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .topbar {
    display: flex;
    align-items: stretch;
    flex-direction: column;
  }

  .brand-wrap {
    width: 230px;
    margin: auto;
  }

  .brand-wrap :deep(img) {
    width: 230px;
    max-width: 230px;
  }

  .topnav {
    width: 100%;
    justify-content: space-around;
  }

  .topnav-link {
    flex: 1;
    justify-content: center;
  }

  .user-pill {
    width: 100%;
  }

  .dashboard-shell {
    padding: 16px;
  }

  .hero-card {
    padding: 20px;
  }

  .hero-actions {
    width: 100%;
  }

  .hero-actions .btn {
    width: 100%;
  }

  .workflow-section {
    padding: 20px;
  }

  .steps-grid {
    grid-template-columns: 1fr;
  }

  .step-card {
    min-height: auto;
  }

  .design-options,
  .process-guide {
    padding: 18px;
  }

  .design-option-card {
    grid-template-columns: 1fr;
  }

  .process-item {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .process-note {
    align-items: flex-start;
  }
}
</style>