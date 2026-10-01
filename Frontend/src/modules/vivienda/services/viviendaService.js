import { buildApiUrl } from "../../../config/apiBaseUrl.js";

const MODULOS_BASE = [
  "preliminares",
  "cimentacion",
  "estructura",
  "albanileria",
  "instalaciones",
  "acabados",
  "complementarios_y_equipamiento",
];

const MODULOS_BASE_REMODELACION = [
  "preliminares",
  "cimentacion",
  "estructura",
  "albanileria",
];

const ALCANCES_OBRA_NUEVA = {
  obra_negra: ["preliminares", "cimentacion", "estructura", "albanileria"],
  obra_gris: ["preliminares", "cimentacion", "estructura", "albanileria", "instalaciones"],
  obra_completa: [...MODULOS_BASE],
  // Compatibilidad con dato previo para no romper sesiones antiguas.
  obra_blanca: [...MODULOS_BASE],
};

export function getTiposIntervencionV4() {
  return [
    {
      key: "obra_nueva",
      title: "Obra nueva",
      description: "Construcción desde arranque con alcances por etapa.",
    },
    {
      key: "remodelacion",
      title: "Remodelación",
      description: "Intervención sobre obra existente con posibilidad de demoliciones.",
    },
    {
      key: "complementaria",
      title: "Complementaria",
      description: "Completar o agregar etapas sin demolición dominante.",
    },
  ];
}

export function getAlcancesPorTipoIntervencion(tipoIntervencion) {
  if (tipoIntervencion === "obra_nueva") {
    return [
      { key: "obra_negra", title: "Obra negra", mode: "auto" },
      { key: "obra_gris", title: "Obra gris", mode: "auto" },
      { key: "obra_completa", title: "Obra completa", mode: "auto" },
    ];
  }

  if (tipoIntervencion === "remodelacion") {
    return [
      {
        key: "remodelacion_por_etapas",
        title: "Remodelación por etapas",
        mode: "manual",
      },
    ];
  }

  if (tipoIntervencion === "complementaria") {
    return [
      {
        key: "complementaria_por_etapas",
        title: "Complementaria por etapas",
        mode: "manual",
      },
    ];
  }

  return [];
}

export function getModulosActivosV4({
  tipoIntervencion,
  alcance,
  partidasSeleccionadas = [],
} = {}) {
  if (tipoIntervencion === "obra_nueva") {
    return [...(ALCANCES_OBRA_NUEVA[alcance] || [])];
  }

  if (tipoIntervencion === "remodelacion" || tipoIntervencion === "complementaria") {
    return [...partidasSeleccionadas];
  }

  return [];
}

export function validateSeleccionAlcanceV4({
  tipoIntervencion,
  alcance,
  partidasSeleccionadas = [],
} = {}) {
  const errors = [];
  const warnings = [];

  if (!tipoIntervencion) {
    errors.push("Selecciona el tipo de intervención para continuar.");
    return { valid: false, errors, warnings };
  }

  if (!alcance) {
    errors.push("Selecciona el alcance para continuar.");
    return { valid: false, errors, warnings };
  }

  if (tipoIntervencion === "obra_nueva") {
    if (!ALCANCES_OBRA_NUEVA[alcance]) {
      errors.push("El alcance elegido no es compatible con obra nueva.");
    }
    return { valid: errors.length === 0, errors, warnings };
  }

  if (partidasSeleccionadas.length === 0) {
    errors.push("Selecciona al menos una partida para continuar.");
  }

  if (tipoIntervencion === "remodelacion") {
    const hasBase = partidasSeleccionadas.some((item) =>
      MODULOS_BASE_REMODELACION.includes(item)
    );

    if (!hasBase) {
      errors.push(
        "En remodelación debes seleccionar al menos una etapa base entre preliminares y albañilería."
      );
    }
  }

  if (tipoIntervencion === "complementaria") {
    warnings.push(
      "Pendiente v4: reclasificar automáticamente si se detecta demolición dominante."
    );
  }

  return { valid: errors.length === 0, errors, warnings };
}

export function getPendientesDefinicionV4() {
  return [
    "P-001 frontera exacta de obra_gris en obra_nueva",
    "P-002 catalogo oficial de nivel_acabado por modulo",
    "P-003 matriz tipo_intervencion -> alcance -> partidas activas",
    "P-004 taxonomia final de subalcances por partida",
    "P-005 compatibilidad formal cimentacion-estructura",
    "P-007 matriz de instalaciones por ambiente y numero de salidas",
  ];
}

export function getPartidasDisponiblesV4() {
  return [
    {
      key: "preliminares",
      title: "Preliminares",
      description: "Condiciones del sitio, acceso, topografía, servicios y demolición.",
    },
    {
      key: "cimentacion",
      title: "Cimentación",
      description: "Sistema de desplante y base estructural.",
    },
    {
      key: "estructura",
      title: "Estructura",
      description: "Sistema portante, niveles y elementos estructurales.",
    },
    {
      key: "albanileria",
      title: "Albañilería",
      description: "Muros, configuración espacial y exteriores base.",
    },
    {
      key: "instalaciones",
      title: "Instalaciones",
      description: "Redes hidráulicas, sanitarias y eléctricas.",
    },
    {
      key: "acabados",
      title: "Acabados",
      description: "Terminaciones por espacio y nivel de acabado.",
    },
    {
      key: "complementarios_y_equipamiento",
      title: "Complementarios y equipamiento",
      description: "Elementos terminales, carpintería y equipamiento.",
    },
  ];
}

export async function readReglasCatalogosV4() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(buildApiUrl("/api/catalogos/reglas-catalogos"), { signal: controller.signal });
    if (!response.ok) throw new Error("No fue posible cargar reglas y cat?logos desde el backend.");
    const data = await response.json();
    return { reglas: Array.isArray(data.reglas) ? data.reglas : [],
      catalogos: Array.isArray(data.catalogos) ? data.catalogos : [], errors: data.errors || [] };
  } catch (error) {
    return { reglas: [], catalogos: [], errors: [error?.message || "Error de conexi?n con el backend."] };
  } finally { clearTimeout(timeout); }
}

export function getModulosBaseV4() {
  return [...MODULOS_BASE];
}
