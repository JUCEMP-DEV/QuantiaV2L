import LandingView from "@/modules/vivienda/views/01LandingView.vue";
import LoginView from "@/modules/vivienda/views/02LoginView.vue";
import RegisterView from "@/modules/vivienda/views/03RegistroUsuarioView.vue";
const ProfileSettingsView = () =>
  import("@/modules/vivienda/views/04ProfileSettingsView.vue");
const DashboardView = () =>
  import("@/modules/vivienda/views/DashboardView.vue");
const DocumentosView = () =>
  import("@/modules/vivienda/views/DocumentosView.vue");

// Workflow
const ProyectoAlcanceView = () =>
  import("@/modules/vivienda/views/workflow/01ProyectoAlcanceView.vue");
const ComoSeConstruiraView = () =>
  import("@/modules/vivienda/views/workflow/02ComoSeConstruiraView.vue");
const CargaDocumentosView = () =>
  import("@/modules/vivienda/views/workflow/03_1CargaDocumentosView.vue");
const AnalisisIAView = () =>
  import("@/modules/vivienda/views/workflow/03_2AnalisisIAView.vue");
// 04 — Diseño de la vivienda
// "Desde plano" usa temporalmente 04DisenoViviendaView.vue hasta crear
// 04DisenoDesdePlanoView.vue. La ruta no tendrá que cambiar cuando se sustituya.
const DisenoDesdePlanoView = () =>
  import("@/modules/vivienda/views/workflow/04DisenoViviendaView.vue");
const DisenoManualView = () =>
  import("@/modules/vivienda/views/workflow/04DisenoManualView.vue");
const CalculoCantidadesView = () =>
  import("@/modules/vivienda/views/workflow/05CalculoCantidadesView.vue");
const PresupuestoResultadosView = () =>
  import("@/modules/vivienda/views/workflow/06PresupuestoResultadosView.vue");

// Imprimibles
const ImprimiblePresupuestoView = () =>
  import("@/modules/vivienda/views/print/06_1ImprimiblePresupuestoView.vue");
const ImprimibleManoObraView = () =>
  import("@/modules/vivienda/views/print/06_2ImprimibleManoObraView.vue");
const ImprimibleMaterialesView = () =>
  import("@/modules/vivienda/views/print/06_3ImprimibleMaterialesView.vue");


const viviendaRoutes = [

  // ============================================================
  // ACCESO
  // ============================================================

  {
    path: "/vivienda",
    redirect: "/vivienda/landing",
  },

  {
    path: "/vivienda/landing",
    name: "vivienda-landing",
    component: LandingView,
    meta: {
      title: "Quantia Vivienda",
      step: 0,
    },
  },

  {
    path: "/vivienda/acceso",
    redirect: "/vivienda/login",
    meta: {
      title: "Login | Quantia Vivienda",
      step: 0,
    },
  },

  {
    path: "/vivienda/login",
    name: "vivienda-login",
    component: LoginView,
    meta: {
      title: "Login | Quantia Vivienda",
      step: 1,
    },
  },

  {
    path: "/vivienda/registro",
    name: "vivienda-registro-usuario",
    component: RegisterView,
    meta: {
      title: "Registro | Quantia Vivienda",
      step: 1,
    },
  },

  {
    path: "/vivienda/dashboard",
    name: "vivienda-dashboard",
    component: DashboardView,
    meta: {
      title: "Dashboard | Quantia Vivienda",
      step: 2,
      requiresAuth: true,
    },
  },

  {
    path: "/vivienda/perfil",
    name: "vivienda-perfil",
    component: ProfileSettingsView,
    meta: {
      title: "Perfil de usuario | Quantia Vivienda",
      step: 2,
      requiresAuth: true,
    },
  },

  {
    path: "/vivienda/documentos",
    name: "vivienda-documentos",
    component: DocumentosView,
    meta: {
      title: "Documentos | Quantia Vivienda",
      step: 2,
      requiresAuth: true,
    },
  },


  // ============================================================
  // WORKFLOW
  // ============================================================

  // 01 — Proyecto y alcance
  {
    path: "/vivienda/workflow/proyecto-alcance",
    name: "workflow-proyecto-alcance",
    component: ProyectoAlcanceView,
    meta: {
      title: "Proyecto y alcance | Quantia Vivienda",
      step: 1,
      requiresAuth: true,
    },
  },

  // 02 — Cómo se construirá
  {
    path: "/vivienda/workflow/como-se-construira",
    name: "workflow-como-se-construira",
    component: ComoSeConstruiraView,
    meta: {
      title: "Cómo se construirá | Quantia Vivienda",
      step: 2,
      requiresAuth: true,
    },
  },

  // 03.1 — Carga de documentos
  {
    path: "/vivienda/workflow/planos-revision/carga",
    name: "workflow-planos-revision-carga",
    component: CargaDocumentosView,
    meta: {
      title: "Planos y revisión | Quantia Vivienda",
      step: 3,
      requiresAuth: true,
    },
  },

  // 03.2 — Análisis con IA
  {
    path: "/vivienda/workflow/planos-revision/analisis",
    name: "workflow-planos-revision-analisis",
    component: AnalisisIAView,
    meta: {
      title: "Análisis con IA | Quantia Vivienda",
      step: 3,
      requiresAuth: true,
    },
  },

  // 04 — Diseño de la vivienda
  // Ruta base conservada como compatibilidad.
  // Por ahora entra a la variante "desde plano".
  {
    path: "/vivienda/workflow/diseno-vivienda",
    name: "workflow-diseno-vivienda",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },

  // 04A — Diseño desde plano / reconstrucción 03.2
  {
    path: "/vivienda/workflow/diseno-vivienda/plano",
    name: "workflow-diseno-vivienda-plano",
    component: DisenoDesdePlanoView,
    meta: {
      title: "Diseño desde plano | Quantia Vivienda",
      step: 4,
      requiresAuth: true,
      designMode: "plan",
    },
  },

  // 04B — Diseño manual / "Dibújalo tú"
  {
    path: "/vivienda/workflow/diseno-vivienda/manual",
    name: "workflow-diseno-vivienda-manual",
    component: DisenoManualView,
    meta: {
      title: "Diseño manual | Quantia Vivienda",
      step: 4,
      requiresAuth: true,
      designMode: "manual",
    },
  },

  // 05 — Cálculo de cantidades
  {
    path: "/vivienda/workflow/calculo-cantidades",
    name: "workflow-calculo-cantidades",
    component: CalculoCantidadesView,
    meta: {
      title: "Cálculo de cantidades | Quantia Vivienda",
      step: 5,
      requiresAuth: true,
    },
  },

  // 06 — Presupuesto y resultados
  {
    path: "/vivienda/workflow/presupuesto-resultados",
    name: "workflow-presupuesto-resultados",
    component: PresupuestoResultadosView,
    meta: {
      title: "Presupuesto y resultados | Quantia Vivienda",
      step: 6,
      requiresAuth: true,
    },
  },


  // ============================================================
  // IMPRIMIBLES
  // ============================================================

  {
    path: "/vivienda/print/presupuesto",
    name: "print-presupuesto",
    component: ImprimiblePresupuestoView,
    meta: {
      title: "Presupuesto | Quantia Vivienda",
      requiresAuth: true,
    },
  },

  {
    path: "/vivienda/print/mano-obra",
    name: "print-mano-obra",
    component: ImprimibleManoObraView,
    meta: {
      title: "Mano de obra | Quantia Vivienda",
      requiresAuth: true,
    },
  },

  {
    path: "/vivienda/print/materiales",
    name: "print-materiales",
    component: ImprimibleMaterialesView,
    meta: {
      title: "Listado de materiales | Quantia Vivienda",
      requiresAuth: true,
    },
  },


  // ============================================================
  // COMPATIBILIDAD CON RUTAS LEGACY
  // ============================================================

  // Proyecto y alcance
  {
    path: "/vivienda/cotizacion/registro",
    redirect: "/vivienda/workflow/proyecto-alcance",
  },
  {
    path: "/vivienda/cotizacion/clasificacion",
    redirect: "/vivienda/workflow/proyecto-alcance",
  },
  {
    path: "/vivienda/cotizacion/alcance",
    redirect: "/vivienda/workflow/proyecto-alcance",
  },

  // Cómo se construirá
  {
    path: "/vivienda/cotizacion/parametrizacion",
    redirect: "/vivienda/workflow/como-se-construira",
  },
  {
    path: "/vivienda/cotizacion/preliminares",
    redirect: "/vivienda/workflow/como-se-construira",
  },

  // Planos y revisión
  {
    path: "/vivienda/cotizacion/documentos/carga",
    redirect: "/vivienda/workflow/planos-revision/carga",
  },
  {
    path: "/vivienda/cotizacion/documentos/analisis",
    redirect: "/vivienda/workflow/planos-revision/analisis",
  },

  // Diseño de la vivienda
  {
    path: "/vivienda/cotizacion/documentos/revision",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/diseno-validacion",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/modelo-espacial",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/datos-generales",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/estructura-espacial",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/colindancias",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/validacion-espacial",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/variables",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },
  {
    path: "/vivienda/cotizacion/parametros",
    redirect: "/vivienda/workflow/diseno-vivienda/plano",
  },

  // Cálculo de cantidades
  {
    path: "/vivienda/cotizacion/calculo-cantidades",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/cimentacion",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/estructura",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/albanileria",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/instalaciones",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/acabados",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/complementarios",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/revision-inferencia",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },
  {
    path: "/vivienda/cotizacion/resumen",
    redirect: "/vivienda/workflow/calculo-cantidades",
  },

  // Presupuesto y resultados
  {
    path: "/vivienda/cotizacion/presupuesto-resultados",
    redirect: "/vivienda/workflow/presupuesto-resultados",
  },
  {
    path: "/vivienda/cotizacion/resultados",
    redirect: "/vivienda/workflow/presupuesto-resultados",
  },

  // Imprimibles antiguos
  {
    path: "/vivienda/cotizacion/imprimible-presupuesto",
    redirect: "/vivienda/print/presupuesto",
  },
  {
    path: "/vivienda/cotizacion/imprimible-mano-obra",
    redirect: "/vivienda/print/mano-obra",
  },
  {
    path: "/vivienda/cotizacion/imprimible-materiales",
    redirect: "/vivienda/print/materiales",
  },
];

export default viviendaRoutes;
