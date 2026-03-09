# Retraining and Hot-Swapping

Phase 4 introduces self-improvement capabilities to the Unified Learning Suite, allowing it to fine-tune new models in the background and hot-swap them into production without API downtime.

## Background Retraining

Retraining is managed by the `RetrainingEngine`.
- **Trigger:** Configured schedule (e.g., daily midnight) or manually via CLI.
- **Process:** It retrieves the latest, highest-quality dataset curated by Phase 3.
- **Asynchronous Execution:** Retraining runs in the background. In an actual environment, it would dispatch to a GPU compute queue.
- **Outcome:** Upon completion, the new model is registered in the `candidate` channel, triggering the Evaluation gate.

## Atomic Hot-Swap

The `HotSwapManager` allows safe deployment of newly promoted stable models.
Instead of restarting the `heidi model serve` process:
1.  **Preload:** The new stable model weights are loaded into VRAM/RAM alongside the current one (if space permits) or queued.
2.  **Switch:** Router configuration is atomically swapped to point the `{model_id}` alias to the new instance.
3.  **Drain:** In-flight requests finishing using the old model.
4.  **Unload:** The old model is cleanly removed from memory.

## CLI Usage

- `heidi learning train-full`: Initiate background retraining immediately.
- `heidi model reload`: Atomically update the internal model routing to align with the registry state.
