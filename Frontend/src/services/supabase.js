const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export function isSupabaseReady() {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

function buildQueryString({ select = "*", filters = {}, limit = 100 } = {}) {
  const params = new URLSearchParams();
  params.set("select", select);
  params.set("limit", String(limit));

  Object.entries(filters).forEach(([field, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(field, `eq.${value}`);
  });

  return params.toString();
}

export async function readSupabaseRows({
  table,
  schema = "public",
  select = "*",
  filters = {},
  limit = 100,
} = {}) {
  if (!table) {
    return { rows: [], error: "missing_table" };
  }

  if (!isSupabaseReady()) {
    return { rows: [], error: "supabase_not_configured" };
  }

  const query = buildQueryString({ select, filters, limit });
  const endpoint = `${SUPABASE_URL}/rest/v1/${table}?${query}`;

  try {
    const response = await fetch(endpoint, {
      method: "GET",
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        "Accept-Profile": schema,
      },
    });

    if (!response.ok) {
      const text = await response.text();
      return {
        rows: [],
        error: `supabase_error_${response.status}`,
        detail: text || "No se pudo leer la información de Supabase.",
      };
    }

    const rows = await response.json();
    return { rows: Array.isArray(rows) ? rows : [], error: null };
  } catch (error) {
    return {
      rows: [],
      error: "supabase_network_error",
      detail: String(error?.message || error),
    };
  }
}
