import { EXTERIOR_NODE } from "@/modules/vivienda/services/spatialRelationsService";

const SIDE_TO_DIRECTION = {
  a1: "norte",
  a2: "sur",
  l1: "oeste",
  l2: "este",
};

function normalizeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function round2(value) {
  return Number((Number(value) || 0).toFixed(2));
}

function roundInt(value) {
  return Math.max(Math.round(Number(value) || 0), 0);
}

function toLower(value) {
  return String(value || "").trim().toLowerCase();
}

function toUpper(value) {
  return String(value || "").trim().toUpperCase();
}

function baseDepthByTopography(topografia = "") {
  const topo = toLower(topografia);
  if (topo === "plana") return 0.15;
  if (topo === "semiplana") return 0.2;
  if (topo === "accidentada") return 0.25;
  if (topo === "con_pendiente") return 0.25;
  return 0.15;
}

function safeArea(width, length) {
  const w = Math.max(normalizeNumber(width, 0), 0);
  const l = Math.max(normalizeNumber(length, 0), 0);
  return w * l;
}

function countByType(spaces = []) {
  const map = {};
  spaces.forEach((item) => {
    const key = toLower(item?.tipo);
    if (!key) return;
    map[key] = (map[key] || 0) + 1;
  });
  return map;
}

function sumStructuralCounts(spaces = []) {
  return spaces.reduce(
    (acc, item) => {
      acc.castillosPzas += Math.max(normalizeNumber(item?.castillosPzas, 0), 0);
      acc.columnasPzas += Math.max(normalizeNumber(item?.columnasPzas, 0), 0);
      acc.zapatasAisladasPzas += Math.max(normalizeNumber(item?.zapatasAisladasPzas, 0), 0);
      return acc;
    },
    { castillosPzas: 0, columnasPzas: 0, zapatasAisladasPzas: 0 }
  );
}

function buildRelationMap(relaciones = []) {
  const map = new Map();
  (Array.isArray(relaciones) ? relaciones : []).forEach((row) => {
    const id = String(row?.espacioId || "").trim();
    if (!id) return;
    map.set(id, row);
  });
  return map;
}

function computeLinearMetrics(spaces = [], relaciones = []) {
  const relationMap = buildRelationMap(relaciones);
  const processedPairs = new Set();
  let totalLinearMl = 0;
  let interiorLinearMl = 0;
  let exteriorLinearMl = 0;

  spaces.forEach((space) => {
    const id = String(space?.id || "").trim();
    if (!id) return;

    const width = Math.max(normalizeNumber(space?.anchoM, 0), 0);
    const length = Math.max(normalizeNumber(space?.largoM, 0), 0);
    const sideFlags = {
      a1: Boolean(space?.ladosCimentacion?.a1),
      a2: Boolean(space?.ladosCimentacion?.a2),
      l1: Boolean(space?.ladosCimentacion?.l1),
      l2: Boolean(space?.ladosCimentacion?.l2),
    };
    const relation = relationMap.get(id) || {};

    Object.entries(sideFlags).forEach(([side, enabled]) => {
      if (!enabled) return;
      const isA = side.startsWith("a");
      const sideLength = isA ? width : length;
      if (sideLength <= 0) return;

      const direction = SIDE_TO_DIRECTION[side];
      const target = String(relation?.[direction] || "").trim();
      const targetId = !target || target === EXTERIOR_NODE ? EXTERIOR_NODE : target;

      if (targetId === EXTERIOR_NODE) {
        totalLinearMl += sideLength;
        exteriorLinearMl += sideLength;
        return;
      }

      const pair = [id, targetId].sort().join("|");
      const edgeKey = `${pair}|${isA ? "a" : "l"}`;
      if (processedPairs.has(edgeKey)) return;

      processedPairs.add(edgeKey);
      totalLinearMl += sideLength;
      interiorLinearMl += sideLength;
    });
  });

  return {
    totalLinearMl: round2(totalLinearMl),
    interiorLinearMl: round2(interiorLinearMl),
    exteriorLinearMl: round2(exteriorLinearMl),
  };
}

function computeOpeningsArea(spaces = []) {
  let windowAreaM2 = 0;
  let doorAreaM2 = 0;
  spaces.forEach((item) => {
    windowAreaM2 += Math.max(normalizeNumber(item?.ventana?.areaM2, 0), 0);
    doorAreaM2 += Math.max(normalizeNumber(item?.puerta?.areaM2, 0), 0);
  });
  return {
    windowAreaM2: round2(windowAreaM2),
    doorAreaM2: round2(doorAreaM2),
    openingsAreaM2: round2(windowAreaM2 + doorAreaM2),
  };
}

export function buildVolumetryContext({
  estructuraEspacial = {},
  colindanciasRecorrido = {},
  datosGeneralesObra = {},
  preliminares = {},
  metrics = {},
} = {}) {
  const spaces = Array.isArray(estructuraEspacial?.espacios) ? estructuraEspacial.espacios : [];
  const levels = new Set(spaces.map((item) => String(item?.nivel || "").trim()).filter(Boolean));
  const typeCounts = countByType(spaces);
  const linear = computeLinearMetrics(spaces, colindanciasRecorrido?.relaciones || []);
  const opening = computeOpeningsArea(spaces);
  const structural = sumStructuralCounts(spaces);

  const areaBySpaces = spaces.reduce((acc, item) => acc + safeArea(item?.anchoM, item?.largoM), 0);
  const areaConstruccion = Math.max(
    normalizeNumber(metrics?.areaConstruccion, 0),
    normalizeNumber(datosGeneralesObra?.areaConstruccionM2, 0),
    areaBySpaces
  );
  const areaPreliminares = Math.max(
    normalizeNumber(preliminares?.areaPreliminares, 0),
    normalizeNumber(preliminares?.superficiePreliminar, 0),
    areaConstruccion
  );
  const avgHeight = Math.max(
    normalizeNumber(datosGeneralesObra?.alturaPromedioM, 0),
    normalizeNumber(datosGeneralesObra?.alturaNivel1M, 0),
    2.6
  );
  const wallAreaM2 = Math.max(linear.totalLinearMl * avgHeight - opening.openingsAreaM2, 0);
  const topografia = toLower(preliminares?.topografia || metrics?.topografia || "");
  const pendingDepth = Math.max(normalizeNumber(preliminares?.pendienteProfundidadM, 0), 0);

  return {
    areaConstruccion: round2(areaConstruccion),
    areaPreliminares: round2(areaPreliminares),
    areaTerreno: round2(
      normalizeNumber(datosGeneralesObra?.areaTerrenoM2, normalizeNumber(metrics?.areaTerreno, areaConstruccion))
    ),
    levelsCount: Math.max(levels.size, Math.max(normalizeNumber(datosGeneralesObra?.niveles, 1), 1)),
    totalSpaces: spaces.length,
    totalBanos:
      (typeCounts.bano_1 || 0) + (typeCounts.bano_2 || 0) + (typeCounts.medio_bano || 0),
    totalRecamaras:
      (typeCounts.recamara_principal || 0) +
      (typeCounts.recamara_2 || 0) +
      (typeCounts.recamara_3 || 0) +
      (typeCounts.recamara_4 || 0),
    totalLinearMl: linear.totalLinearMl,
    foundationLinearMl: linear.totalLinearMl,
    exteriorLinearMl: linear.exteriorLinearMl,
    interiorLinearMl: linear.interiorLinearMl,
    wallAreaM2: round2(wallAreaM2),
    avgHeightM: round2(avgHeight),
    windowAreaM2: opening.windowAreaM2,
    doorAreaM2: opening.doorAreaM2,
    openingsAreaM2: opening.openingsAreaM2,
    areaDemolicionM2: round2(
      Math.max(normalizeNumber(preliminares?.demolicion?.areaDemolicionM2, 0), normalizeNumber(preliminares?.areaDemolicionM2, 0))
    ),
    topografia,
    topografiaDepthM: pendingDepth > 0 ? pendingDepth : baseDepthByTopography(topografia),
    tipoCimentacion: toLower(datosGeneralesObra?.tipoCimentacion),
    sistemaEstructural: toLower(datosGeneralesObra?.sistemaEstructural),
    castillosPzas: round2(structural.castillosPzas),
    columnasPzas: round2(structural.columnasPzas),
    zapatasAisladasPzas: round2(structural.zapatasAisladasPzas),
    countByType: typeCounts,
  };
}

function calculatePre003Quantity(context = {}) {
  const linear = Math.max(normalizeNumber(context.foundationLinearMl, 0), 0);
  const zapatas = Math.max(normalizeNumber(context.zapatasAisladasPzas, 0), 0);
  const columnas = Math.max(normalizeNumber(context.columnasPzas, 0), 0);
  const tipo = toLower(context.tipoCimentacion || context.sistemaEstructural || "");

  if (tipo.includes("zapata_aislada") || (zapatas > 0 && !tipo.includes("corrida"))) {
    const gross = zapatas * 1 * 1 * 1;
    const discountZapata = zapatas * 1 * 1 * 0.25;
    const discountDado = columnas * 0.3 * 0.3 * 0.7;
    return round2(Math.max(gross - discountZapata - discountDado, 0));
  }

  if (tipo.includes("corrida") || tipo.includes("trabe_liga")) {
    const gross = linear * 0.6 * 0.55;
    const discountZapata = linear * 0.6 * 0.2;
    const discountContratrabe = linear * 0.2 * 0.3;
    return round2(Math.max(gross - discountZapata - discountContratrabe, 0));
  }

  const gross = linear * 0.6 * 0.7;
  const discountMasonry = linear * ((0.6 + 0.3) / 2) * 0.65;
  return round2(Math.max(gross - discountMasonry, 0));
}

function inferQuantityByFormula({ code, formula, quantification, context }) {
  const area = Math.max(normalizeNumber(context.areaConstruccion, 0), 1);
  const wallAreaM2 = Math.max(normalizeNumber(context.wallAreaM2, 0), 1);
  const linear = Math.max(normalizeNumber(context.foundationLinearMl, 0), 1);
  const spaces = Math.max(normalizeNumber(context.totalSpaces, 0), 1);
  const banos = Math.max(normalizeNumber(context.totalBanos, 0), 1);
  const codePrefix = String(code).split("-")[0];

  if (formula.includes("M2") || quantification.includes("area")) {
    if (["ALB", "ACA"].includes(codePrefix) && /ALB-00[1-5]|ACA-00[3-7]/.test(code)) {
      return round2(wallAreaM2);
    }
    return round2(area);
  }
  if (formula.includes("M3") || quantification.includes("volumen")) {
    return round2(Math.max(linear * 0.22, area * 0.12));
  }
  if (formula.includes("ML") || quantification.includes("perimetro")) {
    return round2(linear);
  }
  if (formula.includes("SALIDA") || quantification.includes("salida")) {
    if (codePrefix === "ELE") return Math.max(roundInt((spaces + banos) * 1.1), 1);
    if (codePrefix === "HID" || codePrefix === "SAN") return Math.max(roundInt((spaces + banos) * 1.1), 1);
    if (codePrefix === "PLU") return Math.max(roundInt(Math.max(context.exteriorLinearMl / 3.5, 1)), 1);
    return Math.max(roundInt((spaces + banos) * 1.1), 1);
  }
  if (formula.includes("PZA") || quantification.includes("pieza")) {
    if (code === "MSA-001" || code === "MSA-002" || code === "MSA-004" || code === "MSA-005" || code === "MSA-006") {
      return Math.max(roundInt(context.totalBanos), 1);
    }
    if (code === "MSA-003") {
      return Math.max(roundInt(context.countByType?.cocina || 1), 1);
    }
    if (code === "EST-003") {
      return Math.max(roundInt(context.columnasPzas || 0), 1);
    }
    return Math.max(roundInt(spaces * 0.9), 1);
  }
  if (formula.includes("TRAMITE") || quantification.includes("tramite")) {
    return 1;
  }
  return 1;
}

export function estimateCatalogConceptQuantity({
  concept,
  context = {},
  quantitiesByCode = {},
} = {}) {
  const code = toUpper(concept?.code || concept?.key || "");
  const formula = toUpper(concept?.default_formula_code || "");
  const quantification = toLower(concept?.quantification_mode || "");
  const areaPre = Math.max(normalizeNumber(context.areaPreliminares, 0), 1);
  const depth = Math.max(normalizeNumber(context.topografiaDepthM, 0.15), 0.01);
  const areaDemolicion = Math.max(normalizeNumber(context.areaDemolicionM2, 0), 0);

  if (code === "PRE-001") return round2(areaPre);
  if (code === "PRE-002") return round2(areaPre * depth * 1.3);
  if (code === "PRE-003") return calculatePre003Quantity(context);
  if (code === "PRE-004") return round2(areaPre * depth * 1.3);
  if (code === "PRE-005") {
    const total =
      normalizeNumber(quantitiesByCode["PRE-002"], 0) +
      normalizeNumber(quantitiesByCode["PRE-003"], 0) +
      normalizeNumber(quantitiesByCode["PRE-004"], 0);
    return round2(Math.max(total, 0));
  }
  if (code === "PRE-006") return round2(Math.max(areaPre * Math.max(depth, 0.1), 0));
  if (code === "PRE-007" || code === "PRE-008") return round2(Math.max(areaDemolicion, 0));
  if (code === "CIM-005" || code === "CIM-005A") return round2(Math.max(context.foundationLinearMl, 0));
  if (code === "CIM-006") return round2(Math.max(context.foundationLinearMl * 0.2925, 0));
  if (code === "ALB-001" || code === "ALB-002" || code === "ALB-003") {
    return round2(Math.max(context.wallAreaM2, 0));
  }
  if (code === "ALB-004") return round2(Math.max(context.wallAreaM2 * 2, 0));
  if (code === "ALB-005") return round2(Math.max(context.areaConstruccion, 0));

  return inferQuantityByFormula({ code, formula, quantification, context });
}
