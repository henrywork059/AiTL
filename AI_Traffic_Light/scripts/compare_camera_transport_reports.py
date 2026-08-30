from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PRIMARY_KEYS = [
    'snapshot_polling', 'mjpeg', 'direct_sendmsg_1200', 'direct_sendmsg_5000', 'direct_send',
    'staged_send', 'dram_copy_sendmsg', 'dram_copy_send', 'udp'
]


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 3:
        raise SystemExit(f'{path}: not an AiTL R5 transport benchmark report')
    return data


def result_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {x.get('key'): x for x in report.get('results', []) if isinstance(x, dict) and x.get('key')}


def fmt_resource(item: dict[str, Any], key: str) -> str:
    telemetry = item.get('telemetry') if isinstance(item.get('telemetry'), dict) else {}
    after = telemetry.get('resource_after') if isinstance(telemetry.get('resource_after'), dict) else {}
    value = after.get(key)
    return '-' if value is None else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare AiTL R5 camera transport reports across AP/power environments')
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()
    reports = [(path, load(path)) for path in args.reports]

    print('\nAiTL R5 camera transport environment comparison\n')
    print(f"{'Environment':24} {'Diagnosis':31} {'Recommended':18} {'RSSI':>7} {'Duration':>10}")
    print('-' * 105)
    for path, report in reports:
        env = str(report.get('environment_label') or path.stem)
        diagnosis = str((report.get('diagnosis') or {}).get('diagnosis_code') or '-')
        rec = str((report.get('diagnosis') or {}).get('recommended_key') or '-')
        rssi = (report.get('final_device') or {}).get('rssi')
        duration = float((report.get('run_context') or {}).get('duration_ms') or 0) / 1000.0
        print(f'{env[:24]:24} {diagnosis[:31]:31} {rec[:18]:18} {str(rssi):>7} {duration:>8.1f}s')

    print('\nPer-transport result / FPS / completion\n')
    header = f"{'Transport':28}" + ''.join(f" {str(r.get('environment_label') or p.stem)[:24]:>24}" for p, r in reports)
    print(header)
    print('-' * len(header))
    for key in PRIMARY_KEYS:
        row = f'{key:28}'
        for _path, report in reports:
            item = result_map(report).get(key, {})
            text = (
                f"{item.get('status', '-')} "
                f"{float(item.get('measured_fps') or 0):.1f}fps "
                f"{float(item.get('completion_ratio') or 0)*100:.0f}%"
            )
            row += f' {text:>24}'
        print(row)

    print('\nKey memory / accepted-byte evidence\n')
    for path, report in reports:
        env = str(report.get('environment_label') or path.stem)
        results = result_map(report)
        print(f'[{env}]')
        for key in ('direct_sendmsg_1200', 'direct_sendmsg_5000', 'direct_send', 'staged_send', 'dram_copy_send'):
            item = results.get(key)
            if not item:
                continue
            telemetry = item.get('telemetry') if isinstance(item.get('telemetry'), dict) else {}
            after = telemetry.get('device_after') if isinstance(telemetry.get('device_after'), dict) else {}
            poll = telemetry.get('status_poll') if isinstance(telemetry.get('status_poll'), dict) else {}
            summary = poll.get('sample_summary') if isinstance(poll.get('sample_summary'), dict) else {}
            frame = after.get('last_frame_bytes')
            accepted = after.get('last_accepted_bytes')
            ratio = '-'
            try:
                if frame:
                    ratio = f'{float(accepted or 0)/float(frame)*100:.1f}%'
            except (TypeError, ValueError, ZeroDivisionError):
                pass
            print(
                f'  {key:24} {item.get("status", "-"):4} '
                f'errno={after.get("last_errno")} accepted={accepted}/{frame} ({ratio}) '
                f'internal_min={summary.get("internal_free_min")} largest_min={summary.get("internal_largest_min")}'
            )

    if len(reports) >= 2:
        signatures = [(r.get('diagnosis') or {}).get('diagnosis_code') for _, r in reports]
        if len(set(signatures)) > 1:
            print('\nInterpretation: diagnosis changes across environments. Router/RF/power conditions materially affect the failure; do not lock a production transport until that environmental dependency is explained.')
        else:
            print('\nInterpretation: the same diagnosis repeats across environments, strengthening a firmware/transport-path root cause over one AP condition.')

        recommendations = [(r.get('diagnosis') or {}).get('recommended_key') for _, r in reports]
        if len(set(recommendations)) == 1:
            print(f'Production-candidate consistency: all reports recommend {recommendations[0]}.')
        else:
            print(f'Production-candidate consistency: recommendations differ: {recommendations}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
