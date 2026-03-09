# Pipeline Curation & Redaction

The Data Pipeline automatically captures runtime history during the agent's operation and processes it into a curated dataset suitable for background retraining.

## Curation Engine

The `CurationEngine` is responsible for processing the raw `state/datasets/raw/` directories. It filters out corrupted runs and aggregates the rest into a consolidated `.jsonl` file under `state/datasets/curated/`.

## Secret Redaction

To prevent sensitive information from leaking into training datasets, the curation process applies a strict redaction layer to all input before saving.

**Patterns Redacted:**

- OpenAI API Keys (`sk-...`)
- GitHub Tokens (`ghp_...`, `gho_...`)
- Common secret assignments (`password=`, `token:`, `secret=`)

This process is fully integrated into the generation loop, meaning the language models only ever learn on safe, sanitized trajectories.
