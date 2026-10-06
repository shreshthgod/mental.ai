# Step 12 - Packaging

The last step of Phase 1: bundles the two winning models (Steps 9–10's
picks) plus every artifact and code path needed to run them on new raw
text, into one importable module - `package/mental_health_screening/`.

## What was built
- `package/mental_health_screening/preprocessing.py` - Step 4's `clean_text()` + Step 5's contraction-expansion/tokenize/POS-tag/lemmatize logic, copied verbatim for a single string (the pipeline's versions operate on a whole dataframe).
- `package/mental_health_screening/features.py` - Step 7's 38 handcrafted features, copied verbatim for a single (cleaned, lemmatized) text pair.
- `package/mental_health_screening/inference.py` - `MentalHealthScreener` class: loads all bundled artifacts once, exposes `.screen(text) -> dict`.
- `package/mental_health_screening/artifacts/` - the fitted vectorizers, chi2 selector, both winning models, the curated keyword list, the custom emotion lexicon, and `config.json` (exact feature order + thresholds, so nothing is hard-coded twice).
- `package/README.md` - usage, the provenance/screening-not-diagnosis caveat, and the urgency threshold rationale, all in one place for whoever picks this up next.
- `package/requirements.txt` - pinned to the exact versions used throughout this pipeline (see `Reproducibility/requirements.txt`).

## Why copied, not imported
The package doesn't import from the pipeline's Step 4/5/7 scripts - it
copies the same logic into its own files. This is deliberate: the package
needs to be usable on its own (e.g. handed to another developer, deployed
somewhere), without needing this entire `DE_pipeline/` sandbox folder
structure to exist alongside it.

## Verification (not just "it runs")
Copying logic instead of importing it is exactly the kind of change that
can silently drift from the original - so `code/verify_parity.py` doesn't
just check the package runs, it checks the package **matches**: it takes
genuinely raw (pre-Step-4) text from 5 primary_dataset and 5 urgency_dataset
test rows, runs it through the packaged pipeline, and compares every
intermediate value (cleaned text, lemmatized text, final prediction/
probability) against a freshly-computed reference built the pipeline's
original way from the same saved artifacts.

**Result: 10/10 rows matched exactly** (see `code/verify_parity.py`'s
output, saved to this folder). This is what actually justifies calling the
package "done" - not that `run_example.py` printed something plausible.

## Files
- `code/write_config.py` - one-off script that bakes the exact training-time handcrafted-feature column order into `config.json` (run once at packaging time).
- `code/verify_parity.py` - the parity check described above.
- `code/run_example.py` - three example sentences run through the packaged module, for a quick sanity check after install.
- `package/` - the actual deliverable; everything under this folder is self-contained and ready to copy out.

## Phase 1 status
This closes the planned Step 0–12 pipeline for the text-NLP track. What
remains, per the locked division of labor: the transformer fine-tuning
(Step 9c's handed-off GPU script, MentalBERT/DistilBERT - not run in this
sandbox), and Phase 2 (speech), not started.
