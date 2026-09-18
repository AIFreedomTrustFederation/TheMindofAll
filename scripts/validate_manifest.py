#!/usr/bin/env python3
"""Validate model manifest paths, sizes, and SHA-256 provenance offline."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "models" / "manifest.json"
LFS_PATTERN = re.compile(
    rb"version https://git-lfs.github.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\n"
    rb"size ([0-9]+)\n?\Z"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_identity(path: Path) -> tuple[int, str, bool]:
    data = path.read_bytes()
    pointer = LFS_PATTERN.fullmatch(data)
    if pointer:
        return int(pointer.group(2)), pointer.group(1).decode("ascii"), True
    return path.stat().st_size, sha256_file(path), False


def validate() -> list[str]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("version") != 1:
        errors.append("manifest version must be 1")

    models = manifest.get("models")
    if not isinstance(models, list):
        return errors + ["manifest models must be an array"]

    seen_models: set[str] = set()
    for model in models:
        model_id = model.get("id")
        if not isinstance(model_id, str) or not ID_PATTERN.fullmatch(model_id):
            errors.append(f"invalid model id: {model_id!r}")
            continue
        if model_id in seen_models:
            errors.append(f"duplicate model id: {model_id}")
        seen_models.add(model_id)

        expected_model_path = Path("models") / model_id
        if model.get("path") != expected_model_path.as_posix():
            errors.append(f"{model_id}: path must be {expected_model_path.as_posix()}")
        model_root = REPO_ROOT / expected_model_path

        seen_files: set[str] = set()
        for record in model.get("files", []):
            value = record.get("path")
            try:
                relative = safe_relative(value)
            except (TypeError, ValueError) as error:
                errors.append(f"{model_id}: {error}")
                continue
            normalized = relative.as_posix()
            if normalized in seen_files:
                errors.append(f"{model_id}: duplicate file record: {normalized}")
                continue
            seen_files.add(normalized)

            artifact = model_root / relative
            if not artifact.is_file():
                errors.append(f"{model_id}: missing file: {normalized}")
                continue

            size, digest, is_pointer = artifact_identity(artifact)
            if record.get("sizeBytes") != size:
                errors.append(f"{model_id}/{normalized}: size mismatch")
            expected_digest = record.get("sha256")
            if not isinstance(expected_digest, str) or not SHA256_PATTERN.fullmatch(expected_digest):
                errors.append(f"{model_id}/{normalized}: invalid SHA-256")
            elif expected_digest != digest:
                errors.append(f"{model_id}/{normalized}: SHA-256 mismatch")
            if bool(record.get("lfsTracked")) != is_pointer:
                errors.append(f"{model_id}/{normalized}: LFS declaration mismatch")

    return errors


def main() -> int:
    try:
        errors = validate()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"manifest validation failed: {error}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    file_count = sum(len(model.get("files", [])) for model in manifest["models"])
    print(f"Validated {len(manifest['models'])} model and {file_count} file records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
