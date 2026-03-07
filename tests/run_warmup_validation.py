import json
import subprocess
import sys

REPORT_FILE = "tests/warmup_report.json"


def main() -> int:
    command = [
        sys.executable,
        "app/pipeline/warm_up_runtime.py",
        "--flush-cache-state",
        "--verify-second-pass",
    ]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        print(f"Warm-up command failed with exit code {result.returncode}")
        return result.returncode

    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        report = json.load(f)

    summary = {
        "datasets": report.get("datasets", []),
        "row_stats": report.get("row_stats", {}),
        "runs": report.get("runs", []),
    }

    print("\nWARM-UP VALIDATION\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
