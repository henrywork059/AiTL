from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from threading import Condition, RLock
import time
from typing import Any, Callable

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger
from app.services.camera_frames import CameraFrame, camera_frame_service
from app.services.remote_camera import (
    CAMERA_SETTING_KEYS,
    DEFAULT_TARGET_FPS,
    MAX_TARGET_FPS,
    MIN_TARGET_FPS,
    RemoteCameraService,
    _FramePacket,
    normalize_private_lan_ipv4,
)

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "config" / "remote_cameras.json"
MAX_SAVED_CAMERAS = 12
MAX_SWITCH_CACHE_AGE_MS = 1500
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

DEFAULT_CAMERA_SETTINGS: dict[str, Any] = {
    "frame_size": "QVGA",
    "jpeg_quality": 24,
    "brightness": 0,
    "contrast": 0,
    "saturation": 0,
    "special_effect": 0,
    "awb": True,
    "awb_gain": True,
    "wb_mode": 0,
    "aec": True,
    "aec2": False,
    "ae_level": 0,
    "aec_value": 300,
    "agc": True,
    "agc_gain": 0,
    "gainceiling": 0,
    "bpc": False,
    "wpc": True,
    "raw_gma": True,
    "lenc": True,
    "hmirror": False,
    "vflip": False,
    "dcw": True,
    "colorbar": False,
}

FRAME_SIZES = {"QQVGA", "HQVGA", "QVGA", "CIF", "VGA", "SVGA", "XGA", "SXGA", "UXGA"}
INT_SETTING_RANGES: dict[str, tuple[int, int]] = {
    "jpeg_quality": (4, 63),
    "brightness": (-2, 2),
    "contrast": (-2, 2),
    "saturation": (-2, 2),
    "special_effect": (0, 6),
    "wb_mode": (0, 4),
    "ae_level": (-2, 2),
    "aec_value": (0, 1200),
    "agc_gain": (0, 30),
    "gainceiling": (0, 6),
}
BOOL_SETTING_KEYS = {
    "awb", "awb_gain", "aec", "aec2", "agc", "bpc", "wpc", "raw_gma",
    "lenc", "hmirror", "vflip", "dcw", "colorbar",
}


@dataclass(frozen=True)
class _CachedPacket:
    packet: _FramePacket
    received_at_ms: int


class RemoteCameraManager:
    """Persist and coordinate several V037/V036-compatible ESP32-CAM sessions.

    Every saved ESP owns an independent RemoteCameraService/socket worker and a
    private cached newest JPEG. Exactly one saved ESP is selected as the active
    PC Studio source. Only that selected source publishes into CameraFrameService,
    which preserves all existing inference, dataset, zone and analytics consumers.
    Other ESP streams may remain connected in the background for fast switching.
    """

    def __init__(
        self,
        *,
        registry_path: Path | None = None,
        session_factory: Callable[..., RemoteCameraService] | None = None,
    ) -> None:
        configured = os.environ.get("AITL_REMOTE_CAMERAS")
        self._registry_path = Path(configured) if configured else (registry_path or DEFAULT_REGISTRY_PATH)
        self._registry_path = self._registry_path.expanduser().resolve()
        self._lock = RLock()
        # Serializes shared-frame publication with active-source transitions.
        # Profile/session bookkeeping uses _lock; this lock specifically prevents
        # an in-flight frame from the previous ESP racing a camera switch.
        self._publish_lock = RLock()
        self._frame_condition = Condition(self._lock)
        self._profiles: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, RemoteCameraService] = {}
        self._session_generations: dict[str, int] = {}
        self._latest_packets: dict[str, _CachedPacket] = {}
        self._active_source_id: str | None = None
        self._active_frame_number: int | None = None
        self._registry_warning: str | None = None
        self._session_factory = session_factory or RemoteCameraService
        self._load_registry()

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _validate_source_id(value: str) -> str:
        source_id = value.strip()
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise AppError(
                ErrorCode.CAMERA_SOURCE_INVALID,
                "source_id must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
                details={"source_id": source_id},
            )
        return source_id

    @staticmethod
    def _normalize_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
        merged = {**DEFAULT_CAMERA_SETTINGS, **(settings or {})}
        normalized: dict[str, Any] = {}

        frame_size = str(merged.get("frame_size", "QVGA")).upper()
        if frame_size not in FRAME_SIZES:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "Remote camera frame_size is not supported.",
                status_code=422,
                details={"frame_size": frame_size, "allowed": sorted(FRAME_SIZES)},
            )
        normalized["frame_size"] = frame_size

        for key, (minimum, maximum) in INT_SETTING_RANGES.items():
            try:
                value = int(merged[key])
            except (TypeError, ValueError) as exc:
                raise AppError(
                    ErrorCode.INVALID_REQUEST,
                    f"Remote camera setting {key} must be an integer.",
                    status_code=422,
                    details={"setting": key},
                ) from exc
            if value < minimum or value > maximum:
                raise AppError(
                    ErrorCode.INVALID_REQUEST,
                    f"Remote camera setting {key} is outside the supported range.",
                    status_code=422,
                    details={"setting": key, "value": value, "minimum": minimum, "maximum": maximum},
                )
            normalized[key] = value

        for key in BOOL_SETTING_KEYS:
            value = merged[key]
            if not isinstance(value, bool):
                raise AppError(
                    ErrorCode.INVALID_REQUEST,
                    f"Remote camera setting {key} must be true or false.",
                    status_code=422,
                    details={"setting": key},
                )
            normalized[key] = value

        return {key: normalized[key] for key in CAMERA_SETTING_KEYS}

    @staticmethod
    def _normalize_target_fps(value: int | None) -> int:
        fps = DEFAULT_TARGET_FPS if value is None else int(value)
        if fps < MIN_TARGET_FPS or fps > MAX_TARGET_FPS:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"Remote camera target_fps must be {MIN_TARGET_FPS}-{MAX_TARGET_FPS}.",
                status_code=422,
                details={"target_fps": fps},
            )
        return fps

    def _load_registry(self) -> None:
        if not self._registry_path.is_file():
            return
        try:
            payload = read_json(self._registry_path)
            if not isinstance(payload, dict):
                raise ValueError("remote camera registry must be an object")
            raw_cameras = payload.get("cameras", [])
            if not isinstance(raw_cameras, list):
                raise ValueError("remote camera registry cameras must be a list")

            profiles: dict[str, dict[str, Any]] = {}
            invalid_profiles = 0
            for raw in raw_cameras[:MAX_SAVED_CAMERAS]:
                if not isinstance(raw, dict):
                    invalid_profiles += 1
                    continue
                try:
                    source_id = self._validate_source_id(str(raw.get("source_id") or ""))
                    host = normalize_private_lan_ipv4(str(raw.get("host") or ""))
                    profiles[source_id] = {
                        "source_id": source_id,
                        "host": host,
                        "target_fps": self._normalize_target_fps(raw.get("target_fps")),
                        "settings": self._normalize_settings(raw.get("settings") if isinstance(raw.get("settings"), dict) else None),
                        "last_used_ms": int(raw.get("last_used_ms") or 0),
                    }
                except (AppError, TypeError, ValueError):
                    invalid_profiles += 1

            active = payload.get("active_source_id")
            active_id = str(active) if active is not None else None
            if active_id not in profiles:
                active_id = max(profiles.values(), key=lambda item: item["last_used_ms"], default={}).get("source_id")

            with self._lock:
                self._profiles = profiles
                self._active_source_id = active_id
                self._registry_warning = (
                    f"Ignored {invalid_profiles} invalid saved ESP camera profile(s)."
                    if invalid_profiles
                    else None
                )
        except Exception as exc:
            self._registry_warning = f"Saved ESP camera registry could not be read: {exc}"
            logger.warning("Remote camera registry load failed", extra={"path": str(self._registry_path)})

    def _persist_locked(self) -> None:
        payload = {
            "schema_version": 1,
            "active_source_id": self._active_source_id,
            "cameras": [
                {
                    "source_id": profile["source_id"],
                    "host": profile["host"],
                    "target_fps": profile["target_fps"],
                    "settings": profile["settings"],
                    "last_used_ms": profile["last_used_ms"],
                }
                for profile in sorted(
                    self._profiles.values(),
                    key=lambda item: (-int(item["last_used_ms"]), item["source_id"]),
                )
            ],
        }
        try:
            write_json_atomic(self._registry_path, payload)
            self._registry_warning = None
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Remote camera registry save failed")
            raise AppError(
                ErrorCode.SETTINGS_WRITE_FAILED,
                "Failed to save the ESP camera list and settings.",
                status_code=500,
                details={"path": str(self._registry_path)},
            ) from exc

    def _get_profile_locked(self, source_id: str | None = None) -> dict[str, Any]:
        selected = source_id or self._active_source_id
        if selected is None or selected not in self._profiles:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "Add or select an ESP32-CAM before using this action.",
                status_code=409,
            )
        return self._profiles[selected]

    def _session_locked(self, source_id: str, *, create: bool = False) -> RemoteCameraService | None:
        session = self._sessions.get(source_id)
        if session is None and create:
            generation = self._session_generations.get(source_id, 0) + 1
            self._session_generations[source_id] = generation

            def frame_sink(
                actual_source_id: str,
                packet: _FramePacket,
                *,
                expected_source_id: str = source_id,
                expected_generation: int = generation,
            ) -> int:
                if actual_source_id != expected_source_id:
                    logger.warning(
                        "Dropped remote camera frame with unexpected source identity",
                        extra={"expected_source_id": expected_source_id, "actual_source_id": actual_source_id},
                    )
                    return int(packet.sequence)
                return self._ingest_frame(
                    actual_source_id,
                    packet,
                    generation=expected_generation,
                )

            session = self._session_factory(frame_sink=frame_sink)
            self._sessions[source_id] = session
        return session

    def _invalidate_session_locked(self, source_id: str) -> RemoteCameraService | None:
        """Retire one session so any late worker frame is rejected by generation."""
        session = self._sessions.pop(source_id, None)
        self._session_generations[source_id] = self._session_generations.get(source_id, 0) + 1
        self._latest_packets.pop(source_id, None)
        return session

    def _ingest_frame(
        self,
        source_id: str,
        packet: _FramePacket,
        *,
        generation: int | None = None,
    ) -> int:
        """Cache every current session; publish only the selected source without switch races."""
        now_ms = self._now_ms()
        with self._frame_condition:
            if generation is not None and self._session_generations.get(source_id) != generation:
                return int(packet.sequence)
            self._latest_packets[source_id] = _CachedPacket(packet=packet, received_at_ms=now_ms)

        # Selection and session replacement also take _publish_lock. Re-check both
        # active identity and generation while holding it so a late frame from a
        # retired ESP/session cannot overwrite a newly selected or re-addressed ESP.
        with self._publish_lock:
            with self._lock:
                if generation is not None and self._session_generations.get(source_id) != generation:
                    return int(packet.sequence)
                active = self._active_source_id == source_id
            if not active or camera_frame_service.simulation_enabled:
                return int(packet.sequence)

            frame = camera_frame_service.store_upload(
                source_id=source_id,
                content_type="image/jpeg",
                content=packet.content,
            )
            with self._frame_condition:
                self._active_frame_number = frame.frame_number
                self._frame_condition.notify_all()
            return frame.frame_number

    @staticmethod
    def _clear_shared_physical_frame() -> None:
        """Clear the shared receiver frame during a selected-source transition.

        CameraFrameService intentionally owns one physical receiver slot. V036
        multi-camera selection must not leave the previous source in that slot
        while waiting for the newly selected ESP. The operation uses the service's
        own lock so concurrent uploads cannot expose a half-transition.
        """

        lock = getattr(camera_frame_service, "_lock")
        with lock:
            camera_frame_service._uploaded_frame = None  # type: ignore[attr-defined]

    def _switch_cache_max_age_ms_locked(self, source_id: str) -> int:
        """Allow only a few expected frame periods when promoting a cached source."""
        profile = self._profiles.get(source_id)
        fps = int(profile.get("target_fps", DEFAULT_TARGET_FPS)) if profile else DEFAULT_TARGET_FPS
        # At normal 10-30 FPS, an immediate switch should use a frame only a few
        # periods old. Very-low-FPS profiles get a wider bounded window.
        return min(MAX_SWITCH_CACHE_AGE_MS, max(250, round(3000 / max(1, fps))))

    def _publish_selected_cache_locked(self) -> None:
        """Switch the shared pipeline while the publication lock is held."""

        self._clear_shared_physical_frame()
        if camera_frame_service.simulation_enabled:
            with self._frame_condition:
                self._active_frame_number = None
                self._frame_condition.notify_all()
            return

        with self._lock:
            source_id = self._active_source_id
            cached = self._latest_packets.get(source_id) if source_id else None
            session = self._sessions.get(source_id) if source_id else None
            max_cache_age_ms = self._switch_cache_max_age_ms_locked(source_id) if source_id else 0

        fresh = bool(
            source_id
            and cached is not None
            and session is not None
            and session.streaming_requested
            and self._now_ms() - cached.received_at_ms <= max_cache_age_ms
        )
        if not fresh or source_id is None or cached is None:
            with self._frame_condition:
                self._active_frame_number = None
                self._frame_condition.notify_all()
            return

        frame = camera_frame_service.store_upload(
            source_id=source_id,
            content_type="image/jpeg",
            content=cached.packet.content,
        )
        with self._frame_condition:
            self._active_frame_number = frame.frame_number
            self._frame_condition.notify_all()

    def _publish_selected_cache(self) -> None:
        """Serialize a selected-source transition with all live frame publications."""
        with self._publish_lock:
            self._publish_selected_cache_locked()

    def sync_after_simulation_change(self) -> None:
        """Clear/reselect physical input after simulation is toggled.

        On simulation start this clears the receiver slot while simulated imagery
        owns CameraFrameService. On simulation stop it promotes only a recent
        selected cache; otherwise it waits for the next fresh ESP frame.
        """
        self._publish_selected_cache()

    def save_profile(
        self,
        *,
        host: str,
        source_id: str,
        settings: dict[str, Any] | None = None,
        target_fps: int | None = None,
        select: bool = True,
    ) -> dict:
        normalized_host = normalize_private_lan_ipv4(host)
        normalized_source = self._validate_source_id(source_id)
        normalized_settings = self._normalize_settings(settings)
        normalized_fps = self._normalize_target_fps(target_fps)

        # Host/source transitions are serialized with frame publication. A changed
        # IP retires the old session generation before the profile is replaced, so
        # even a worker that finishes late cannot publish bytes from the old ESP.
        session_to_reset: RemoteCameraService | None = None
        with self._publish_lock:
            with self._lock:
                previous_active = self._active_source_id
                existing = self._profiles.get(normalized_source)
                host_changed = existing is not None and existing.get("host") != normalized_host
                if existing is None and len(self._profiles) >= MAX_SAVED_CAMERAS:
                    raise AppError(
                        ErrorCode.INVALID_REQUEST,
                        f"PC Studio supports up to {MAX_SAVED_CAMERAS} saved ESP cameras in V036.",
                        status_code=409,
                    )
                for other_id, profile in self._profiles.items():
                    if other_id != normalized_source and profile["host"] == normalized_host:
                        raise AppError(
                            ErrorCode.CAMERA_SOURCE_INVALID,
                            "That ESP IP address is already saved under another source ID.",
                            status_code=409,
                            details={"host": normalized_host, "source_id": other_id},
                        )
                if host_changed:
                    session_to_reset = self._invalidate_session_locked(normalized_source)

                now_ms = self._now_ms()
                self._profiles[normalized_source] = {
                    "source_id": normalized_source,
                    "host": normalized_host,
                    "target_fps": normalized_fps,
                    "settings": normalized_settings,
                    "last_used_ms": now_ms,
                }
                if select or self._active_source_id is None:
                    self._active_source_id = normalized_source
                selection_changed = self._active_source_id != previous_active
                active_host_changed = host_changed and previous_active == normalized_source
                self._persist_locked()

            if selection_changed or active_host_changed:
                self._publish_selected_cache_locked()

        # Disconnect outside the publication lock. The generation was already
        # retired, so late frames are harmless and shutdown cannot wait on a worker
        # that is blocked behind this manager lock.
        if session_to_reset is not None:
            session_to_reset.disconnect()

        return self.status()

    def select(self, source_id: str) -> dict:
        normalized_source = self._validate_source_id(source_id)
        with self._publish_lock:
            with self._frame_condition:
                if normalized_source not in self._profiles:
                    raise AppError(
                        ErrorCode.CAMERA_SOURCE_INVALID,
                        "The requested ESP camera is not saved.",
                        status_code=404,
                        details={"source_id": normalized_source},
                    )
                selection_changed = self._active_source_id != normalized_source
                self._active_source_id = normalized_source
                self._profiles[normalized_source]["last_used_ms"] = self._now_ms()
                self._persist_locked()

            if selection_changed:
                self._publish_selected_cache_locked()
        logger.info("Active ESP camera selected", extra={"source_id": normalized_source})
        return self.status(refresh_device=False)

    def delete_profile(self, source_id: str) -> dict:
        normalized_source = self._validate_source_id(source_id)
        session: RemoteCameraService | None = None
        with self._publish_lock:
            with self._frame_condition:
                if normalized_source not in self._profiles:
                    raise AppError(
                        ErrorCode.CAMERA_SOURCE_INVALID,
                        "The requested ESP camera is not saved.",
                        status_code=404,
                        details={"source_id": normalized_source},
                    )
                was_active = self._active_source_id == normalized_source
                session = self._invalidate_session_locked(normalized_source)
                self._profiles.pop(normalized_source, None)
                if was_active:
                    self._active_source_id = max(
                        self._profiles.values(),
                        key=lambda item: int(item["last_used_ms"]),
                        default={},
                    ).get("source_id")
                    self._active_frame_number = None
                self._persist_locked()
                self._frame_condition.notify_all()

            if was_active:
                self._publish_selected_cache_locked()

        if session is not None:
            session.disconnect()
        return self.status()

    def connect(self, *, host: str, source_id: str) -> dict:
        normalized_host = normalize_private_lan_ipv4(host)
        normalized_source = self._validate_source_id(source_id)

        with self._lock:
            profile = self._profiles.get(normalized_source)
            settings = profile["settings"] if profile else DEFAULT_CAMERA_SETTINGS
            fps = profile["target_fps"] if profile else DEFAULT_TARGET_FPS

        self.save_profile(
            host=normalized_host,
            source_id=normalized_source,
            settings=dict(settings),
            target_fps=int(fps),
            select=True,
        )

        with self._lock:
            session = self._session_locked(normalized_source, create=True)
        assert session is not None
        session.connect(host=normalized_host, source_id=normalized_source)
        return self.status(refresh_device=False)

    def start_stream(
        self,
        *,
        settings: dict[str, Any],
        target_fps: int = DEFAULT_TARGET_FPS,
        fetch_interval_ms: int | None = None,
    ) -> dict:
        with self._lock:
            profile = self._get_profile_locked()
            source_id = profile["source_id"]
            host = profile["host"]
            session = self._session_locked(source_id, create=False)
        if session is None or not session.status().get("configured"):
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "Connect the selected ESP32-CAM before starting its stream.",
                status_code=409,
                details={"source_id": source_id, "host": host},
            )

        effective_fps = int(target_fps)
        if fetch_interval_ms is not None and effective_fps == DEFAULT_TARGET_FPS:
            interval = max(1, int(fetch_interval_ms))
            effective_fps = max(MIN_TARGET_FPS, min(MAX_TARGET_FPS, round(1000 / interval)))

        normalized_fps = self._normalize_target_fps(effective_fps)
        normalized_settings = self._normalize_settings(settings)
        self.save_profile(
            host=host,
            source_id=source_id,
            settings=normalized_settings,
            target_fps=normalized_fps,
            select=True,
        )
        session.start_stream(
            settings=normalized_settings,
            target_fps=normalized_fps,
            fetch_interval_ms=fetch_interval_ms,
        )
        return self.status(refresh_device=False)

    def stop_stream(self, *, best_effort: bool = False) -> dict:
        with self._lock:
            profile = self._get_profile_locked()
            session = self._session_locked(profile["source_id"], create=False)
        if session is None:
            return self.status()
        session.stop_stream(best_effort=best_effort)
        return self.status(refresh_device=False)

    def disconnect(self) -> dict:
        with self._lock:
            profile = self._get_profile_locked()
            session = self._session_locked(profile["source_id"], create=False)
        if session is not None:
            session.disconnect()
        return self.status(refresh_device=False)

    def disconnect_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            try:
                session.disconnect()
            except Exception:
                logger.exception("Remote camera shutdown disconnect failed")

    def stop(self) -> None:
        """FastAPI lifespan hook: close every saved camera's live session."""
        self.disconnect_all()

    @property
    def streaming_requested(self) -> bool:
        with self._lock:
            active = self._active_source_id
            session = self._sessions.get(active) if active else None
        return bool(session and session.streaming_requested)

    def wait_for_new_frame(self, after_frame_number: int, timeout_seconds: float = 1.0) -> CameraFrame | None:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        with self._frame_condition:
            while self.streaming_requested:
                current = self._active_frame_number
                if current is not None and current != after_frame_number:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._frame_condition.wait(timeout=remaining)

        frame = camera_frame_service.latest_frame()
        with self._lock:
            active = self._active_source_id
        if frame is None or frame.frame_number == after_frame_number or frame.source_id != active:
            return None
        return frame

    def _camera_summary_locked(self, profile: dict[str, Any], *, refresh_device: bool = False) -> dict[str, Any]:
        source_id = profile["source_id"]
        session = self._sessions.get(source_id)
        session_status = session.status(refresh_device=refresh_device) if session is not None else None
        return {
            "source_id": source_id,
            "host": profile["host"],
            "target_fps": profile["target_fps"],
            "settings": dict(profile["settings"]),
            "last_used_ms": profile["last_used_ms"],
            "selected": source_id == self._active_source_id,
            "connected": bool(session_status and session_status.get("configured")),
            "device_reachable": bool(session_status and session_status.get("device_reachable")),
            "streaming": bool(session_status and session_status.get("streaming")),
            "stream_connected": bool(session_status and session_status.get("stream_connected")),
            "paused_for_simulation": bool(session_status and session_status.get("paused_for_simulation")),
            "measured_fps": float(session_status.get("measured_fps", 0.0)) if session_status else 0.0,
            "last_success_at_ms": session_status.get("last_success_at_ms") if session_status else None,
            "last_error": session_status.get("last_error") if session_status else None,
        }

    def status(self, *, refresh_device: bool = False) -> dict:
        with self._lock:
            active_id = self._active_source_id
            profile = self._profiles.get(active_id) if active_id else None
            session = self._sessions.get(active_id) if active_id else None

        if session is not None:
            active_status = session.status(refresh_device=refresh_device)
        else:
            active_status = {
                "configured": False,
                "device_reachable": False,
                "worker_running": False,
                "streaming": False,
                "stream_connected": False,
                "paused_for_simulation": False,
                "transport": "idle",
                "stream_protocol": None,
                "host": profile["host"] if profile else None,
                "source_id": profile["source_id"] if profile else None,
                "status_url": f"http://{profile['host']}/status" if profile else None,
                "capture_url": f"http://{profile['host']}/capture" if profile else None,
                "stream_url": f"tcp://{profile['host']}:81" if profile else None,
                "target_fps": profile["target_fps"] if profile else DEFAULT_TARGET_FPS,
                "fetch_interval_ms": round(1000 / (profile["target_fps"] if profile else DEFAULT_TARGET_FPS)),
                "measured_fps": 0.0,
                "last_frame_interval_ms": None,
                "stream_reconnects": 0,
                "session_recoveries": 0,
                "consecutive_failures": 0,
                "reconnect_backoff_ms": 0,
                "stream_bytes_received": 0,
                "dropped_stale_frames": 0,
                "source_sequence_gaps": 0,
                "last_remote_sequence": None,
                "last_source_uptime_ms": None,
                "connected_at_ms": None,
                "stream_started_at_ms": None,
                "last_stream_connected_at_ms": None,
                "last_recovery_at_ms": None,
                "last_probe_at_ms": None,
                "last_attempt_at_ms": None,
                "last_success_at_ms": None,
                "last_http_status": None,
                "last_frame_number": None,
                "last_frame_bytes": 0,
                "successful_fetches": 0,
                "failed_fetches": 0,
                "last_error": None,
                "settings": dict(profile["settings"]) if profile else dict(DEFAULT_CAMERA_SETTINGS),
                "device": {},
                "control_sequence": ["select", "connect", "config", "start", "persistent_tcp_jpeg", "stop"],
                "prototype_only": True,
            }

        with self._lock:
            # Re-read after optional status refresh in case another request changed selection.
            active_id = self._active_source_id
            profile = self._profiles.get(active_id) if active_id else None
            if profile is not None:
                active_status["host"] = profile["host"]
                active_status["source_id"] = profile["source_id"]
                active_status["target_fps"] = profile["target_fps"]
                active_status["settings"] = dict(profile["settings"])
                active_status["fetch_interval_ms"] = round(1000 / max(1, int(profile["target_fps"])))
            summaries = [
                self._camera_summary_locked(item, refresh_device=False)
                for item in sorted(
                    self._profiles.values(),
                    key=lambda value: (-int(value["last_used_ms"]), value["source_id"]),
                )
            ]
            warning = self._registry_warning

        active_status.update(
            {
                "active_source_id": active_id,
                "camera_count": len(summaries),
                "cameras": summaries,
                "registry_warning": warning,
                "multi_camera": True,
                "max_saved_cameras": MAX_SAVED_CAMERAS,
            }
        )
        return active_status


remote_camera_manager = RemoteCameraManager()
