<template>
    <QuantiaPrintableShell title="PRESUPUESTO DE OBRA"
        footer="Precios unitarios provenientes de PU-Core. Cantidades validadas en Quantia.">
        <table>
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
            <tbody v-for="group in groups" :key="group.name">
                <tr class="group">
                    <td colspan="6">{{ group.name }}</td>
                </tr>
                <tr v-for="item in group.items" :key="item.key">
                    <td>{{ item.key }}</td>
                    <td>{{ item.title }}</td>
                    <td>{{ item.unit }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ money(item.unitPrice) }}</td>
                    <td>{{ money(item.total) }}</td>
                </tr>
                <tr class="subtotal">
                    <td colspan="5">Subtotal {{ group.name }}</td>
                    <td>{{ money(group.total) }}</td>
                </tr>
            </tbody>
        </table>
        <section class="totals">
            <span>Costo directo</span>
            <b>{{ money(direct) }}</b>

            <span>
                Indirectos ({{ params.indirectos }}%)
            </span>
            <b>{{ money(indirects) }}</b>

            <span>
                Financiamiento ({{ params.financiamiento }}%)
            </span>
            <b>{{ money(financing) }}</b>

            <span>
                Utilidad ({{ params.utilidad }}%)
            </span>
            <b>{{ money(profit) }}</b>

            <span>
                IVA ({{ params.iva }}%)
            </span>
            <b>{{ money(iva) }}</b>

            <strong>PRESUPUESTO TOTAL</strong>
            <strong>{{ money(total) }}</strong>
        </section>
    </QuantiaPrintableShell>
</template>
<script setup>
import { computed } from "vue";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import QuantiaPrintableShell from "./QuantiaPrintableShell.vue";

const store = useViviendaStore();

const concepts = computed(() =>
    Array.isArray(
        store.revisionInferencia?.conceptosConfirmados
    )
        ? store.revisionInferencia.conceptosConfirmados
        : []
);

const params = computed(() => ({
    indirectos: Number(
        store.revisionInferencia?.parametrosPresupuesto?.indirectos ?? 0
    ),
    financiamiento: Number(
        store.revisionInferencia?.parametrosPresupuesto?.financiamiento ?? 0
    ),
    utilidad: Number(
        store.revisionInferencia?.parametrosPresupuesto?.utilidad ?? 0
    ),
    iva: Number(
        store.revisionInferencia?.parametrosPresupuesto?.iva ?? 0
    ),
}));

const budget = computed(
    () => store.revisionInferencia?.presupuesto || {}
);

const groups = computed(() => {
    const map = {};

    concepts.value.forEach((item) => {
        const groupName =
            item.partida ||
            item.group ||
            "Otros";

        (map[groupName] ??= []).push(item);
    });

    return Object.entries(map).map(
        ([name, items]) => ({
            name,
            items,

            total: items.reduce(
                (sum, item) =>
                    sum + Number(item.total || 0),
                0
            ),
        })
    );
});

const direct = computed(
    () =>
        Number(
            budget.value.costoDirecto ?? 0
        )
);

const indirects = computed(
    () =>
        Number(
            budget.value.indirectos ?? 0
        )
);

const financing = computed(
    () =>
        Number(
            budget.value.financiamiento ?? 0
        )
);

const profit = computed(
    () =>
        Number(
            budget.value.utilidad ?? 0
        )
);

const iva = computed(
    () =>
        Number(
            budget.value.iva ?? 0
        )
);

const total = computed(
    () =>
        Number(
            budget.value.total ??
            store.revisionInferencia?.presupuestoTotal ??
            0
        )
);

function money(value) {
    return new Intl.NumberFormat(
        "es-MX",
        {
            style: "currency",
            currency: "MXN",
        }
    ).format(Number(value || 0));
}
</script>
<style scoped>
table {
    width: 100%;
    border-collapse: collapse
}

th,
td {
    padding: 9px 12px;
    border-bottom: 1px solid #d8deea;
    text-align: left
}

.group td {
    font-size: 1.15rem;
    font-weight: 900;
    background: #edf5ff
}

.subtotal td {
    text-align: right;
    font-weight: 800
}

.totals {
    display: grid;
    grid-template-columns: 1fr 180px;
    margin-top: 15px;
    border-top: 2px solid #0c2e86
}

.totals>* {
    padding: 7px 12px;
    border-bottom: 1px dotted #aeb9d1
}

.totals b {
    text-align: right
}

.totals strong {
    font-size: 1.2rem;
    border-top: 2px solid #0c2e86;
    border-bottom: 2px solid #0c2e86
}
</style>
