<template>
    <QuantiaPrintableShell title="LISTADO DE MATERIALES"
        subtitle="Cantidades consolidadas sin duplicar insumos entre conceptos."
        footer="Información obtenida de la explosión de tarjetas de precios unitarios en PU-Core.">
        <section class="metrics">
            <div>Insumos distintos <b>{{ materials.length }}</b></div>
            <div>Grupos de materiales <b>{{ groups.length }}</b></div>
            <div>Costo estimado <b>{{ money(total) }}</b></div>
        </section>
        <p v-if="!materials.length" class="warning">La inferencia actual no incluye la explosión de insumos de PU-Core.
            Publica o consulta las tarjetas desglosadas antes de generar este listado.</p>
        <table v-else>
            <thead>
                <tr>
                    <th>Clave</th>
                    <th>Conceptos</th>
                    <th>Material</th>
                    <th>Unidad</th>
                    <th>Cantidad requerida</th>
                    <th>Precio unitario</th>
                    <th>Importe</th>
                </tr>
            </thead>

            <tbody v-for="group in groups" :key="group.name">
                <tr class="group">
                    <td colspan="7">
                        {{ group.name }}
                    </td>
                </tr>

                <tr v-for="item in group.items" :key="`${item.key}-${item.unit}`">
                    <td>{{ item.key }}</td>

                    <td>
                        {{ item.conceptKeys.join(", ") }}
                    </td>

                    <td>{{ item.name }}</td>

                    <td>{{ item.unit }}</td>

                    <td>{{ item.quantity }}</td>

                    <td>
                        {{ money(item.unitPrice) }}
                    </td>

                    <td>
                        {{ money(item.total) }}
                    </td>
                </tr>

                <tr class="subtotal">
                    <td colspan="6">
                        Subtotal {{ group.name }}
                    </td>

                    <td>
                        {{ money(group.total) }}
                    </td>
                </tr>
            </tbody>

            <tfoot>
                <tr>
                    <td colspan="6">
                        TOTAL MATERIALES
                    </td>

                    <td>
                        {{ money(total) }}
                    </td>
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

function getMaterialRows(concept) {
    if (Array.isArray(concept.materials)) {
        return concept.materials;
    }

    if (Array.isArray(concept.materiales)) {
        return concept.materiales;
    }

    if (Array.isArray(concept.insumos)) {
        return concept.insumos.filter((item) => {
            const type = String(
                item.insumo_type ??
                item.insumoType ??
                item.tipo ??
                item.type ??
                ""
            )
                .trim()
                .toLowerCase();

            return type === "material";
        });
    }

    return [];
}

const materials = computed(() => {
    const map = new Map();

    for (const concept of concepts.value) {
        for (const item of getMaterialRows(concept)) {
            const key = String(
                item.key ??
                item.clave ??
                item.code ??
                item.id ??
                ""
            );

            if (!key) continue;

            const unit =
                item.unit ??
                item.unidad ??
                "";

            const mapKey = `${key}|${unit}`;

            const quantity = Number(
                item.quantity ??
                item.cantidad ??
                0
            );

            const unitPrice = Number(
                item.unitPrice ??
                item.precioUnitario ??
                item.unit_price ??
                0
            );

            const lineTotal = Number(
                item.total ??
                item.importe ??
                quantity * unitPrice
            );

            const previous = map.get(mapKey) || {
                key,
                name:
                    item.name ??
                    item.nombre ??
                    item.description ??
                    item.descripcion ??
                    "Material",

                unit,

                quantity: 0,
                total: 0,

                group:
                    item.group ??
                    item.categoria ??
                    "Otros",

                conceptKeys: new Set(),
            };

            previous.quantity += quantity;
            previous.total += lineTotal;

            if (concept.key) {
                previous.conceptKeys.add(
                    String(concept.key)
                );
            }

            map.set(mapKey, previous);
        }
    }

    return [...map.values()].map((item) => ({
        ...item,

        quantity:
            Number(item.quantity.toFixed(4)),

        total:
            Number(item.total.toFixed(2)),

        unitPrice:
            item.quantity > 0
                ? Number(
                    (
                        item.total /
                        item.quantity
                    ).toFixed(2)
                )
                : 0,

        conceptKeys:
            [...item.conceptKeys],
    }));
});

const groups = computed(() => {
    const map = {};

    materials.value.forEach((item) => {
        const groupName =
            item.group || "Otros";

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

const total = computed(() =>
    materials.value.reduce(
        (sum, item) =>
            sum + Number(item.total || 0),
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
    border: 1px solid #aebde1;
    border-radius: 8px
}

.metrics div {
    padding: 22px;
    border-right: 1px solid #cbd4e9
}

.metrics div:last-child {
    border: 0
}

.metrics b {
    display: block;
    margin-top: 8px;
    font-size: 1.8rem;
    color: #143ed7
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
    border-bottom: 1px dotted #b9c5df;
    text-align: left
}

th {
    border-bottom: 2px solid #123bad
}

.group td {
    font-size: 1.15rem;
    font-weight: 800;
    color: #123dae;
    background: #eef5ff
}

.subtotal td {
    text-align: right;
    font-weight: 800
}

tfoot td {
    border-top: 3px solid #123dae;
    font-size: 1.25rem;
    font-weight: 900
}
</style>
