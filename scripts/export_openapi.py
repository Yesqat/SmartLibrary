"""Export the current API schema, without connecting to PostgreSQL or Redis."""

import argparse
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.main import create_app  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true", help="Fail if the saved schema has drifted")
args = parser.parse_args()
schema = create_app().openapi()
target = root / "docs/openapi.json"
if args.check:
    if not target.exists() or json.loads(target.read_text(encoding="utf-8")) != schema:
        raise SystemExit("OpenAPI schema drift: export the schema and regenerate frontend types.")
    print("OpenAPI schema is synchronized")
else:
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported docs/openapi.json")
