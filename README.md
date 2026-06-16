# TheMindofAll

Local-first model hub for The Mind of All.

This repository is intended to store model artifacts, tokenizer files, manifests,
and notes for models we own or build locally. Large binary files are tracked with
Git LFS.

## Layout

- `models/` - model folders, one directory per model.
- `models/manifest.json` - registry of available local models.
- `datasets/` - small metadata, examples, or dataset cards. Large datasets should
  use Git LFS or an external storage location referenced by metadata.
- `runs/` - training or conversion notes and reproducibility records.

## Model Folder Convention

Use this structure for each model:

```text
models/
  model-id/
    README.md
    config.json
    tokenizer.json
    tokenizer_config.json
    model.safetensors
```

For Transformers.js/browser-ready models, keep ONNX files in the same model
folder when applicable.

## Notes

- Do not commit large model files unless Git LFS is active.
- Prefer `safetensors`, `onnx`, or `gguf` over raw framework checkpoints when
  possible.
- Keep model cards concise and include source, license, intended use, and local
  loading instructions.
