const MODULE_CONFIG = {
  cimentacion: {
    title: "Cimentación",
    description:
      "El motor V1.8 propone conceptos según las reglas declarativas y los datos confirmados del proyecto.",
  },
  estructura: {
    title: "Estructura",
    description:
      "El motor V1.8 activa y cuantifica conceptos estructurales únicamente con contexto e inputs válidos.",
  },
  albanileria: {
    title: "Albañilería",
    description:
      "Revisa las propuestas del motor declarativo y confirma únicamente los conceptos aplicables.",
  },
  instalaciones: {
    title: "Instalaciones",
    description:
      "Define los servicios del proyecto y revisa las propuestas generadas por reglas declarativas.",
  },
  acabados: {
    title: "Acabados",
    description:
      "Revisa conceptos de acabado propuestos con base en el alcance y los inputs confirmados.",
  },
  complementarios_y_equipamiento: {
    title: "Complementarios y equipamiento",
    description:
      "Revisa conceptos complementarios y de equipamiento propuestos por el motor V1.8.",
  },
};

export function getModuleConfig(moduleKey) {
  return MODULE_CONFIG[moduleKey] || MODULE_CONFIG.cimentacion;
}

export const CIMENTACION_ZAPATA_OPTIONS = [
  { value: "", label: "Sin definir" },
  { value: "080", label: "0.80 × 0.80 m" },
  { value: "100", label: "1.00 × 1.00 m" },
];

export const LOSA_OPTIONS = [
  { value: "", label: "Sin definir" },
  { value: "maciza", label: "Maciza" },
  { value: "aligerada_caseton_nervaduras", label: "Aligerada casetón-nervaduras" },
  { value: "vigueta_bovedilla", label: "Sistema vigueta-bovedilla" },
];

export const ACABADO_OPTIONS = [
  { value: "estandar", label: "Estándar" },
  { value: "personalizado", label: "Personalizado" },
];
