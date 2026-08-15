from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import sys
from zipfile import BadZipFile, ZipFile

REQUIRED_PREFIX = "AI_Traffic_Light/"
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "datasets",
    "dist",
    "node_modules",
    "outputs",
}
FORBIDDEN_SUFFIXES = {".pt", ".pyc"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate structural safety rules for an AiTL changed-files patch ZIP.")
    parser.add_argument("zip_path", type=Path, help="Patch ZIP to inspect.")
    return parser.parse_args()


def validate_member(name: str) -> list[str]:
    errors: list[str] = []
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute() or ".." in path.parts:
        errors.append(f"unsafe path traversal or absolute member: {name}")
        return errors

    if normalized.endswith("/"):
        return errors

    if not normalized.startswith(REQUIRED_PREFIX):
        errors.append(f"member is outside {REQUIRED_PREFIX}: {name}")

    lowered_parts = {part.lower() for part in path.parts}
    forbidden = sorted(part for part in FORBIDDEN_PARTS if part.lower() in lowered_parts)
    if forbidden:
        errors.append(f"forbidden runtime/generated path in ZIP: {name} ({', '.join(forbidden)})")

    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        errors.append(f"forbidden generated/model file in ZIP: {name}")

    return errors


def main() -> int:
    args = parse_args()
    zip_path = args.zip_path.resolve()
    if not zip_path.is_file():
        print(f"Patch ZIP not found: {zip_path}")
        return 1

    try:
        with ZipFile(zip_path) as archive:
            members = archive.namelist()
            errors: list[str] = []
            if not any(not name.endswith("/") for name in members):
                errors.append("patch ZIP contains no files")

            for name in members:
                errors.extend(validate_member(name))

            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                errors.append(f"ZIP CRC/integrity failure: {corrupt_member}")
    except BadZipFile as exc:
        print(f"Invalid ZIP: {exc}")
        return 1

    if errors:
        print("AiTL patch ZIP validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    file_count = sum(1 for name in members if not name.endswith("/"))
    print(f"AiTL patch ZIP validation OK: {file_count} file(s)")
    print("Note: this validates path/integrity/exclusion rules; compare against git diff to prove changed-files-only scope.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
