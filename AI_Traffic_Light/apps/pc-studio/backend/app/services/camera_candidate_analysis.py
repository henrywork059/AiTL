from __future__ import annotations
from typing import Any


def _i(p: dict[str, Any], k: str) -> int:
    try: return int(p.get(k, 0) or 0)
    except (TypeError, ValueError): return 0

def _f(p: dict[str, Any], k: str) -> float:
    try: return float(p.get(k, 0.0) or 0.0)
    except (TypeError, ValueError): return 0.0

def good(p: dict[str, Any], minimum_ratio: float = 0.65) -> bool:
    target=max(1,_i(p,'target_fps'))
    return _i(p,'frames')>0 and _i(p,'disconnects')==0 and _i(p,'bad_frames')==0 and _i(p,'unexpected_send_failures')==0 and _i(p,'deadline_drops')==0 and _f(p,'measured_fps')/target>=minimum_ratio

def isolate_transport_candidates(*, synthetic: dict[str,Any], capture_synthetic: dict[str,Any], direct: dict[str,Any], staged: dict[str,Any], managed: dict[str,Any], capture_probe: dict[str,Any], control_successes:int, control_total:int, rssi_min:int|None) -> dict[str,Any]:
    sg=good(synthetic); cg=good(capture_synthetic); dg=good(direct); tg=good(staged)
    mg=_i(managed,'frames')>=3 and _i(managed,'failed_fetches')==0 and _i(managed,'reconnects')==0
    findings=[]; ruled=[]
    def add(code,layer,confidence,evidence,action): findings.append({'code':code,'layer':layer,'confidence':confidence,'evidence':evidence,'action':action})
    if _i(capture_probe,'successes')==0:
        add('camera_capture_path','camera_capture','high','Camera-only capture probes failed before TCP streaming.','Inspect sensor/ribbon/camera DMA before network tuning.')
    elif sg is False:
        add('camera_independent_tcp_path','lan_lwip','high',f"Internal-DRAM synthetic stream failed: {_i(synthetic,'frames')} frames, {_i(synthetic,'disconnects')} disconnects, {_i(synthetic,'unexpected_send_failures')} ESP send failures.",'The failure does not require camera framebuffer/PSRAM traffic; inspect Wi-Fi/LAN, TCP ACK/window progress, AP path and lwIP scheduling.')
        ruled.append('camera framebuffer/PSRAM is not required to reproduce the failure')
    elif sg and not cg:
        add('camera_network_coexistence','camera_wifi_scheduling','high','Synthetic DRAM transport is healthy until camera capture/DMA load is added.','Investigate camera DMA/PSRAM activity starving Wi-Fi/lwIP task servicing.')
        ruled.append('basic LAN/TCP path works without camera activity')
    elif sg and cg and not dg and tg:
        add('direct_psram_to_lwip','psram_lwip','high','Synthetic transport and camera-load synthetic transport pass; direct PSRAM framebuffer send fails; staged internal-RAM send passes.','Use staged internal-RAM chunks for production sending; direct framebuffer pointer/lwIP interaction is isolated.')
        ruled += ['basic LAN/TCP path','camera capture alone','PC managed receiver']
    elif sg and cg and not dg and not tg:
        add('camera_stream_backpressure','camera_tcp_interaction','high','Synthetic paths pass but both direct and staged real-JPEG sends fail.','The issue depends on real camera streaming but is not fixed by removing the PSRAM pointer from send(); inspect camera/Wi-Fi coexistence, packet ACK latency and sender scheduling.')
    elif sg and cg and dg and not mg:
        add('pc_studio_receiver','pc_studio','high','Direct diagnostic receiving passes but the normal managed worker fails.','Focus on RemoteCameraService/manager receive, session and reconnect logic.')
        ruled += ['ESP camera sender','basic LAN/TCP transport']
    elif sg and cg and dg and tg and mg:
        add('none_reproduced','none','medium','Synthetic, camera-load, direct, staged and managed paths all passed.','Repeat while the intermittent fault is visible; no candidate reproduced during this run.')
    if control_successes < control_total:
        add('http_control_plane','http_control','high' if control_successes==0 else 'medium',f'HTTP control succeeded {control_successes}/{control_total} times.','Treat control-server responsiveness separately from image transport.')
    if rssi_min is not None and rssi_min <= -68:
        add('rf_margin','wifi','medium',f'RSSI reached {rssi_min} dBm.','Repeat on the strongest intended BSSID; stable association does not guarantee low retransmission/ACK latency.')
    return {'primary_candidate':findings[0]['code'] if findings else 'unknown','findings':findings,'ruled_out':ruled,'matrix':{'synthetic_dram':sg,'camera_load_synthetic':cg,'camera_direct_psram':dg,'camera_staged_internal_ram':tg,'pc_studio_managed':mg}}
