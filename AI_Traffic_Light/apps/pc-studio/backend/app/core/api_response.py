from typing import Any

from app.core.error_codes import ErrorCode


def ok(data: Any, *, request_id: str | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a standard successful API response envelope."""
    response_meta = dict(meta or {})
    if request_id:
        response_meta["request_id"] = request_id
    return {
        "ok": True,
        "data": data,
        "meta": response_meta,
    }


def fail(
    *,
    code: ErrorCode | str,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standard failed API response envelope."""
    return {
        "ok": False,
        "error": {
            "code": str(code.value if isinstance(code, ErrorCode) else code),
            "message": message,
            "details": details or {},
        },
        "meta": {
            "request_id": request_id,
        },
    }
