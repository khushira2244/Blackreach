// src/services/apiClient.js

const DEFAULT_TIMEOUT_MS = 15000;

// You can set this in .env as:
// VITE_API_BASE_URL=http://localhost:8000
const BASE_URL =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE_URL) ||
  "http://localhost:8000";


// Normalize unknown errors to a consistent shape
function normalizeError(err, fallbackStatus = 0) {
  if (err && typeof err === "object") {
    // Our own normalized errors
    if ("status" in err && "message" in err) return err;
  }

  // Abort errors
  if (err && err.name === "AbortError") {
    return { status: 0, message: "Request aborted" };
  }

  return {
    status: fallbackStatus,
    message: (err && err.message) || "Request failed",
  };
}

// Parse response body safely (JSON or text)
async function safeParseBody(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }

  // fallback to text
  try {
    const text = await res.text();
    return text || null;
  } catch {
    return null;
  }
}

// Extract best message from backend payloads
function extractMessage(body, res) {
  if (!body) return res.statusText || "Request failed";

  if (typeof body === "string") return body;

  // Common patterns
  if (body.message) return String(body.message);
  if (body.error) return String(body.error);
  if (body.detail) return String(body.detail);

  return res.statusText || "Request failed";
}

/**
 * fetchJSON(url, options)
 *
 * - HTTP mechanics only
 * - JSON parsing
 * - AbortController support (external signal optional)
 * - timeout support
 * - normalized errors: { status, message, details? }
 */
export async function fetchJSON(path, options = {}) {
  const {
    method = "GET",
    headers = {},
    body,
    signal, // optional external AbortSignal
    timeoutMs = DEFAULT_TIMEOUT_MS,
  } = options;

  const controller = new AbortController();

  // If caller provided a signal, abort this controller too
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = path.startsWith("http") ? path : `${BASE_URL}${path}`;

    const res = await fetch(url, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const parsed = await safeParseBody(res);

    if (!res.ok) {
      const message = extractMessage(parsed, res);
      throw {
        status: res.status,
        message,
        details: parsed,
      };
    }

    return parsed;
  } catch (err) {
    throw normalizeError(err);
  } finally {
    clearTimeout(timeoutId);
  }
}

// Export config if needed by other service files
export const apiConfig = {
  BASE_URL,
  DEFAULT_TIMEOUT_MS,
};
