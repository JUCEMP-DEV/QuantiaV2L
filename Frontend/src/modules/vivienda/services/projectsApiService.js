import { buildApiUrl } from '../../../config/apiBaseUrl.js';
export async function projectsRequest(token, path = '', body) {
  if (!token) throw new Error('Inicia sesión para acceder a tus proyectos.');
  const response = await fetch(buildApiUrl(`/api/cotizaciones${path}`), {
    method: body ? 'POST' : 'GET',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo consultar o guardar el proyecto.');
  return data;
}
export function projectSnapshot(state) {
  const copy = JSON.parse(JSON.stringify(state));
  delete copy.projectPersistence;
  delete copy.reglasSnapshot;
  return { schemaVersion: 'QUANTIA_PROJECT_V1', state: copy };
}
export function restoreProject(store, quote) {
  if (quote.payload_json?.schemaVersion !== 'QUANTIA_PROJECT_V1' || !quote.payload_json?.state)
    throw new Error('Este registro usa un formato anterior. Descarga el archivo para revisarlo; no se reemplazó la sesión.');
  const source = quote.payload_json.state;
  const keys = Object.keys(store.$state).filter(key => !['projectPersistence', 'reglasSnapshot'].includes(key));
  store.$reset();
  store.$patch(Object.fromEntries(keys.filter(key => Object.hasOwn(source, key)).map(key => [key, source[key]])));
  store.projectPersistence = { id: quote.id, userId: quote.user_id };
}
