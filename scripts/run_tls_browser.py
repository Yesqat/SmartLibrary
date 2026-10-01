"""Run only the localhost TLS browser test inside the matching pinned Linux browser image."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = (
    "mcr.microsoft.com/playwright:v1.63.0-noble@sha256:"
    "eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27"
)


def main() -> None:
    results = ROOT / "work/tls-browser-results"
    results.mkdir(parents=True, exist_ok=True)
    args = [
        "docker",
        "run",
        "--rm",
        "--init",
        "--shm-size=1g",
        "--network",
        "smartlibrary-production-check_application",
    ]
    for name in ("frontend", "tests", "scripts"):
        args += ["-v", f"{ROOT / name}:/workspace/{name}:ro"]
    args += [
        "-v",
        f"{results}:/results",
        "-e",
        "PLAYWRIGHT_OUTPUT_DIR=/results/run",
        IMAGE,
        "node",
        "/workspace/scripts/run_tls_browser.cjs",
    ]
    raise SystemExit(subprocess.run(args, cwd=ROOT, check=False).returncode)


if __name__ == "__main__":
    main()
