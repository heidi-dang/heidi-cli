# Data Pipeline

The Data Pipeline handles the "sensory" and "curation" aspects of the Heidi Unified Learning Suite. It ensures that every run is recorded safely and prepared for future retraining.

## Capture Process

Every interaction with the model host is recorded by the `CaptureEngine`:
1.  **Run Folders:** Data is stored in `state/datasets/raw/YYYY-MM-DD/<run_id>/`.
2.  **Transcripts:** The full message history and the model's response are saved.
3.  **Metadata:** Contextual information (tags, timestamps, task descriptions) is preserved.

## Secret Redaction

To ensure safety, the `CurationEngine` applies strict redaction rules to all captured data before it is moved to the curated pool:
- **API Keys:** Detection of OpenAI, GitHub, and generic key patterns.
- **Passwords:** Pattern matching for common password/token assignments.
- **Recursive JSON Redaction:** Entire data structures are traversed and scrubbed.

## Dataset Curation

The curation process transforms raw experiences into high-quality training data:
- **Filtering:** Noise and corrupted runs are rejected.
- **Export:** Redacted runs are bundled into `.jsonl` datasets in `state/datasets/curated/`.
- **Naming:** Datasets are timestamped for version control.

## CLI Commands

- `heidi learning curate`: Trigger a curation run across all raw data.
- `heidi learning curate --date 2024-03-09`: Curate data from a specific day.
