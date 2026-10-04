#!/usr/bin/env python3
"""Validate model manifest paths, sizes, and SHA-256 provenance offline."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "models" / "manifest.json"
SCHEMA_PATH = REPO_ROOT / "models" / "manifest.schema.json"
LFS_PATTERN = re.compile(
    rb"version https://git-lfs.github.com/spec/v1\n"
    rb"oid sha256:([0-9a-f]{64})\n"
    rb"size ([0-9]+)\n?\Z"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def matches_json_type(value: object, expected: str) -> bool:
    type_checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return expected in type_checks and type_checks[expected](value)


def validate_property_types(
    value: dict[str, object],
    properties: dict[str, dict[str, object]],
    label: str,
    errors: list[str],
) -> None:
    for field, field_schema in properties.items():
        if field not in value or "type" not in field_schema:
            continue
        expected = field_schema["type"]
        allowed_types = expected if isinstance(expected, list) else [expected]
        if not any(matches_json_type(value[field], item) for item in allowed_types):
            errors.append(f"{label}.{field} must have schema type {expected!r}")


def validate_known_properties(
    value: dict[str, object],
    properties: dict[str, dict[str, object]],
    label: str,
    errors: list[str],
) -> None:
    for field in sorted(value.keys() - properties.keys()):
        errors.append(f"{label} has unknown field: {field}")


def validate_timestamp(
    value: object,
    label: str,
    errors: list[str],
    *,
    require_utc: bool = False,
) -> None:
    if not isinstance(value, str):
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} must be an ISO-8601 timestamp")
        return
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{label} must include a timezone offset")
    elif require_utc and parsed.utcoffset() != timedelta(0):
        errors.append(f"{label} must use UTC")


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


def artifact_identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    pointer = LFS_PATTERN.fullmatch(data)
    if pointer:
        return int(pointer.group(2)), pointer.group(1).decode("ascii")
    return path.stat().st_size, sha256_file(path)


def is_lfs_tracked(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-attr", "filter", "--", path.as_posix()],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.rstrip().endswith(": filter: lfs")


def validate() -> list[str]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    model_schema = schema["properties"]["models"]["items"]
    required_model_fields = model_schema["required"]
    file_schema = model_schema["properties"]["files"]["items"]
    required_file_fields = file_schema["required"]
    validate_known_properties(manifest, schema["properties"], "manifest", errors)
    validate_property_types(manifest, schema["properties"], "manifest", errors)
    validate_timestamp(
        manifest.get("updatedAt"), "manifest.updatedAt", errors, require_utc=True
    )
    if manifest.get("version") != 1:
        errors.append("manifest version must be 1")

    models = manifest.get("models")
    if not isinstance(models, list):
        return errors + ["manifest models must be an array"]

    seen_models: set[str] = set()
    for model in models:
        if not isinstance(model, dict):
            errors.append(f"model entry must be an object: {model!r}")
            continue
        for field in required_model_fields:
            if field not in model:
                errors.append(f"model missing required field: {field}")
        validate_known_properties(model, model_schema["properties"], "model", errors)
        validate_property_types(model, model_schema["properties"], "model", errors)
        validate_timestamp(model.get("createdAt"), "model.createdAt", errors)

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
        if model_root.is_symlink():
            errors.append(f"{model_id}: model directory must not be a symbolic link")
            continue

        seen_files: set[str] = set()
        file_records = model.get("files", [])
        if not isinstance(file_records, list):
            continue
        for record in file_records:
            if not isinstance(record, dict):
                errors.append(f"{model_id}: file record must be an object: {record!r}")
                continue
            for field in required_file_fields:
                if field not in record:
                    errors.append(f"{model_id}: file record missing required field: {field}")
            validate_known_properties(
                record, file_schema["properties"], f"{model_id}.file", errors
            )
            validate_property_types(record, file_schema["properties"], f"{model_id}.file", errors)

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
            if artifact.is_symlink():
                errors.append(f"{model_id}/{normalized}: symbolic links are not allowed")
                continue
            try:
                artifact.resolve().relative_to(model_root.resolve())
            except ValueError:
                errors.append(f"{model_id}/{normalized}: file resolves outside model directory")
                continue

            size, digest = artifact_identity(artifact)
            if record.get("sizeBytes") != size:
                errors.append(f"{model_id}/{normalized}: size mismatch")
            expected_digest = record.get("sha256")
            if not isinstance(expected_digest, str) or not SHA256_PATTERN.fullmatch(expected_digest):
                errors.append(f"{model_id}/{normalized}: invalid SHA-256")
            elif expected_digest != digest:
                errors.append(f"{model_id}/{normalized}: SHA-256 mismatch")
            repository_path = expected_model_path / relative
            if bool(record.get("lfsTracked")) != is_lfs_tracked(repository_path):
                errors.append(f"{model_id}/{normalized}: LFS declaration mismatch")

        actual_files = {
            path.relative_to(model_root).as_posix()
            for path in model_root.rglob("*")
            if path.is_file()
        }
        for unrecorded in sorted(actual_files - seen_files):
            errors.append(f"{model_id}: unrecorded file: {unrecorded}")

    return errors


def main() -> int:
    try:
        errors = validate()
    except (
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
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
