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

export class ApiRequestError extends Error {
  code?: string;
  requestId?: string;

  constructor(message: string, code?: string, requestId?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.requestId = requestId;
  }
}

export async function requestJsonStrict<T>(endpoint: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(endpoint, options);
    let payload: unknown;
    try {
      payload = await res.json();
    } catch {
      throw new ApiRequestError(`API returned HTTP ${res.status} without a JSON response.`);
    }

    if (isApiEnvelope<T>(payload)) {
      if (res.ok && payload.ok && payload.data !== undefined) {
        logInfo("api", "API envelope response received", {
          endpoint,
          request_id: payload.meta?.request_id,
        });
        return payload.data;
      }

      throw new ApiRequestError(
        payload.error?.message ?? `API request failed with HTTP ${res.status}.`,
        payload.error?.code,
        payload.meta?.request_id,
      );
    }

    if (!res.ok) {
      throw new ApiRequestError(`API request failed with HTTP ${res.status}.`);
    }

    logInfo("api", "Legacy raw API response received", { endpoint });
    return payload as T;
  } catch (error) {
    logError("api", FrontendErrorCodes.API_FETCH_FAILED, error, { endpoint });
    throw error;
  }
}

export async function requestJson<T>(
  endpoint: string,
  fallback: T,
  options?: RequestInit,
): Promise<T> {
  try {
    return await requestJsonStrict<T>(endpoint, options);
  } catch {
    return fallback;
  }
}
