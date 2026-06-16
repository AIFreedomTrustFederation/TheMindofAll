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
