const runtimeEnv = import.meta.env || {};
const processEnv = typeof process !== "undefined" ? process.env || {} : {};

const envBaseUrl = String(
  runtimeEnv.VITE_BACKEND_URL ||
    runtimeEnv.VITE_API_URLBackend ||
    runtimeEnv.VITE_API_BASE_URL ||
    processEnv.VITE_BACKEND_URL ||
    processEnv.VITE_API_URLBackend ||
    processEnv.VITE_API_BASE_URL ||
    "http://127.0.0.1:8000"
)
  .trim()
  .replace(/\/+$/, "");

export const API_BASE_URL = envBaseUrl;

export function buildApiUrl(path = "") {
  const normalizedPath = `/${String(path || "").replace(/^\/+/, "")}`;
  if (!API_BASE_URL) return normalizedPath;
  if (API_BASE_URL.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${API_BASE_URL}${normalizedPath.slice(4)}`;
  }
  return `${API_BASE_URL}${normalizedPath}`;
}
