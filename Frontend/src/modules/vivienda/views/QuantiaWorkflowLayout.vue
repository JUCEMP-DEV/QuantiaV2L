<template>
  <div class="qw-layout">
    <aside class="qw-sidebar">
      <LogoQuantia class="qw-logo" />
      <nav>
        <button @click="go('/vivienda/dashboard')">⌂ <span>Dashboard</span></button>
        <button @click="go('/vivienda/workflow/proyecto-alcance')">▱ <span>Proyectos</span></button>
        <button :class="{ active: step === 2 }" @click="go('/vivienda/workflow/como-se-construira')">▤
          <span>Como se construira</span></button>
        <button :class="{ active: step === 3 }" @click="go('/vivienda/workflow/planos-revision/carga')">▤
          <span>Documentos e IA</span></button>
        <button :class="{ active: step === 4 }" @click="go('/vivienda/workflow/diseno-vivienda')">▧ <span>Diseño y
            validación</span></button>
        <button :class="{ active: step === 5 }" @click="go('/vivienda/workflow/calculo-cantidades')">◇
          <span>Cuantificación</span></button>
        <button :class="{ active: step === 6 }" @click="go('/vivienda/workflow/presupuesto-resultados')">▥
          <span>Presupuesto y resultados</span></button>
      </nav>
      <div class="qw-user"><b>{{ initial }}</b><span><strong>{{ userName }}</strong><small>{{ profile }}</small></span>
      </div>
    </aside>
    <main class="qw-main">
      <header class="qw-header">
        <ol class="qw-stepper">
          <li v-for="item in steps.filter(item => !(manualMode && item.number === 3))" :key="item.number"
            :class="{ done: item.number < step, active: item.number === step }"><i>{{ item.number < step ? '✓' :
              item.number }}</i><span>{{ item.label }}</span></li>
        </ol>
        <ProjectSaveButton />
      </header>
      <section class="qw-title">
        <div>
          <h1>{{ title }}</h1>
          <p>{{ subtitle }}</p>
        </div>
        <slot name="title-actions" />
      </section>
      <slot />
      <footer v-if="$slots.footer" class="qw-footer">
        <slot name="footer" />
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import ProjectSaveButton from "@/components/design/ProjectSaveButton.vue";
import { useRouter } from "vue-router";
import LogoQuantia from "@/components/common/LogoQuantia.vue";
import { useAuthStore } from "@/stores/authStore";
import { useViviendaStore } from "@/modules/vivienda/store/viviendaStore";
defineProps({ step: { type: Number, required: true }, title: String, subtitle: String, savedText: { type: String, default: "Cambios sincronizados" } });
const router = useRouter(); const auth = useAuthStore();
const vivienda = useViviendaStore();
const manualMode = computed(() => vivienda.datosGeneralesObra?.engineInputs?.modo_diseno === 'dibujar');
const userName = computed(() => auth.user?.nombre || "Jucemp");
const initial = computed(() => userName.value.slice(0, 2).toUpperCase());
const profile = computed(() => auth.accessProfile === "tecnico" ? "Técnico" : "Administrador");
const steps = [
  { number: 1, label: "Proyecto y alcance" }, { number: 2, label: "Cómo se construirá" },
  { number: 3, label: "Planos y revisión" }, { number: 4, label: "Diseño y validación" },
  { number: 5, label: "Cuantificación" }, { number: 6, label: "Presupuesto y resultados" },
];
function go(path) { router.push(path); }
</script>

<style scoped>
.qw-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 220px 1fr;
  background: #fbfcff;
  color: #071a62;
  font-family: Inter, system-ui, sans-serif
}

.qw-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 18px 14px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e9f3;
  background: #fff
}

.qw-logo {
  max-height: 92px;
  overflow: hidden
}

.qw-sidebar nav {
  display: grid;
  gap: 7px;
  margin-top: 45px
}

.qw-sidebar button {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 13px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #162a76;
  text-align: left;
  cursor: pointer
}

.qw-sidebar button.active,
.qw-sidebar button:hover {
  color: #2519ee;
  background: #f0efff
}

.qw-user {
  margin-top: auto;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid #e2e6f0;
  border-radius: 12px
}

.qw-user>b {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, #1449ff, #5914e8)
}

.qw-user span strong,
.qw-user span small {
  display: block
}

.qw-user small {
  margin-top: 3px;
  color: #7883a4
}

.qw-main {
  min-width: 0;
  padding: 0 24px 82px
}

.qw-header {
  min-height: 104px;
  display: grid;
  grid-template-columns: 1fr 205px;
  gap: 20px;
  align-items: center;
  border-bottom: 1px solid #e4e8f1
}

.qw-stepper {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  list-style: none;
  margin: 0;
  padding: 0
}

.qw-stepper li {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 7px;
  color: #53618f;
  text-align: center;
  font-size: .72rem
}

.qw-stepper li:after {
  content: "";
  position: absolute;
  top: 18px;
  left: calc(50% + 23px);
  right: calc(-50% + 23px);
  height: 2px;
  background: #dfe3ec
}

.qw-stepper li:last-child:after {
  display: none
}

.qw-stepper i {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border: 1px solid #d9deea;
  border-radius: 50%;
  background: #fff;
  font-style: normal;
  font-weight: 800;
  z-index: 1
}

.qw-stepper .done i {
  color: #fff;
  border-color: #08a551;
  background: #08a551
}

.qw-stepper .done:after {
  background: #08a551
}

.qw-stepper .active {
  color: #2519ec
}

.qw-stepper .active i {
  color: #fff;
  border-color: #3219ec;
  background: linear-gradient(135deg, #144cff, #5214e7)
}

.qw-saved {
  display: flex;
  gap: 9px;
  color: #0aa14c
}

.qw-saved span strong,
.qw-saved span small {
  display: block
}

.qw-saved small {
  margin-top: 4px;
  color: #7782a6
}

.qw-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 8px 16px
}

.qw-title h1 {
  margin: 0 0 6px;
  font-size: 1.55rem
}

.qw-title p {
  margin: 0;
  color: #58678f
}

.qw-footer {
  position: fixed;
  left: 220px;
  right: 0;
  bottom: 0;
  min-height: 68px;
  padding: 10px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #e0e5ef;
  background: rgba(255, 255, 255, .96);
  z-index: 5
}

@media(max-width:900px) {
  .qw-layout {
    grid-template-columns: 76px 1fr
  }

  .qw-sidebar button span,
  .qw-user span {
    display: none
  }

  .qw-main {
    padding-inline: 12px
  }

  .qw-header {
    grid-template-columns: 1fr
  }

  .qw-saved {
    display: none
  }

  .qw-stepper li span {
    display: none
  }

  .qw-footer {
    left: 76px
  }

  .qw-sidebar {
    padding-inline: 8px
  }
}

@media(max-width:600px) {
  .qw-layout {
    display: block
  }

  .qw-sidebar {
    display: none
  }

  .qw-footer {
    left: 0
  }

  .qw-main {
    padding-bottom: 85px
  }
}
</style>
