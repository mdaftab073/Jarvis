import json
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from app.services.system_health_service import validate_system


def main() -> int:
    checks = validate_system()
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0 if checks["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())