export const EXTERIOR_NODE = "__EXTERIOR__";

const RELATION_DIRECTIONS = ["norte", "sur", "este", "oeste"];

const OPPOSITE_DIRECTION = {
  norte: "sur",
  sur: "norte",
  este: "oeste",
  oeste: "este",
};

const LEVEL_LABELS = {
  planta_baja: "Planta Baja",
  segunda_planta: "Segunda Planta",
  tercera_planta: "Tercera Planta",
  planta_azotea: "Planta Azotea",
};

const TYPE_LABELS = {
  recamara_principal: "Recamara Principal",
  recamara_2: "Recamara 2",
  recamara_3: "Recamara 3",
  recamara_4: "Recamara 4",
  bano_1: "Bano 1",
  bano_2: "Bano 2",
  medio_bano: "Medio Bano",
  sala: "Sala",
  cocina: "Cocina",
  comedor: "Comedor",
  estancia: "Estancia",
  estudio: "Estudio",
  escalera_1: "Escalera 1",
  escalera_2: "Escalera 2",
  escalera_3: "Escalera 3",
  terraza: "Terraza",
  pasillo_interior: "Pasillo interior",
  patio_servicio: "Patio Servicio",
  patio_exterior: "Patio Exterior",
  cochera: "Cochera",
  jardin: "Jardin",
};

function directionLabel(direction) {
  const map = {
    norte: "Norte",
    sur: "Sur",
    este: "Este",
    oeste: "Oeste",
  };
  return map[String(direction || "").trim()] || String(direction || "").trim();
}

function emptyRelationRow(espacioId) {
  return {
    espacioId,
    norte: EXTERIOR_NODE,
    sur: EXTERIOR_NODE,
    este: EXTERIOR_NODE,
    oeste: EXTERIOR_NODE,
  };
}

export function normalizeSpatialRelations({ espacios = [], relaciones = [] } = {}) {
  const rows = Array.isArray(relaciones) ? relaciones : [];
  const byId = new Map(rows.map((item) => [String(item?.espacioId || ""), item]));

  return (Array.isArray(espacios) ? espacios : []).map((espacio) => {
    const id = String(espacio?.id || "");
    const base = emptyRelationRow(id);
    const saved = byId.get(id) || {};

    return RELATION_DIRECTIONS.reduce(
      (acc, dir) => {
        const value = String(saved[dir] || "").trim();
        acc[dir] = value || EXTERIOR_NODE;
        return acc;
      },
      { ...base }
    );
  });
}

export function validateSpatialRelations({ espacios = [], relaciones = [] } = {}) {
  const issues = [];
  const spaces = Array.isArray(espacios) ? espacios : [];
  const relations = normalizeSpatialRelations({ espacios: spaces, relaciones });
  const labelMap = buildSpaceLabelMap(spaces);
  const typeById = new Map(
    spaces.map((item) => [String(item?.id || ""), String(item?.tipo || "").trim()])
  );
  const validIds = new Set(spaces.map((item) => String(item?.id || "")));
  const byId = new Map(relations.map((item) => [String(item.espacioId || ""), item]));
  let internalLinks = 0;
  let reciprocalLinks = 0;

  for (const row of relations) {
    const fromId = String(row.espacioId || "");
    const fromLabel = labelMap[fromId] || fromId || "espacio_sin_id";
    if (!fromId || !validIds.has(fromId)) {
      issues.push(`Relacion sin espacio valido: ${fromLabel}.`);
      continue;
    }

    for (const dir of RELATION_DIRECTIONS) {
      const dirLabel = directionLabel(dir);
      const targetId = String(row[dir] || "").trim();
      if (!targetId) {
        issues.push(`Falta definir ${dirLabel} en ${fromLabel}.`);
        continue;
      }

      if (targetId === EXTERIOR_NODE) {
        continue;
      }

      const targetLabel = labelMap[targetId] || targetId;
      if (!validIds.has(targetId)) {
        issues.push(`${fromLabel} apunta a ${targetLabel} en ${dirLabel}, pero no existe.`);
        continue;
      }

      if (targetId === fromId) {
        issues.push(`${fromLabel} no puede colindar consigo mismo en ${dirLabel}.`);
        continue;
      }

      internalLinks += 1;
      const opposite = OPPOSITE_DIRECTION[dir];
      const oppositeRow = byId.get(targetId);
      const backward = String(oppositeRow?.[opposite] || "").trim();
      const targetType = String(typeById.get(targetId) || "");
      const hasAnyBackwardMatch = RELATION_DIRECTIONS.some(
        (direction) => String(oppositeRow?.[direction] || "").trim() === fromId
      );

      if (backward === fromId || (targetType === "pasillo_interior" && hasAnyBackwardMatch)) {
        reciprocalLinks += 1;
      } else {
        const oppositeLabel = directionLabel(opposite);
        issues.push(
          `No hay reciprocidad: ${fromLabel} al ${dirLabel} con ${targetLabel}. Debe reflejarse ${targetLabel} al ${oppositeLabel} con ${fromLabel}.`
        );
      }
    }
  }

  const coverageBase = Math.max(internalLinks, 1);
  const coverageRatio = Number((reciprocalLinks / coverageBase).toFixed(4));

  return {
    valid: issues.length === 0 && relations.length === spaces.length,
    issues,
    normalizedRelations: relations,
    summary: {
      spacesCount: spaces.length,
      relationRowsCount: relations.length,
      internalLinks,
      reciprocalLinks,
      brokenLinks: Math.max(internalLinks - reciprocalLinks, 0),
      coverageRatio,
    },
  };
}

export function buildSpaceLabelMap(espacios = []) {
  return Object.fromEntries(
    (Array.isArray(espacios) ? espacios : []).map((item, index) => {
      const id = String(item?.id || `espacio-${index + 1}`);
      const type = TYPE_LABELS[String(item?.tipo || "").trim()] || `Espacio ${index + 1}`;
      const level = LEVEL_LABELS[String(item?.nivel || "").trim()] || "Nivel sin definir";
      return [id, `${type} - ${level}`];
    })
  );
}

export const SPATIAL_RELATION_DIRECTIONS = RELATION_DIRECTIONS;
