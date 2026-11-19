#!/usr/bin/env python3
"""Pre-commit hook: fail if a secret or private value from .env appears in a staged file.

Gitleaks catches known key formats and personal-info patterns. This catches your actual
values, whatever they look like. Tags come from .env.example (see scripts/setup_env.py).
Prints the variable name and file, never the value.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_env import ENV, EXAMPLE, parse_example, read_env  # noqa: E402

MIN_LEN = 6


def main(files):
    if not ENV.exists() or not EXAMPLE.exists():
        return 0
    spec = parse_example()
    values = read_env(ENV)
    watched = {
        k: v
        for k, v in values.items()
        if len(v) >= MIN_LEN and spec.get(k, ("private", ""))[0] != "public"
    }
    found = 0
    for f in files:
        path = Path(f)
        if path.name in {".env", ".env.example"} or not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for k, v in watched.items():
            if v in text:
                print(f"{f}: contains the value of {k} from .env")
                found += 1
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
