# Pipeline Curation & Redaction

The Data Pipeline automatically captures runtime history during the agent's operation and processes it into a curated dataset suitable for background retraining.

## Curation Engine
The curation process applies a strict redaction layer to all input before saving.

**Patterns Redacted:**
* OpenAI API Keys
* GitHub Tokens
* Common secret assignments
