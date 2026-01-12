#!/usr/bin/env python3
"""CI secret scanner: lightweight heuristic checks for likely secrets.
Exits 0 if no matches, 1 if matches found.

Behavior:
 - respects an ignore file `.secret-scan-ignore` containing newline-separated glob patterns
 - ignores common directories (.git, node_modules, venv, dist, build)
"""
import argparse
import fnmatch
import re
import sys
from pathlib import Path

# Patterns to scan for (heuristic)
PATTERNS = {
    "AWS Access Key ID": re.compile(r"AKIA[0-9A-Z]{16}"),
    "AWS Secret": re.compile(r"(?i)aws(.{0,20})?secret"),
    "Private Key Block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "Slack Token": re.compile(r"xox[baprs]-[0-9A-Za-z]{10,}") ,
    "API Key (sk_)": re.compile(r"sk_(live|test|prod)_[0-9a-zA-Z]{8,}"),
    "Password like": re.compile(r"(?i)password\s*=\s*.+")
}

# Default ignored dirs
DEFAULT_IGNORED = {".git", "node_modules", "venv", "dist", "build", ".venv"}

root = Path.cwd()


def load_ignore_globs(ignore_file: Path):
    if not ignore_file.exists():
        return []
    globs = []
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        globs.append(line)
    return globs


def is_ignored(path: Path, ignore_globs):
    # match against repository-relative posix path
    try:
        rel = str(path.relative_to(root).as_posix())
    except Exception:
        rel = str(path)
    for g in ignore_globs:
        if fnmatch.fnmatch(rel, g):
            return True
    return False


parser = argparse.ArgumentParser(description="Lightweight repo secret scanner")
parser.add_argument("--ignore-file", default=".secret-scan-ignore", help="Path to ignore globs file")
parser.add_argument("--verbose", action="store_true", help="Verbose output")
args = parser.parse_args()

ignore_file = root.joinpath(args.ignore_file)
ignore_globs = load_ignore_globs(ignore_file)

matches = []
scanned_files = 0
for path in root.rglob("*"):
    if any(part in DEFAULT_IGNORED for part in path.parts):
        continue
    if path.is_file():
        # skip binary files by suffix heuristic
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pyc", ".class", ".exe"}:
            continue
        if is_ignored(path, ignore_globs):
            if args.verbose:
                print(f"Skipping (ignored): {path}")
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        scanned_files += 1
        for name, pattern in PATTERNS.items():
            for m in pattern.finditer(text):
                # ignore .env.example and known template placeholders
                if "env.example" in str(path).lower():
                    continue
                matches.append((str(path), name, m.group(0)))

if matches:
    print("Potential secrets found:")
    for p, name, val in matches:
        print(f"  - {name} in {p}: {val}")
    print(f"Scanned files: {scanned_files}")
    sys.exit(1)

if args.verbose:
    print(f"No likely secrets found. Scanned files: {scanned_files}")
else:
    print("No likely secrets found.")
sys.exit(0)
