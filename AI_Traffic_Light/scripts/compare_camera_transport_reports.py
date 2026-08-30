from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PRIMARY_KEYS = [
    'snapshot_polling', 'mjpeg', 'direct_sendmsg_5000', 'direct_send',
    'staged_send', 'dram_copy_send', 'udp'
]


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema_version') != 2:
        raise SystemExit(f'{path}: not an AiTL R4 transport benchmark report')
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description='Compare AiTL R4 camera transport reports across AP/power environments')
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()
    reports = [(path, load(path)) for path in args.reports]

    print('\nAiTL camera transport environment comparison\n')
    print(f"{'Environment':24} {'Diagnosis':31} {'Recommended':18} {'RSSI':>7}")
    print('-' * 90)
    for path, report in reports:
        env = str(report.get('environment_label') or path.stem)
        diagnosis = str((report.get('diagnosis') or {}).get('diagnosis_code') or '-')
        rec = str((report.get('diagnosis') or {}).get('recommended_key') or '-')
        rssi = (report.get('final_device') or {}).get('rssi')
        print(f'{env[:24]:24} {diagnosis[:31]:31} {rec[:18]:18} {str(rssi):>7}')

    print('\nPer-transport result / FPS\n')
    header = f"{'Transport':28}" + ''.join(f" {str(r.get('environment_label') or p.stem)[:18]:>18}" for p, r in reports)
    print(header)
    print('-' * len(header))
    for key in PRIMARY_KEYS:
        row = f'{key:28}'
        for _path, report in reports:
            results = {x.get('key'): x for x in report.get('results', []) if isinstance(x, dict)}
            item = results.get(key, {})
            text = f"{item.get('status', '-')} {float(item.get('measured_fps') or 0):.1f}fps"
            row += f' {text:>18}'
        print(row)

    if len(reports) >= 2:
        signatures = [(r.get('diagnosis') or {}).get('diagnosis_code') for _, r in reports]
        if len(set(signatures)) > 1:
            print('\nInterpretation: the diagnosis changes across environments. Router/RF/power conditions materially affect the failure and must be resolved before locking a production transport.')
        else:
            print('\nInterpretation: the same diagnosis repeats across environments, which strengthens the case for a firmware/transport-path root cause rather than one AP condition.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
