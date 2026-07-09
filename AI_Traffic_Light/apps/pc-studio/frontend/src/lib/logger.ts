import type { FrontendErrorCode } from "./errorCodes";

export function logInfo(scope: string, message: string, meta?: Record<string, unknown>) {
  console.info(`[AiTL][${scope}] ${message}`, meta ?? {});
}

export function logWarn(scope: string, message: string, meta?: Record<string, unknown>) {
  console.warn(`[AiTL][${scope}] ${message}`, meta ?? {});
}

export function logError(
  scope: string,
  code: FrontendErrorCode | string,
  error: unknown,
  meta?: Record<string, unknown>,
) {
  console.error(`[AiTL][${scope}][${code}]`, {
    error,
    ...(meta ?? {}),
  });
}
