<template>
  <QuantiaWorkflowLayout :step="2" title="2. Cómo se construirá"
    subtitle="Define las condiciones del terreno, sistema constructivo, cimentación, losa e instalaciones. Al final podrás elegir si continuarás desde un plano o dibujando la vivienda.">
    <div class="content-grid">
      <!-- =================================================
             FORMULARIO
             ================================================= -->
      <form class="configuration-form" @submit.prevent="continueFlow">
        <!-- =================================================
               01 CONDICIONES DEL PROYECTO
               ================================================= -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="mountain" :size="23" />
            </div>

            <div>
              <span class="section-number">
                01
              </span>

              <h2>Condiciones del proyecto</h2>

              <p>
                Define las características actuales del terreno
                y las condiciones de acceso al sitio.
              </p>
            </div>
          </header>

          <div class="condition-grid">
            <!-- TOPOGRAFÍA -->
            <fieldset class="setting-block">
              <legend>Topografía del terreno</legend>

              <div class="option-grid three">
                <button v-for="item in topographyOptions" :key="item.value" type="button" class="choice-card compact"
                  :class="{
                    selected:
                      form.topografia === item.value,
                  }" @click="selectTopography(item.value)">
                  <span class="selection-mark">
                    <QuantiaIcon v-if="
                      form.topografia === item.value
                    " name="check" :size="11" :stroke-width="2.6" />
                  </span>

                  <span class="choice-icon">
                    <QuantiaIcon :name="item.icon" :size="23" />
                  </span>

                  <strong>{{ item.label }}</strong>
                </button>
              </div>

              <div v-if="
                form.topografia === 'con_pendiente'
              " class="configuration-detail">
                <label for="pendienteProfundidadM">
                  Profundidad o desnivel de referencia
                </label>

                <div class="input-with-unit">
                  <input id="pendienteProfundidadM" v-model="form.pendienteProfundidadM
                    " type="number" min="0.01" step="0.01" placeholder="Ej. 0.30" @input="markPending" />

                  <span>m</span>
                </div>
              </div>
            </fieldset>

            <!-- CONDICIÓN DEL TERRENO -->
            <fieldset class="setting-block">
              <legend>
                Condición actual del terreno
              </legend>

              <div class="option-grid terrain">
                <button v-for="item in terrainOptions" :key="item.value" type="button"
                  class="choice-card compact terrain-option" :class="{
                    selected:
                      form.condicionTerreno ===
                      item.value,
                  }" @click="
                    form.condicionTerreno =
                    item.value;
                  markPending();
                  ">
                  <span class="selection-mark">
                    <QuantiaIcon v-if="
                      form.condicionTerreno ===
                      item.value
                    " name="check" :size="11" :stroke-width="2.6" />
                  </span>

                  <span class="choice-icon">
                    <QuantiaIcon :name="item.icon" :size="21" />
                  </span>

                  <strong>{{ item.label }}</strong>
                </button>
              </div>
            </fieldset>

            <!-- DEMOLICIÓN -->
            <section v-if="showDemolitionBlock" class="demolition-panel">
              <header class="subsection-heading">
                <div class="subsection-title-row">
                  <div class="subsection-icon">
                    <QuantiaIcon name="trash" :size="20" />
                  </div>

                  <div>
                    <span class="subsection-tag">
                      CONSTRUCCIÓN EXISTENTE
                    </span>

                    <h3>Demolición</h3>
                  </div>
                </div>

                <p>
                  Captura los datos generales de la
                  construcción que deberá retirarse.
                </p>
              </header>

              <div class="demolition-grid">
                <label class="field">
                  Tipo de demolición

                  <select v-model="form.demolicion
                    .tipoDemolicion
                    " @change="markPending">
                    <option value="">
                      Selecciona
                    </option>

                    <option value="manual">
                      Manual
                    </option>

                    <option value="mecanica">
                      Mecánica
                    </option>
                  </select>
                </label>

                <label class="field">
                  Estructura existente

                  <select v-model="form.demolicion
                    .tipoEstructuraExistente
                    " @change="markPending">
                    <option value="">
                      Selecciona
                    </option>

                    <option value="precaria">
                      Precaria / mampostería
                    </option>

                    <option value="construccion_previa">
                      Concreto y muros existentes
                    </option>
                  </select>
                </label>

                <label class="field">
                  Niveles existentes

                  <input v-model="form.demolicion
                    .nivelesExistentes
                    " type="number" min="1" @input="markPending" />
                </label>

                <label class="field">
                  Ancho

                  <div class="input-with-unit">
                    <input v-model="form.demolicion
                      .anchoDemolicionM
                      " type="number" min="0" step="0.01" @input="markPending" />

                    <span>m</span>
                  </div>
                </label>

                <label class="field">
                  Largo

                  <div class="input-with-unit">
                    <input v-model="form.demolicion
                      .largoDemolicionM
                      " type="number" min="0" step="0.01" @input="markPending" />

                    <span>m</span>
                  </div>
                </label>

                <label class="field">
                  Área estimada

                  <div class="calculated-field">
                    {{
                      areaDemolicionCalculada.toFixed(
                        2
                      )
                    }}
                    m²
                  </div>
                </label>
              </div>
            </section>

            <!-- ACCESO -->
            <fieldset class="setting-block access-block">
              <legend>Acceso al sitio</legend>

              <div class="option-grid two">
                <button v-for="item in accessOptions" :key="item.value" type="button" class="choice-card compact"
                  :class="{
                    selected:
                      form.tipoAcceso === item.value,
                  }" @click="
                    form.tipoAcceso = item.value;
                  markPending();
                  ">
                  <span class="selection-mark">
                    <QuantiaIcon v-if="
                      form.tipoAcceso === item.value
                    " name="check" :size="11" :stroke-width="2.6" />
                  </span>

                  <span class="choice-icon">
                    <QuantiaIcon :name="item.icon" :size="22" />
                  </span>

                  <strong>{{ item.label }}</strong>
                </button>
              </div>
            </fieldset>
          </div>
        </section>

        <!-- =================================================
               02 SISTEMA CONSTRUCTIVO
               ================================================= -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="construction" :size="23" />
            </div>

            <div>
              <span class="section-number">
                02
              </span>

              <h2>Sistema constructivo</h2>

              <p>
                Selecciona el sistema estructural principal
                previsto para la vivienda.
              </p>
            </div>
          </header>

          <div class="option-grid three wide">
            <button v-for="item in structuralOptions" :key="item.value" type="button" class="choice-card descriptive"
              :class="{
                selected:
                  form.sistemaEstructural ===
                  item.value,
              }" @click="selectStructural(item.value)">
              <span class="selection-mark">
                <QuantiaIcon v-if="
                  form.sistemaEstructural ===
                  item.value
                " name="check" :size="11" :stroke-width="2.6" />
              </span>

              <span class="technical-icon">
                <QuantiaIcon :name="item.icon" :size="27" />
              </span>

              <strong>{{ item.label }}</strong>

              <small>
                {{ item.description }}
              </small>
            </button>
          </div>
        </section>

        <!-- =================================================
               03 CIMENTACIÓN
               ================================================= -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="layers" :size="23" />
            </div>

            <div>
              <span class="section-number">
                03
              </span>

              <h2>Cimentación</h2>

              <p>
                Define el tipo de cimentación considerado
                para el proyecto.
              </p>
            </div>
          </header>

          <div class="option-grid four wide">
            <button v-for="item in foundationOptions" :key="item.value" type="button"
              class="choice-card foundation-card" :class="{
                selected:
                  form.tipoCimentacion ===
                  item.value,
              }" @click="
                form.tipoCimentacion = item.value;
              markPending();
              ">
              <span class="selection-mark">
                <QuantiaIcon v-if="
                  form.tipoCimentacion ===
                  item.value
                " name="check" :size="11" :stroke-width="2.6" />
              </span>

              <span class="technical-icon">
                <QuantiaIcon :name="item.icon" :size="27" />
              </span>

              <strong>{{ item.label }}</strong>
            </button>
          </div>
        </section>

        <!-- =================================================
               04 LOSA
               ================================================= -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="layers" :size="23" />
            </div>

            <div>
              <span class="section-number">
                04
              </span>

              <h2>Tipo de losa</h2>

              <p>
                Selecciona el sistema de losa previsto
                para la vivienda.
              </p>
            </div>
          </header>

          <div class="option-grid three wide">
            <button v-for="item in slabOptions" :key="item.value" type="button" class="choice-card slab-card" :class="{
              selected:
                form.tipoLosa === item.value,
            }" @click="
              form.tipoLosa = item.value;
            markPending();
            ">
              <span class="selection-mark">
                <QuantiaIcon v-if="
                  form.tipoLosa === item.value
                " name="check" :size="11" :stroke-width="2.6" />
              </span>

              <span class="technical-icon">
                <QuantiaIcon :name="item.icon" :size="27" />
              </span>

              <strong>{{ item.label }}</strong>
            </button>
          </div>
        </section>

        <!-- =================================================
               05 INSTALACIONES
               ================================================= -->
        <section class="form-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="zap" :size="23" />
            </div>

            <div>
              <span class="section-number">
                05
              </span>

              <h2>Instalaciones</h2>

              <p>
                Indica qué sistemas tendrá la vivienda.
                Cada opción puede definirse como Sí,
                No o Por definir.
              </p>
            </div>
          </header>

          <div class="installation-grid">
            <button v-for="item in installationOptions" :key="item.value" type="button" class="installation-card"
              :class="{
                yes:
                  form.instalaciones[
                  item.value
                  ] === true,

                no:
                  form.instalaciones[
                  item.value
                  ] === false,
              }" @click="
                toggleInstallation(item.value)
                ">
              <span class="installation-icon">
                <QuantiaIcon :name="item.icon" :size="25" />
              </span>

              <strong>{{ item.label }}</strong>

              <span class="installation-status" :class="{
                defined:
                  form.instalaciones[
                  item.value
                  ] !== null,
              }">
                {{
                  installationStatus(
                    form.instalaciones[item.value]
                  )
                }}
              </span>
            </button>
          </div>

          <div class="installation-note">
            <QuantiaIcon name="info" :size="15" />

            <span>
              Selecciona cada tarjeta para cambiar entre
              <strong>Sí</strong>,
              <strong>No</strong> y
              <strong>Por definir</strong>.
            </span>
          </div>
        </section>

        <!-- =================================================
               06 DISEÑO
               ================================================= -->
        <section class="form-section design-section">
          <header class="section-heading">
            <div class="section-icon">
              <QuantiaIcon name="home" :size="23" />
            </div>

            <div>
              <span class="section-number">
                06
              </span>

              <h2>Diseño de la vivienda</h2>

              <p>
                Elige cómo quieres proporcionar la
                información espacial de la vivienda.
              </p>
            </div>
          </header>

          <div class="design-options">
            <button v-for="item in designOptions" :key="item.value" type="button" class="design-card" :class="{
              selected:
                form.modoDiseno === item.value,
            }" @click="
              form.modoDiseno = item.value;
            markPending();
            ">
              <div class="design-icon">
                <QuantiaIcon :name="item.icon" :size="31" />
              </div>

              <div class="design-copy">
                <span class="option-label">
                  {{
                    item.value === "subir_plano"
                      ? "OPCIÓN 1"
                      : "OPCIÓN 2"
                  }}
                </span>

                <strong>{{ item.label }}</strong>

                <p>{{ item.description }}</p>

                <small>
                  {{
                    item.value === "subir_plano"
                      ? "Continuarás a Planos y revisión"
                      : "Continuarás directamente al Diseño de la vivienda"
                  }}
                </small>
              </div>

              <span class="design-radio"></span>
            </button>
          </div>
        </section>

        <!-- ERROR -->
        <p v-if="error" class="error-message">
          {{ error }}
        </p>

        <!-- =================================================
               ACCIONES
               ================================================= -->
        <footer class="bottom-actions">
          <button type="button" class="back-btn" @click="goBack">
            <QuantiaIcon name="arrow-left" :size="17" :stroke-width="2" />

            Anterior
          </button>

          <div class="right-actions">
            <button type="button" class="save-btn" @click="saveDraft">
              <QuantiaIcon name="save" :size="17" />

              Guardar cambios
            </button>

            <button type="submit" class="continue-btn">
              <span>
                Continuar

                <small>
                  {{ nextStepLabel }}
                </small>
              </span>

              <QuantiaIcon name="arrow-right" :size="17" :stroke-width="2" />
            </button>
          </div>
        </footer>
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

            <h2>Configuración del proyecto</h2>
          </div>

          <span class="capture-badge">
            <span></span>
            En configuración
          </span>
        </header>

        <div class="summary-list">
          <div class="summary-item">
            <dt>Topografía</dt>
            <dd>{{ topographyLabel }}</dd>
          </div>

          <div class="summary-item">
            <dt>Condición del terreno</dt>
            <dd>{{ terrainLabel }}</dd>
          </div>

          <div class="summary-item">
            <dt>Acceso</dt>
            <dd>{{ accessLabel }}</dd>
          </div>

          <div class="summary-item">
            <dt>Sistema constructivo</dt>

            <dd>
              {{ structuralLabel }}

              <small>
                {{ structuralNote }}
              </small>
            </dd>
          </div>

          <div class="summary-item">
            <dt>Cimentación</dt>
            <dd>{{ foundationLabel }}</dd>
          </div>

          <div class="summary-item">
            <dt>Tipo de losa</dt>
            <dd>{{ slabLabel }}</dd>
          </div>

          <div class="summary-item">
            <dt>Instalaciones</dt>

            <dd>
              {{ definedInstallations }} de 5
              definidas
            </dd>
          </div>

          <div class="summary-item">
            <dt>Diseño</dt>
            <dd>{{ designLabel }}</dd>
          </div>
        </div>

        <div class="next-card">
          <div class="next-icon">
            <QuantiaIcon name="arrow-right" :size="18" />
          </div>

          <div>
            <small>Siguiente etapa</small>

            <strong>
              {{ nextStepLabel }}
            </strong>

            <p v-if="
              form.modoDiseno === 'subir_plano'
            ">
              Cargarás el plano para iniciar su
              revisión y análisis.
            </p>

            <p v-else-if="
              form.modoDiseno === 'dibujar'
            ">
              Continuarás directamente a la captura
              y definición espacial de la vivienda.
            </p>

            <p v-else>
              Selecciona cómo quieres continuar con
              el diseño de la vivienda.
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
  reactive,
  ref,
} from "vue";

import { useRouter } from "vue-router";

import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import QuantiaIcon from "@/components/common/QuantiaIcon.vue";

import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";

const router = useRouter();
const viviendaStore = useViviendaStore();

const storedPreliminares =
  viviendaStore.preliminares || {};

const storedGeneral =
  viviendaStore.datosGeneralesObra || {};

const storedInstallations =
  viviendaStore.modulos?.instalaciones
    ?.controles?.serviciosInstalaciones || {};

const form = reactive({
  topografia:
    storedPreliminares.topografia || "",

  pendienteProfundidadM:
    storedPreliminares.pendienteProfundidadM ||
    "",

  tipoAcceso:
    storedPreliminares.tipoAcceso || "",

  condicionTerreno:
    storedPreliminares.condicionTerreno || "",

  sistemaEstructural:
    storedGeneral.sistemaEstructural || "",

  tipoCimentacion:
    storedGeneral.tipoCimentacion || "",

  tipoLosa:
    storedGeneral.tipoLosa ||
    storedGeneral.engineInputs?.tipo_losa ||
    "",

  modoDiseno:
    storedGeneral.engineInputs?.modo_diseno ||
    "",

  demolicion: {
    tipoDemolicion:
      storedPreliminares.demolicion
        ?.tipoDemolicion || "",

    tipoEstructuraExistente:
      storedPreliminares.demolicion
        ?.tipoEstructuraExistente || "",

    nivelesExistentes:
      storedPreliminares.demolicion
        ?.nivelesExistentes || "",

    anchoDemolicionM:
      storedPreliminares.demolicion
        ?.anchoDemolicionM || "",

    largoDemolicionM:
      storedPreliminares.demolicion
        ?.largoDemolicionM || "",
  },

  instalaciones: {
    agua:
      storedInstallations.agua ??
      storedPreliminares.servicios?.agua ??
      null,

    drenaje:
      storedInstallations.drenaje ??
      storedPreliminares.servicios?.drenaje ??
      null,

    energia:
      storedInstallations.energia ??
      storedPreliminares.servicios?.energia ??
      null,

    gas:
      storedInstallations.gas ??
      storedPreliminares
        .configuracionInicial?.instalaciones
        ?.gas ??
      null,

    telecomunicaciones:
      storedInstallations.telecomunicaciones ??
      storedPreliminares
        .configuracionInicial?.instalaciones
        ?.telecomunicaciones ??
      null,
  },
});

const error = ref("");

const saveStatus = ref(
  "Configuración cargada"
);

const saveDetail = ref(
  "Sin cambios pendientes"
);

/* =========================================================
   OPCIONES
   ========================================================= */

const topographyOptions = [
  {
    value: "plana",
    label: "Regular",
    icon: "terrain-flat",
  },
  {
    value: "con_pendiente",
    label: "Con desnivel",
    icon: "terrain-slope",
  },
  {
    value: "por_definir",
    label: "No sé",
    icon: "help",
  },
];

const terrainOptions = [
  {
    value: "limpio",
    label: "Limpio",
    icon: "terrain-clean",
  },
  {
    value: "con_malezas",
    label: "Con malezas",
    icon: "terrain-vegetation",
  },
  {
    value: "con_construccion_previa",
    label: "Con construcción existente",
    icon: "building",
  },
  {
    value: "con_escombro",
    label: "Con escombro",
    icon: "rubble",
  },
  {
    value: "mixto",
    label: "Mixto",
    icon: "terrain-mixed",
  },
];

const accessOptions = [
  {
    value: "facil",
    label: "Acceso normal",
    icon: "access-normal",
  },
  {
    value: "dificil",
    label: "Acceso limitado",
    icon: "access-limited",
  },
];

const structuralOptions = [
  {
    value: "tradicional",
    label: "Mampostería",
    description:
      "Muros de carga como sistema principal.",
    icon: "masonry",
  },
  {
    value: "concreto_reforzado",
    label: "Concreto armado",
    description:
      "Elementos estructurales principales de concreto.",
    icon: "reinforced-concrete",
  },
  {
    value: "mixta",
    label: "Mixto",
    description:
      "Combinación de mampostería y concreto armado.",
    icon: "mixed-structure",
  },
];

const foundationOptions = [
  {
    value: "mamposteria_corrida",
    label: "Mampostería corrida",
    icon: "masonry-foundation",
  },
  {
    value: "zapata_corrida",
    label: "Zapata corrida",
    icon: "strip-footing",
  },
  {
    value: "zapata_aislada_trabe_liga",
    label: "Zapata aislada + trabe de liga",
    icon: "isolated-footing-beam",
  },
  {
    value: "por_definir",
    label: "No sé / Por definir",
    icon: "help",
  },
];

const slabOptions = [
  {
    value: "maciza",
    label: "Losa maciza",
    icon: "solid-slab",
  },
  {
    value: "vigueta_bovedilla",
    label: "Vigueta y bovedilla",
    icon: "joist-block-slab",
  },
  {
    value: "aligerada_caseton_nervaduras",
    label: "Casetón y nervaduras",
    icon: "waffle-slab",
  },
];

const installationOptions = [
  {
    value: "agua",
    label: "Hidráulica",
    icon: "droplets",
  },
  {
    value: "drenaje",
    label: "Sanitaria",
    icon: "sanitary",
  },
  {
    value: "energia",
    label: "Eléctrica",
    icon: "zap",
  },
  {
    value: "gas",
    label: "Gas",
    icon: "flame",
  },
  {
    value: "telecomunicaciones",
    label: "TV y voz",
    icon: "wifi",
  },
];

const designOptions = [
  {
    value: "subir_plano",
    label: "Sube el plano",
    icon: "upload",
    description:
      "Carga tu plano en PDF, DWG o imagen. Quantia analizará la información disponible y preparará una propuesta para su revisión.",
  },
  {
    value: "dibujar",
    label: "Dibújalo tú",
    icon: "pencil",
    description:
      "Captura la vivienda directamente en Quantia definiendo espacios, medidas y elementos de forma manual.",
  },
];

/* =========================================================
   COMPUTED
   ========================================================= */

const nextStepLabel = computed(() => {
  if (form.modoDiseno === "dibujar") {
    return "Diseño de la vivienda";
  }

  if (form.modoDiseno === "subir_plano") {
    return "Planos y revisión";
  }

  return "Selecciona cómo continuar";
});

const topographyLabel = computed(
  () =>
    topographyOptions.find(
      (item) =>
        item.value === form.topografia
    )?.label || "Pendiente"
);

const accessLabel = computed(
  () =>
    accessOptions.find(
      (item) =>
        item.value === form.tipoAcceso
    )?.label || "Pendiente"
);

const terrainLabel = computed(
  () =>
    terrainOptions.find(
      (item) =>
        item.value === form.condicionTerreno
    )?.label || "Pendiente"
);

const structuralLabel = computed(
  () =>
    structuralOptions.find(
      (item) =>
        item.value ===
        form.sistemaEstructural
    )?.label || "Pendiente"
);

const structuralNote = computed(() => {
  if (
    form.sistemaEstructural ===
    "tradicional"
  ) {
    return "Muros de carga";
  }

  if (
    form.sistemaEstructural ===
    "concreto_reforzado"
  ) {
    return "Marcos de concreto";
  }

  if (
    form.sistemaEstructural === "mixta"
  ) {
    return "Sistema combinado";
  }

  return "Sin definir";
});

const foundationLabel = computed(
  () =>
    foundationOptions.find(
      (item) =>
        item.value ===
        form.tipoCimentacion
    )?.label || "Pendiente"
);

const slabLabel = computed(
  () =>
    slabOptions.find(
      (item) =>
        item.value === form.tipoLosa
    )?.label || "Pendiente"
);

const showDemolitionBlock = computed(
  () =>
    form.condicionTerreno ===
    "con_construccion_previa"
);

const areaDemolicionCalculada =
  computed(() => {
    const ancho = Number(
      form.demolicion.anchoDemolicionM || 0
    );

    const largo = Number(
      form.demolicion.largoDemolicionM || 0
    );

    if (ancho <= 0 || largo <= 0) {
      return 0;
    }

    return Number(
      (ancho * largo).toFixed(2)
    );
  });

const definedInstallations = computed(
  () =>
    Object.values(
      form.instalaciones
    ).filter(
      (value) => value !== null
    ).length
);

const designLabel = computed(
  () =>
    designOptions.find(
      (item) =>
        item.value === form.modoDiseno
    )?.label || "Pendiente"
);

/* =========================================================
   ACCIONES
   ========================================================= */

function markPending() {
  saveStatus.value =
    "Cambios sin guardar";

  saveDetail.value =
    "Guarda los cambios para conservarlos";
}

function selectTopography(value) {
  form.topografia = value;

  if (value !== "con_pendiente") {
    form.pendienteProfundidadM = "";
  }

  markPending();
}

function selectStructural(value) {
  form.sistemaEstructural = value;
  markPending();
}

function toggleInstallation(key) {
  const current =
    form.instalaciones[key];

  if (current === null) {
    form.instalaciones[key] = true;
  } else if (current === true) {
    form.instalaciones[key] = false;
  } else {
    form.instalaciones[key] = null;
  }

  markPending();
}

function installationStatus(value) {
  if (value === true) {
    return "Sí";
  }

  if (value === false) {
    return "No";
  }

  return "Por definir";
}

/* =========================================================
   PERSISTENCIA
   ========================================================= */

function persistConfiguration() {
  const previousEngineInputs =
    storedGeneral.engineInputs || {};

  const normalizedFoundation =
    form.tipoCimentacion === "por_definir"
      ? ""
      : form.tipoCimentacion;

  viviendaStore.setDatosGeneralesObra({
    ...JSON.parse(
      JSON.stringify(storedGeneral)
    ),

    sistemaEstructural:
      form.sistemaEstructural,

    tipoCimentacion:
      normalizedFoundation,

    tipoLosa: form.tipoLosa,

    engineInputs: {
      ...JSON.parse(
        JSON.stringify(
          previousEngineInputs
        )
      ),

      sistema_estructural:
        form.sistemaEstructural,

      tipo_cimentacion:
        normalizedFoundation,

      tipo_losa:
        form.tipoLosa,

      modo_diseno:
        form.modoDiseno,

      servicios_instalaciones:
        JSON.parse(
          JSON.stringify(
            form.instalaciones
          )
        ),
    },
  });

  viviendaStore.setPreliminares({
    ...JSON.parse(
      JSON.stringify(
        storedPreliminares
      )
    ),

    topografia:
      form.topografia === "por_definir"
        ? ""
        : form.topografia,

    topografiaPendienteDefinicion:
      form.topografia === "por_definir",

    pendienteProfundidadM:
      form.pendienteProfundidadM,

    tipoAcceso:
      form.tipoAcceso,

    servicios: {
      agua:
        form.instalaciones.agua,

      energia:
        form.instalaciones.energia,

      drenaje:
        form.instalaciones.drenaje,
    },

    configuracionInicial: {
      sistemaEstructural:
        form.sistemaEstructural,

      tipoCimentacion:
        normalizedFoundation,

      cimentacionPendienteDefinicion:
        form.tipoCimentacion ===
        "por_definir",

      modoDiseno:
        form.modoDiseno,

      instalaciones:
        JSON.parse(
          JSON.stringify(
            form.instalaciones
          )
        ),
    },

    condicionTerreno:
      form.condicionTerreno,

    demolicion:
      showDemolitionBlock.value
        ? {
          ...JSON.parse(
            JSON.stringify(
              form.demolicion
            )
          ),

          areaDemolicionM2:
            areaDemolicionCalculada.value,
        }
        : {
          tipoDemolicion: "",
          tipoEstructuraExistente: "",
          nivelesExistentes: "",
          anchoDemolicionM: "",
          largoDemolicionM: "",
          areaDemolicionM2: 0,
        },
  });
}

/* =========================================================
   VALIDACIÓN
   ========================================================= */

function validateConfiguration() {
  error.value = "";

  if (
    !form.topografia ||
    !form.tipoAcceso ||
    !form.condicionTerreno ||
    !form.sistemaEstructural ||
    !form.tipoCimentacion ||
    !form.tipoLosa ||
    !form.modoDiseno
  ) {
    error.value =
      "Completa las condiciones del proyecto, sistema constructivo, cimentación, losa y modalidad de diseño.";

    return false;
  }

  if (
    form.topografia ===
    "con_pendiente" &&
    Number(
      form.pendienteProfundidadM || 0
    ) <= 0
  ) {
    error.value =
      "Captura la profundidad o desnivel de referencia del terreno.";

    return false;
  }

  if (showDemolitionBlock.value) {
    const demolition =
      form.demolicion;

    if (
      !demolition.tipoDemolicion ||
      !demolition.tipoEstructuraExistente ||
      Number(
        demolition.nivelesExistentes ||
        0
      ) <= 0 ||
      Number(
        demolition.anchoDemolicionM ||
        0
      ) <= 0 ||
      Number(
        demolition.largoDemolicionM ||
        0
      ) <= 0
    ) {
      error.value =
        "Completa los datos de la construcción existente y su demolición.";

      return false;
    }
  }

  return true;
}

/* =========================================================
   NAVEGACIÓN
   ========================================================= */

function saveDraft() {
  persistConfiguration();

  saveStatus.value =
    "Cambios guardados";

  saveDetail.value =
    "Configuración almacenada";
}

function continueFlow() {
  if (!validateConfiguration()) {
    return;
  }

  persistConfiguration();

  if (
    form.modoDiseno === "subir_plano"
  ) {
    router.push(
      "/vivienda/workflow/planos-revision/carga"
    );

    return;
  }

  router.push(
    "/vivienda/workflow/diseno-vivienda/manual"
  );
}

function goBack() {
  persistConfiguration();

  router.push(
    "/vivienda/workflow/proyecto-alcance"
  );
}
</script>

<style scoped>
* {
  box-sizing: border-box;
}


/* =========================================================
   GRID
   ========================================================= */

.content-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1fr) 360px;
  gap: 20px;
}

.configuration-form {
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

.section-number {
  display: block;
  margin-bottom: 2px;
  color: #94a7c5;
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.08em;
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
  line-height: 1.4;
}

/* =========================================================
   CONFIGURACIÓN
   ========================================================= */

.condition-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.setting-block {
  min-width: 0;
  margin: 0;
  padding: 14px;
  border: 1px solid #c5d0e1;
  border-radius: 10px;
  background: #fbfcfe;
}

.setting-block legend {
  padding: 0 7px;
  color: #52678d;
  font-size: 0.71rem;
  font-weight: 750;
}

.access-block {
  grid-column: 1 / -1;
}

/* =========================================================
   OPCIONES
   ========================================================= */

.option-grid {
  display: grid;
  gap: 9px;
}

.option-grid.two {
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
}

.option-grid.three {
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
}

.option-grid.four {
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
}

.option-grid.terrain {
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
}

.choice-card {
  position: relative;
  min-height: 92px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 7px;
  padding: 12px 10px;
  border: 1px solid #c5d0e1;
  border-radius: 9px;
  background: #ffffff;
  color: #162d70;
  text-align: center;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.choice-card.compact {
  min-height: 76px;
}

.choice-card:hover {
  transform: translateY(-1px);
  border-color: #9db4dd;
  box-shadow:
    0 5px 14px rgba(44, 69, 126, 0.06);
}

.choice-card.selected {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f4f8ff,
      #f8f5ff);
}

.selection-mark {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border: 1px solid #b7c4d8;
  border-radius: 50%;
  background: #ffffff;
  color: #ffffff;
}

.choice-card.selected .selection-mark {
  border-color: #075ff2;
  background: #075ff2;
}

.choice-icon,
.technical-icon {
  display: grid;
  place-items: center;
  color: #075ff2;
}

.technical-icon {
  width: 48px;
  height: 48px;
  border: 1px solid #d7e1ef;
  border-radius: 11px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
}

.choice-card strong {
  color: #162d70;
  font-size: 0.75rem;
}

.choice-card small {
  max-width: 190px;
  color: #7180a2;
  font-size: 0.68rem;
  line-height: 1.4;
}

.choice-card.descriptive {
  min-height: 135px;
}

.foundation-card,
.slab-card {
  min-height: 112px;
}

/* =========================================================
   INPUTS
   ========================================================= */

.configuration-detail {
  display: grid;
  gap: 6px;
  margin-top: 12px;
}

.configuration-detail label,
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #42527f;
  font-size: 0.72rem;
  font-weight: 650;
}

.configuration-detail input,
.field input,
.field select {
  width: 100%;
  min-height: 42px;
  padding: 0 11px;
  border: 1px solid #c5d0e1;
  border-radius: 8px;
  background: #ffffff;
  color: #162d70;
  font: inherit;
  font-weight: 500;
}

.configuration-detail input:focus,
.field input:focus,
.field select:focus {
  outline: none;
  border-color: #075ff2;
  box-shadow:
    0 0 0 3px rgba(7, 95, 242, 0.1);
}

.input-with-unit {
  display: grid;
  grid-template-columns: 1fr 36px;
  align-items: center;
  overflow: hidden;
  border: 1px solid #c5d0e1;
  border-radius: 8px;
  background: #ffffff;
}

.input-with-unit input {
  min-width: 0;
  border: 0;
  border-radius: 0;
}

.input-with-unit span {
  color: #7180a2;
  font-size: 0.72rem;
  text-align: center;
}

.calculated-field {
  min-height: 42px;
  display: flex;
  align-items: center;
  padding: 0 11px;
  border: 1px solid #d1dae8;
  border-radius: 8px;
  background: #f3f6fb;
  color: #162d70;
  font-size: 0.8rem;
  font-weight: 700;
}

/* =========================================================
   DEMOLICIÓN
   ========================================================= */

.demolition-panel {
  grid-column: 1 / -1;
  padding: 18px;
  border: 1px solid #c2cede;
  border-radius: 10px;
  background: #f3f6fb;
}

.subsection-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subsection-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #edf4ff;
  color: #075ff2;
}

.subsection-tag {
  display: block;
  margin-bottom: 3px;
  color: #0877ef;
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.subsection-heading h3 {
  margin: 0;
  color: #162d70;
  font-size: 0.92rem;
}

.subsection-heading>p {
  margin: 8px 0 14px;
  color: #7180a2;
  font-size: 0.73rem;
}

.demolition-grid {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  gap: 11px;
}

/* =========================================================
   INSTALACIONES
   ========================================================= */

.installation-grid {
  display: grid;
  grid-template-columns:
    repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.installation-card {
  position: relative;
  min-height: 105px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 13px 8px;
  border: 1px solid #c5d0e1;
  border-radius: 9px;
  background: #ffffff;
  color: #162d70;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease;
}

.installation-card:hover {
  transform: translateY(-1px);
  border-color: #9db4dd;
}

.installation-card.yes {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f4f8ff,
      #f8f5ff);
}

.installation-card.no {
  background: #f8f9fb;
}

.installation-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.installation-card strong {
  font-size: 0.75rem;
}

.installation-status {
  padding: 4px 7px;
  border: 1px solid #d5deeb;
  border-radius: 6px;
  background: #f4f6fa;
  color: #7b87a7;
  font-size: 0.62rem;
  font-weight: 700;
}

.installation-status.defined {
  border-color: #ccd9ef;
  background: #edf4ff;
  color: #075ff2;
}

.installation-note {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 12px;
  color: #7180a2;
  font-size: 0.69rem;
}

.installation-note>svg {
  flex-shrink: 0;
  color: #075ff2;
}

/* =========================================================
   DISEÑO
   ========================================================= */

.design-section {
  border-color: #aabce0;
}

.design-options {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.design-card {
  position: relative;
  min-height: 180px;
  display: grid;
  grid-template-columns:
    64px minmax(0, 1fr) 20px;
  gap: 16px;
  align-items: center;
  padding: 20px;
  border: 1px solid #c5d0e1;
  border-radius: 10px;
  background: #ffffff;
  color: #162d70;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.design-card:hover {
  transform: translateY(-2px);
  border-color: #9db4dd;
  box-shadow:
    0 8px 18px rgba(40, 66, 135, 0.07);
}

.design-card.selected {
  border-color: #075ff2;
  background:
    linear-gradient(135deg,
      #f4f8ff,
      #f8f5ff);
}

.design-icon {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border: 1px solid #d2deef;
  border-radius: 11px;
  background:
    linear-gradient(135deg,
      #edf4ff,
      #f3efff);
  color: #075ff2;
}

.option-label {
  display: block;
  margin-bottom: 5px;
  color: #0877ef;
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.design-copy strong {
  display: block;
  color: #162d70;
  font-size: 0.96rem;
}

.design-copy p {
  margin: 7px 0 10px;
  color: #667797;
  font-size: 0.74rem;
  line-height: 1.47;
}

.design-copy small {
  color: #075ff2;
  font-size: 0.68rem;
  font-weight: 700;
}

.design-radio {
  width: 20px;
  height: 20px;
  border: 2px solid #b8c4d6;
  border-radius: 50%;
}

.design-card.selected .design-radio {
  border: 6px solid #075ff2;
}

/* =========================================================
   ERROR
   ========================================================= */

.error-message {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid #e8b9b9;
  border-radius: 9px;
  background: #fff5f5;
  color: #b02b2b;
  font-size: 0.76rem;
}

/* =========================================================
   ACCIONES
   ========================================================= */

.bottom-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-top: 2px;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn,
.save-btn,
.continue-btn {
  min-height: 47px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 24px;
  border-radius: 9px;
  font-size: 0.84rem;
  font-weight: 750;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.back-btn:hover,
.save-btn:hover,
.continue-btn:hover {
  transform: translateY(-1px);
}

.back-btn,
.save-btn {
  border: 1px solid #aebed5;
  background: #ffffff;
  color: #52678d;
}

.back-btn:hover,
.save-btn:hover {
  border-color: #075ff2;
  color: #075ff2;
}

.continue-btn {
  min-width: 220px;
  border: 0;
  background:
    linear-gradient(90deg,
      #075ff2,
      #8421f1);
  color: #ffffff;
  box-shadow:
    0 7px 17px rgba(51, 69, 211, 0.2);
}

.continue-btn>span {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.continue-btn small {
  margin-top: 2px;
  color:
    rgba(255, 255, 255, 0.8);
  font-size: 0.61rem;
}

/* =========================================================
   RESUMEN
   ========================================================= */

.summary-panel {
  position: sticky;
  top: 18px;
  align-self: start;
  padding: 20px;
}

.summary-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 15px;
  border-bottom: 1px solid #d4ddea;
}

.summary-heading h2 {
  margin: 0;
  color: #162d70;
  font-size: 0.96rem;
}

.capture-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 6px 9px;
  border: 1px solid #d2def0;
  border-radius: 8px;
  background: #f1f5fb;
  color: #075ff2;
  font-size: 0.64rem;
  font-weight: 700;
}

.capture-badge>span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #075ff2;
}

.summary-list {
  margin-top: 9px;
}

.summary-item {
  padding: 12px 0;
  border-bottom: 1px solid #e0e6ef;
}

.summary-item dt {
  color: #7b87a7;
  font-size: 0.68rem;
}

.summary-item dd {
  margin: 5px 0 0;
  color: #162d70;
  font-size: 0.82rem;
  font-weight: 750;
}

.summary-item dd small {
  display: block;
  margin-top: 3px;
  color: #7180a2;
  font-size: 0.67rem;
  font-weight: 500;
}

/* =========================================================
   SIGUIENTE
   ========================================================= */

.next-card {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-top: 20px;
  padding: 17px 15px;
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

.next-card div:last-child {
  display: flex;
  flex-direction: column;
}

.next-card small {
  color: #7180a2;
  font-size: 0.67rem;
}

.next-card strong {
  margin: 4px 0 5px;
  color: #075ff2;
  font-size: 0.82rem;
}

.next-card p {
  margin: 0;
  color: #5e7093;
  font-size: 0.72rem;
  line-height: 1.45;
}

/* =========================================================
   RESPONSIVE
   ========================================================= */

@media (max-width: 1180px) {

  .configuration-shell {
    padding-left: 24px;
    padding-right: 24px;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .summary-panel {
    position: static;
  }

  .stepper small {
    white-space: normal;
  }

  .installation-grid {
    grid-template-columns:
      repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 850px) {

  .condition-grid {
    grid-template-columns: 1fr;
  }

  .access-block,
  .demolition-panel {
    grid-column: auto;
  }

  .option-grid.four {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .design-options {
    grid-template-columns: 1fr;
  }

  .demolition-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {

  .form-section,
  .summary-panel {
    padding: 18px;
  }

  .option-grid.two,
  .option-grid.three,
  .option-grid.four,
  .option-grid.terrain,
  .installation-grid {
    grid-template-columns: 1fr;
  }

  .demolition-grid {
    grid-template-columns: 1fr;
  }

  .design-card {
    grid-template-columns:
      50px minmax(0, 1fr) 20px;
    padding: 16px;
  }

  .design-icon {
    width: 48px;
    height: 48px;
  }

  .bottom-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .right-actions {
    width: 100%;
  }

  .back-btn {
    width: 100%;
  }

  .save-btn,
  .continue-btn {
    flex: 1;
    min-width: 0;
  }
}

@media (max-width: 470px) {
  .right-actions {
    flex-direction: column;
  }

  .save-btn,
  .continue-btn {
    width: 100%;
  }
}
</style>