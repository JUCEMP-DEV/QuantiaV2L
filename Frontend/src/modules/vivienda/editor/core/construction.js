import { validateOpening } from './constraints.js';

export const knownNumber = (v) => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
export const positive = (v) => knownNumber(v) && Number(v) > 0;

export function stairRise(stair, levels) {
  const a = levels.find(l => l.id === stair.levelFromId);
  const b = levels.find(l => l.id === stair.levelToId);
  return knownNumber(a?.elevationM) && knownNumber(b?.elevationM) ? Number(b.elevationM) - Number(a.elevationM) : null;
}

export function constructionErrors(entity, type, state) {
  const errors = [];
  if (type === 'door' || type === 'window') {
    errors.push(...validateOpening({ opening: entity, ...state, requireComplete: true }).conflicts.map(x => x.message));
    if (!entity.material || entity.material === 'UNKNOWN') errors.push('Especifica el material.');
    if (!entity.operation || entity.operation === 'UNKNOWN') errors.push('Especifica el tipo de apertura.');
    if (type === 'door' && (!entity.usage || entity.usage === 'UNKNOWN')) errors.push('Especifica el uso de la puerta.');
    if (type === 'door' && entity.leafCount != null && (!Number.isInteger(Number(entity.leafCount)) || Number(entity.leafCount) < 1)) errors.push('El número de hojas debe ser un entero positivo.');
    if (entity.kind === 'GARAGE_DOOR' && entity.usage !== 'VEHICLE_ACCESS') errors.push('El portón debe identificarse como acceso vehicular.');
    if ((type === 'window' || entity.material === 'ALUMINUM') && (!entity.glazing || entity.glazing === 'UNKNOWN')) errors.push('Especifica el acristalamiento.');
  }
  if (type === 'wall') {
    const height = entity.heightM ?? state.levels.find(l => l.id === entity.levelId)?.heightM;
    if (!positive(height) || !positive(entity.thicknessM)) errors.push('Define altura y espesor del muro.');
    if (!entity.material || entity.material === 'UNKNOWN') errors.push('Especifica el material del muro.');
    if (!['LOAD_BEARING', 'PARTITION'].includes(entity.structuralRole)) errors.push('Define si el muro es portante o divisorio.');
  }
  if (type === 'stair') {
    const rise = stairRise(entity, state.levels);
    if (!positive(rise) || entity.levelFromId === entity.levelToId) errors.push('Selecciona niveles distintos con elevaciones conocidas y destino superior.');
    if (!entity.geometry?.vertices?.length) errors.push('Dibuja la huella de la escalera.');
    if (!entity.flights?.length) errors.push('Agrega al menos un tramo.');
    if (!entity.system || entity.system === 'UNKNOWN') errors.push('Especifica el sistema de la escalera.');
    for (const flight of entity.flights || []) {
      if (!positive(flight.widthM) || !Number.isInteger(Number(flight.riserCount)) || Number(flight.riserCount) < 2)
        errors.push('Cada tramo necesita ancho y al menos dos contrahuellas.');
      const points = flight.pathM || [];
      if (points.length !== 2 || points.some(p => !knownNumber(p.x) || !knownNumber(p.y)) || Math.hypot(points[1]?.x - points[0]?.x, points[1]?.y - points[0]?.y) <= 0)
        errors.push('Define inicio y final distintos para cada tramo.');
    }
    if (entity.type !== 'STRAIGHT' && !entity.landings?.length) errors.push('Las escaleras con cambio de dirección requieren descansos.');
    if (['LEFT','RIGHT','BOTH'].includes(entity.railingSide) && (!entity.railingMaterial || entity.railingMaterial === 'UNKNOWN')) errors.push('Especifica el material del barandal.');
  }
  return [...new Set(errors)];
}

// Derive only dimensions implied by explicitly supplied geometry/counts.
export function resolveStair(stair, levels) {
  const rise = stairRise(stair, levels);
  const count = (stair.flights || []).reduce((n, f) => n + (Number(f.riserCount) || 0), 0);
  return { ...stair, totalRiseM: rise,
    slabVoidIds: stair.hasSlabVoid ? [`${stair.id}:slab-void`] : [],
    railingIds: ['LEFT','RIGHT','BOTH'].includes(stair.railingSide) ? (stair.flights || []).flatMap(f => (stair.railingSide === 'BOTH' ? ['LEFT','RIGHT'] : [stair.railingSide]).map(side=>`${stair.id}:${f.id}:${side}`)) : [],
    flights: (stair.flights || []).map(f => {
    const [a, b] = f.pathM || [];
    const run = a && b ? Math.hypot(b.x - a.x, b.y - a.y) : null;
    return { ...f, riserCount: knownNumber(f.riserCount) ? Number(f.riserCount) : null,
      widthM: knownNumber(f.widthM) ? Number(f.widthM) : null,
      riserHeightM: positive(rise) && count > 0 ? rise / count : null,
      treadDepthM: positive(run) && f.riserCount > 1 ? run / (f.riserCount - 1) : null };
  }) };
}
