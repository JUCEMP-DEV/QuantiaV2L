import {
  buildRawInferenceSnapshot,
  buildInferenceSnapshotAudit,
  normalizeInferenceSnapshot,
} from "@/modules/vivienda/services/inferenciaSnapshotService";
import { API_BASE_URL } from "@/config/apiBaseUrl";

const REQUEST_TIMEOUT_MS = 10000;

export async function inferirResultadoV4({
  preliminares = {},
  modulos = {},
  datosGeneralesObra = {},
  variablesEntrada = {},
  estructuraEspacial = {},
  colindanciasRecorrido = {},
  validacionEspacial = {},
  perfil = "oficial",
  requiredModuleKeys = [],
} = {}) {
  const normalizedSnapshot = normalizeInferenceSnapshot({
    preliminares,
    modulos,
    datosGeneralesObra,
    variablesEntrada,
    estructuraEspacial,
    colindanciasRecorrido,
    validacionEspacial,
    perfil,
    strict: true,
  });
  const snapshot = buildRawInferenceSnapshot(normalizedSnapshot, { requiredModuleKeys });
  const audit = buildInferenceSnapshotAudit(snapshot, { requiredModuleKeys });
  if (!audit.ok) {
    throw new Error(`Snapshot incompleto para inferencia: ${audit.errors.join(" | ")}`);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const capturedModules = Object.entries(snapshot.modulos || {}).filter(
    ([, row]) => Boolean(row?.capturado)
  ).length;
  console.info("[TRACE][INFERENCIA][REQUEST]", {
    preliminaresArea: Number(snapshot.preliminares?.areaPreliminares || 0),
    capturedModules,
    requiredModules: snapshot.requiredModuleKeys?.length || requiredModuleKeys.length,
    perfil: snapshot.perfil,
    mode: "raw_capture_backend_recompute",
  });

  try {
    const response = await fetch(`${API_BASE_URL}/api/resultados/inferir`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
      body: JSON.stringify({
        preliminares: snapshot.preliminares,
        modulos: snapshot.modulos,
        datosGeneralesObra: snapshot.datosGeneralesObra,
        variablesEntrada: snapshot.variablesEntrada,
        estructuraEspacial: snapshot.estructuraEspacial,
        colindanciasRecorrido: snapshot.colindanciasRecorrido,
        validacionEspacial: snapshot.validacionEspacial,
        requiredModuleKeys: snapshot.requiredModuleKeys || requiredModuleKeys,
        perfil: snapshot.perfil,
      }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data?.detail || "No se pudo ejecutar inferencia en backend.");
    }
    console.info("[TRACE][INFERENCIA][RESPONSE]", {
      technicalConcepts: Array.isArray(data?.desglose?.technicalConcepts)
        ? data.desglose.technicalConcepts.length
        : 0,
      officialSummary: Array.isArray(data?.desglose?.officialSummary)
        ? data.desglose.officialSummary.length
        : 0,
      total: Number(data?.resultadoFinal || 0),
    });
    return data;
  } catch (error) {
    const message = String(error?.message || "");
    if (message.toLowerCase().includes("aborted")) {
      throw new Error("Tiempo de espera agotado al ejecutar inferencia.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
