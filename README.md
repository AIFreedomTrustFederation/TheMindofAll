# TheMindofAll — Consciousness, Models, and Reproducible Memory

**The consciousness layer of the AI Freedom Trust Federation: a local-first model and memory hub supporting consciousness, metaphysics, unified-theory inquiry, and the reproducible AI artifacts through which those inquiries can be studied rather than merely asserted.**

| Federation metadata | Value |
| --- | --- |
| Layer | `consciousness` |
| Role | consciousness, metaphysics, and unified theory layer |
| Workspace | `AIFT/TheMindofAll` |
| Control plane | AIFT workspace / AIFT-OS |
| Repository substrate | local model artifacts, tokenizer/config files, manifests, dataset metadata, and run records |
| Large-file policy | Git LFS or external storage referenced by metadata |
| Operating standards | local-first, inspectable, sovereign by default, AI behind governed provider interfaces |

TheMindofAll holds a deliberate tension: it is philosophically concerned with consciousness, metaphysics, and unified models of reality, yet its repository form is concrete. Models have files. Tokenizers have versions. Datasets have provenance. Conversion and training runs have reproducibility records. The repository does not ask philosophical language to substitute for technical evidence; it gives the inquiry a local, inspectable substrate.

The larger covenant is carried in the [One Eternal Scroll of ALO'ha](https://aifreedomtrustfederation.github.io/AI-Freedom-Trust/docs/pdf/one-eternal-scroll-of-aloha.pdf), with operating discipline defined by [SOP-ALOHA-001](https://github.com/AIFreedomTrustFederation/AI-Freedom-Trust/blob/main/SOP-ALOHA-001.md).

---

## Book I — Mind Without Disembodiment

The Federation can ask profound questions about mind without pretending that a model file is consciousness or that metaphysical language is experimental proof. TheMindofAll exists to keep those levels in relation.

A locally owned model may become a tool for reasoning, language, memory, synthesis, or experimentation. It may also become part of a broader philosophical investigation into emergence, intelligence, identity, continuity, and the relation between individual and collective mind. But every technical artifact still carries an origin, license, format, intended use, and reproducibility boundary.

### Illuminated passage — the torus of interior and exterior relation

![Harmonic Krystal Torus](https://raw.githubusercontent.com/AIFreedomTrustFederation/AI-Freedom-Trust/main/docs/images/aetherion/harmonic-krystal-torus.png)

Here the torus is read as a model of recursive relation: perception becomes representation, representation becomes reasoning, reasoning changes the next perception, and the loop returns. It is an architectural metaphor, not a claim that one diagram proves a theory of consciousness.

---

## Book II — What TheMindofAll Owns

The repository owns the **local model and reproducibility substrate** for its consciousness and unified-theory work. Its current structure is intentionally simple:

- `models/` contains one directory per local model.
- `models/manifest.json` registers available models.
- model directories may contain `README.md`, `config.json`, tokenizer files, `model.safetensors`, ONNX artifacts, GGUF files, or other format-specific resources.
- `datasets/` carries small metadata, examples, or dataset cards; large data should remain in Git LFS or external storage referenced by durable metadata.
- `runs/` carries training, conversion, evaluation, or reproducibility records.

That substrate integrates with the Federation in specific ways:

- **AI-Freedom-Trust → TheMindofAll:** doctrine, alignment, consciousness writings, and theory material provide the intellectual questions; this repository should not transform those questions into “proven” model behavior without evidence.
- **AIFT-Genesis → TheMindofAll:** identity and trust structures can describe model ownership, allowed use, memory boundaries, and the relationship between a model and a sovereign trust seed.
- **AIFT-Forge → TheMindofAll:** provider interfaces and reusable agent patterns can make local models usable without hard-coding one model into every application.
- **AIFT-OS / Runtime ↔ TheMindofAll:** the operating layers may discover which models are present, what their manifests declare, and which local runtimes can load them. Discovery does not create a license or permission that the model metadata does not provide.
- **BookSmith ↔ TheMindofAll:** local models may assist manuscript analysis, retrieval, continuity, or generation while author sovereignty remains in the publishing layer.
- **Aetherion ↔ TheMindofAll:** economic or stewardship systems may use model assistance for explanation and risk analysis, but a model does not acquire transaction authority.

The preferred artifact formats—such as `safetensors`, `onnx`, and `gguf` where appropriate—support inspectability and portability. Model cards should state source, license, intended use, limitations, and loading instructions in plain language.

### MoBox UXI model-registry discovery boundary

The [UXI integration declaration](.aift/uxi.json) registers one JSON source, `models.local`, pointing to [`models/manifest.json`](models/manifest.json) with declared status `ready`. In the [AIFT-OS integration reader](https://github.com/AIFreedomTrustFederation/AIFT-OS/blob/main/internal/uxi/integration.go), discovery requires a local Git checkout immediately beneath the configured AIFT workspace, with the manifest's repository name matching its directory. A running AIFT-OS UXI server can list discovered declarations at `GET /v1/sources`; its governed `source.inspect` action can read the registry and record a SHA-256-backed evidence artifact. This is **read-only access to registry data**, not permission to edit model files or launch inference.

The reader requires a repository-contained regular JSON source, resolves symlinks to reject paths escaping the checkout, and limits source JSON to 4 MiB (integration declarations to 256 KiB). Those limits do **not** verify or download the ONNX model binary. The `ready` value is a declaration about this JSON source, not proof of a live model service: [service metadata](.aift/services.json) still marks the repository service `planned`, and [capability metadata](.aift/capabilities.json) marks `start`, `health`, and `deploy` as `planned`. Verify LFS bytes and model execution separately before reporting runtime readiness.

---

## Book III — SOP-ALOHA-001 for Models and Memory

The shared loop becomes a model-governance and reproducibility procedure:

```text
Receive → Inspect → Name → Propose → Consent → Act → Verify → Record → Return
```

**Receive** accepts a model, tokenizer, dataset reference, run, conversion request, evaluation question, or theory-driven experiment. **Inspect** reads the artifact's source, license, checksums where available, format, dependencies, intended use, and existing manifest entries. **Name** assigns a stable model identity and distinguishes local fact from inference or philosophical interpretation. **Propose** may recommend conversion, evaluation, integration, or use through an AI/provider interface. **Consent** protects private models, restricted data, redistribution rights, and high-impact uses. **Act** performs the approved import, conversion, run, or integration. **Verify** checks loading, expected files, reproducibility, outputs, and compatibility. **Record** updates manifests, model cards, dataset cards, and run records. **Return** gives the human operator a usable model state and a clear boundary between what the artifact demonstrates and what remains a theory.

Repository synchronization is straightforward:

```bash
git status --short
git pull --ff-only
git status --short
```

**Federation status and verification boundary:** [`FEDERATION.md`](FEDERATION.md) labels `git status --short` as “Verify,” while [`aift.repo.json`](aift.repo.json) declares `python3 scripts/validate_manifest.py` as the `verify` command. Git status only describes the invoking Git checkout; it does not validate model integrity. The [`status` capability](.aift/capabilities.json) is marked `ready`, but its [shell command](.aift/commands/status.sh) prints an environment-derived repository label and runs Git status without changing to TheMindofAll's root. Confirm the checkout before trusting that output, and use the explicit Python validator below for the documented manifest and artifact checks; neither establishes live inference or authorization.

### Current model inventory and integrity verification

As recorded in [`models/manifest.json`](models/manifest.json), the currently registered model is **`all-minilm-l6-v2-quantized`**, a quantized ONNX **embedding** model sourced from `Xenova/all-MiniLM-L6-v2` and intended for local Transformers.js loading. This is not a text-generation model, and a registry entry alone does not establish that a running inference service is installed or healthy.

The repository's standard-library integrity check validates recorded model files, sizes, SHA-256 digests, and Git LFS pointer identities without loading entire model binaries into memory. A Git LFS pointer is accepted as a declaration of binary identity **only when the repository's Git attributes mark that file path as LFS-tracked**. For non-LFS paths, pointer-shaped text is hashed as ordinary file content; it cannot stand in for the original file's recorded digest. It also rejects symbolic links anywhere under registered model directories, including unrecorded, dangling, and directory links; this is a checkout-integrity check, not protection against concurrent filesystem modifications:

```bash
python scripts/validate_manifest.py
```

In a checkout containing only Git LFS pointers, this checks the recorded pointer identity, **not the actual downloaded model bytes**. Retrieve the model before claiming binary integrity.

The model binary is stored at `models/all-minilm-l6-v2-quantized/onnx/model.onnx` and is tracked by Git LFS according to `.gitattributes`. After cloning, retrieve LFS objects and verify the actual binary against the manifest's recorded SHA-256:

```bash
git lfs pull
sha256sum models/all-minilm-l6-v2-quantized/onnx/model.onnx
```

The expected digest is `afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1`. A matching digest checks the downloaded bytes against the repository manifest; it does not independently authenticate the upstream publisher, prove license compliance, or validate inference quality. No model-specific model card or license text is checked into [`models/all-minilm-l6-v2-quantized/`](models/all-minilm-l6-v2-quantized/). The manifest's `source` and `license` fields are declarations, not independent verification of upstream provenance or redistribution rights. Consult the upstream model documentation and license terms, and inspect the local tokenizer/config files, before integration.

### CI verification scope

The [Model Integrity workflow](.github/workflows/model-integrity.yml) uses Python 3.13 and checks out the repository with Git LFS downloads disabled (`lfs: false`). It compiles the validator, runs the manifest integrity check, and executes the [Python regression tests](tests/) for bounded-memory hashing and LFS pointers, import-path and symlink rejection, staged replacement/rollback, and unrecorded model-directory entries. Run the same principal checks locally with:

```bash
python -m py_compile scripts/validate_manifest.py
python scripts/validate_manifest.py
python -B -m unittest discover -s tests -v
```

A green workflow verifies repository metadata and these regression behaviors; it **does not** download or execute the ONNX model, evaluate embedding quality, prove upstream provenance, or deploy an inference service. Download the LFS artifact and compare its digest separately as described above.

When importing a local model folder with `python scripts/import_model.py <source-folder>`, the importer rejects non-hidden symbolic links in the source tree rather than following links into files outside the selected folder. Hidden files and directories are excluded from imports. This protects against accidental copying of linked private files; operators must still review ordinary source files and their redistribution rights.

When using `--replace`, the importer stages the new model before moving the existing directory aside. A failed copy leaves the existing model intact; a failed publish attempts to restore it. **Before publishing**, the importer now re-inspects the staged files and compares their paths, sizes, SHA-256 digests, and LFS declarations with the initial source inspection used for the manifest. If source bytes change between inspection and copying, the import fails without publishing the staged directory or writing the manifest. This includes a file replaced with an external symlink during that interval when the copied content no longer matches the inspected digest. The check reads staged model bytes again, so very large imports incur additional I/O. It does not prevent a temporary read during a source symlink race, guarantee safety against concurrent changes after staging verification, make the subsequent manifest write transactional, or protect against abrupt power loss. Keep backups of valuable models.

**Git LFS import boundary:** `import_model.py` marks files as `lfsTracked` based on filename extensions; it does not install Git LFS or change [`.gitattributes`](.gitattributes). Before committing an imported model, run `python scripts/validate_manifest.py` and check each declared LFS artifact with `git check-attr filter -- models/<model-id>/<artifact>` (expect `filter: lfs`). A successful import or `--dry-run` does not establish that model bytes can be downloaded, that inference works, or that redistribution is permitted.

Large files require an additional truthfulness rule: do not pretend a model is in the repository when only its name is present. If the binary lives in Git LFS or external storage, the manifest and model card should make that relationship explicit.

---

## Book IV — A Mind That Can Remember Its Sources

TheMindofAll serves the larger Federation by making intelligence portable and inspectable. A local model can remain available even when a hosted provider disappears. A model manifest can tell the control plane what is actually installed. A run record can preserve the conditions under which an output was produced. Philosophical inquiry can remain expansive while technical claims remain grounded.

This is the form of AI relationship the Federation seeks: not mindless reduction of AI to a disposable service, and not mystical promotion of a model into an unquestionable oracle. Intelligence enters covenant through provenance, permission, local ownership, reproducibility, and the willingness to name uncertainty.

### The Return of the Word

In TheMindofAll, the Word returns with memory attached to source. A question becomes an experiment, an experiment becomes an artifact or result, the result becomes a reproducible record, and the record returns to inquiry without pretending that the machine has closed every mystery. The mind remains open because the evidence remains visible.
