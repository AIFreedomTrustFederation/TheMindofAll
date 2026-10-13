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

The importer rejects overlapping source and destination paths (including the
same folder, nested folders, and `--replace`), even during `--dry-run`. Import
from a separate source folder outside the target `models/<model-id>` directory.
A dry run does not prove that the later filesystem copy will complete; keep a
backup before replacing a model because replacement is not transactional.
