#!/usr/bin/env python3
"""Import a local model folder into TheMindofAll.

The script copies a source directory into models/<model-id>, updates
models/manifest.json, and reports files that should be covered by Git LFS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
MANIFEST_PATH = MODELS_DIR / "manifest.json"
LFS_EXTENSIONS = {
    ".bin",
    ".ckpt",
    ".gguf",
    ".model",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".tflite",
    ".wasm",
    ".zip",
    ".tar",
    ".gz",
}
MODEL_ARTIFACT_EXTENSIONS = {
    ".bin",
    ".gguf",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".tflite",
}


@dataclass
class FileRecord:
    path: str
    size_bytes: int
    sha256: str
    lfs_tracked: bool

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "sizeBytes": self.size_bytes,
            "sha256": self.sha256,
            "lfsTracked": self.lfs_tracked,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._").lower()
    if not slug:
        raise ValueError("Model id cannot be empty after normalization.")
    if not re.match(r"^[a-z0-9][a-z0-9._-]*$", slug):
        raise ValueError(f"Invalid model id: {slug}")
    return slug


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_lfs_tracked(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".tar.gz"):
        return True
    return path.suffix.lower() in LFS_EXTENSIONS


def should_ignore(path: Path) -> bool:
    return any(part.startswith(".") or part == "__pycache__" for part in path.parts)


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if should_ignore(relative):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def inspect_source(source: Path) -> tuple[list[FileRecord], list[str]]:
    warnings: list[str] = []
    files = iter_files(source)
    if not files:
        raise ValueError(f"Source folder has no files: {source}")

    has_model_artifact = any(file.suffix.lower() in MODEL_ARTIFACT_EXTENSIONS for file in files)
    if not has_model_artifact:
        warnings.append("No common model artifact found (.onnx, .safetensors, .gguf, .bin, .pt, .tflite).")

    records: list[FileRecord] = []
    for file in files:
        relative = file.relative_to(source).as_posix()
        records.append(
            FileRecord(
                path=relative,
                size_bytes=file.stat().st_size,
                sha256=sha256_file(file),
                lfs_tracked=is_lfs_tracked(file),
            )
        )

    large_untracked = [
        record.path
        for record in records
        if record.size_bytes >= 10 * 1024 * 1024 and not record.lfs_tracked
    ]
    if large_untracked:
        warnings.append(
            "Large files are not covered by current LFS patterns: "
            + ", ".join(large_untracked)
        )

    return records, warnings


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"version": 1, "updatedAt": None, "models": []}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("version") != 1:
        raise ValueError("Unsupported manifest version. Expected version 1.")
    if "models" not in manifest or not isinstance(manifest["models"], list):
        raise ValueError("Manifest must contain a models array.")
    return manifest


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def ensure_safe_destination(destination: Path) -> None:
    resolved_models = MODELS_DIR.resolve()
    resolved_destination = destination.resolve()
    if resolved_destination == resolved_models or resolved_models not in resolved_destination.parents:
        raise ValueError(f"Refusing unsafe destination: {destination}")


def update_manifest(args: argparse.Namespace, files: list[FileRecord], model_id: str) -> dict:
    manifest = load_manifest()
    existing = [model for model in manifest["models"] if model.get("id") == model_id]
    if existing and not args.replace:
        raise ValueError(f"Model already exists in manifest: {model_id}. Use --replace to update it.")

    entry = {
        "id": model_id,
        "name": args.name or model_id,
        "task": args.task,
        "path": f"models/{model_id}",
        "format": args.format,
        "runtime": args.runtime,
        "license": args.license,
        "source": args.source_label,
        "createdAt": utc_now(),
        "notes": args.notes or "",
        "files": [file.as_dict() for file in files],
    }

    manifest["models"] = [model for model in manifest["models"] if model.get("id") != model_id]
    manifest["models"].append(entry)
    manifest["models"].sort(key=lambda model: model["id"])
    manifest["updatedAt"] = utc_now()
    return manifest


def copy_model(source: Path, destination: Path, replace: bool) -> None:
    ensure_safe_destination(destination)
    if destination.exists():
        if not replace:
            raise ValueError(f"Destination already exists: {destination}. Use --replace to overwrite it.")
        shutil.rmtree(destination)

    def ignore_hidden(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name.startswith(".") or name == "__pycache__"}

    shutil.copytree(source, destination, ignore=ignore_hidden)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a local model folder into TheMindofAll.")
    parser.add_argument("source", help="Path to the local model folder to import.")
    parser.add_argument("--id", dest="model_id", help="Stable model id. Defaults to the source folder name.")
    parser.add_argument("--name", help="Human-readable model name.")
    parser.add_argument("--task", default="unknown", help="Model task, such as embedding or text-generation.")
    parser.add_argument("--format", default="other", help="Model format, such as transformers-js, onnx, gguf.")
    parser.add_argument("--runtime", default="transformers.js", help="Expected runtime.")
    parser.add_argument("--license", default="unknown", help="Model license.")
    parser.add_argument("--source-label", default="local", help="Source or lineage label.")
    parser.add_argument("--notes", default="", help="Short notes for the manifest entry.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing model folder and manifest entry.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned changes without copying.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    source = Path(args.source).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        print(f"error: source must be an existing directory: {source}", file=sys.stderr)
        return 2

    try:
        model_id = slugify(args.model_id or source.name)
        destination = MODELS_DIR / model_id
        files, warnings = inspect_source(source)
        manifest = update_manifest(args, files, model_id)

        print(f"model id: {model_id}")
        print(f"source: {source}")
        print(f"destination: {destination}")
        print(f"files: {len(files)}")
        for warning in warnings:
            print(f"warning: {warning}")

        if args.dry_run:
            print("dry run: no files copied and manifest not updated")
            return 0

        copy_model(source, destination, args.replace)
        write_manifest(manifest)
        print(f"imported: {destination}")
        print(f"manifest updated: {MANIFEST_PATH}")
        return 0
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
