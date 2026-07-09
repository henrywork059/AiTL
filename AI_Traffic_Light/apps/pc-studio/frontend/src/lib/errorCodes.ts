export const FrontendErrorCodes = {
  FRONTEND_UNKNOWN: "ATL-FE-001",
  API_FETCH_FAILED: "ATL-FE-API-001",
  API_RESPONSE_INVALID: "ATL-FE-API-002",
  RENDER_FAILED: "ATL-FE-RENDER-001",
} as const;

export type FrontendErrorCode =
  (typeof FrontendErrorCodes)[keyof typeof FrontendErrorCodes];
