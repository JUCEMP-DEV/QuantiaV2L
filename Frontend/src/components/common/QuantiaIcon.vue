<template>
    <!-- =====================================================
       CONDICIONES DEL TERRENO
       ===================================================== -->

    <!-- TERRENO REGULAR / PLANO -->
    <svg v-if="name === 'terrain-flat'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 17h18" />
        <path d="M5 13h14" />
        <path d="M7 13v4M12 13v4M17 13v4" />
        <path d="M4 20h16" />
    </svg>

    <!-- TERRENO CON PENDIENTE -->
    <svg v-else-if="name === 'terrain-slope'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 18 20 7" />
        <path d="M3 21h18" />
        <path d="M6 16v5M11 13v8M16 10v11" />
    </svg>

    <!-- TERRENO LIMPIO -->
    <svg v-else-if="name === 'terrain-clean'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 17h18" />
        <path d="M5 20h14" />
        <path d="m15 8 1.2 2.5L19 12l-2.8 1.5L15 16l-1.2-2.5L11 12l2.8-1.5Z" />
    </svg>

    <!-- TERRENO CON VEGETACIÓN -->
    <svg v-else-if="name === 'terrain-vegetation'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 19h18" />
        <path d="M7 19c0-4 1-7 4-10" />
        <path d="M11 9c-3 0-5-1-6-4 4 0 6 1 6 4Z" />
        <path d="M12 14c1-3 3-5 6-6 0 4-2 6-6 6Z" />
    </svg>

    <!-- TERRENO MIXTO -->
    <svg v-else-if="name === 'terrain-mixed'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 19h18" />
        <path d="M4 16 10 12l4 2 6-5" />
        <path d="M6 16v3M12 13v6M18 11v8" />
    </svg>

    <!-- ESCOMBRO -->
    <svg v-else-if="name === 'rubble'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 19h18" />
        <path d="m5 17 3-5 4 3 3-6 4 8" />
        <path d="m8 12 2-4 3 2" />
    </svg>

    <!-- ACCESO NORMAL -->
    <svg v-else-if="name === 'access-normal'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M8 21 10 3M16 21 14 3" />
        <path d="M12 5v3M12 11v3M12 17v3" />
        <path d="M5 21h14" />
    </svg>

    <!-- ACCESO LIMITADO -->
    <svg v-else-if="name === 'access-limited'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M9 21 10.5 3M15 21 13.5 3" />
        <path d="M12 6v3M12 12v3M12 18v2" />
        <path d="M4 8h4M16 8h4" />
        <path d="m6 6-2 2 2 2M18 6l2 2-2 2" />
    </svg>

    <!-- DEMOLICIÓN -->
    <svg v-else-if="name === 'demolition'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M4 20h16" />
        <path d="M6 20V9l6-5 6 5v11" />
        <path d="m7 11 4 3-3 3M17 10l-4 3 3 4" />
    </svg>

    <!-- =====================================================
       SISTEMAS CONSTRUCTIVOS
       ===================================================== -->

    <!-- MAMPOSTERÍA -->
    <svg v-else-if="name === 'masonry'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="1" />
        <path d="M3 10h18M3 15h18" />
        <path d="M8 5v5M16 5v5" />
        <path d="M6 10v5M14 10v5" />
        <path d="M9 15v4M17 15v4" />
    </svg>

    <!-- CONCRETO REFORZADO -->
    <svg v-else-if="name === 'reinforced-concrete'" class="quantia-icon" :width="size" :height="size"
        viewBox="0 0 24 24" fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M5 21V5M19 21V5M5 6h14" />
        <path d="M8 21V10h8v11" />
        <path d="M3 21h18" />
        <path d="M7 5V3M12 5V3M17 5V3" />
    </svg>

    <!-- SISTEMA MIXTO -->
    <svg v-else-if="name === 'mixed-structure'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M4 21V4M20 21V4M4 5h16" />
        <rect x="7" y="9" width="10" height="12" />
        <path d="M7 13h10M7 17h10" />
        <path d="M12 9v4M10 13v4M14 17v4" />
    </svg>

    <!-- =====================================================
       CIMENTACIÓN
       ===================================================== -->

    <!-- CIMENTACIÓN GENERAL -->
    <svg v-else-if="name === 'foundation'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M9 4h6v9H9z" />
        <path d="M6 13h12l3 6H3z" />
        <path d="M2 21h20" />
    </svg>

    <!-- CIMENTACIÓN DE MAMPOSTERÍA -->
    <svg v-else-if="name === 'masonry-foundation'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M9 4h6v6H9z" />
        <path d="M7 10h10l3 9H4z" />
        <path d="M8 13h8M6 16h12" />
        <path d="M2 21h20" />
    </svg>

    <!-- ZAPATA CORRIDA -->
    <svg v-else-if="name === 'strip-footing'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M9 4h6v10H9z" />
        <path d="M4 14h16v5H4z" />
        <path d="M2 21h20" />
    </svg>

    <!-- ZAPATA AISLADA -->
    <svg v-else-if="name === 'isolated-footing'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M10 3h4v10h-4z" />
        <path d="M6 13h12l2 6H4z" />
        <path d="M2 21h20" />
    </svg>

    <!-- ZAPATA AISLADA + TRABE DE LIGA -->
    <svg v-else-if="name === 'isolated-footing-beam'" class="quantia-icon" :width="size" :height="size"
        viewBox="0 0 24 24" fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M4 5h3v8H4zM17 5h3v8h-3z" />
        <path d="M2 13h7l1 5H1z" />
        <path d="M15 13h7l1 5h-9z" />
        <path d="M7 9h10v3H7z" />
        <path d="M1 20h22" />
    </svg>

    <!-- =====================================================
       LOSAS
       ===================================================== -->

    <!-- LOSA GENERAL -->
    <svg v-else-if="name === 'slab'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 8h18v6H3z" />
        <path d="M6 14v5M18 14v5" />
        <path d="M3 19h18" />
    </svg>

    <!-- LOSA MACIZA -->
    <svg v-else-if="name === 'solid-slab'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="3" y="8" width="18" height="7" rx="1" />
        <path d="M5 11h14" />
        <path d="M7 15v4M17 15v4" />
    </svg>

    <!-- VIGUETA Y BOVEDILLA -->
    <svg v-else-if="name === 'joist-block-slab'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 7h18v3H3z" />
        <path d="M4 10v8M9 10v8M15 10v8M20 10v8" />
        <path d="M4 18h5M9 18h6M15 18h5" />
        <path d="M5 13h3v3H5zM10 13h4v3h-4zM16 13h3v3h-3z" />
    </svg>

    <!-- CASETÓN Y NERVADURAS -->
    <svg v-else-if="name === 'waffle-slab'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="3" y="5" width="18" height="14" rx="1" />
        <path d="M9 5v14M15 5v14" />
        <path d="M3 10h18M3 15h18" />
    </svg>

    <!-- =====================================================
       INSTALACIONES
       ===================================================== -->

    <!-- INSTALACIONES GENERAL -->
    <svg v-else-if="name === 'utilities'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M12 3v6" />
        <path d="M6 9h12" />
        <path d="M6 9v6a3 3 0 0 0 3 3h3" />
        <path d="M18 9v6a3 3 0 0 1-3 3h-3" />
        <path d="M12 18v3" />
    </svg>

    <!-- SANITARIA -->
    <svg v-else-if="name === 'sanitary'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M5 4v6a3 3 0 0 0 3 3h4" />
        <path d="M19 4v5a4 4 0 0 1-4 4h-3" />
        <path d="M12 13v8" />
        <path d="m9 18 3 3 3-3" />
    </svg>

    <!-- =====================================================
       DISEÑO ARQUITECTÓNICO
       ===================================================== -->

    <!-- PLANTA -->
    <svg v-else-if="name === 'floor-plan'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 3h18v18H3z" />
        <path d="M11 3v8H3" />
        <path d="M11 8h10" />
        <path d="M15 8v13" />
        <path d="M3 16h12" />
    </svg>

    <!-- HABITACIÓN -->
    <svg v-else-if="name === 'room'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="4" y="4" width="16" height="16" rx="1" />
        <path d="M9 20v-5h5" />
        <path d="M14 15a5 5 0 0 1 5 5" />
    </svg>

    <!-- MURO -->
    <svg v-else-if="name === 'wall'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="3" y="6" width="18" height="12" rx="1" />
        <path d="M3 10h18M3 14h18" />
        <path d="M8 6v4M16 6v4M6 10v4M14 10v4M9 14v4M17 14v4" />
    </svg>

    <!-- PUERTA -->
    <svg v-else-if="name === 'door'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M5 21V3h12v18" />
        <path d="M17 21h3" />
        <path d="M9 12h.01" />
        <path d="M5 21h12" />
    </svg>

    <!-- VENTANA -->
    <svg v-else-if="name === 'window'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="4" y="4" width="16" height="16" rx="1" />
        <path d="M12 4v16M4 12h16" />
    </svg>

    <!-- ARISTA -->
    <svg v-else-if="name === 'edge'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <circle cx="5" cy="17" r="2" />
        <circle cx="19" cy="7" r="2" />
        <path d="M7 16 17 8" />
    </svg>

    <!-- VÉRTICE -->
    <svg v-else-if="name === 'vertex'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <circle cx="12" cy="12" r="2.5" />
        <path d="M12 9.5V3M9.5 12H3M14.5 12H21M12 14.5V21" />
    </svg>

    <!-- DOBLE ALTURA -->
    <svg v-else-if="name === 'double-height'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M5 21V3h14v18" />
        <path d="M5 12h5M14 12h5" />
        <path d="M12 5v14" />
        <path d="m9 8 3-3 3 3M9 16l3 3 3-3" />
    </svg>

    <!-- NIVELES -->
    <svg v-else-if="name === 'levels'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="m12 3 9 4-9 4-9-4Z" />
        <path d="m3 12 9 4 9-4" />
        <path d="m3 17 9 4 9-4" />
    </svg>

    <!-- MEDICIÓN -->
    <svg v-else-if="name === 'measure'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="m4 17 13-13 3 3L7 20z" />
        <path d="m9 12 3 3M12 9l3 3M15 6l3 3" />
    </svg>

    <!-- =====================================================
       CUANTIFICACIÓN
       ===================================================== -->

    <!-- ÁREA -->
    <svg v-else-if="name === 'area'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <rect x="4" y="4" width="16" height="16" rx="1" />
        <path d="M7 7h4M7 7v4M17 17h-4M17 17v-4" />
        <text x="12" y="14" text-anchor="middle" font-size="5" fill="currentColor" stroke="none">
            m²
        </text>
    </svg>

    <!-- LONGITUD -->
    <svg v-else-if="name === 'length'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M4 12h16" />
        <path d="m7 9-3 3 3 3M17 9l3 3-3 3" />
        <path d="M4 6v12M20 6v12" />
    </svg>

    <!-- VOLUMEN -->
    <svg v-else-if="name === 'volume'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="m12 3 8 4v10l-8 4-8-4V7z" />
        <path d="m4 7 8 4 8-4" />
        <path d="M12 11v10" />
    </svg>

    <!-- CANTIDADES -->
    <svg v-else-if="name === 'quantities'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M4 19V8l8-4 8 4v11l-8 3z" />
        <path d="m4 8 8 4 8-4" />
        <path d="M12 12v10" />
        <path d="M7 15h2M15 15h2" />
    </svg>

    <!-- =====================================================
       PRESUPUESTO
       ===================================================== -->

    <!-- MATERIALES -->
    <svg v-else-if="name === 'materials'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24"
        fill="none" :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M3 18h18" />
        <path d="M5 18V9h6v9" />
        <path d="M13 18V5h6v13" />
        <path d="M7 12h2M15 8h2M15 12h2" />
    </svg>

    <!-- PRESUPUESTO -->
    <svg v-else-if="name === 'budget'" class="quantia-icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none"
        :stroke-width="strokeWidth" aria-hidden="true">
        <path d="M6 3h12v18H6z" />
        <path d="M9 7h6M9 17h6" />
        <path d="M12 8.5v7" />
        <path d="M14 10c-.5-.6-1.2-1-2-1-1.1 0-2 .6-2 1.5s.9 1.5 2 1.5 2 .6 2 1.5-.9 1.5-2 1.5c-.8 0-1.5-.3-2-.8" />
    </svg>

    <!-- =====================================================
       LUCIDE / GENERALES
       ===================================================== -->

    <component v-else :is="iconComponent" :size="size" :stroke-width="strokeWidth" aria-hidden="true"
        class="quantia-icon" />
</template>

<script setup>
import { computed } from "vue";

import {
    ArrowLeft,
    ArrowRight,
    BadgeDollarSign,
    Bot,
    BrickWall,
    Building2,
    Calculator,
    Check,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    CircleHelp,
    CircleUserRound,
    ClipboardList,
    Clock3,
    Construction,
    Database,
    Download,
    Droplets,
    Expand,
    FileCheck2,
    FileImage,
    FileSearch,
    FileText,
    Flame,
    FolderOpen,
    Gauge,
    HardHat,
    House,
    Image,
    Info,
    LandPlot,
    Layers3,
    LogOut,
    Map,
    MapPin,
    Menu,
    MousePointer2,
    Move,
    Package,
    PaintRoller,
    Pencil,
    Plus,
    Printer,
    ReceiptText,
    Redo2,
    RotateCcw,
    Ruler,
    Save,
    ScanLine,
    ScanText,
    Search,
    Settings,
    Sparkles,
    Trash2,
    TriangleAlert,
    Undo2,
    Upload,
    User,
    UserCheck,
    Wifi,
    X,
    Zap,
    ZoomIn,
    ZoomOut,
} from "lucide-vue-next";

const props = defineProps({
    name: {
        type: String,
        required: true,
    },

    size: {
        type: [Number, String],
        default: 24,
    },

    strokeWidth: {
        type: [Number, String],
        default: 1.8,
    },
});

/* =========================================================
   CATÁLOGO GENERAL
   ========================================================= */

const icons = {
    /* Navegación */
    "arrow-left": ArrowLeft,
    "arrow-right": ArrowRight,
    "chevron-left": ChevronLeft,
    "chevron-right": ChevronRight,
    "chevron-down": ChevronDown,

    /* Estados */
    check: Check,
    close: X,
    plus: Plus,
    info: Info,
    help: CircleHelp,
    warning: TriangleAlert,
    pending: Clock3,

    /* Usuario */
    user: User,
    account: CircleUserRound,
    "user-check": UserCheck,

    /* Proyecto */
    home: House,
    project: ClipboardList,
    clipboard: ClipboardList,
    building: Building2,
    "brick-wall": BrickWall,
    construction: Construction,
    "land-plot": LandPlot,

    /* Ubicación */
    location: MapPin,
    map: Map,

    /* Documentos */
    file: FileText,
    plan: FileImage,
    image: Image,
    folder: FolderOpen,
    upload: Upload,
    download: Download,
    "file-search": FileSearch,
    "file-check": FileCheck2,

    /* IA */
    ai: Sparkles,
    bot: Bot,
    scan: ScanLine,
    "scan-line": ScanLine,
    "scan-text": ScanText,
    confidence: Gauge,

    /* Edición */
    pencil: Pencil,
    edit: Pencil,
    ruler: Ruler,
    select: MousePointer2,
    move: Move,
    "zoom-in": ZoomIn,
    "zoom-out": ZoomOut,
    undo: Undo2,
    redo: Redo2,
    reset: RotateCcw,
    expand: Expand,

    /* Instalaciones */
    droplets: Droplets,
    zap: Zap,
    flame: Flame,
    wifi: Wifi,

    /* Cálculo */
    calculator: Calculator,
    package: Package,

    /* Presupuesto */
    receipt: ReceiptText,
    price: BadgeDollarSign,
    "hard-hat": HardHat,
    paint: PaintRoller,
    printer: Printer,

    /* Sistema */
    layers: Layers3,
    database: Database,
    save: Save,
    search: Search,
    settings: Settings,
    trash: Trash2,
    logout: LogOut,
    menu: Menu,
};

/* =========================================================
   ALIASES CANÓNICOS
   ========================================================= */

const aliases = {
    /* 01 Proyecto y alcance */
    "clipboard-project": "project",
    "file-project": "file",
    "house-new": "home",
    "house-existing": "building",
    "list-concepts": "clipboard",
    renovation: "construction",
    "expand-house": "expand",

    /* 03 Planos */
    "upload-plan": "upload",
    "cad-plan": "plan",

    /* 04 Diseño */
    draw: "pencil",
    annotation: "pencil",

    /* 05 Cantidades */
    piece: "package",

    /* 06 Presupuesto */
    labor: "hard-hat",
    equipment: "construction",
    results: "calculator",
};

/* =========================================================
   COMPONENTE RESUELTO
   ========================================================= */

const iconComponent = computed(() => {
    const resolvedName =
        aliases[props.name] || props.name;

    return (
        icons[resolvedName] ||
        CircleHelp
    );
});
</script>

<style scoped>
.quantia-icon {
    display: block;
    flex-shrink: 0;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
}
</style>