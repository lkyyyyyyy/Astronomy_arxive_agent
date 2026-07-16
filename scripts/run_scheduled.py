from __future__ import annotations

import argparse
from datetime import datetime, time
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.loader import load_config


STATE_PATH = PROJECT_ROOT / ".state/scheduled-runs.json"
SUMMARY_PATH = PROJECT_ROOT / ".state/last-scheduled-summary.json"
RUN_HOUR = 8


def main() -> int:
    os.chdir(PROJECT_ROOT)
    args = parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    config = load_config(config_path)
    now = datetime.now(ZoneInfo(config.app.timezone))
    run_date = now.date().isoformat()

    if now.time() < time(RUN_HOUR, 0):
        print(f"[scheduled] {now.isoformat()} before 08:00; waiting for calendar run.")
        return 0

    state = read_state()
    if state.get("last_successful_run_date") == run_date:
        print(f"[scheduled] {run_date} already sent successfully; skipping duplicate.")
        return 0

    command = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--config",
        str(config_path),
        "--skip-delivery-if-empty",
        "--summary-json",
        str(SUMMARY_PATH),
    ]
    print(f"[scheduled] running {' '.join(command)}")
    result = subprocess.run(command, check=False)
    summary = read_json(SUMMARY_PATH)

    if result.returncode == 0 and is_successful_summary(summary):
        write_state(
            {
                "last_successful_run_date": run_date,
                "target_date": summary.get("target_date", ""),
                "total_fetched": summary.get("total_fetched", 0),
                "selected_count": summary.get("selected_count", 0),
                "updated_at": now.isoformat(),
            }
        )
        print(f"[scheduled] marked {run_date} as successfully sent.")
        return 0

    print(
        "[scheduled] run did not count as successful; "
        "it will retry on the next automatic launch after 08:00."
    )
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded scheduled runner.")
    parser.add_argument("--config", default="config/config.yaml")
    return parser.parse_args()


def is_successful_summary(summary: dict[str, object]) -> bool:
    return (
        int(summary.get("total_fetched") or 0) > 0
        and int(summary.get("delivery_errors") or 0) == 0
    )


def read_state() -> dict[str, object]:
    return read_json(STATE_PATH)


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_state(payload: dict[str, object]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
