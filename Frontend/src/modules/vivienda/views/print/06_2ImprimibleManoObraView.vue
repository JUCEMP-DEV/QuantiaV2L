<template>
    <QuantiaPrintableShell title="COSTO DE MANO DE OBRA"
        footer="Información obtenida de la explosión de tarjetas de precios unitarios en PU-Core.">
        <section class="metrics">
            <div>Conceptos incluidos <b>{{ rows.length }}</b></div>
            <div>Partidas <b>{{ groups.length }}</b></div>
            <div>Costo total <b>{{ money(total) }}</b></div>
        </section>
        <p v-if="!rows.length" class="warning">La inferencia no incluye el desglose de mano de obra. Verifica que las
            tarjetas publicadas en PU-Core contengan insumos de tipo mano de obra.</p>
        <table v-else>
            <thead>
                <tr>
                    <th>Clave</th>
                    <th>Concepto</th>
                    <th>Unidad</th>
                    <th>Cantidad</th>
                    <th>M.O. unitaria</th>
                    <th>Importe M.O.</th>
                </tr>
            </thead>
            <tbody v-for="g in groups" :key="g.name">
                <tr class="group">
                    <td colspan="6">{{ g.name }}</td>
                </tr>
                <tr v-for="x in g.items" :key="x.key">
                    <td>{{ x.key }}</td>
                    <td>{{ x.title }}</td>
                    <td>{{ x.unit }}</td>
                    <td>{{ x.quantity }}</td>
                    <td>{{ money(x.laborUnit) }}</td>
                    <td>{{ money(x.laborTotal) }}</td>
                </tr>
                <tr class="subtotal">
                    <td colspan="5">Subtotal {{ g.name }}</td>
                    <td>{{ money(g.total) }}</td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="5">TOTAL MANO DE OBRA</td>
                    <td>{{ money(total) }}</td>
                </tr>
            </tfoot>
        </table>
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

const rows = computed(() =>
    concepts.value
        .map((item) => ({
            ...item,

            laborUnit: Number(
                item.laborUnitPrice ??
                item.manoObraUnitario ??
                0
            ),

            laborTotal: Number(
                item.laborTotal ??
                item.manoObraTotal ??
                0
            ),
        }))
        .filter(
            (item) => item.laborTotal > 0
        )
);

const groups = computed(() => {
    const map = {};

    rows.value.forEach((item) => {
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
                    sum + Number(item.laborTotal || 0),
                0
            ),
        })
    );
});

const total = computed(() =>
    rows.value.reduce(
        (sum, item) =>
            sum + Number(item.laborTotal || 0),
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
.metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin: 20px 0;
    border: 1px solid #aebde1
}

.metrics div {
    padding: 20px
}

.metrics b {
    display: block;
    margin-top: 8px;
    font-size: 1.7rem;
    color: #123fd9
}

.warning {
    padding: 20px;
    border: 1px solid #ffd59d;
    background: #fff8e9;
    color: #865200
}

table {
    width: 100%;
    border-collapse: collapse
}

th,
td {
    padding: 9px 12px;
    border: 1px solid #cbd5e9;
    text-align: left
}

th,
tfoot {
    color: #fff;
    background: #06256e
}

.group td {
    font-size: 1.15rem;
    font-weight: 900;
    color: #1244d6;
    background: #eef5ff
}

.subtotal td {
    text-align: right;
    font-weight: 800
}

tfoot td {
    font-size: 1.2rem;
    font-weight: 900
}
</style>
