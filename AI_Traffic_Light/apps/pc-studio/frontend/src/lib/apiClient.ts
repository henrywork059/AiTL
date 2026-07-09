import { FrontendErrorCodes } from "./errorCodes";
import { logError, logInfo } from "./logger";

export type ApiEnvelope<T> = {
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    request_id?: string;
    [key: string]: unknown;
  };
};

function isApiEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  return Boolean(value && typeof value === "object" && "ok" in value);
}

export async function requestJson<T>(
  endpoint: string,
  fallback: T,
  options?: RequestInit,
): Promise<T> {
  try {
    const res = await fetch(endpoint, options);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const payload = await res.json();

    if (isApiEnvelope<T>(payload)) {
      if (payload.ok && payload.data !== undefined) {
        logInfo("api", "API envelope response received", {
          endpoint,
          request_id: payload.meta?.request_id,
        });
        return payload.data;
      }

      throw new Error(payload.error?.message ?? "API returned failure envelope");
    }

    logInfo("api", "Legacy raw API response received", { endpoint });
    return payload as T;
  } catch (error) {
    logError("api", FrontendErrorCodes.API_FETCH_FAILED, error, { endpoint });
    return fallback;
  }
}
