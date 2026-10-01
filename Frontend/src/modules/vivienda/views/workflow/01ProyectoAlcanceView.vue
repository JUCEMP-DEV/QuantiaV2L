<template>
  <QuantiaWorkflowLayout :step="1" title="1. Proyecto y alcance"
    subtitle="Ingresa los datos básicos del proyecto y define el tipo de trabajo que deseas cuantificar y presupuestar.">
    <div class="content-grid">
      <form class="project-form" @submit.prevent="handleContinue">
        <!-- DATOS DEL PROYECTO -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 21V5a2 2 0 0 1 2-2h8l6 6v12Z" />
                <path d="M14 3v6h6" />
                <path d="M8 13h8M8 17h5" />
              </svg>
            </div>

            <div>
              <h2>Datos del proyecto</h2>
              <p>
                Identifica el proyecto y registra a las personas relacionadas.
              </p>
            </div>
          </header>

          <div class="project-row">
            <label class="field project-name">
              Nombre del proyecto *

              <input v-model.trim="form.proyecto.nombre" type="text" placeholder="Ej. Casa habitación — Morelia"
                :class="{ invalid: errors.proyecto }" />

              <span v-if="errors.proyecto" class="field-error">
                {{ errors.proyecto }}
              </span>
            </label>

            <label class="field">
              Folio / referencia

              <input v-model.trim="form.proyecto.folio" type="text" placeholder="QNT-2026-0001" />
            </label>

            <label class="field date-field">
              Fecha

              <input v-model="form.proyecto.fecha" type="date" />
            </label>
          </div>

          <!-- RESPONSABLE / CLIENTE -->
          <div class="people-row">
            <div class="responsible-card">
              <span class="mini-label">
                Responsable de la cotización
              </span>

              <strong>
                {{ form.prestador.nombre || "Sin responsable" }}
              </strong>

              <button type="button" @click="editingResponsible = !editingResponsible">
                {{ editingResponsible ? "Cerrar" : "Editar" }}
              </button>
            </div>

            <div class="client-box">
              <h3>Cliente</h3>

              <div class="client-grid">
                <label class="field">
                  Nombre / razón social *

                  <input v-model.trim="form.cliente.nombre" type="text" placeholder="Nombre del cliente"
                    :class="{ invalid: errors.clienteNombre }" />

                  <span v-if="errors.clienteNombre" class="field-error">
                    {{ errors.clienteNombre }}
                  </span>
                </label>

                <label class="field">
                  Teléfono

                  <input v-model.trim="form.cliente.telefono" type="text" placeholder="Número de contacto" />
                </label>

                <label class="field">
                  Correo

                  <input v-model.trim="form.cliente.correo" type="email" placeholder="cliente@correo.com" />
                </label>
              </div>
            </div>
          </div>

          <div v-if="editingResponsible" class="edit-responsible">
            <label class="field">
              Nombre

              <input v-model.trim="form.prestador.nombre" type="text" />
            </label>

            <label class="field">
              Teléfono

              <input v-model.trim="form.prestador.telefono" type="text" />
            </label>

            <label class="field">
              Profesión

              <input v-model.trim="form.prestador.profesion" type="text" />
            </label>
          </div>
        </section>

        <!-- UBICACIÓN -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
                <circle cx="12" cy="10" r="2.5" />
              </svg>
            </div>

            <div>
              <h2>Ubicación</h2>
              <p>
                Define dónde se encuentra la vivienda que será analizada.
              </p>
            </div>
          </header>

          <div class="location-grid">
            <label class="field">
              Estado *

              <input v-model.trim="form.ubicacion.estado" type="text" placeholder="Michoacán"
                :class="{ invalid: errors.ubicacion }" />
            </label>

            <label class="field">
              Municipio *

              <input v-model.trim="form.ubicacion.municipio" type="text" placeholder="Morelia"
                :class="{ invalid: errors.ubicacion }" />
            </label>

            <label class="field">
              Localidad / colonia

              <input v-model.trim="form.ubicacion.localidad" type="text" placeholder="Localidad o colonia" />
            </label>

            <label class="field full">
              Dirección o referencia

              <input v-model.trim="form.ubicacion.direccion" type="text" placeholder="Calle, número o referencia" />
            </label>
          </div>

          <p v-if="errors.ubicacion" class="error-text">
            {{ errors.ubicacion }}
          </p>
        </section>

        <!-- TIPO DE PROYECTO -->
        <section class="form-section classification-section">
          <header class="section-heading">
            <div class="section-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 4h6v6H4Z" />
                <path d="M14 4h6v6h-6Z" />
                <path d="M4 14h6v6H4Z" />
                <path d="M14 14h6v6h-6Z" />
              </svg>
            </div>

            <div>
              <h2>¿Qué tipo de proyecto vas a realizar?</h2>
              <p>
                Primero selecciona si se trata de una obra nueva o de una
                intervención sobre una vivienda existente.
              </p>
            </div>
          </header>

          <div class="project-type-grid">
            <button type="button" :class="[
              'choice-card',
              { selected: isNewProject },
            ]" @click="selectProjectType('obra_nueva')">
              <span class="radio"></span>

              <div class="choice-copy">
                <strong>Obra nueva</strong>
                <small>
                  Construcción de una vivienda nueva.
                </small>
              </div>
            </button>

            <button type="button" :class="[
              'choice-card',
              { selected: isExistingProject },
            ]" @click="selectProjectType('obra_existente')">
              <span class="radio"></span>

              <div class="choice-copy">
                <strong>Obra existente</strong>
                <small>
                  Remodelación, ampliación o trabajos específicos.
                </small>
              </div>
            </button>
          </div>

          <!-- MODALIDADES -->
          <div class="modality-columns">
            <fieldset :disabled="!isNewProject">
              <legend>
                Modalidades de obra nueva
              </legend>

              <div class="modality-grid three">
                <button v-for="option in newProjectOptions" :key="option.key" type="button" :class="[
                  'modality',
                  {
                    selected:
                      form.alcance === option.key,
                  },
                ]" @click="selectNewModality(option.key)">
                  <span class="radio"></span>
                  {{ option.title }}
                </button>
              </div>
            </fieldset>

            <fieldset :disabled="!isExistingProject">
              <legend>
                Modalidades de obra existente
              </legend>

              <div class="modality-grid three">
                <button type="button" :class="[
                  'modality',
                  {
                    selected:
                      form.tipoIntervencion ===
                      'remodelacion',
                  },
                ]" @click="
                  selectExistingModality(
                    'remodelacion'
                  )
                  ">
                  <span class="radio"></span>
                  Remodelación
                </button>

                <button type="button" :class="[
                  'modality',
                  {
                    selected:
                      form.tipoIntervencion ===
                      'ampliacion',
                  },
                ]" @click="
                  selectExistingModality(
                    'ampliacion'
                  )
                  ">
                  <span class="radio"></span>
                  Ampliación
                </button>

                <button type="button" :class="[
                  'modality',
                  {
                    selected:
                      form.tipoIntervencion ===
                      'complementaria',
                  },
                ]" @click="
                  selectExistingModality(
                    'complementaria'
                  )
                  ">
                  <span class="radio"></span>
                  Por concepto
                </button>
              </div>
            </fieldset>
          </div>

          <p v-if="errors.clasificacion" class="error-text">
            {{ errors.clasificacion }}
          </p>

          <div class="info-note">
            <div class="info-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 10v6M12 7h.01" />
              </svg>
            </div>

            <p>
              Selecciona primero el tipo de proyecto y después la modalidad
              correspondiente. Esta información determinará qué elementos
              debe revisar Quantia en las siguientes etapas.
            </p>
          </div>
        </section>

        <!-- ACCIONES -->
        <div class="bottom-actions">
          <button type="button" class="back-btn" @click="returnToDashboard">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M19 12H5M11 18l-6-6 6-6" />
            </svg>

            Volver al panel
          </button>

          <button type="submit" class="continue-btn">
            Continuar

            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </button>
        </div>
      </form>

      <!-- =================================================
             RESUMEN
             ================================================= -->
      <aside class="summary-panel">
        <header class="summary-heading">
          <div>
            <span class="section-tag">
              RESUMEN
            </span>

            <h2>Resumen del proyecto</h2>
          </div>

          <span class="capture-badge">
            <span></span>
            En captura
          </span>
        </header>

        <h3>
          {{ form.proyecto.nombre || "Proyecto sin nombre" }}
        </h3>

        <dl>
          <div>
            <dt>Tipo de proyecto</dt>
            <dd>{{ projectTypeLabel }}</dd>
          </div>

          <div>
            <dt>Modalidad</dt>
            <dd>{{ modalityLabel }}</dd>
          </div>

          <div>
            <dt>Ubicación</dt>
            <dd>{{ locationLabel }}</dd>
          </div>

          <div>
            <dt>Responsable</dt>
            <dd>
              {{ form.prestador.nombre || "Sin definir" }}
            </dd>
          </div>
        </dl>

        <div class="next-card">
          <div class="next-icon">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </div>

          <div>
            <small>Siguiente etapa</small>

            <strong>
              Cómo se construirá
            </strong>

            <p>
              Definirás sistema constructivo, cimentación, losa,
              instalaciones y la forma de continuar con el diseño.
            </p>
          </div>
        </div>
      </aside>
    </div>
  </QuantiaWorkflowLayout>
</template>

<script setup>
import {
  computed,
  onMounted,
  reactive,
  ref,
} from "vue";
import { useRouter } from "vue-router";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import { useAuthStore } from "@/stores/authStore";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";

import {
  getModulosActivosV4,
  validateSeleccionAlcanceV4,
} from "@/modules/vivienda/services/viviendaService";

const router = useRouter();
const authStore = useAuthStore();
const viviendaStore = useViviendaStore();

const editingResponsible = ref(false);


const today = new Date()
  .toISOString()
  .slice(0, 10);

const savedRegistro =
  viviendaStore.registro || {};

const savedProject =
  savedRegistro.proyecto || {};

const savedLocation =
  savedRegistro.ubicacion || {};

const initialType =
  viviendaStore.clasificacion?.tipoIntervencion ||
  viviendaStore.alcance?.tipoIntervencion ||
  "";

const initialProjectCategory =
  initialType === "obra_nueva"
    ? "obra_nueva"
    : initialType
      ? "obra_existente"
      : "";

const projectCategory = ref(
  initialProjectCategory
);

const form = reactive({
  proyecto: {
    nombre: savedProject.nombre || "",
    folio: savedProject.folio || "",
    fecha: savedProject.fecha || today,
  },

  prestador: {
    nombre:
      savedRegistro.prestador?.nombre ||
      authStore.user?.nombre ||
      "",
    telefono:
      savedRegistro.prestador?.telefono ||
      authStore.user?.telefono ||
      "",
    profesion:
      savedRegistro.prestador?.profesion ||
      authStore.user?.profesion ||
      "",
    alias:
      savedRegistro.prestador?.alias ||
      authStore.user?.alias ||
      "",
  },

  cliente: {
    nombre:
      savedRegistro.cliente?.nombre || "",
    telefono:
      savedRegistro.cliente?.telefono || "",
    correo:
      savedRegistro.cliente?.correo || "",
  },

  ubicacion: {
    estado:
      savedLocation.estado || "Michoacán",

    municipio:
      savedLocation.municipio ||
      savedRegistro.cliente?.ubicacion ||
      "",

    localidad:
      savedLocation.localidad || "",

    direccion:
      savedLocation.direccion || "",
  },

  tipoIntervencion: initialType,

  alcance:
    viviendaStore.alcance?.alcance || "",

  partidasSeleccionadas: [
    ...(
      viviendaStore.alcance
        ?.partidasSeleccionadas || []
    ),
  ],
});

const errors = reactive({
  proyecto: "",
  clienteNombre: "",
  ubicacion: "",
  clasificacion: "",
});

const newProjectOptions = [
  {
    key: "obra_negra",
    title: "Obra negra",
  },
  {
    key: "obra_blanca",
    title: "Obra blanca",
  },
  {
    key: "obra_completa",
    title: "Obra completa",
  },
];

const isNewProject = computed(
  () =>
    projectCategory.value === "obra_nueva"
);

const isExistingProject = computed(
  () =>
    projectCategory.value === "obra_existente"
);

const projectTypeLabel = computed(() => {
  if (isNewProject.value) {
    return "Obra nueva";
  }

  if (isExistingProject.value) {
    return "Obra existente";
  }

  return "Sin definir";
});

const modalityLabel = computed(() => {
  const labels = {
    obra_negra: "Obra negra",
    obra_blanca: "Obra blanca",
    obra_completa: "Obra completa",
    remodelacion: "Remodelación",
    ampliacion: "Ampliación",
    complementaria: "Por concepto",
  };

  return (
    labels[
    isNewProject.value
      ? form.alcance
      : form.tipoIntervencion
    ] || "Sin definir"
  );
});

const locationLabel = computed(
  () =>
    [
      form.ubicacion.municipio,
      form.ubicacion.estado,
    ]
      .filter(Boolean)
      .join(", ") || "Sin definir"
);

function selectProjectType(type) {
  projectCategory.value = type;

  form.tipoIntervencion =
    type === "obra_nueva"
      ? "obra_nueva"
      : "";

  form.alcance = "";
  form.partidasSeleccionadas = [];
}

function selectNewModality(alcance) {
  projectCategory.value = "obra_nueva";
  form.tipoIntervencion = "obra_nueva";
  form.alcance = alcance;
}

function selectExistingModality(tipo) {
  projectCategory.value =
    "obra_existente";

  form.tipoIntervencion = tipo;
  form.alcance = "por_concepto";
  form.partidasSeleccionadas = [];
}

function validateForm() {
  Object.keys(errors).forEach((key) => {
    errors[key] = "";
  });

  if (!form.proyecto.nombre) {
    errors.proyecto =
      "Captura el nombre del proyecto.";
  }

  if (!form.cliente.nombre) {
    errors.clienteNombre =
      "Captura el nombre del cliente.";
  }

  if (
    !form.ubicacion.estado ||
    !form.ubicacion.municipio
  ) {
    errors.ubicacion =
      "Captura estado y municipio.";
  }

  if (
    !form.tipoIntervencion ||
    !form.alcance
  ) {
    errors.clasificacion =
      "Selecciona el tipo de proyecto y su modalidad.";
  }

  if (
    isNewProject.value &&
    form.tipoIntervencion &&
    form.alcance
  ) {
    const result =
      validateSeleccionAlcanceV4({
        tipoIntervencion:
          form.tipoIntervencion,
        alcance: form.alcance,
        partidasSeleccionadas:
          form.partidasSeleccionadas,
      });

    if (!result.valid) {
      errors.clasificacion =
        result.errors.join(" ");
    }
  }

  return !Object.values(errors).some(
    Boolean
  );
}

function persistAll() {
  viviendaStore.setRegistro({
    proyecto: JSON.parse(
      JSON.stringify(form.proyecto)
    ),

    prestador: JSON.parse(
      JSON.stringify(form.prestador)
    ),

    cliente: {
      ...JSON.parse(
        JSON.stringify(form.cliente)
      ),
      ubicacion:
        form.ubicacion.municipio,
    },

    ubicacion: JSON.parse(
      JSON.stringify(form.ubicacion)
    ),

    terminosAceptados:
      savedRegistro.terminosAceptados ??
      false,
  });

  viviendaStore.setClasificacion({
    tipoIntervencion:
      form.tipoIntervencion,
    nivelAcabado: "",
    arquitecturaVersion: "v4",
  });

  const modulosActivos =
    isNewProject.value
      ? getModulosActivosV4({
        tipoIntervencion:
          form.tipoIntervencion,
        alcance: form.alcance,
        partidasSeleccionadas: [],
      })
      : [];

  viviendaStore.setAlcance({
    tipoIntervencion:
      form.tipoIntervencion,

    alcance: form.alcance,

    subalcances: isNewProject.value
      ? [...modulosActivos]
      : [...form.partidasSeleccionadas],

    restricciones: {
      requiereSeleccionManual:
        !isNewProject.value,

      pendienteReclasificacionComplementaria:
        form.tipoIntervencion ===
        "complementaria",
    },

    partidasSeleccionadas: [
      ...form.partidasSeleccionadas,
    ],

    modulosActivos,

    activacionModo:
      isNewProject.value
        ? "automatico_por_alcance"
        : "manual_por_etapas",
  });
}

function returnToDashboard() {
  persistAll();

  router.push("/vivienda/dashboard");
}

function handleContinue() {
  if (!validateForm()) {
    return;
  }

  persistAll();

  router.push(
    "/vivienda/workflow/como-se-construira"
  );
}

onMounted(() => {
  if (
    !viviendaStore.reglasSnapshot.loaded
  ) {
    viviendaStore.loadReglasSnapshot();
  }
});
</script>

<style scoped>
/* =========================================================
   GRID
   ========================================================= */

.content-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1fr) 390px;
  gap: 20px;
}

.project-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* =========================================================
   SECCIONES
   ========================================================= */

.form-section,
.summary-panel {
  border: 1px solid #bcc9dc;
  border-radius: 11px;
  background: #ffffff;
  box-shadow:
    0 3px 10px rgba(32, 55, 105, 0.03);
}

.form-section {
  padding: 20px;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 18px;
}

.section-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border: 1px solid #d2deef;
  border-radius: 10px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.section-icon svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.section-heading h2 {
  margin: 0;
  color: #162d70;
  font-size: 1rem;
}

.section-heading p {
  margin: 3px 0 0;
  color: #7180a2;
  font-size: 0.76rem;
}

/* =========================================================
   CAMPOS
   ========================================================= */

.project-row {
  display: grid;
  grid-template-columns:
    1.55fr 0.95fr 0.72fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #42527f;
  font-size: 0.73rem;
  font-weight: 650;
}

.field input {
  width: 100%;
  height: 43px;
  padding: 0 12px;
  border: 1px solid #c5d0e1;
  border-radius: 8px;
  background: #ffffff;
  color: #162d70;
  font: inherit;
  font-weight: 500;
  transition:
    border-color 0.17s ease,
    box-shadow 0.17s ease;
}

.field input::placeholder {
  color: #9aa7bc;
}

.field input:focus {
  outline: none;
  border-color: #075ff2;
  box-shadow:
    0 0 0 3px rgba(7, 95, 242, 0.11);
}

.field input.invalid {
  border-color: #d83434;
}

.field-error {
  color: #c82727;
  font-size: 0.69rem;
  font-weight: 600;
}

/* =========================================================
   RESPONSABLE / CLIENTE
   ========================================================= */

.people-row {
  display: grid;
  grid-template-columns: 330px 1fr;
  gap: 14px;
  margin-top: 16px;
}

.responsible-card,
.client-box {
  position: relative;
  border: 1px solid #c7d2e2;
  border-radius: 9px;
  background: #ffffff;
}

.responsible-card {
  padding: 15px;
}

.mini-label {
  display: block;
  margin-bottom: 9px;
  color: #74819f;
  font-size: 0.69rem;
}

.responsible-card strong {
  display: block;
  max-width: calc(100% - 70px);
  color: #162d70;
  font-size: 0.87rem;
}

.responsible-card button {
  position: absolute;
  right: 14px;
  bottom: 13px;
  border: 0;
  background: transparent;
  color: #075ff2;
  font-size: 0.75rem;
  font-weight: 750;
  cursor: pointer;
}

.client-box {
  padding: 15px;
}

.client-box h3 {
  margin: 0 0 12px;
  color: #162d70;
  font-size: 0.82rem;
}

.client-grid {
  display: grid;
  grid-template-columns:
    1.1fr 1fr 1.1fr;
  gap: 10px;
}

.edit-responsible {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 10px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid #cbd6e6;
  border-radius: 9px;
  background: #f3f6fb;
}

/* =========================================================
   UBICACIÓN
   ========================================================= */

.location-grid {
  display: grid;
  grid-template-columns:
    repeat(3, 1fr);
  gap: 10px;
}

.location-grid .full {
  grid-column: 1 / -1;
}

/* =========================================================
   TIPO DE PROYECTO
   ========================================================= */

.project-type-grid {
  display: grid;
  grid-template-columns:
    repeat(2, 1fr);
  gap: 14px;
}

.choice-card {
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 13px;
  padding: 14px 16px;
  border: 1px solid #c5d0e1;
  border-radius: 10px;
  background: #ffffff;
  color: #1b3273;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.choice-card:hover {
  transform: translateY(-1px);
  border-color: #9db4dd;
  box-shadow:
    0 6px 15px rgba(44, 69, 126, 0.06);
}

.choice-card.selected {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f4f8ff,
      #f8f5ff);
  box-shadow:
    0 0 0 1px rgba(7, 95, 242, 0.15);
}

.choice-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.choice-copy strong {
  color: #162d70;
  font-size: 0.84rem;
}

.choice-copy small {
  color: #7180a2;
  font-size: 0.69rem;
  line-height: 1.35;
}

.radio {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border: 2px solid #9eabc7;
  border-radius: 50%;
}

.selected .radio {
  border: 5px solid #075ff2;
}

/* =========================================================
   MODALIDADES
   ========================================================= */

.modality-columns {
  display: grid;
  grid-template-columns:
    1fr 1fr;
  gap: 14px;
  margin-top: 15px;
}

.modality-columns fieldset {
  margin: 0;
  padding: 13px;
  border: 1px solid #c5d0e1;
  border-radius: 10px;
  background: #fbfcfe;
}

.modality-columns fieldset:disabled {
  opacity: 0.46;
}

.modality-columns legend {
  padding: 0 7px;
  color: #657699;
  font-size: 0.7rem;
  font-weight: 700;
}

.modality-grid {
  display: grid;
  gap: 8px;
}

.modality-grid.three {
  grid-template-columns:
    repeat(3, 1fr);
}

.modality {
  min-height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 7px;
  border: 1px solid #c7d2e2;
  border-radius: 8px;
  background: #ffffff;
  color: #1b3273;
  font-size: 0.72rem;
  font-weight: 650;
  cursor: pointer;
}

.modality:hover:not(:disabled) {
  border-color: #9db4dd;
}

.modality.selected {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f4f8ff,
      #f8f5ff);
}

.modality .radio {
  width: 16px;
  height: 16px;
}

.modality.selected .radio {
  border: 4px solid #075ff2;
}

/* =========================================================
   NOTAS / ERRORES
   ========================================================= */

.info-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 13px;
  padding: 12px 13px;
  border: 1px solid #cbd6e6;
  border-radius: 9px;
  background: #f3f6fb;
}

.info-icon {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #edf4ff;
  color: #075ff2;
}

.info-icon svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.info-note p {
  margin: 0;
  color: #667797;
  font-size: 0.73rem;
  line-height: 1.45;
}

.error-text {
  margin: 9px 0 0;
  color: #c82727;
  font-size: 0.74rem;
}

/* =========================================================
   ACCIONES
   ========================================================= */

.bottom-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 4px 0 0;
}

.back-btn,
.continue-btn {
  min-height: 47px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 24px;
  border-radius: 9px;
  font-size: 0.86rem;
  font-weight: 750;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.back-btn:hover,
.continue-btn:hover {
  transform: translateY(-1px);
}

.back-btn {
  border: 1px solid #aebed5;
  background: #ffffff;
  color: #52678d;
}

.back-btn:hover {
  border-color: #075ff2;
  color: #075ff2;
}

.back-btn svg,
.continue-btn svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.continue-btn {
  min-width: 210px;
  border: 0;
  background:
    linear-gradient(90deg,
      #075ff2,
      #8421f1);
  color: #ffffff;
  box-shadow:
    0 7px 17px rgba(51, 69, 211, 0.2);
}

.continue-btn svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* =========================================================
   RESUMEN
   ========================================================= */

.summary-panel {
  position: sticky;
  top: 18px;
  align-self: start;
  min-height: 590px;
  padding: 20px;
}

.summary-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid #d4ddea;
}

.summary-heading h2 {
  margin: 0;
  color: #162d70;
  font-size: 1rem;
}

.capture-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 7px 10px;
  border: 1px solid #d2def0;
  border-radius: 8px;
  background: #f1f5fb;
  color: #075ff2;
  font-size: 0.7rem;
  font-weight: 700;
}

.capture-badge>span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #075ff2;
}

.summary-panel>h3 {
  margin: 18px 0 17px;
  color: #0a2368;
  font-size: 1.1rem;
}

.summary-panel dl {
  margin: 0;
}

.summary-panel dl>div {
  padding: 13px 0;
  border-bottom: 1px solid #e0e6ef;
}

.summary-panel dt {
  color: #7b87a7;
  font-size: 0.7rem;
}

.summary-panel dd {
  margin: 5px 0 0;
  color: #162d70;
  font-size: 0.86rem;
  font-weight: 750;
}

/* =========================================================
   SIGUIENTE
   ========================================================= */

.next-card {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-top: 22px;
  padding: 18px 15px;
  border: 1px solid #c9d4e6;
  border-radius: 10px;
  background:
    linear-gradient(135deg,
      #f2f6ff,
      #f7f4ff);
}

.next-icon {
  width: 39px;
  height: 39px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #eaf1ff;
  color: #075ff2;
}

.next-icon svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.next-card div:last-child {
  display: flex;
  flex-direction: column;
}

.next-card small {
  color: #7180a2;
  font-size: 0.69rem;
}

.next-card strong {
  margin: 4px 0 5px;
  color: #075ff2;
  font-size: 0.84rem;
}

.next-card p {
  margin: 0;
  color: #5e7093;
  font-size: 0.74rem;
  line-height: 1.45;
}

/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 1100px) {


  .content-grid {
    grid-template-columns: 1fr;
  }

  .summary-panel {
    position: static;
    min-height: auto;
  }


  .people-row {
    grid-template-columns: 1fr;
  }

  .client-grid {
    grid-template-columns:
      1fr 1fr;
  }
}

@media (max-width: 760px) {


  .project-row,
  .client-grid,
  .location-grid,
  .modality-columns,
  .edit-responsible {
    grid-template-columns: 1fr;
  }

  .location-grid .full {
    grid-column: auto;
  }

  .project-type-grid {
    grid-template-columns: 1fr;
  }

  .modality-grid.three {
    grid-template-columns: 1fr;
  }

  .bottom-actions {
    gap: 10px;
  }

  .back-btn,
  .continue-btn {
    width: 50%;
    min-width: 0;
    padding: 0 10px;
  }
}

@media (max-width: 520px) {

  .form-section,
  .summary-panel {
    padding: 18px;
  }

  .bottom-actions {
    flex-direction: column;
  }

  .draft-btn,
  .continue-btn {
    width: 100%;
  }
}
</style>