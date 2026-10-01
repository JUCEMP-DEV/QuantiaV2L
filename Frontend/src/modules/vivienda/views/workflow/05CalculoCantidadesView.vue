<template>
  <QuantiaWorkflowLayout :step="5" title="5. Cálculo de cantidades"
    subtitle="Revisa las cantidades generadas por el motor. Confirma, ajusta o excluye conceptos antes de continuar.">
    <template #title-actions>
      <button class="qw-btn primary" :disabled="loading" @click="generate">
        {{ loading ? 'Calculando…' : 'Generar cantidades' }}
      </button>
    </template>
    <section class="metrics">
      <article class="qw-card"><small>Conceptos generados</small><strong>{{ concepts.length }}</strong></article>
      <article class="qw-card"><small>Cantidades confirmadas</small><strong>{{ confirmedCount }}</strong></article>
      <article class="qw-card"><small>Por revisar</small><strong>{{ reviewCount }}</strong></article>
      <article class="qw-card"><small>Excluidos</small><strong>{{ excludedCount }}</strong></article>
      <article class="qw-card"><small>Área de construcción</small><strong>{{ area }} m²</strong></article>
    </section>
    <div v-if="error" class="qw-error">{{ error }}</div>
    <section class="qw-card" style="padding: 16px; margin-bottom: 16px">
      <strong>Modelo recibido de 04</strong>
      <details v-if="consumptionIssues.length" open><summary>Pendientes de elementos en 04</summary>
        <p v-for="(issue,index) in consumptionIssues" :key="index">{{ issue.entityIds.join(', ') }} · {{ issue.message }} · Resolver en {{ issue.resolveIn }}</p>
        <button class="qw-btn" @click="goToDesign">Revisar modelo en 04</button>
      </details>
      <p>{{ store.estructuraEspacial?.espacios?.length || 0 }} espacios · {{ store.estructuraEspacial?.muros?.length || 0 }} muros. El motor obtiene las mediciones de este modelo y de las condiciones constructivas de 02.</p>
      <p>Las cantidades calculadas son propuestas para revisión. Si falta una definición del proyecto, corrígela en 02 o 04.</p>
      <details v-if="Object.keys(moduleSimulations).length"><summary>Procedencia de las mediciones automáticas</summary>
        <div v-for="(simulation, key) in moduleSimulations" :key="key">
          <p v-for="entry in (simulation.contextSnapshot?.geometryInference || []).filter(item => simulation.availableConcepts?.some(concept => concept.key === item.concept))" :key="entry.concept + entry.input">{{ entry.concept }} · {{ entry.scopeRefs.join(', ') }} · Geometría de 04</p>
        </div>
      </details>
    </section>
    <div v-if="blockedConcepts.length" class="qw-error">
      <strong>
        {{ blockedConcepts.length }} conceptos bloqueados por información faltante.
      </strong>

      <p v-for="item in blockedConcepts" :key="item.key">
        {{ item.key }} — {{ item.title }}
        <span v-if="item.missingInputs?.length">
          · Falta: {{ item.missingInputs.join(", ") }}
        </span>
        <span v-else> · Revisa las condiciones de aplicación y dependencias del concepto.</span>
        <details v-if="item.alerts?.length"><summary>Motivos del bloqueo</summary><pre>{{ JSON.stringify(item.alerts, null, 2) }}</pre></details>
      </p>
    </div>
    <section class="quantity-grid">
      <aside class="chapters qw-card"><input v-model="search" class="qw-input" placeholder="Buscar concepto"><button
          v-for="group in grouped" :key="group.name" @click="activeGroup = group.name"
          :class="{ active: activeGroup === group.name }"><b>{{ group.name }}</b><span>{{ group.items.length
          }}</span></button>
      </aside>
      <article class="quantity-table qw-card">
        <table class="qw-table">
          <thead>
            <tr>
              <th>Clave</th>
              <th>Concepto</th>
              <th>Unidad</th>
              <th>Cantidad</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in visible" :key="item.key">
              <td>{{ item.key }}</td>
              <td>{{ item.title }}</td>
              <td>{{ item.unit }}</td>
              <td><input class="qty" type="number" min="0" step="0.01" v-model.number="item.quantity"
                  @change="recalc(item)"></td>
              <td><select v-model="item.uiStatus" @change="item.statusEdited = true">
                  <option value="confirmed">Confirmado</option>
                  <option value="review">Por revisar</option>
                  <option value="excluded">Excluido</option>
                </select></td>
            </tr>
          </tbody>
        </table>
      </article>
      <aside class="summary qw-card">
        <h3>Resumen por capítulo</h3>
        <div v-for="g in grouped" :key="g.name"><span>{{ g.name }}</span><b>{{ g.items.length }}</b></div>
        <hr><strong>Total {{ concepts.length }}</strong>
      </aside>
    </section>
    <template #footer><span>Motor de inferencia Quantia V2</span>
      <div><button class="qw-btn" @click="goToDesign">
          ← Diseño
        </button><button class="qw-btn primary" :disabled="loading ||
          !confirmedCount ||
          reviewCount > 0 ||
          blockedConcepts.length > 0
          " @click="continueFlow">Continuar →
          Presupuesto
        </button></div>
    </template>
  </QuantiaWorkflowLayout>
</template>
<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/authStore";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import { inferirResultadoV4 } from "@/modules/vivienda/services/resultadosApiService";
import { simularModuloBackend } from "@/modules/vivienda/services/motorApiService";
import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import "@/assets/styles/quantia-workflow.css";


const moduleSimulations = ref({});
const consumptionIssues = computed(() => {
  const issues = Object.values(moduleSimulations.value).flatMap(s => s.contextSnapshot?.consumption04?.issues || []);
  return [...new Map(issues.map(i=>[JSON.stringify(i),i])).values()];
});
const router = useRouter(), auth = useAuthStore(), store = useViviendaStore(),
  concepts = ref([]), loading = ref(false), error = ref(""), search = ref(""), activeGroup = ref("");
const area = computed(() => Number(store.datosGeneralesObra?.areaConstruccionM2 || 0).toFixed(2));
const confirmedCount = computed(() => concepts.value.filter(x => x.uiStatus === 'confirmed').length),
  reviewCount = computed(() => concepts.value.filter(x => x.uiStatus === 'review').length),
  excludedCount = computed(() => concepts.value.filter(x => x.uiStatus === 'excluded').length);
const grouped = computed(() => {
  const m = {};
  concepts.value.forEach(x => (m[x.partida || x.group || 'Otros'] ??= []).push(x));
  return Object.entries(m).map(([name, items]) => ({ name, items }))
});
const visible = computed(() =>
  concepts.value.filter(x => (!activeGroup.value || (x.partida || x.group || 'Otros') === activeGroup.value)
    && (`${x.key} ${x.title}`.toLowerCase().includes(search.value.toLowerCase()))));

const blockedConcepts = computed(() => {
  const simulations = Object.values(
    moduleSimulations.value
  );

  const storedModules = Object.values(
    store.modulos || {}
  );

  const items = (simulations.length ? simulations : storedModules).flatMap((source) =>
    Array.isArray(source?.blockedConcepts)
      ? source.blockedConcepts
      : []
  );

  const unique = new Map();

  for (const item of items) {
    const key = String(item?.key || "");

    if (key && !unique.has(key)) {
      unique.set(key, item);
    }
  }

  return [...unique.values()];
});


function buildModuleControls(moduleKey) {
  const saved =
    store.modulos?.[moduleKey]?.controles || {};

  const engineInputs =
    store.datosGeneralesObra?.engineInputs || {};

  const instalaciones =
    engineInputs.servicios_instalaciones ||
    store.preliminares?.configuracionInicial?.instalaciones ||
    {};

  return {
    sistemaEstructural:
      store.datosGeneralesObra?.sistemaEstructural || "",

    tipoCimentacion:
      store.datosGeneralesObra?.tipoCimentacion || "",

    tipoIntervencion:
      store.clasificacion?.tipoIntervencion || "",

    alcanceProyecto:
      store.alcance?.alcance || "",

    varianteZapata:
      saved.varianteZapata || "",

    tipoLosa:
      saved.tipoLosa ||
      store.datosGeneralesObra?.tipoLosa ||
      engineInputs.tipo_losa ||
      "",

    nivelAcabado:
      saved.nivelAcabado ||
      store.clasificacion?.nivelAcabado ||
      "",

    serviciosInstalaciones: {
      agua:
        saved.serviciosInstalaciones?.agua ??
        instalaciones.agua ??
        null,

      energia:
        saved.serviciosInstalaciones?.energia ??
        instalaciones.energia ??
        null,

      drenaje:
        saved.serviciosInstalaciones?.drenaje ??
        instalaciones.drenaje ??
        null,

      gas:
        saved.serviciosInstalaciones?.gas ??
        instalaciones.gas ??
        null,
    },
  };
}

function buildSpatialContextForModule(moduleKey, controls) {
  const base = JSON.parse(
    JSON.stringify(store.estructuraEspacial || {})
  );

  const byConcept = {
    ...(base.engineInputsByConcept || {}),
  };

  if (
    moduleKey === "cimentacion" &&
    controls.varianteZapata
  ) {
    const count = (base.espacios || []).reduce(
      (sum, item) =>
        sum + Math.max(
          Number(item?.zapatasAisladasPzas || 0),
          0
        ),
      0
    );

    if (count > 0) {
      const conceptKey =
        controls.varianteZapata === "100"
          ? "CIM-003A"
          : "CIM-003";

      const inputName =
        controls.varianteZapata === "100"
          ? "cantidad_zapatas_100_confirmada"
          : "cantidad_zapatas_080_confirmada";

      byConcept[conceptKey] = {
        ...(byConcept[conceptKey] || {}),
        [inputName]: byConcept[conceptKey]?.[inputName] ?? count,
      };
    }
  }

  return {
    ...base,
    engineInputsByConcept: byConcept,
  };
}

async function simulateRequiredModules() {
  const moduleKeys = store.getRequiredModuleOrder();
  const simulations = {};
  const rows = [];
  const addedKeys = new Set();

  for (const moduleKey of moduleKeys) {
    const controls = buildModuleControls(moduleKey);

    const previousSelectedKeys = Array.isArray(
      store.modulos?.[moduleKey]?.selectedConceptKeys
    )
      ? store.modulos[moduleKey].selectedConceptKeys
      : [];

    const response = await simularModuloBackend({
      moduleKey,
      controles: controls,
      selectedConceptKeys: previousSelectedKeys,
      forceSelectAll: false,
      preliminares: store.preliminares,
      datosGeneralesObra: store.datosGeneralesObra,
      estructuraEspacial:
        buildSpatialContextForModule(
          moduleKey,
          controls
        ),
      colindanciasRecorrido:
        store.colindanciasRecorrido,
    });

    simulations[moduleKey] = response;

    const selectedKeys = new Set(
      Array.isArray(response?.selectedConceptKeys)
        ? response.selectedConceptKeys
        : []
    );

    const candidates = [
      ...(Array.isArray(response?.proposedConcepts)
        ? response.proposedConcepts
        : []),

      ...(Array.isArray(response?.confirmedConcepts)
        ? response.confirmedConcepts
        : []),
    ];

    for (const item of candidates) {
      const key = String(item?.key || "");

      if (!key || addedKeys.has(key)) continue;

      addedKeys.add(key);

      rows.push({
        ...item,
        moduleKey,
        uiStatus:
          selectedKeys.has(key)
            ? "confirmed"
            : "review",
      });
    }
  }

  moduleSimulations.value = simulations;

  return rows;
}

async function generate() {
  loading.value = true;
  error.value = "";

  try {
    const currentState = new Map(
      concepts.value.map((item) => [
        String(item.key || ""),
        {
          uiStatus: item.uiStatus,
          statusEdited: item.statusEdited,
          quantity: item.quantity,
          quantityEdited: item.quantityEdited,
        },
      ])
    );

    const rows = await simulateRequiredModules();

    concepts.value = rows.map((item) => {
      const previous = currentState.get(
        String(item.key || "")
      );

      if (!previous) return item;

      return {
        ...item,

        uiStatus:
          previous.statusEdited
            ? previous.uiStatus
            : item.uiStatus,

        statusEdited:
          Boolean(previous.statusEdited),

        quantity:
          previous.quantityEdited
            ? previous.quantity
            : item.quantity,

        quantityEdited:
          Boolean(previous.quantityEdited),
      };
    });

    if (
      !activeGroup.value ||
      !grouped.value.some(
        (group) => group.name === activeGroup.value
      )
    ) {
      activeGroup.value =
        grouped.value[0]?.name || "";
    }

    if (!concepts.value.length) {
      error.value =
        blockedConcepts.value.length
          ? `El motor encontro conceptos, pero ${blockedConcepts.value.length} estan bloqueados. Completa sus mediciones o revisa sus condiciones.`
          : "No hay conceptos propuestos para el alcance y las condiciones actuales. Revisa los modulos seleccionados.";
    }
  } catch (e) {
    concepts.value = [];
    activeGroup.value = "";

    error.value =
      e?.message ||
      "No fue posible generar las cantidades.";
  } finally {
    loading.value = false;
  }
}

async function persistModuleSelections() {
  const moduleKeys = store.getRequiredModuleOrder();

  for (const moduleKey of moduleKeys) {
    const moduleRows = concepts.value.filter(
      (item) => item.moduleKey === moduleKey
    );

    const selectedConceptKeys = moduleRows
      .filter((item) => item.uiStatus === "confirmed")
      .map((item) => String(item.key || ""))
      .filter(Boolean);

    if (
      moduleRows.length &&
      !selectedConceptKeys.length
    ) {
      throw new Error(
        `Confirma al menos un concepto del módulo ${moduleKey}.`
      );
    }

    const controls =
      buildModuleControls(moduleKey);

    const response =
      await simularModuloBackend({
        moduleKey,
        controles: controls,
        selectedConceptKeys,
        forceSelectAll: false,

        preliminares:
          store.preliminares,

        datosGeneralesObra:
          store.datosGeneralesObra,

        estructuraEspacial:
          buildSpatialContextForModule(
            moduleKey,
            controls
          ),

        colindanciasRecorrido:
          store.colindanciasRecorrido,
      });

    const selectedConcepts =
      Array.isArray(response?.selectedConcepts)
        ? response.selectedConcepts
        : [];

    const summaryByPartida =
      Array.isArray(response?.summaryByPartida)
        ? response.summaryByPartida
        : [];

    const proposedConcepts =
      Array.isArray(response?.proposedConcepts)
        ? response.proposedConcepts
        : [];

    const blockedConcepts =
      Array.isArray(response?.blockedConcepts)
        ? response.blockedConcepts
        : [];

    const notApplicableConcepts =
      Array.isArray(response?.notApplicableConcepts)
        ? response.notApplicableConcepts
        : [];

    const noApplicable =
      !selectedConcepts.length &&
      !blockedConcepts.length &&
      !proposedConcepts.length &&
      notApplicableConcepts.length > 0;

    if (
      !noApplicable &&
      !selectedConcepts.length
    ) {
      throw new Error(
        `El módulo ${moduleKey} no tiene conceptos confirmados válidos.`
      );
    }

    const selectedTotal = selectedConcepts.reduce(
      (sum, item) =>
        sum + Number(item?.total || 0),
      0
    );

    const summaryTotal = summaryByPartida.reduce(
      (sum, item) =>
        sum + Number(item?.total || 0),
      0
    );

    const backendCost =
      Number(response?.costoEstimado || 0);

    const normalizedCost = Number(
      Math.max(
        backendCost,
        selectedTotal,
        summaryTotal,
        0
      ).toFixed(2)
    );

    const base = Math.max(
      selectedTotal,
      summaryTotal,
      1
    );

    if (
      Math.abs(
        selectedTotal - summaryTotal
      ) / base > 0.05
    ) {
      throw new Error(
        `El resumen del módulo ${moduleKey} no coincide con los conceptos seleccionados.`
      );
    }
    const persisted =
      store.setModuloData(moduleKey, {
        noApplicable,

        controles: controls,

        selectedConceptKeys:
          response?.selectedConceptKeys ||
          selectedConceptKeys,

        selectedConcepts,

        summaryByPartida,

        proposedConcepts,

        blockedConcepts,

        notApplicableConcepts,

        inactiveConcepts:
          response?.inactiveConcepts || [],

        activationCoverage:
          response?.activationCoverage || {},

        costoEstimado:
          normalizedCost,
      });

    if (!persisted) {
      throw new Error(
        `No fue posible guardar el módulo ${moduleKey}.`
      );
    }

    moduleSimulations.value[moduleKey] =
      response;
  }
}


function recalc(item) {
  item.quantity = Math.max(
    Number(item.quantity || 0),
    0
  );

  item.total = Number(
    (
      item.quantity *
      Number(item.unitPrice || 0)
    ).toFixed(2)
  );

  item.quantityEdited = true;
}


async function continueFlow() {
  loading.value = true;
  error.value = "";

  if (reviewCount.value > 0) {
    error.value =
      "Debes confirmar o excluir todos los conceptos pendientes.";
    loading.value = false;
    return;
  }

  if (blockedConcepts.value.length > 0) {
    error.value =
      "Existen conceptos bloqueados por información faltante.";
    loading.value = false;
    return;
  }

  if (!confirmedCount.value) {
    error.value =
      "Debes confirmar al menos un concepto.";
    loading.value = false;
    return;
  }

  const invalidConfirmed = concepts.value.find(
    (item) =>
      item.uiStatus === "confirmed" &&
      Number(item.quantity || 0) <= 0
  );

  if (invalidConfirmed) {
    error.value =
      `Revisa la cantidad del concepto ${invalidConfirmed.key}.`;

    loading.value = false;
    return;
  }


  try {
    await persistModuleSelections();

    const result = await inferirResultadoV4({
      preliminares: store.preliminares,
      modulos: store.modulos,
      datosGeneralesObra: store.datosGeneralesObra,
      variablesEntrada: store.variablesEntrada,
      estructuraEspacial: store.estructuraEspacial,
      colindanciasRecorrido: store.colindanciasRecorrido,
      validacionEspacial: store.validacionEspacial,
      perfil: auth.accessProfile || "oficial",
      requiredModuleKeys: store.getRequiredModuleOrder(),
    });

    const backendConcepts =
      Array.isArray(result?.desglose?.technicalConcepts)
        ? result.desglose.technicalConcepts
        : [];

    const confirmedMap = new Map(
      concepts.value
        .filter((item) => item.uiStatus === "confirmed")
        .map((item) => [String(item.key), item])
    );

    const finalConcepts = backendConcepts
      .filter((item) =>
        confirmedMap.has(String(item.key))
      )
      .map((item) => {
        const edited = confirmedMap.get(
          String(item.key)
        );

        const quantity = Number(
          edited?.quantity ?? item.quantity ?? 0
        );

        const unitPrice = Number(
          item.unitPrice ?? edited?.unitPrice ?? 0
        );

        return {
          ...item,
          quantity,
          unitPrice,
          total: Number(
            (quantity * unitPrice).toFixed(2)
          ),
          quantityEdited:
            quantity !== Number(item.quantity || 0),
        };
      });

    store.setRevisionInferencia?.({
      ...(store.revisionInferencia || {}),

      preview: result,

      revisado: true,

      conceptosConfirmados: finalConcepts,

      conceptosPendientes:
        concepts.value.filter(
          (item) => item.uiStatus === "review"
        ),

      conceptosExcluidos:
        concepts.value.filter(
          (item) => item.uiStatus === "excluded"
        ),
    });

    router.push(
      "/vivienda/workflow/presupuesto-resultados"
    );
  } catch (e) {
    error.value =
      e?.message ||
      "No fue posible consolidar las cantidades.";
  } finally {
    loading.value = false;
  }
}

function restoreOrGenerate() {
  const confirmed =
    store.revisionInferencia?.conceptosConfirmados || [];

  const pending =
    store.revisionInferencia?.conceptosPendientes || [];

  const excluded =
    store.revisionInferencia?.conceptosExcluidos || [];

  const saved = [
    ...confirmed.map((item) => ({
      ...item,
      uiStatus: "confirmed",
    })),

    ...pending.map((item) => ({
      ...item,
      uiStatus: "review",
    })),

    ...excluded.map((item) => ({
      ...item,
      uiStatus: "excluded",
    })),
  ];

  if (saved.length) {
    concepts.value = saved;
    activeGroup.value =
      grouped.value[0]?.name || "";
    return;
  }

  generate();
}
function goToDesign() {
  const modoDiseno =
    store.datosGeneralesObra?.engineInputs?.modo_diseno ||
    store.preliminares?.configuracionInicial?.modoDiseno ||
    "";

  if (modoDiseno === "dibujar") {
    router.push(
      "/vivienda/workflow/diseno-vivienda/manual"
    );
    return;
  }

  if (modoDiseno === "subir_plano") {
    router.push(
      "/vivienda/workflow/diseno-vivienda/plano"
    );
    return;
  }

  router.push(
    "/vivienda/workflow/como-se-construira"
  );
}
onMounted(restoreOrGenerate);
</script>
<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 14px
}

.metrics article {
  padding: 18px
}

.metrics small,
.metrics strong {
  display: block
}

.metrics strong {
  margin-top: 10px;
  font-size: 1.45rem;
  color: #123eea
}

.quantity-grid {
  display: grid;
  grid-template-columns: 280px 1fr 235px;
  gap: 12px;
  min-height: 620px
}

.chapters,
.summary {
  padding: 12px
}

.chapters button {
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 13px;
  border: 0;
  border-bottom: 1px solid #e5e9f1;
  color: #152a75;
  background: #fff
}

.chapters button.active {
  color: #2719ed;
  background: #f3f2ff
}

.quantity-table {
  overflow: auto
}

.qty {
  width: 80px;
  padding: 6px;
  border: 1px solid #dce2ec;
  border-radius: 6px
}

.summary div {
  display: flex;
  justify-content: space-between;
  padding: 9px 0
}

.qw-footer>div {
  display: flex;
  gap: 12px
}

@media(max-width:1100px) {
  .quantity-grid {
    grid-template-columns: 230px 1fr
  }

  .summary {
    grid-column: 1/-1
  }

  .metrics {
    grid-template-columns: repeat(3, 1fr)
  }
}

@media(max-width:720px) {
  .quantity-grid {
    grid-template-columns: 1fr
  }

  .chapters {
    display: none
  }

  .metrics {
    grid-template-columns: 1fr 1fr
  }
}
</style>
