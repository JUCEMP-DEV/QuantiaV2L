import { API_BASE_URL } from "@/config/apiBaseUrl";

const REQUEST_TIMEOUT_MS = 15000;

export async function exportarConsumo04Backend(payload) {
  return postJson(`${API_BASE_URL}/api/motor/consumo-04`, payload);
}

async function postJson(url, payload = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data?.detail || "No se pudo ejecutar simulacion en backend."
      );
    }

    return data;
  } catch (error) {
    const message = String(error?.message || "").toLowerCase();

    if (message.includes("aborted")) {
      throw new Error(
        "Tiempo de espera agotado al simular en backend."
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function simularPreliminaresBackend({
  preliminares = {},
  datosGeneralesObra = {},
  estructuraEspacial = {},
  colindanciasRecorrido = {},
  sourceName = "CONSTRUBASE_PU_48_CONSTRUCTOR",
} = {}) {
  return postJson(
    `${API_BASE_URL}/api/motor/preliminares/simular`,
    {
      preliminares,
      datosGeneralesObra,
      estructuraEspacial,
      colindanciasRecorrido,
      sourceName,
    }
  );
}

export async function simularModuloBackend({
  moduleKey,
  controles = {},
  selectedConceptKeys = [],
  forceSelectAll = false,
  preliminares = {},
  datosGeneralesObra = {},
  estructuraEspacial = {},
  colindanciasRecorrido = {},
  sourceName = "CONSTRUBASE_PU_48_CONSTRUCTOR",
} = {}) {
  if (!moduleKey) {
    throw new Error(
      "moduleKey es requerido para simular modulo en backend."
    );
  }

  return postJson(
    `${API_BASE_URL}/api/motor/modulos/${moduleKey}/simular`,
    {
      controles,
      selectedConceptKeys,
      forceSelectAll,
      preliminares,
      datosGeneralesObra,
      estructuraEspacial,
      colindanciasRecorrido,
      sourceName,
    }
  );
}
