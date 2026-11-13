"""List Chinese text left in tracked files.

Exempt: vendored files pinned in python/flow2api/upstream.json, README.zh-CN.md,
"locales" blocks in JSON files, and lines carrying the zh-compat marker. The
marker keeps a literal that must match Chinese text from pinned upstream code
or from data written by earlier GFlow versions.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CJK_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x3000, 0x303F), (0xFF01, 0xFF5E))
CJK = re.compile("[" + "".join(f"{chr(low)}-{chr(high)}" for low, high in CJK_RANGES) + "]")
MARKER = "zh-compat"
EXEMPT = {"README.zh-CN.md"}


def strip_locales(value):
    if isinstance(value, dict):
        return {key: strip_locales(item) for key, item in value.items() if key != "locales"}
    if isinstance(value, list):
        return [strip_locales(item) for item in value]
    return value


def json_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_strings(item)
    elif isinstance(value, str):
        yield value


def findings():
    pinned = set(json.loads((ROOT / "python/flow2api/upstream.json").read_text(encoding="utf-8"))["files"])
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    for name in sorted(filter(None, tracked.decode("utf-8").split("\0"))):
        if name in pinned or name in EXEMPT or not (ROOT / name).is_file():
            continue
        data = (ROOT / name).read_bytes()
        if b"\0" in data:  # binary assets (images, archives) and UTF-16 text
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            yield name, 0, "not UTF-8 text, so it cannot be checked"
            continue
        lines = text.splitlines()
        if name.endswith(".json"):
            yield from json_findings(name, lines, strip_locales(json.loads(text)))
            continue
        for number, line in enumerate(lines, 1):
            if CJK.search(line) and MARKER not in line:
                yield name, number, line.strip()


def json_findings(name, lines, document):
    for value in json_strings(document):
        if not CJK.search(value):
            continue
        spellings = {json.dumps(value, ensure_ascii=False)[1:-1], json.dumps(value)[1:-1]}
        numbers = [number for number, line in enumerate(lines, 1) if any(spelling in line for spelling in spellings)]
        for number in numbers or [0]:
            yield name, number, lines[number - 1].strip() if number else value


def main():
    rows = list(findings())
    for name, number, line in rows:
        print(f"{name}:{number}: {line[:160]}")
    print(f"{len(rows)} line(s) with Chinese text in {len({row[0] for row in rows})} file(s)")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
