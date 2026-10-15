# Scripts

## Import a Model

Use `import_model.py` to copy a local model folder into `models/<model-id>` and
update `models/manifest.json`.

Example:

```powershell
python scripts\import_model.py C:\path\to\model-folder `
  --id local-embedding-model `
  --name "Local Embedding Model" `
  --task embedding `
  --format onnx `
  --runtime transformers.js `
  --license unknown `
  --source-label local
```

Run first with `--dry-run` to validate without copying.

Use `--replace` only when intentionally replacing an existing model entry.

`--replace` requires a source directory separate from the destination model directory.
The importer rejects the destination itself, its parent directories, and its
subdirectories as sources, including during `--dry-run`. This prevents accidental
self-deletion and recursive copies. Replacement is not atomic: keep a backup
until the imported files and manifest have been verified.
