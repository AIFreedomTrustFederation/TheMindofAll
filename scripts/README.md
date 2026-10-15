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

Run first with `--dry-run` to validate without copying. The importer rejects
symbolic links to files or directories within the included source tree, rather
than following them and potentially copying files outside the chosen folder.
Hidden files and `__pycache__` directories are ignored by both the inspection
and copy steps. Supply real, local model files instead of symlinks.

Use `--replace` only when intentionally replacing an existing model entry.
The replacement removes the existing model directory before copying, so keep a
backup and do not treat replacement as an atomic operation.

Offline importer regression tests:

```bash
python -B -m unittest discover -s tests -v
```
