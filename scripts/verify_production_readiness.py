from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from copilot.server import _production_setup_payload  # noqa: E402


def main() -> None:
    payload = _production_setup_payload()
    print(f"TradePulse production readiness: {payload['score']}%")
    print(f"Required ready: {payload['required_ready']}/{payload['required_total']}")
    print(f"Private beta: {'ready' if payload['private_beta_ready'] else 'setup needed'}")
    print(f"Paid beta: {'ready' if payload['paid_beta_ready'] else 'setup needed'}")
    print("")
    if payload["blockers"]:
        print("Required next actions:")
        for item in payload["blockers"]:
            print(f"- {item['missing_text']}")
    else:
        print("No required production blockers were detected.")
    print("")
    print("Important URLs:")
    for label, value in payload["urls"].items():
        print(f"- {label}: {value}")
    print("")
    print("Runtime modes:")
    for label, value in payload["runtime_modes"].items():
        print(f"- {label}: {value}")


if __name__ == "__main__":
    main()
