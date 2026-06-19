const env = import.meta.env;

export const API_CONFIG = {
  baseUrl: (env.VITE_API_BASE_URL || "").replace(/\/$/, ""),
  uploadEndpoint: env.VITE_UPLOAD_ENDPOINT || "/api/upload",
  queryEndpoint: env.VITE_QUERY_ENDPOINT || "/api/query",
  statusEndpoint: env.VITE_STATUS_ENDPOINT || "/api/status/:documentId",
  pollIntervalMs: Number(env.VITE_POLL_INTERVAL_MS) || 1800,
  maxFileSizeMb: Number(env.VITE_MAX_FILE_SIZE_MB) || 30,
};

export function apiUrl(endpoint) {
  if (/^https?:\/\//i.test(endpoint)) return endpoint;
  return `${API_CONFIG.baseUrl}${endpoint}`;
}
