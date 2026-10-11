"""Crosswalk configuration endpoints; no camera or signal control."""
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.crosswalks import crosswalk_service

router = APIRouter()
logger = get_logger(__name__)


class SaveCrosswalksRequest(BaseModel):
    config: dict[str, Any]


@router.get("")
def list_crosswalks(request: Request) -> dict:
    return ok(crosswalk_service.get(), request_id=request.state.request_id)


@router.put("")
def save_crosswalks(payload: SaveCrosswalksRequest, request: Request) -> dict:
    saved = crosswalk_service.save(payload.config)
    logger.info("Crosswalks saved", extra={
        "request_id": request.state.request_id,
        "crosswalk_count": len(saved["crosswalks"]),
    })
    return ok(saved, request_id=request.state.request_id)
