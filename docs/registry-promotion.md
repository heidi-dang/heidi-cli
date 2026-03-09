# Registry and Promotion Policy

The `ModelRegistry` oversees the lifecycle of locally trained models within the Unified Learning Suite.

## Channels

Every model version resides in a channel:
1.  **Experimental:** Scratchpad models, manual tests, or early checkpoints.
2.  **Candidate:** Fully trained models pending formal evaluation.
3.  **Stable:** The active model(s) serving traffic for `/v1/chat/completions`.

## Promotion Policy and Eval Gate

Before a `candidate` can become `stable`, it must pass the `EvalHarness`.

- **Policy Engine:** Configured in `suite.json` (e.g., `promotion_policy: "beat_stable"`).
- **Harness:** Runs the candidate against a set of benchmarks (accuracy, latency, adherence to rules).
- **Gate:** If the candidate underperforms the current stable model (regression), promotion is blocked.
- **Logs:** Evaluations are logged defensively in `state/evals/`.

## CLI Usage

- `heidi learning eval <version_id>`: Run the evaluation harness on a candidate.
- `heidi learning promote <version_id>`: Manually promote a passed candidate to stable.
- `heidi learning rollback`: Revert the stable pointer to the previous known-good model version.
