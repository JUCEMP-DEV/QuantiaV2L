function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toText(value, fallback = "") {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function normalizeSelectedConcepts(selectedConcepts = [], moduleKey = "") {
  const rows = Array.isArray(selectedConcepts) ? selectedConcepts : [];
  return rows
    .map((item, index) => {
      const row = item && typeof item === "object" ? item : {};
      const quantity = toNumber(row.quantity, 0);
      const unitPrice = toNumber(row.unitPrice, 0);
      const totalFromRow = toNumber(row.total, 0);
      const total = totalFromRow > 0 ? totalFromRow : quantity * unitPrice;
      const key = toText(
        row.key,
        `${String(moduleKey || "MOD").slice(0, 3).toUpperCase()}-${String(index + 1).padStart(3, "0")}`
      );

      return {
        key,
        partida: toText(row.partida, "General"),
        title: toText(row.title, "Concepto de modulo"),
        description: toText(row.description, `Concepto derivado del modulo ${moduleKey}.`),
        unit: toText(row.unit, "pza"),
        quantity: Number(quantity.toFixed(4)),
        unitPrice: Number(unitPrice.toFixed(2)),
        total: Number(total.toFixed(2)),
      };
    })
    .filter((item) => item.key);
}

function buildSummaryByPartidaFromSelected(selectedConcepts = []) {
  const grouped = {};
  for (const concept of selectedConcepts) {
    const partida = toText(concept.partida, "General");
    if (!grouped[partida]) {
      grouped[partida] = { partida, concepts: 0, total: 0 };
    }
    grouped[partida].concepts += 1;
    grouped[partida].total += toNumber(concept.total, 0);
  }
  return Object.values(grouped).map((item) => ({
    partida: item.partida,
    concepts: item.concepts,
    total: Number(item.total.toFixed(2)),
  }));
}

function normalizeSummaryByPartida(summaryByPartida = []) {
  const rows = Array.isArray(summaryByPartida) ? summaryByPartida : [];
  return rows
    .map((item) => {
      const row = item && typeof item === "object" ? item : {};
      return {
        partida: toText(row.partida, "General"),
        concepts: Math.max(Math.round(toNumber(row.concepts, 0)), 0),
        total: Number(toNumber(row.total, 0).toFixed(2)),
      };
    })
    .filter((item) => item.total > 0 || item.concepts > 0);
}

function normalizeModuloRow(moduleKey, rawRow = {}, options = {}) {
  const strict = options?.strict !== false;
  const row = rawRow && typeof rawRow === "object" ? rawRow : {};
  const selectedConcepts = normalizeSelectedConcepts(row.selectedConcepts, moduleKey);
  const selectedTotal = selectedConcepts.reduce((acc, item) => acc + toNumber(item.total, 0), 0);

  let summaryByPartida = normalizeSummaryByPartida(row.summaryByPartida);
  if (!strict && !summaryByPartida.length && selectedConcepts.length) {
    summaryByPartida = buildSummaryByPartidaFromSelected(selectedConcepts);
  }
  const summaryTotal = summaryByPartida.reduce((acc, item) => acc + toNumber(item.total, 0), 0);

  const providedCost = toNumber(row.costoEstimado, 0);
  const costoEstimado = strict
    ? Number(providedCost.toFixed(2))
    : Number(Math.max(providedCost, selectedTotal, summaryTotal).toFixed(2));

  const providedKeys = Array.isArray(row.selectedConceptKeys) ? row.selectedConceptKeys : [];
  const selectedConceptKeys = strict
    ? [...new Set(providedKeys.map((key) => String(key)).filter(Boolean))]
    : [...new Set([...providedKeys.map((key) => String(key)), ...selectedConcepts.map((item) => item.key)])];

  return {
    ...row,
    capturado: strict
      ? Boolean(row.capturado)
      : Boolean(row.capturado || selectedConcepts.length || summaryByPartida.length || costoEstimado > 0),
    selectedConceptKeys,
    selectedConcepts,
    summaryByPartida,
    costoEstimado,
  };
}

function normalizeModulos(modulos = {}, options = {}) {
  const normalized = {};
  const entries = modulos && typeof modulos === "object" ? Object.entries(modulos) : [];
  for (const [moduleKey, moduleRow] of entries) {
    normalized[moduleKey] = normalizeModuloRow(moduleKey, moduleRow, options);
  }
  return normalized;
}

function normalizeTechnicalConcepts(technicalConcepts = []) {
  const rows = Array.isArray(technicalConcepts) ? technicalConcepts : [];
  return rows
    .map((item, index) => {
      const row = item && typeof item === "object" ? item : {};
      const quantity = toNumber(row.quantity, 0);
      const unitPrice = toNumber(row.unitPrice, 0);
      const totalFromRow = toNumber(row.total, 0);
      const total = totalFromRow > 0 ? totalFromRow : quantity * unitPrice;
      return {
        ...row,
        key: toText(row.key, `PRE-${String(index + 1).padStart(3, "0")}`),
        sourceKey: toText(row.sourceKey, "preliminares"),
        group: toText(row.group, "Preliminares"),
        title: toText(row.title, "Concepto preliminar"),
        description: toText(row.description, "Concepto generado desde preliminares."),
        unit: toText(row.unit, "pza"),
        quantity: Number(quantity.toFixed(4)),
        unitPrice: Number(unitPrice.toFixed(2)),
        total: Number(total.toFixed(2)),
      };
    })
    .filter((item) => item.key);
}

function buildOfficialSummaryFromTechnical(technicalConcepts = []) {
  const grouped = {};
  for (const item of technicalConcepts) {
    const group = toText(item.group, "General");
    const key = group
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "_");
    if (!grouped[key]) {
      grouped[key] = {
        group: key,
        title: group,
        description: `Resumen de actividades del grupo ${group}.`,
        labor: "Cuadrilla de apoyo",
        materials: "Material menor",
        total: 0,
      };
    }
    grouped[key].total += toNumber(item.total, 0);
  }
  return Object.values(grouped).map((item) => ({
    ...item,
    total: Number(item.total.toFixed(2)),
  }));
}

function normalizePreliminares(preliminares = {}, options = {}) {
  const strict = options?.strict !== false;
  const row = preliminares && typeof preliminares === "object" ? preliminares : {};
  const technicalConcepts = normalizeTechnicalConcepts(row.technicalConcepts);
  const technicalTotal = technicalConcepts.reduce((acc, item) => acc + toNumber(item.total, 0), 0);
  const providedCost = toNumber(row.costoEstimado, 0);
  const costoEstimado = strict
    ? Number(providedCost.toFixed(2))
    : Number(Math.max(providedCost, technicalTotal).toFixed(2));

  const officialSummaryRaw = Array.isArray(row.officialSummary) ? row.officialSummary : [];
  const officialSummary = officialSummaryRaw.length
    ? officialSummaryRaw.map((item) => ({
        group: toText(item?.group, "general"),
        title: toText(item?.title, "General"),
        description: toText(item?.description, "Resumen de actividades."),
        labor: toText(item?.labor, "Cuadrilla de apoyo"),
        materials: toText(item?.materials, "Material menor"),
        total: Number(toNumber(item?.total, 0).toFixed(2)),
      }))
    : strict
    ? []
    : buildOfficialSummaryFromTechnical(technicalConcepts);

  const conceptosActivos = Array.isArray(row.conceptosActivos) && row.conceptosActivos.length
    ? row.conceptosActivos
    : strict
    ? []
    : technicalConcepts.map((item) => ({
        key: item.sourceKey || item.key,
        group: item.group,
        title: item.title,
        description: item.description,
      }));

  return {
    ...row,
    conceptosActivos,
    technicalConcepts,
    officialSummary,
    costoEstimado,
  };
}

export function normalizeInferenceSnapshot({
  preliminares = {},
  modulos = {},
  datosGeneralesObra = {},
  variablesEntrada = {},
  estructuraEspacial = {},
  colindanciasRecorrido = {},
  validacionEspacial = {},
  perfil = "oficial",
  strict = true,
} = {}) {
  const options = { strict };
  return {
    preliminares: normalizePreliminares(preliminares, options),
    modulos: normalizeModulos(modulos, options),
    datosGeneralesObra,
    variablesEntrada,
    estructuraEspacial,
    colindanciasRecorrido,
    validacionEspacial,
    perfil,
  };
}

function uniqueModuleKeys(keys = []) {
  const seen = new Set();
  const list = [];
  for (const raw of Array.isArray(keys) ? keys : []) {
    const key = toText(raw, "").toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    list.push(key);
  }
  return list;
}

const MODULE_KEY_ALIASES = {
  cimentacion: "cimentacion",
  estructura: "estructura",
  albanileria: "albanileria",
  instalaciones: "instalaciones",
  acabados: "acabados",
  complementarios: "complementarios_y_equipamiento",
  complementarios_y_equipamiento: "complementarios_y_equipamiento",
};

function normalizeModuleKey(rawKey = "") {
  const key = toText(rawKey, "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "_")
    .replace(/-+/g, "_");
  return MODULE_KEY_ALIASES[key] || "";
}

function sanitizePreliminaresCapture(preliminares = {}) {
  const row = preliminares && typeof preliminares === "object" ? preliminares : {};
  const demolicion = row.demolicion && typeof row.demolicion === "object" ? row.demolicion : {};
  return {
    tipoIntervencion: toText(row.tipoIntervencion, ""),
    alcanceSeleccionado: toText(row.alcanceSeleccionado, ""),
    areaPreliminares: Number(toNumber(row.areaPreliminares || row.superficiePreliminar, 0).toFixed(2)),
    superficiePreliminar: Number(toNumber(row.superficiePreliminar || row.areaPreliminares, 0).toFixed(2)),
    tipoAcceso: toText(row.tipoAcceso, ""),
    condicionTerreno: toText(row.condicionTerreno, ""),
    topografia: toText(row.topografia, ""),
    pendienteProfundidadM: Number(toNumber(row.pendienteProfundidadM, 0).toFixed(4)),
    demolicion: {
      tipoDemolicion: toText(demolicion.tipoDemolicion, ""),
      tipoEstructuraExistente: toText(demolicion.tipoEstructuraExistente, ""),
      nivelesExistentes: Number(toNumber(demolicion.nivelesExistentes, 0).toFixed(2)),
      anchoDemolicionM: Number(toNumber(demolicion.anchoDemolicionM, 0).toFixed(2)),
      largoDemolicionM: Number(toNumber(demolicion.largoDemolicionM, 0).toFixed(2)),
      areaDemolicionM2: Number(toNumber(demolicion.areaDemolicionM2 || row.areaDemolicionM2, 0).toFixed(2)),
      volumenDemolicion: Number(toNumber(demolicion.volumenDemolicion, 0).toFixed(2)),
    },
    observaciones: toText(row.observaciones, ""),
  };
}

function sanitizeModulosCapture(modulos = {}) {
  const output = {};
  for (const [moduleKey, moduleRow] of Object.entries(modulos || {})) {
    const key = normalizeModuleKey(moduleKey);
    if (!key) continue;
    const row = moduleRow && typeof moduleRow === "object" ? moduleRow : {};
    const controles = row.controles && typeof row.controles === "object" ? row.controles : {};
    const selectedConceptKeys = Array.isArray(row.selectedConceptKeys)
      ? [...new Set(row.selectedConceptKeys.map((item) => toText(item, "").toUpperCase()).filter(Boolean))]
      : [];
    output[key] = {
      capturado: Boolean(row.capturado),
      controles,
      selectedConceptKeys,
    };
  }
  return output;
}

export function buildRawInferenceSnapshot(snapshot = {}, { requiredModuleKeys = [] } = {}) {
  const required = uniqueModuleKeys(requiredModuleKeys)
    .map((item) => normalizeModuleKey(item))
    .filter(Boolean);
  const requiredNormalized = [...new Set(required)];
  return {
    preliminares: sanitizePreliminaresCapture(snapshot?.preliminares || {}),
    modulos: sanitizeModulosCapture(snapshot?.modulos || {}),
    datosGeneralesObra: snapshot?.datosGeneralesObra || {},
    variablesEntrada: snapshot?.variablesEntrada || {},
    estructuraEspacial: snapshot?.estructuraEspacial || {},
    colindanciasRecorrido: snapshot?.colindanciasRecorrido || {},
    validacionEspacial: snapshot?.validacionEspacial || {},
    perfil: toText(snapshot?.perfil, "oficial"),
    requiredModuleKeys: requiredNormalized,
  };
}

export function buildInferenceSnapshotAudit(snapshot = {}, { requiredModuleKeys = [] } = {}) {
  const errors = [];
  const captureSnapshot = buildRawInferenceSnapshot(snapshot, { requiredModuleKeys });
  const preliminares = captureSnapshot.preliminares || {};
  const modulos = captureSnapshot.modulos || {};
  const datosGeneralesObra = captureSnapshot.datosGeneralesObra || {};
  const estructuraEspacial = captureSnapshot.estructuraEspacial || {};
  const colindanciasRecorrido = captureSnapshot.colindanciasRecorrido || {};
  const validacionEspacial = captureSnapshot.validacionEspacial || {};
  const required = captureSnapshot.requiredModuleKeys || [];

  const prelimArea = toNumber(preliminares?.areaPreliminares || preliminares?.superficiePreliminar, 0);
  if (prelimArea <= 0) errors.push("Preliminares sin area valida.");
  if (!toText(preliminares?.tipoAcceso, "")) errors.push("Preliminares sin tipoAcceso.");
  if (!toText(preliminares?.condicionTerreno, "")) errors.push("Preliminares sin condicionTerreno.");
  const topografia = toText(preliminares?.topografia, "");
  if (!topografia) errors.push("Preliminares sin topografia.");
  if (topografia === "con_pendiente" && toNumber(preliminares?.pendienteProfundidadM, 0) <= 0) {
    errors.push("Preliminares con topografia con_pendiente sin pendienteProfundidadM.");
  }

  const areaTerreno = toNumber(datosGeneralesObra?.areaTerrenoM2, 0);
  const areaConstruccion = toNumber(datosGeneralesObra?.areaConstruccionM2, 0);
  const niveles = toNumber(datosGeneralesObra?.niveles, 0);
  const sistema = toText(datosGeneralesObra?.sistemaEstructural, "");
  const cimentacion = toText(datosGeneralesObra?.tipoCimentacion, "");
  if (areaTerreno <= 0 || areaConstruccion <= 0 || niveles <= 0 || !sistema || !cimentacion) {
    errors.push("Datos generales de obra incompletos para inferencia.");
  }

  const espacios = Array.isArray(estructuraEspacial?.espacios) ? estructuraEspacial.espacios : [];
  const relaciones = Array.isArray(colindanciasRecorrido?.relaciones)
    ? colindanciasRecorrido.relaciones
    : [];
  if (!espacios.length) errors.push("Estructura espacial sin espacios validos.");
  if (!relaciones.length) errors.push("Colindancias sin relaciones validas.");
  if (!Boolean(validacionEspacial?.revisado)) {
    errors.push("Validacion espacial no confirmada.");
  }

  if (!required.length) {
    errors.push("No hay modulos requeridos definidos para inferencia final.");
  }

  for (const key of required) {
    const row = modulos?.[key] || {};
    if (!row?.capturado) {
      errors.push(`Modulo requerido '${key}' no esta capturado.`);
      continue;
    }
    if (row?.noApplicable === true) {
      continue;
    }

    const controles =
      row.controles && typeof row.controles === "object"
        ? row.controles
        : {};
    const tipoCimentacion = toText(
      datosGeneralesObra?.tipoCimentacion,
      ""
    ).toLowerCase();

    if (
      key === "cimentacion" &&
      tipoCimentacion === "zapata_aislada_trabe_liga" &&
      !toText(controles?.varianteZapata, "")
    ) {
      errors.push(
        "Modulo 'cimentacion' sin varianteZapata para zapata aislada."
      );
    }

    if (key === "estructura" && !toText(controles?.tipoLosa, "")) {
      errors.push("Modulo 'estructura' sin control tipoLosa.");
    }

    if (key === "acabados" && !toText(controles?.nivelAcabado, "")) {
      errors.push("Modulo 'acabados' sin control nivelAcabado.");
    }

    if (key === "instalaciones") {
      const services =
        controles?.serviciosInstalaciones &&
        typeof controles.serviciosInstalaciones === "object"
          ? controles.serviciosInstalaciones
          : {};

      for (const flag of ["agua", "energia", "drenaje"]) {
        if (services?.[flag] !== true && services?.[flag] !== false) {
          errors.push(
            `Modulo 'instalaciones' requiere definir ${flag} como Si/No.`
          );
        }
      }
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    stats: {
      modules: Object.keys(modulos || {}).length,
      requiredModules: required.length,
      preliminaresArea: prelimArea,
    },
  };
}
