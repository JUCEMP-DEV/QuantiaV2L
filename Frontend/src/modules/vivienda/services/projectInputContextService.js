export const PROJECT_INPUT_CONTEXT_VERSION = "PROJECT_INPUT_CONTEXT_V1";

export const EVIDENCE_TYPES = Object.freeze({
  USER_DECLARED: "USER_DECLARED",
  SYSTEM_DERIVED_FROM_USER_DATA: "SYSTEM_DERIVED_FROM_USER_DATA",
  DEFAULT: "DEFAULT",
  NO_EVIDENCE: "NO_EVIDENCE",
});

export function buildProjectInputContext(store = {}) {
  const registro = store.registro || {};
  const ubicacion = registro.ubicacion || {};
  const clasificacion = store.clasificacion || {};
  const alcance = store.alcance || {};
  const general = store.datosGeneralesObra || {};
  const preliminares = store.preliminares || {};
  const evidence = [];

  const declared = (target, key, value, field, sourceInterface) => {
    if (!hasEvidence(value)) return;
    target[key] = clone(value);
    evidence.push({
      field,
      evidence_type: EVIDENCE_TYPES.USER_DECLARED,
      source_interface: sourceInterface,
    });
  };

  const location = {};
  declared(location, "state", ubicacion.estado, "location.state", "01");
  declared(location, "municipality", ubicacion.municipio, "location.municipality", "01");
  declared(location, "locality", ubicacion.localidad, "location.locality", "01");
  declared(location, "address", ubicacion.direccion, "location.address", "01");

  const site = {};
  declared(site, "area_m2", positiveNumberOrNull(general.areaTerrenoM2), "site.area_m2", "02");

  const geometryType = normalizeSiteGeometry(general.geometriaPredio);
  declared(site, "geometry_type", geometryType, "site.geometry_type", "02");

  const boundaries = {};
  const sourceBoundaries = general.colindanciasPredio || {};
  declared(boundaries, "front", sourceBoundaries.frente, "site.boundaries.front", "02");
  declared(boundaries, "rear", sourceBoundaries.fondo, "site.boundaries.rear", "02");
  declared(boundaries, "left", sourceBoundaries.lateralIzquierdo, "site.boundaries.left", "02");
  declared(boundaries, "right", sourceBoundaries.lateralDerecho, "site.boundaries.right", "02");
  declared(boundaries, "other", sourceBoundaries.otras, "site.boundaries.other", "02");
  if (Object.keys(boundaries).length) site.boundaries = boundaries;

  const project = {};
  declared(
    project,
    "intervention_type",
    clasificacion.tipoIntervencion || alcance.tipoIntervencion,
    "project.intervention_type",
    "01",
  );
  declared(project, "scope", alcance.alcance, "project.scope", "01");

  const construction = {};
  declared(
    construction,
    "structural_system",
    general.sistemaEstructural,
    "construction.structural_system",
    "02",
  );
  declared(
    construction,
    "foundation_type",
    general.tipoCimentacion,
    "construction.foundation_type",
    "02",
  );
  declared(
    construction,
    "slab_type",
    general.tipoLosa,
    "construction.slab_type",
    "02",
  );

  const siteConditions = {};
  declared(
    siteConditions,
    "topography",
    preliminares.topografia,
    "site_conditions.topography",
    "02",
  );
  declared(
    siteConditions,
    "terrain_condition",
    preliminares.condicionTerreno,
    "site_conditions.terrain_condition",
    "02",
  );
  declared(
    siteConditions,
    "slope_depth_m",
    positiveNumberOrNull(preliminares.pendienteProfundidadM),
    "site_conditions.slope_depth_m",
    "02",
  );
  declared(
    siteConditions,
    "access_type",
    preliminares.tipoAcceso,
    "site_conditions.access_type",
    "02",
  );

  const services = {};
  for (const key of ["agua", "drenaje", "energia", "gas", "telecomunicaciones"]) {
    declared(
      services,
      key,
      preliminares.servicios?.[key],
      `site_conditions.services.${key}`,
      "02",
    );
  }
  if (Object.keys(services).length) siteConditions.services = services;

  return compactObject({
    contract_version: PROJECT_INPUT_CONTEXT_VERSION,
    source: EVIDENCE_TYPES.USER_DECLARED,
    location,
    site,
    project,
    construction,
    site_conditions: siteConditions,
    evidence,
  });
}

function normalizeSiteGeometry(value) {
  if (value === "rectangular") return "RECTANGULAR";
  if (value === "varios_lados") return "POLYGONAL";
  return null;
}

function positiveNumberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : null;
}

function hasEvidence(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  return true;
}

function compactObject(value) {
  if (Array.isArray(value)) {
    return value.map(compactObject);
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  return Object.fromEntries(
    Object.entries(value)
      .map(([key, item]) => [key, compactObject(item)])
      .filter(([, item]) => {
        if (item === null || item === undefined || item === "") return false;
        if (Array.isArray(item)) return item.length > 0;
        if (typeof item === "object") return Object.keys(item).length > 0;
        return true;
      }),
  );
}

function clone(value) {
  if (value && typeof value === "object") {
    return JSON.parse(JSON.stringify(value));
  }
  return value;
}
