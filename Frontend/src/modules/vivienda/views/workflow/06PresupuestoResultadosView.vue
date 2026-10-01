<template>
  <QuantiaWorkflowLayout :step="6" title="6. Presupuesto y resultados"
    subtitle="Revisa costos, ajusta parámetros y genera el presupuesto final.">
    <template #title-actions><button class="qw-btn" @click="showConfig = !showConfig">⚙ Configuración</button> <button
        class="qw-btn primary" :disabled="!hasValidBudget" @click="refresh">Guardar configuración</button></template>
    <section class="costs">
      <article class="qw-card">
        <small>Mano de obra</small>
        <strong>
          {{
            hasLaborBreakdown
              ? money(labor)
              : "Sin desglose"
          }}
        </strong>
      </article>

      <article class="qw-card">
        <small>Materiales</small>
        <strong>
          {{
            hasMaterialBreakdown
              ? money(materials)
              : "Sin desglose"
          }}
        </strong>
      </article>
      <article class="qw-card"><small>Indirectos ({{ params.indirectos }}%)</small><strong>{{ money(indirects)
          }}</strong>
      </article>
      <article class="qw-card"><small>Financiamiento
          ({{ params.financiamiento }}%)</small><strong>{{ money(financing) }}</strong></article>
      <article class="qw-card"><small>Utilidad ({{ params.utilidad }}%)</small><strong>{{ money(profit) }}</strong>
      </article>
      <article class="qw-card">
        <small>IVA ({{ params.iva }}%)</small>
        <strong>{{ money(ivaAmount) }}</strong>
      </article>

      <article class="qw-card total"><small>Presupuesto total</small><strong>{{ money(grandTotal) }}</strong></article>
    </section>
    <section v-if="showConfig" class="config qw-card"><label>Indirectos % <input v-model.number="params.indirectos"
          type="number" min="0" step="0.01"></label><label>Financiamiento % <input
          v-model.number="params.financiamiento" type="number" min="0" step="0.01"></label><label> Utilidad % <input
          v-model.number="params.utilidad" type="number" min="0" step="0.01"></label><label>IVA%
        <input v-model.number="params.iva" type="number" min="0" step="0.01"></label></section>
    <p v-if="!concepts.length" class="qw-error">
      No existen conceptos confirmados para generar el presupuesto.
    </p>
    <div v-if="missingPriceConcepts.length" class="qw-error">
      <strong>
        Presupuesto incompleto:
        {{ missingPriceConcepts.length }}
        conceptos no tienen P.U. publicado.
      </strong>

      <p v-for="item in missingPriceConcepts.slice(0, 5)" :key="item.key">
        {{ item.key }} — {{ item.title }}
      </p>
    </div>
    <section class="budget-grid">
      <article class="qw-card table">
        <div class="tabs">
          Conceptos confirmados
        </div>
        <table class="qw-table">
          <thead>
            <tr>
              <th>Clave</th>
              <th>Concepto</th>
              <th>Unidad</th>
              <th>Cantidad</th>
              <th>P.U.</th>
              <th>Importe</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in concepts" :key="item.key">
              <td>{{ item.key }}</td>
              <td>{{ item.title }}</td>
              <td>{{ item.unit }}</td>
              <td>{{ item.quantity }}</td>
              <td>
                <span v-if="Number(item.unitPrice || 0) > 0">
                  {{ money(item.unitPrice) }}
                </span>

                <span v-else>
                  Sin PU publicado
                </span>
              </td>

              <td>
                <span v-if="Number(item.unitPrice || 0) > 0">
                  {{ money(item.total) }}
                </span>

                <span v-else>
                  —
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="direct"><span>Costo directo total</span><strong>{{ money(directCost) }}</strong></div>
      </article>
      <aside class="qw-card summary">
        <h3>Parámetros aplicados</h3>
        <p>Indirectos <b>{{ params.indirectos }}%</b></p>
        <p>Financiamiento <b>{{ params.financiamiento }}%</b></p>
        <p>Utilidad <b>{{ params.utilidad }}%</b></p>
        <p>IVA <b>{{ params.iva }}%</b></p>
        <hr><button class="qw-btn" :disabled="!hasValidBudget" @click="openPrint('/vivienda/print/materiales')">
          Listado de materiales
        </button>

        <button class="qw-btn" :disabled="!hasValidBudget" @click="openPrint('/vivienda/print/mano-obra')">
          Mano de obra
        </button>

        <button class="qw-btn primary" :disabled="!hasValidBudget" @click="openPrint('/vivienda/print/presupuesto')">
          Presupuesto imprimible
        </button>
      </aside>
    </section>
    <template #footer><span>Precios unitarios provenientes de PU-Core</span><button class="qw-btn"
        @click="router.push('/vivienda/workflow/calculo-cantidades')">← Cuantificación</button></template>
  </QuantiaWorkflowLayout>
</template>
<script setup>

import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import QuantiaWorkflowLayout from "../QuantiaWorkflowLayout.vue";
import "@/assets/styles/quantia-workflow.css";



const router = useRouter(), store = useViviendaStore(), showConfig = ref(false);
const savedParams =
  store.revisionInferencia?.parametrosPresupuesto || {};

const params = ref({
  indirectos:
    Number(savedParams.indirectos ?? 0),

  financiamiento:
    Number(savedParams.financiamiento ?? 0),

  utilidad:
    Number(savedParams.utilidad ?? 0),

  iva:
    Number(savedParams.iva ?? 0),
});

const concepts = computed(() =>
  Array.isArray(
    store.revisionInferencia?.conceptosConfirmados
  )
    ? store.revisionInferencia.conceptosConfirmados
    : []
);

const missingPriceConcepts = computed(() =>
  concepts.value.filter(
    (item) => Number(item.unitPrice || 0) <= 0
  )
);

const hasValidBudget = computed(
  () =>
    concepts.value.length > 0 &&
    missingPriceConcepts.value.length === 0
);

const directCost = computed(() =>
  concepts.value.reduce((sum, item) => {
    const total = Number(item.total);

    if (Number.isFinite(total) && total > 0) {
      return sum + total;
    }

    return (
      sum +
      Number(item.quantity || 0) *
      Number(item.unitPrice || 0)
    );
  }, 0)
);

const labor = computed(() =>
  concepts.value.reduce(
    (sum, item) =>
      sum +
      Number(
        item.laborTotal ??
        item.manoObraTotal ??
        0
      ),
    0
  )
);

const materials = computed(() =>
  concepts.value.reduce(
    (sum, item) =>
      sum +
      Number(
        item.materialTotal ??
        item.materialesTotal ??
        0
      ),
    0
  )
);

const indirects = computed(
  () =>
    directCost.value *
    params.value.indirectos /
    100
);

const financing = computed(
  () =>
    directCost.value *
    params.value.financiamiento /
    100
);

const profit = computed(
  () =>
    directCost.value *
    params.value.utilidad /
    100
);

const subtotal = computed(
  () =>
    directCost.value +
    indirects.value +
    financing.value +
    profit.value
);

const ivaAmount = computed(
  () =>
    subtotal.value *
    params.value.iva /
    100
);

const grandTotal = computed(
  () =>
    subtotal.value +
    ivaAmount.value
);

const hasLaborBreakdown = computed(() =>
  concepts.value.some(
    (item) =>
      item.laborTotal != null ||
      item.manoObraTotal != null
  )
);

const hasMaterialBreakdown = computed(() =>
  concepts.value.some(
    (item) =>
      item.materialTotal != null ||
      item.materialesTotal != null
  )
);

function money(v) { return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(Number(v || 0)) }

function normalizePercent(value) {
  return Math.max(Number(value || 0), 0);
}

function refresh() {
  params.value = {
    indirectos:
      normalizePercent(params.value.indirectos),

    financiamiento:
      normalizePercent(params.value.financiamiento),

    utilidad:
      normalizePercent(params.value.utilidad),

    iva:
      normalizePercent(params.value.iva),
  };

  if (!hasValidBudget.value) return;

  store.setRevisionInferencia?.({
    ...(store.revisionInferencia || {}),

    parametrosPresupuesto: {
      ...params.value,
    },

    presupuesto: {
      costoDirecto:
        directCost.value,

      manoObra:
        hasLaborBreakdown.value
          ? labor.value
          : null,

      materiales:
        hasMaterialBreakdown.value
          ? materials.value
          : null,

      indirectos:
        indirects.value,

      financiamiento:
        financing.value,

      utilidad:
        profit.value,

      iva:
        ivaAmount.value,

      subtotal:
        subtotal.value,

      total:
        grandTotal.value,
    },

    presupuestoTotal:
      grandTotal.value,
  });
}

function openPrint(path) {
  refresh();

  if (!hasValidBudget.value) return;

  router.push(path);
}

</script>
<style scoped>
.costs {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.costs article {
  padding: 17px
}

.costs small,
.costs strong {
  display: block
}

.costs strong {
  margin-top: 9px;
  font-size: 1.05rem
}

.costs .total {
  color: #3219ed;
  border-color: #7257ff
}

.config {
  display: flex;
  gap: 15px;
  margin-top: 12px;
  padding: 14px
}

.config label {
  display: flex;
  align-items: center;
  gap: 7px
}

.config input {
  width: 70px;
  padding: 7px
}

.budget-grid {
  display: grid;
  grid-template-columns: 1fr 290px;
  gap: 14px;
  margin-top: 14px
}

.table {
  overflow: auto
}

.tabs {
  padding: 16px;
  color: #2519e9;
  border-bottom: 1px solid #e2e6ef
}

.direct {
  display: flex;
  justify-content: flex-end;
  gap: 50px;
  padding: 18px
}

.summary {
  padding: 16px
}

.summary p {
  display: flex;
  justify-content: space-between
}

.summary .qw-btn {
  width: 100%;
  margin-top: 9px
}

@media(max-width:1100px) {
  .costs {
    grid-template-columns: repeat(3, 1fr)
  }

  .budget-grid {
    grid-template-columns: 1fr
  }
}

@media(max-width:650px) {
  .costs {
    grid-template-columns: 1fr 1fr
  }

  .config {
    display: grid
  }
}
</style>
