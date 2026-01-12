#!/usr/bin/env python3
"""CI secret scanner: lightweight heuristic checks for likely secrets.
Exits 0 if no matches, 1 if matches found.
"""
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

# Files / directories to ignore
IGNORED = {".git", "node_modules", "venv", "dist", "build"}

root = Path.cwd()

matches = []
for path in root.rglob("*"):
    if any(part in IGNORED for part in path.parts):
        continue
    if path.is_file():
        # skip binary files by suffix heuristic
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pyc", ".class", ".exe"}:
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
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
    sys.exit(1)

print("No likely secrets found.")
sys.exit(0)
