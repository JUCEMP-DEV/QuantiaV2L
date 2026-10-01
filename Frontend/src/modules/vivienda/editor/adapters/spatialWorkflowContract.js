// Boundary 03 -> 04 and draft 04 -> 05. No quantities are inferred here.
const list = (value) => Array.isArray(value) ? value : [];
const copy = (value) => JSON.parse(JSON.stringify(value));

export function receiveSpatialAnalysis(payload = {}) {
  if (payload?.schemaVersion === 'QUANTIA_03_04_V1') {
    if (!payload.spatial || typeof payload.spatial !== 'object' || Array.isArray(payload.spatial))
      throw new Error('El archivo de 03 no contiene un modelo espacial.');
    const spatial = receiveSpatialAnalysis(payload.spatial);
    return { ...spatial, sourceMode: 'plan', intake03: copy(payload) };
  }
  const source = copy(payload || {});
  const isReview = source.schemaVersion === 'SPATIAL_INTERFACE04_REVIEW_V1';
  if (!isReview) return source;
  const levels = list(source.niveles);
  const walls = list(source.muros).map((wall) => ({
    ...wall,
    nivel: levels.find((level) => level.id === wall.levelId)?.key || wall.levelId,
  }));
  const rasterReference = source.planoBase?.referencia;
  const usableRaster = typeof rasterReference === 'string' && /^(https?:\/\/|blob:|data:image\/|\/)/.test(rasterReference);
  return {
    ...source, sourceMode: 'plan', muros: walls,
    planoBase: { ...source.planoBase, referencia: usableRaster ? rasterReference : null },
    metadata: {
      ...source.metadata,
      sourceRasterAsset: source.metadata?.sourceRasterAsset ?? rasterReference,
      requiresLocalRasterUrl: !usableRaster,
      sourceDocumentId: source.source?.documentId ?? source.metadata?.sourceDocumentId,
      sourcePageNumber: source.source?.pageNumber ?? source.metadata?.sourcePageNumber,
      sourceBBoxPx: source.source?.bboxPx,
    },
  };
}

export function buildPhase03Delivery(spatial, store = {}) {
  const source = copy(spatial || {});
  delete source.intake03;
  delete source.quantityHandoff;
  return { schemaVersion: 'QUANTIA_03_04_V1', spatial: source,
    context01: copy({ proyecto: store.registro?.proyecto || {}, clasificacion: store.clasificacion || {}, alcance: store.alcance || {} }),
    context02: copy(store.datosGeneralesObra || {}) };
}

export function workflowConstructionContext(store = {}) {
  const general = store.datosGeneralesObra || {};
  return { sistemaEstructural: general.sistemaEstructural || '', tipoCimentacion: general.tipoCimentacion || '',
    tipoLosa: general.tipoLosa || general.engineInputs?.tipo_losa || '',
    tipoIntervencion: store.clasificacion?.tipoIntervencion || '', alcanceProyecto: store.alcance?.alcance || '',
    serviciosInstalaciones: general.engineInputs?.servicios_instalaciones || {} };
}

export function canOpenMetricEditor(spatial = {}) {
  const known = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
  const point = p => p && known(p.x) && known(p.y);
  const walls = list(spatial.muros), spaces = list(spatial.espacios);
  return (walls.length > 0 || spaces.length > 0)
    && walls.every(w => point(w.start) && point(w.end))
    && spaces.every(s => {
      const g = s.geometry || s.geometria || {};
      return (g.metrica?.vertices || g.vertices || []).length >= 3;
    });
}

export function buildQuantityHandoff(spatial = {}, project = {}) {
  const source = copy(spatial);
  delete source.quantityHandoff;
  const openingsComplete = source.completeness?.openings === 'CONFIRMED';
  const spaces = list(source.espacios);
  const walls = list(source.muros);
  const missing = [];
  if (!spaces.length) missing.push('Faltan espacios con geometría y medidas.');
  if (spaces.some((s) => !s.confirmed || !(Number(s.areaM2) > 0)))
    missing.push('Hay espacios sin confirmar o sin área métrica.');
  if (!walls.length) missing.push('Faltan muros parametrizados.');
  if (walls.some((w) => !w.confirmed || !(Number(w.heightM) > 0) || !(Number(w.thicknessM) > 0)))
    missing.push('Hay muros sin confirmar, altura o espesor.');
  if (!openingsComplete) missing.push('La identificación de aberturas no está confirmada.');
  for (const item of list(source.readiness?.missing)) missing.push(String(item));
  return {
    schemaVersion: 'QUANTIA_04_TO_05_DRAFT_V1',
    status: 'DRAFT', readyForCalculation: false,
    sourceRevision: source.revision ?? null,
    projectId: source.projectId ?? null,
    missing: [...new Set(missing)],
    // This is a template, not the existing motor request. Unknown != empty.
    data: {
      niveles: list(source.niveles), muros: walls, espacios: spaces,
      puertas: openingsComplete ? list(source.puertas) : null,
      ventanas: openingsComplete ? list(source.ventanas) : null,
      completeness: { ...source.completeness, openings: openingsComplete ? 'CONFIRMED' : 'UNKNOWN' },
      coordinateSystem: source.coordinateSystem ?? null,
      datosGeneralesObra: copy(project),
      engineInputs: source.engineInputs || {},
      engineInputsByConcept: source.engineInputsByConcept || {},
    },
    reviewSource: source,
  };
}
