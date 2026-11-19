#!/usr/bin/env python3
"""Fill .env from .env.example and keep a copy in the central env store.

    python3 scripts/setup_env.py           ask for anything missing, then sync the store copy
    python3 scripts/setup_env.py --pull    restore .env from the store (fresh clone, new machine)
    python3 scripts/setup_env.py --github  also push secret and private values to GitHub secrets

Stdlib only (Python 3.9+), so it runs before `uv sync` and in non-Python repos.
"""

import argparse
import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / ".env.example"
ENV = ROOT / ".env"
LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=\s*(?:#(.*))?$")


def parse_example():
    """Return {name: (tag, default)} in file order."""
    spec = {}
    for line in EXAMPLE.read_text().splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        notes = (m.group(2) or "").split()
        tag = "secret" if "secret" in notes else "private" if "private" in notes else "public"
        default = next((n.split("=", 1)[1] for n in notes if n.startswith("default=")), "")
        spec[m.group(1)] = (tag, default)
    return spec


def read_env(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        values[key.strip()] = val
    return values


def write_env(path, spec, values):
    lines = [f"{k}='{values.get(k, '')}'" for k in spec]
    lines += [f"{k}='{v}'" for k, v in values.items() if k not in spec]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)


def ask(name, tag, default):
    label = f"{name} [{tag}]" + (f" (default {default})" if default else "")
    prompt = f"  {label}: "
    val = getpass.getpass(prompt) if tag == "secret" else input(prompt)
    val = val.strip() or default
    if "'" in val:
        sys.exit(f"{name}: single quotes are not supported in values")
    return val


def repo_name():
    answers = ROOT / ".copier-answers.yml"
    if answers.exists():
        for line in answers.read_text().splitlines():
            if line.startswith("project_name:"):
                return line.split(":", 1)[1].strip()
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'^name\s*=\s*"([^"]+)"', pyproject.read_text(), re.M)
        if m:
            return m.group(1)
    return ROOT.name


def store_dir_default():
    answers = ROOT / ".copier-answers.yml"
    if answers.exists():
        for line in answers.read_text().splitlines():
            if line.startswith("env_store_dir:"):
                return line.split(":", 1)[1].strip()
    return "~/workspace/envs"


def push_github(spec, values):
    names = [k for k, (tag, _) in spec.items() if tag != "public" and values.get(k)]
    if not names:
        print("No secret or private values to push.")
        return
    print("Push to GitHub Actions secrets: " + ", ".join(names))
    if input("Continue? [y/N] ").strip().lower() != "y":
        return
    for k in names:
        subprocess.run(
            ["gh", "secret", "set", k.upper()], input=values[k], text=True, check=True, cwd=ROOT
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", default=None)
    p.add_argument("--repo", default=None)
    p.add_argument("--pull", action="store_true", help="restore .env from the store copy")
    p.add_argument("--github", action="store_true", help="push secret and private values to GitHub")
    args = p.parse_args()

    store = Path(os.path.expanduser(args.store_dir or store_dir_default()))
    stored = store / f"{args.repo or repo_name()}.env"
    spec = parse_example()

    if args.pull:
        if not stored.exists():
            sys.exit(f"No store copy at {stored}")
        shutil.copy2(stored, ENV)
        ENV.chmod(0o600)
        print(f"Restored .env from {stored}")
        return

    values = read_env(ENV)
    if not values and stored.exists():
        print(f"No .env here; using the store copy at {stored}")
        values = read_env(stored)

    missing = [k for k in spec if k not in values]
    if missing:
        print("Values for .env (enter to leave blank):")
        for k in missing:
            tag, default = spec[k]
            values[k] = ask(k, tag, default)
    write_env(ENV, spec, values)

    if stored.exists() and read_env(stored) != read_env(ENV):
        backup = stored.with_suffix(".env.bak")
        shutil.copy2(stored, backup)
        print(f"Store copy differed; old version saved to {backup}")
    store.mkdir(parents=True, exist_ok=True)
    store.chmod(0o700)
    shutil.copy2(ENV, stored)
    stored.chmod(0o600)
    print(f"Wrote .env and {stored}")

    if args.github:
        push_github(spec, values)


if __name__ == "__main__":
    main()
