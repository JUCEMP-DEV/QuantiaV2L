<template>
    <div class="print-page">
        <header>
            <LogoQuantia />
            <dl>
                <dt>Proyecto:</dt>
                <dd>{{ project }}</dd>
                <dt>Ubicación:</dt>
                <dd>{{ location }}</dd>
                <dt>Folio:</dt>
                <dd>{{ folio }}</dd>
                <dt>Fecha:</dt>
                <dd>{{ date }}</dd>
            </dl>
        </header>
        <h1>{{ title }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
        <slot />
        <footer>{{ footer }}</footer>

        <div class="print-actions">
            <button class="back-button" @click="goBack">
                ← Volver al presupuesto
            </button>

            <button class="print-button" @click="print">
                Imprimir / Guardar PDF
            </button>
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
import LogoQuantia from "@/components/common/LogoQuantia.vue";

defineProps({
    title: String,
    subtitle: String,
    footer: String,
});

const router = useRouter();
const store = useViviendaStore();

const project = computed(
    () =>
        store.registro?.proyecto?.nombre ||
        "Proyecto de vivienda"
);

const location = computed(() => {
    const ubicacion = store.registro?.ubicacion || {};

    return [
        ubicacion.localidad,
        ubicacion.municipio,
        ubicacion.estado,
    ]
        .filter(Boolean)
        .join(", ") || "Sin ubicación";
});

const folio = computed(
    () =>
        store.registro?.proyecto?.folio ||
        "Sin folio"
);

const date = computed(() => {
    const savedDate =
        store.registro?.proyecto?.fecha;

    if (!savedDate) {
        return new Intl.DateTimeFormat(
            "es-MX"
        ).format(new Date());
    }

    const parsed = new Date(
        `${savedDate}T00:00:00`
    );

    return new Intl.DateTimeFormat(
        "es-MX"
    ).format(parsed);
});

function goBack() {
    router.push(
        "/vivienda/workflow/presupuesto-resultados"
    );
}

function print() {
    window.print();
}
</script>

<style scoped>
.print-page {
    width: min(100%, 1050px);
    min-height: 1400px;
    margin: 20px auto;
    padding: 34px 38px;
    color: #071a62;
    background: #fff;
    font-family: Inter, system-ui, sans-serif;
    box-shadow: 0 5px 30px #dce2ef
}

.print-page>header {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    align-items: center;
    padding-bottom: 22px;
    border-bottom: 2px solid #153aa7
}

.print-page>header :deep(img) {
    max-width: 470px;
    max-height: 170px;
    object-fit: contain;
}

.print-page dl {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 12px;
    margin: 0;
    padding-left: 28px;
    border-left: 1px solid #27479f
}

.print-page dt {
    font-weight: 500
}

.print-page dd {
    margin: 0;
    font-weight: 800
}

.print-page h1 {
    margin: 25px 0 5px;
    font-size: 2.25rem
}

.subtitle {
    margin: 0 0 25px;
    color: #52628e
}

.print-page>footer {
    margin-top: 20px;
    padding-top: 10px;
    border-top: 1px solid #9eb0dd;
    font-size: .82rem
}

.print-actions {
    position: fixed;
    right: 28px;
    bottom: 28px;
    display: flex;
    gap: 10px;
}

.print-button,
.back-button {
    padding: 14px 22px;
    border-radius: 9px;
    font-weight: 800;
    cursor: pointer;
}

.print-button {
    border: 0;
    color: #fff;
    background: linear-gradient(90deg,
            #143cff,
            #5815ed);
}

.back-button {
    border: 1px solid #d7deeb;
    color: #14307d;
    background: #fff;
}

@media print {
    .print-page {
        width: 100%;
        min-height: 0;
        margin: 0;
        padding: 18mm;
        box-shadow: none
    }

    .print-actions {
        display: none;
    }
}

@media(max-width:700px) {
    .print-page>header {
        grid-template-columns: 1fr
    }

    .print-page dl {
        border-left: 0;
        padding-left: 0
    }

    .print-page {
        padding: 20px
    }
}
</style>
