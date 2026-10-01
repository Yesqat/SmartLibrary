"""Run real browser cases on the isolated E2E stack, with per-file Redis fixture isolation.

Never targets the development project. Limits retain their actual configured values;
no keys are reset within a test file. Public registration/login remain real HTTP flows.
"""

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "smartlibrary-e2e",
    "--env-file",
    "work/e2e.env",
    "-f",
    "docker-compose.yml",
    "-f",
    "docker-compose.dev.yml",
    "-f",
    "docker-compose.e2e.yml",
]
RESET_TEST_KEYS = """
from app.core.config import Settings
from redis import Redis
s=Settings()
assert s.app_env == 'test' and s.auth_rate_namespace == 'smartlibrary:e2e'
with Redis.from_url(s.redis_dsn) as r:
    keys=list(r.scan_iter(match=s.auth_rate_namespace+':*'))
    if keys: r.delete(*keys)
print('Isolated test-file rate counters initialized; policy limits unchanged.')
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="Optional *.spec.ts basenames")
    parser.add_argument("--label", default="phase20")
    args = parser.parse_args()
    if not args.label.replace("-", "").isalnum():
        raise SystemExit("Use a simple log label")
    values = {}
    for line in (ROOT / "work/e2e.env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    env = dict(os.environ)
    env.update(
        E2E_SEED_PASSWORD=values["DEV_SEED_PASSWORD"],
        E2E_BASE_URL="http://localhost:8081",
        PLAYWRIGHT_CHANNEL=os.environ.get("PLAYWRIGHT_CHANNEL", "msedge"),
    )
    files = args.files or [p.name for p in sorted((ROOT / "tests/e2e").glob("*.spec.ts"))]
    for name in files:
        if Path(name).name != name or not (ROOT / "tests/e2e" / name).is_file():
            raise SystemExit("Use an existing test basename")
        subprocess.run(
            [*COMPOSE, "exec", "-T", "backend", "python", "-c", RESET_TEST_KEYS],
            cwd=ROOT,
            check=True,
        )
        log = ROOT / "work/logs" / f"{args.label}-e2e-{name}.txt"
        print(f"Running {name}; log {log.relative_to(ROOT)}", flush=True)
        with log.open("w", encoding="utf-8") as output:
            result = subprocess.run(
                ["node", "node_modules/@playwright/test/cli.js", "test", name, "--workers=1"],
                cwd=ROOT / "frontend",
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if result.returncode:
            raise SystemExit(f"FAILED {name}; inspect its saved log (credentials stay private).")
        print(f"PASS {name}", flush=True)
    print(f"All {len(files)} selected browser files passed.")


if __name__ == "__main__":
    main()
